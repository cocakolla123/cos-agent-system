#!/usr/bin/env python3
"""Direct connections: read new items from your accounts without Claude Code.

Each connection is read-only and keeps a bookmark, so a check fetches only
what arrived since the last one:

  imap     any mailbox over IMAP with an app password (Gmail, Outlook, Fastmail...)
           bookmark: the last UID per folder (reset if UIDVALIDITY changes)
  slack    a Slack user token (xoxp-...): channels, group DMs and DMs you are in
           bookmark: the newest message timestamp per conversation
  jira     Jira Cloud with your email and an API token
           bookmark: the newest "updated" time
  github   a personal access token: issues and PRs that involve you
           bookmark: the newest "updated_at"
  ical     a calendar's private iCal link (Google Calendar: "Secret address in iCal format")
           bookmark: the newest LAST-MODIFIED
  folder   folders on this computer (Zoom's local recordings, Downloads, a project...)
           bookmark: each file's modified time; meeting transcripts come out
           as their own kind, cleaned to who said what (transcripts.py)
  zoom     Zoom cloud recordings through a Server-to-Server OAuth app (read-only
           recording scope): each new meeting's transcript
           bookmark: the meetings already read

Items come out in the same shape as the benchmark's connectors
(evals/longrun/BENCHMARK.md), so dashboard/sift.py and the extraction step
treat a real account and the test world the same way.

Settings live in ``connections.json`` next to the config: who you are (names,
addresses, handles) and one entry per connection, secrets included. The file is
mode 0600, git-ignored and excluded from publishing; ``status`` never returns a
secret. Bookmarks live in ``fetch-state.json``; new items are appended to
``inbox/YYYY-MM-DD.jsonl`` so later checks know your threads.
"""

from __future__ import annotations

import base64
import datetime as _dt
import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import stat
import urllib.parse
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = "connections.json"
STATE_FILE = "fetch-state.json"
INBOX_DIR = "inbox"
TIMEOUT = 30
MAX_PER_SOURCE = 2000

KINDS = {
    "imap": {"label": "Email (IMAP)", "fields": ["host", "port", "user", "password", "folders", "workspace"],
             "secret": ["password"], "connector": "gmail"},
    "slack": {"label": "Slack", "fields": ["token", "workspace"], "secret": ["token"], "connector": "slack"},
    "jira": {"label": "Jira Cloud", "fields": ["base_url", "email", "token", "workspace"], "secret": ["token"],
             "connector": "jira"},
    "github": {"label": "GitHub", "fields": ["token", "login", "workspace"], "secret": ["token"],
               "connector": "github"},
    "ical": {"label": "Calendar (iCal link)", "fields": ["url", "workspace"], "secret": ["url"],
             "connector": "calendar"},
    "folder": {"label": "Folders on this computer", "fields": ["path", "keep", "workspace"], "secret": [],
               "connector": "file"},
    "zoom": {"label": "Zoom cloud recordings", "fields": ["account_id", "client_id", "client_secret", "workspace"],
             "secret": ["client_secret"], "connector": "transcript"},
}
OPTIONAL = ("port", "folders", "workspace", "login", "keep")


class ConnectionError_(RuntimeError):
    pass


# ---------------------------------------------------------------- settings

def _path(config_dir, name):
    return os.path.join(config_dir, name)


def load(config_dir):
    try:
        with open(_path(config_dir, CONFIG_FILE)) as f:
            data = json.load(f) or {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("me", {})
    data.setdefault("sources", [])
    return data


def _write_private(path, obj):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def save_me(config_dir, me):
    data = load(config_dir)
    clean = {}
    for k in ("name", "slack", "github"):
        if (me.get(k) or "").strip():
            clean[k] = me[k].strip()
    emails = [e.strip() for e in (me.get("emails") or []) if e and "@" in e]
    if emails:
        clean["emails"] = emails
    data["me"] = clean
    _write_private(_path(config_dir, CONFIG_FILE), data)
    return clean


def upsert_source(config_dir, src):
    """Add or update one connection. A blank secret keeps the saved one."""
    kind = src.get("kind")
    if kind not in KINDS:
        raise ConnectionError_("unknown connection kind %r" % kind)
    sid = re.sub(r"[^a-z0-9-]+", "-", (src.get("id") or kind).lower()).strip("-") or kind
    data = load(config_dir)
    old = next((s for s in data["sources"] if s["id"] == sid), {})
    row = {"id": sid, "kind": kind}
    for f in KINDS[kind]["fields"]:
        v = src.get(f)
        if isinstance(v, str):
            v = v.strip()
        if f in KINDS[kind]["secret"] and not v:
            v = old.get(f)
        if v not in (None, "", []):
            row[f] = v
    missing = [f for f in KINDS[kind]["fields"] if f not in row and f not in OPTIONAL]
    if missing:
        raise ConnectionError_("missing: %s" % ", ".join(missing))
    data["sources"] = [s for s in data["sources"] if s["id"] != sid] + [row]
    _write_private(_path(config_dir, CONFIG_FILE), data)
    return sid


def remove_source(config_dir, sid):
    data = load(config_dir)
    data["sources"] = [s for s in data["sources"] if s["id"] != sid]
    _write_private(_path(config_dir, CONFIG_FILE), data)
    state = load_state(config_dir)
    state.pop(sid, None)
    save_state(config_dir, state)


def status(config_dir):
    """Connections without secrets, with their bookmark and last result."""
    data, state = load(config_dir), load_state(config_dir)
    rows = []
    for s in data["sources"]:
        st = state.get(s["id"]) or {}
        rows.append({"id": s["id"], "kind": s["kind"], "label": KINDS[s["kind"]]["label"],
                     "account": s.get("user") or s.get("email") or s.get("login") or s.get("path") or "",
                     "workspace": s.get("workspace") or "", "last_ok": st.get("last_ok"),
                     "last_error": st.get("last_error"), "last_count": st.get("last_count")})
    return {"me": data["me"], "sources": rows}


def load_state(config_dir):
    try:
        with open(_path(config_dir, STATE_FILE)) as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def save_state(config_dir, state):
    path = _path(config_dir, STATE_FILE)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def user_identity(config_dir):
    """The ``user`` frame sift.Sifter and the extraction prompt expect."""
    me = load(config_dir)["me"]
    emails = list(me.get("emails") or [])
    for s in load(config_dir)["sources"]:
        if s["kind"] == "imap" and s.get("user") and s["user"] not in emails:
            emails.append(s["user"])
    return {"name": me.get("name", ""), "email": emails[0] if emails else "",
            "other_emails": emails[1:], "slack": me.get("slack", ""),
            "github": me.get("github") or next((s.get("login") for s in load(config_dir)["sources"]
                                               if s["kind"] == "github" and s.get("login")), "")}


# ---------------------------------------------------------------- helpers

def _iso(ts):
    return ts.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(url, headers=None, opener=None):
    req = urllib.request.Request(url, headers=dict(headers or {}, Accept="application/json"))
    with (opener or urllib.request.urlopen)(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_text(url, opener=None):
    req = urllib.request.Request(url)
    with (opener or urllib.request.urlopen)(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def _decode(h):
    try:
        return str(email.header.make_header(email.header.decode_header(h or "")))
    except Exception:  # noqa: BLE001  (malformed headers are common in real mail)
        return h or ""


def _body(msg, limit=6000):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition") or ""):
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", "replace")[:limit]
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", "replace")
                return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))[:limit]
        return ""
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", "replace")[:limit]


# ---------------------------------------------------------------- fetchers

def fetch_imap(src, cursor, _imap=None):
    """New mail since the last UID in each folder. Returns (items, cursor)."""
    folders = src.get("folders") or ["INBOX"]
    if isinstance(folders, str):
        folders = [f.strip() for f in folders.split(",") if f.strip()]
    conn = _imap or imaplib.IMAP4_SSL(src["host"], int(src.get("port") or 993))
    items, cursor = [], dict(cursor or {})
    try:
        conn.login(src["user"], src["password"])
        for folder in folders:
            typ, data = conn.select('"%s"' % folder, readonly=True)
            if typ != "OK":
                continue
            validity = (conn.response("UIDVALIDITY")[1] or [b""])[0]
            validity = validity.decode() if isinstance(validity, bytes) else str(validity or "")
            fc = cursor.get(folder) or {}
            last = int(fc.get("uid") or 0) if fc.get("validity") == validity else 0
            if not last:
                # first run: start from the newest message, read the past 14 days only
                since = (_dt.date.today() - _dt.timedelta(days=14)).strftime("%d-%b-%Y")
                typ, data = conn.uid("SEARCH", None, "SINCE", since)
            else:
                typ, data = conn.uid("SEARCH", None, "UID", "%d:*" % (last + 1))
            # oldest first, and at most MAX_PER_SOURCE a check: the bookmark stops at the
            # last one read, so a backlog is read over several checks, never skipped
            uids = sorted(int(x) for x in (data[0] or b"").split() if int(x) > last)[:MAX_PER_SOURCE]
            sent = "sent" in folder.lower()
            for uid in uids:
                typ, msgdata = conn.uid("FETCH", str(uid), "(BODY.PEEK[] X-GM-THRID)")
                raw = next((p[1] for p in msgdata or [] if isinstance(p, tuple)), None)
                if not raw:
                    continue
                meta = (msgdata[0][0] if isinstance(msgdata[0], tuple) else b"").decode("ascii", "ignore")
                thrid = re.search(r"X-GM-THRID (\d+)", meta)
                msg = email.message_from_bytes(raw)
                try:
                    when = email.utils.parsedate_to_datetime(msg.get("Date"))
                except (TypeError, ValueError):
                    when = _dt.datetime.now(_dt.timezone.utc)
                refs = (msg.get("References") or msg.get("In-Reply-To") or "").split()
                items.append({
                    "connector": "gmail", "id": "em-%s-%s-%d" % (src["id"], re.sub(r"\W", "", folder)[:8], uid),
                    "date": _iso(when), "account": src["user"],
                    "labelIds": ["SENT"] if sent else ["INBOX"],
                    "from": _decode(msg.get("From")),
                    "to": [a for _, a in email.utils.getaddresses([msg.get("To") or ""]) if a],
                    "cc": [a for _, a in email.utils.getaddresses([msg.get("Cc") or ""]) if a],
                    "subject": _decode(msg.get("Subject")), "body": _body(msg),
                    "threadId": "th-" + (thrid.group(1) if thrid else (refs[0] if refs else (msg.get("Message-ID") or str(uid))))})
            if uids:
                cursor[folder] = {"uid": max(uids), "validity": validity}
            else:
                cursor.setdefault(folder, {"uid": last, "validity": validity})
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001
            pass
    return items, cursor


def fetch_slack(src, cursor, opener=None, base="https://slack.com/api"):
    """New messages in conversations you are in, newest first per channel."""
    h = {"Authorization": "Bearer " + src["token"]}
    cursor = dict(cursor or {})
    names, users = {}, {}
    convs, nxt = [], ""
    while True:
        q = urllib.parse.urlencode({"types": "public_channel,private_channel,mpim,im",
                                    "exclude_archived": "true", "limit": 200, "cursor": nxt})
        r = _http_json("%s/users.conversations?%s" % (base, q), h, opener)
        if not r.get("ok"):
            raise ConnectionError_("slack: %s" % r.get("error"))
        convs += r.get("channels") or []
        nxt = (r.get("response_metadata") or {}).get("next_cursor") or ""
        if not nxt:
            break

    def uname(uid):
        if uid and uid not in users:
            try:
                u = _http_json("%s/users.info?user=%s" % (base, uid), h, opener).get("user") or {}
                users[uid] = (u.get("name") or uid, u.get("real_name") or u.get("name") or uid)
            except Exception:  # noqa: BLE001
                users[uid] = (uid, uid)
        return users.get(uid, (uid, uid))

    items = []
    first = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=14)).timestamp()
    for c in convs:
        cid = c["id"]
        if c.get("is_im"):
            name = "D-%s" % uname(c.get("user"))[0]
        elif c.get("is_mpim"):
            name = "mpdm-" + (c.get("name") or cid)
        else:
            name = "#" + (c.get("name") or cid)
        names[cid] = name
        oldest = cursor.get(cid) or ("%.6f" % first)
        try:
            msgs = _slack_pages(base, "conversations.history", {"channel": cid, "oldest": oldest}, h, opener)
        except ConnectionError_:
            continue
        for m in list(msgs):        # thread replies arrive only through conversations.replies
            if m.get("reply_count") and float(m.get("latest_reply") or 0) > float(oldest):
                try:
                    rep = _slack_pages(base, "conversations.replies",
                                       {"channel": cid, "ts": m["ts"], "oldest": oldest}, h, opener)
                except ConnectionError_:
                    rep = []
                msgs += [x for x in rep if x.get("ts") != m["ts"]]
        # oldest first; past the cap, the bookmark stops at the last one kept
        msgs = sorted({m["ts"]: m for m in msgs if m.get("ts")}.values(), key=lambda m: float(m["ts"]))
        msgs = msgs[:MAX_PER_SOURCE]
        newest = oldest
        for m in msgs:
            ts = m.get("ts")
            if float(ts) > float(newest):
                newest = ts
            if m.get("subtype") in ("channel_join", "channel_leave"):
                continue
            handle, real = uname(m.get("user")) if m.get("user") else (m.get("username") or "bot", m.get("username") or "bot")
            items.append({"connector": "slack", "id": "sl-%s-%s" % (cid, ts), "channel": name,
                          "date": _iso(_dt.datetime.fromtimestamp(float(ts), _dt.timezone.utc)),
                          "user": handle, "user_name": real, "text": m.get("text") or "",
                          "thread_ts": ("sl-%s-%s" % (cid, m["thread_ts"])) if m.get("thread_ts") and m.get("thread_ts") != ts else None,
                          "reactions": [x.get("name") for x in m.get("reactions") or []]})
        cursor[cid] = newest
    return items, cursor


SLACK_MAX_PAGES = 50


def _slack_pages(base, method, params, h, opener):
    """Every page of a Slack history or replies call (200 a page)."""
    out, nxt = [], ""
    for _ in range(SLACK_MAX_PAGES):
        q = dict(params, limit=200)
        if nxt:
            q["cursor"] = nxt
        r = _http_json("%s/%s?%s" % (base, method, urllib.parse.urlencode(q)), h, opener)
        if not r.get("ok"):
            raise ConnectionError_("slack %s: %s" % (method, r.get("error")))
        out += r.get("messages") or []
        nxt = (r.get("response_metadata") or {}).get("next_cursor") or ""
        if not (r.get("has_more") or nxt) or not nxt:
            break
    return out


JIRA_MAX_PAGES = 50


def fetch_jira(src, cursor, opener=None):
    auth = base64.b64encode(("%s:%s" % (src["email"], src["token"])).encode()).decode()
    h = {"Authorization": "Basic " + auth}
    since = cursor.get("updated") if cursor else None
    if not since:
        since = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=14)).strftime("%Y-%m-%d %H:%M")
    jql = 'updated >= "%s" ORDER BY updated ASC' % since
    issues, start, token = [], 0, ""
    for _ in range(JIRA_MAX_PAGES):
        params = {"jql": jql, "maxResults": 100,
                  "fields": "summary,status,assignee,reporter,duedate,priority,description,updated,comment"}
        if token:
            params["nextPageToken"] = token
        else:
            params["startAt"] = start
        r = _http_json("%s/rest/api/3/search?%s" % (src["base_url"].rstrip("/"), urllib.parse.urlencode(params)),
                       h, opener)
        page = r.get("issues") or []
        issues += page
        token = r.get("nextPageToken") or ""
        start += len(page)
        if token:
            continue
        if not page or r.get("isLast") or start >= int(r.get("total") or 0):
            break
    items, newest = [], since
    for iss in issues[:MAX_PER_SOURCE]:
        f = iss.get("fields") or {}
        upd = f.get("updated") or ""
        name = lambda x: (x or {}).get("displayName") if x else None  # noqa: E731
        desc = f.get("description")
        if isinstance(desc, dict):        # Atlassian document format
            desc = " ".join(re.findall(r'"text":\s*"([^"]*)"', json.dumps(desc)))
        items.append({"connector": "jira", "id": "jr-%s-%s" % (iss.get("key"), re.sub(r"\D", "", upd)[:14]),
                      "date": upd[:19] + "Z" if upd else _iso(_dt.datetime.now(_dt.timezone.utc)), "key": iss.get("key"),
                      "fields": {"summary": f.get("summary"), "status": (f.get("status") or {}).get("name"),
                                 "assignee": name(f.get("assignee")), "reporter": name(f.get("reporter")),
                                 "duedate": f.get("duedate"), "priority": (f.get("priority") or {}).get("name"),
                                 "description": desc or "", "watchers": [], "updated": upd},
                      "comments": [{"author": name(c.get("author")), "body": " ".join(re.findall(r'"text":\s*"([^"]*)"', json.dumps(c.get("body"))))
                                    if isinstance(c.get("body"), dict) else c.get("body")}
                                   for c in ((f.get("comment") or {}).get("comments") or [])[-5:]],
                      "changelog": []})
        if upd:
            newest = max(newest, upd[:16].replace("T", " "))
    return items, {"updated": newest}


def fetch_github(src, cursor, opener=None, base="https://api.github.com"):
    h = {"Authorization": "Bearer " + src["token"], "X-GitHub-Api-Version": "2022-11-28"}
    login = src.get("login") or _http_json(base + "/user", h, opener).get("login")
    since = (cursor or {}).get("updated_at") or _iso(_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=14))
    q = urllib.parse.quote("involves:%s updated:>=%s" % (login, since))
    found = []
    for page in range(1, 11):         # the search API returns at most 1,000 results
        r = _http_json("%s/search/issues?q=%s&sort=updated&order=asc&per_page=100&page=%d" % (base, q, page),
                       h, opener)
        batch = r.get("items") or []
        found += batch
        if len(batch) < 100:
            break
    items, newest = [], since
    for it in found[:MAX_PER_SOURCE]:
        repo = "/".join((it.get("repository_url") or "").split("/")[-2:])
        upd = it.get("updated_at") or since
        items.append({"connector": "github", "id": "gh-%s-%s-%s" % (repo.replace("/", "-"), it.get("number"), re.sub(r"\D", "", upd)),
                      "date": upd, "repo": repo, "type": "pull_request" if it.get("pull_request") else "issue",
                      "number": it.get("number"), "title": it.get("title"), "state": it.get("state"),
                      "user": (it.get("user") or {}).get("login"), "body": (it.get("body") or "")[:4000],
                      "assignees": [a.get("login") for a in it.get("assignees") or []],
                      "requested_reviewers": [], "requested_teams": [], "comments": [], "merged": False,
                      "labels": [x.get("name") for x in it.get("labels") or []], "updated_at": upd})
        newest = max(newest, upd)
    return items, {"updated_at": newest, "login": login}


def _ical_events(text):
    text = re.sub(r"\r?\n[ \t]", "", text)        # unfold
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        ev = {}
        for line in block.strip().splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            name, _, params = k.partition(";")
            ev.setdefault(name.upper(), []).append((params, v.strip()))
        yield ev


def _ical_time(v):
    v = v.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            t = _dt.datetime.strptime(v, fmt)
            return _iso(t.replace(tzinfo=_dt.timezone.utc))
        except ValueError:
            continue
    return None


def fetch_ical(src, cursor, opener=None):
    text = _http_text(src["url"], opener)
    since = (cursor or {}).get("modified") or ""
    items, newest = [], since
    for ev in _ical_events(text):
        get = lambda k: (ev.get(k) or [("", "")])[0][1]  # noqa: E731
        mod = _ical_time(get("LAST-MODIFIED") or get("DTSTAMP") or "") or ""
        if since and mod <= since:
            continue
        start = _ical_time(get("DTSTART"))
        items.append({"connector": "calendar", "id": "cal-%s-%s" % (src["id"], re.sub(r"\W", "", get("UID"))[:40] + re.sub(r"\D", "", mod)),
                      "date": mod or start or _iso(_dt.datetime.now(_dt.timezone.utc)),
                      "summary": get("SUMMARY").replace("\\,", ",").replace("\\n", " "),
                      "start": start, "end": _ical_time(get("DTEND")),
                      "organizer": get("ORGANIZER").replace("mailto:", "").replace("MAILTO:", ""),
                      "attendees": [v.replace("mailto:", "").replace("MAILTO:", "") for _, v in ev.get("ATTENDEE") or []],
                      "description": get("DESCRIPTION").replace("\\n", "\n").replace("\\,", ",")[:2000],
                      "status": get("STATUS").lower() or "confirmed", "recurrence": get("RRULE") or None,
                      "_mod": mod})
    # oldest change first; past the cap, the bookmark stops at the last one kept
    items.sort(key=lambda i: i["_mod"])
    items = items[:MAX_PER_SOURCE]
    newest = max([since] + [i["_mod"] for i in items])
    for i in items:
        i.pop("_mod")
    return items, {"modified": newest}


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "Library", ".Trash", ".cache", "site-packages"}
FILE_MAX = 5_000_000
FIRST_DAYS = 14


def _paths(src):
    p = src.get("path") or ""
    return [os.path.expanduser(x.strip()) for x in (p if isinstance(p, list) else p.split(",")) if x.strip()]


def fetch_folder(src, cursor, now=None):
    """New or changed files under each folder. Meeting transcripts come out as
    ``transcript`` items (cleaned text); other text files as ``file`` items.
    The first check only looks back FIRST_DAYS days. Nothing leaves this
    machine here: reading a folder is a local walk with no model."""
    import hashlib
    import transcripts
    seen = dict((cursor or {}).get("files") or {})
    first = not seen and not (cursor or {}).get("started")
    since = ((now or _dt.datetime.now(_dt.timezone.utc)) - _dt.timedelta(days=FIRST_DAYS)).timestamp()
    items, alive = [], {}
    for root_dir in _paths(src):
        if not os.path.isdir(root_dir):
            raise ConnectionError_("no such folder: %s" % root_dir)
        base_depth = root_dir.rstrip(os.sep).count(os.sep)
        for d, dirs, names in os.walk(root_dir):
            dirs[:] = [x for x in dirs if not x.startswith(".") and x not in SKIP_DIRS]
            if d.count(os.sep) - base_depth >= 5:
                dirs[:] = []
            for n in names:
                p = os.path.join(d, n)
                if n.startswith(".") or os.path.splitext(n)[1].lower() not in transcripts.TEXT_EXT:
                    continue
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size > FILE_MAX:
                    continue
                mark = "%d:%d" % (int(st.st_mtime), st.st_size)
                alive[p] = mark
                if seen.get(p) == mark or (first and st.st_mtime < since):
                    continue
                text = transcripts.read_text(p)
                if not text.strip():
                    continue
                fid = hashlib.sha1(("%s|%s" % (p, mark)).encode()).hexdigest()[:12]
                date = _iso(_dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc))
                rel = os.path.relpath(p, root_dir)
                if transcripts.looks_like_transcript(p, text):
                    body = transcripts.clean(text)
                    items.append({"connector": "transcript", "id": "tr-" + fid, "date": date,
                                  "title": _meeting_title(rel), "path": p,
                                  "speakers": transcripts.speakers(text)[:20], "text": body,
                                  "origin": "file"})
                else:
                    items.append({"connector": "file", "id": "file-" + fid, "date": date, "name": rel,
                                  "path": p, "content": text[:6000],
                                  "keep_all": (src.get("keep") or "").lower() in ("all", "everything", "yes")})
    items.sort(key=lambda i: i["date"])
    for i in items[MAX_PER_SOURCE:]:      # past the cap: not marked read, so the next check takes them
        if seen.get(i["path"]):
            alive[i["path"]] = seen[i["path"]]
        else:
            alive.pop(i["path"], None)
    return items[:MAX_PER_SOURCE], {"files": alive, "started": True}


def _meeting_title(rel):
    """Zoom names a local recording's folder "2026-10-26 14.00.12 Topic name"."""
    parts = rel.split(os.sep)
    folder = parts[-2] if len(parts) > 1 else os.path.splitext(parts[-1])[0]
    m = re.match(r"\d{4}-\d{2}-\d{2}[ _]\d{2}\.\d{2}\.\d{2}\s+(.+?)(?:\s+\d{6,})?$", folder)
    return (m.group(1) if m else folder).strip()


ZOOM_API = "https://api.zoom.us/v2"
ZOOM_OAUTH = "https://zoom.us/oauth/token"


def fetch_zoom(src, cursor, opener=None, base=ZOOM_API, oauth=ZOOM_OAUTH, now=None):
    """Transcripts of cloud recordings since the last check. Needs a
    Server-to-Server OAuth app with the read-only recording scope."""
    import transcripts
    opener = opener or urllib.request.urlopen
    auth = base64.b64encode(("%s:%s" % (src["client_id"], src["client_secret"])).encode()).decode()
    req = urllib.request.Request("%s?grant_type=account_credentials&account_id=%s" % (
        oauth, urllib.parse.quote(src["account_id"])), data=b"", method="POST",
        headers={"Authorization": "Basic " + auth})
    with opener(req, timeout=TIMEOUT) as r:
        token = json.loads(r.read().decode("utf-8"))["access_token"]
    hdr = {"Authorization": "Bearer " + token}
    now = now or _dt.datetime.now(_dt.timezone.utc)
    done = list((cursor or {}).get("done") or [])
    frm = (cursor or {}).get("from") or (now - _dt.timedelta(days=FIRST_DAYS)).date().isoformat()
    items, token_next = [], ""
    while True:
        url = "%s/users/me/recordings?page_size=100&from=%s&to=%s%s" % (
            base, frm, now.date().isoformat(), ("&next_page_token=" + token_next) if token_next else "")
        page = _http_json(url, hdr, opener)
        for m in page.get("meetings") or []:
            mid = str(m.get("uuid") or m.get("id"))
            files = [f for f in m.get("recording_files") or []
                     if f.get("file_type") == "TRANSCRIPT" and f.get("status", "completed") == "completed"]
            if mid in done or not files:
                continue
            dl = urllib.request.Request(files[0]["download_url"], headers=hdr)
            with opener(dl, timeout=TIMEOUT) as r:
                vtt = r.read().decode("utf-8", "replace")
            items.append({"connector": "transcript", "id": "zoom-%s" % re.sub(r"\W", "", mid)[:24],
                          "date": m.get("start_time") or _iso(now), "title": m.get("topic") or "Zoom meeting",
                          "host": m.get("host_email") or "", "speakers": transcripts.speakers(vtt)[:20],
                          "text": transcripts.clean(vtt), "origin": "zoom",
                          "duration_min": m.get("duration")})
            done.append(mid)
        token_next = page.get("next_page_token") or ""
        if not token_next:
            break
    # look back two days next time: a recording can take hours to process
    frm = (now - _dt.timedelta(days=2)).date().isoformat()
    return items, {"done": done[-500:], "from": frm}


FETCHERS = {"imap": fetch_imap, "slack": fetch_slack, "jira": fetch_jira, "github": fetch_github, "ical": fetch_ical,
            "folder": fetch_folder, "zoom": fetch_zoom}


def fetch_all(config_dir, only=None, _fetchers=None, now=None, commit=True):
    """Fetch every connection (or ``only`` these ids). A bookmark moves only
    when its fetch succeeds. Returns {"items": [...], "per_source": {...}}.

    commit=False saves nothing: the new bookmarks travel in the result
    ("_state") and ``commit_fetch`` saves them, with the items, once the
    caller has put what it needs somewhere safe. A dry run never commits."""
    fetchers = _fetchers or FETCHERS
    data, state = load(config_dir), load_state(config_dir)
    out, per = [], {}
    for src in data["sources"]:
        if only and src["id"] not in only:
            continue
        st = dict(state.get(src["id"]) or {})
        try:
            items, cursor = fetchers[src["kind"]](src, st.get("cursor") or {})
            for i in items:
                i.setdefault("source", src["id"])
                if src.get("workspace"):
                    i.setdefault("workspace_hint", src["workspace"])
            out += items
            st.update({"cursor": cursor, "last_ok": _iso(now or _dt.datetime.now(_dt.timezone.utc)),
                       "last_count": len(items), "last_error": None})
            per[src["id"]] = {"ok": True, "count": len(items)}
        except Exception as e:  # noqa: BLE001  (one broken account must not stop the others)
            st["last_error"] = str(e)[:300]
            per[src["id"]] = {"ok": False, "error": str(e)[:300]}
        state[src["id"]] = st
    res = {"items": sorted(out, key=lambda x: x.get("date") or ""), "per_source": per,
           "_state": state, "_day": (now or _dt.datetime.now(_dt.timezone.utc)).date().isoformat()}
    if commit:
        commit_fetch(config_dir, res)
    return res


def commit_fetch(config_dir, res):
    """Save a fetch's bookmarks and append its items to the inbox."""
    if res.get("_committed"):
        return
    if res["items"]:
        d = _path(config_dir, INBOX_DIR)
        os.makedirs(d, mode=0o700, exist_ok=True)
        path = os.path.join(d, res["_day"] + ".jsonl")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            for i in res["items"]:
                f.write(json.dumps(i, ensure_ascii=False) + "\n")
    save_state(config_dir, res["_state"])
    res["_committed"] = True


def recent_items(config_dir, days=30, now=None):
    """Items fetched in the past ``days`` days (for thread context)."""
    d = _path(config_dir, INBOX_DIR)
    if not os.path.isdir(d):
        return []
    cut = ((now or _dt.datetime.now(_dt.timezone.utc)).date() - _dt.timedelta(days=days)).isoformat()
    out = []
    for name in sorted(os.listdir(d)):
        if name.endswith(".jsonl") and name[:10] >= cut:
            with open(os.path.join(d, name)) as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    return out
