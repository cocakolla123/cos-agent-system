#!/usr/bin/env python3
"""Per-run tracing: what each check did, and what happened to every item.

One JSON line per run in ``runs.jsonl`` next to the config (owner-only):
the run id, kind, start/end, outcome, each step's duration, every source's
result (count, complete or why not, duplicates, error), the fate of every
item by id, model cost and tokens, and the retry count. It never holds
message text: items appear by id only, and error strings pass through
``redact``. ``explain`` joins the fates with the local inbox (which already
holds the text, on this machine) so a user can ask about a message by its
subject and see why it was missed, delayed, rejected or deduplicated.

Model calls made inside a run are tagged with its id through ``CURRENT``
(a context variable, so a server thread never inherits another's run).
"""

from __future__ import annotations

import contextvars
import datetime as _dt
import json
import os
import re
import time
import uuid

RUNS_FILE = "runs.jsonl"
MAX_BYTES = 5 * 1024 * 1024        # past this the oldest half is dropped
CURRENT = contextvars.ContextVar("cos_run", default=None)

_SECRETS = [
    (re.compile(r"xox[abposr]-[A-Za-z0-9-]+"), "xox?-<redacted>"),
    (re.compile(r"(github_pat_|gh[pousr]_)[A-Za-z0-9_]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(bearer|basic|token)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 <redacted>"),
    (re.compile(r"(?i)(password|passwd|pwd|secret|api[_-]?key|token)=([^&\s]+)"), r"\1=<redacted>"),
    (re.compile(r"://[^/\s:@]+:[^/\s@]+@"), "://<redacted>@"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
    (re.compile(r"\b[A-Za-z0-9+/_-]{32,}={0,2}\b"), "<redacted>"),
]


def redact(text, limit=300):
    """An error message with secrets, credentials and addresses masked."""
    s = str(text or "")
    for pat, rep in _SECRETS:
        s = pat.sub(rep, s)
    return s[:limit]


def _now():
    return _dt.datetime.now(_dt.timezone.utc)


class Run:
    def __init__(self, config_dir, kind, now=None):
        self.config_dir = config_dir
        self.rec = {"run_id": uuid.uuid4().hex[:12], "kind": kind,
                    "started": (now or _now()).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "steps": [], "sources": {}, "items": {}, "retries": 0}
        self._t0 = time.monotonic()
        self._step_t = self._t0
        self._token = None

    @property
    def run_id(self):
        return self.rec["run_id"]

    def __enter__(self):
        self._token = CURRENT.set(self)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self.finish("failed", error=exc)
        elif "outcome" not in self.rec:
            self.finish("ok")
        CURRENT.reset(self._token)
        return False

    def step(self, name, **fields):
        t = time.monotonic()
        row = {"name": name, "ms": int((t - self._step_t) * 1000)}
        row.update({k: v for k, v in fields.items() if v is not None})
        self.rec["steps"].append(row)
        self._step_t = t

    def sources(self, per_source):
        for sid, r in (per_source or {}).items():
            row = {k: r.get(k) for k in ("ok", "count", "complete", "incomplete", "duplicates")
                   if r.get(k) is not None}
            if r.get("error"):
                row["error"] = redact(r["error"])
            if r.get("incomplete"):
                row["incomplete"] = redact(r["incomplete"])
            self.rec["sources"][sid] = row

    def item(self, item_id, fate, **fields):
        if not item_id:
            return
        row = {"fate": fate}
        row.update({k: v for k, v in fields.items() if v is not None})
        self.rec["items"][str(item_id)] = row

    def model_call(self, usage_rec):
        """Called by usage.record for a model call made inside this run."""
        m = self.rec.setdefault("model", {"calls": 0, "cost_usd": 0.0, "input_tokens": 0,
                                          "output_tokens": 0, "cache_read_tokens": 0})
        m["calls"] += 1
        for k in ("cost_usd", "input_tokens", "output_tokens", "cache_read_tokens"):
            m[k] = round(m[k] + (usage_rec.get(k) or 0), 6)

    def finish(self, outcome, error=None, **fields):
        self.rec["outcome"] = outcome
        self.rec["ended"] = _now().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.rec["duration_ms"] = int((time.monotonic() - self._t0) * 1000)
        if error is not None:
            self.rec["error"] = redact("%s: %s" % (type(error).__name__, error)
                                       if isinstance(error, BaseException) else error)
        self.rec.update({k: v for k, v in fields.items() if v is not None})
        _append(self.config_dir, self.rec)


def start(config_dir, kind, now=None):
    return Run(config_dir, kind, now=now)


def _append(config_dir, rec):
    path = os.path.join(config_dir, RUNS_FILE)
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
            with open(path) as f:
                lines = f.readlines()
            tmp = path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.writelines(lines[len(lines) // 2:])
            os.replace(tmp, path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass        # tracing must never break the run it describes


def runs(config_dir, limit=None):
    out = []
    try:
        with open(os.path.join(config_dir, RUNS_FILE)) as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out[-limit:] if limit else out


FATE_TEXT = {
    "dropped": "skipped by the free sift: no rule marked it as needing you",
    "duplicate": "already delivered by an earlier check (a re-read at the bookmark), not a new event",
    "waiting": "kept, waiting for the next batch read (not urgent)",
    "backoff": "kept, waiting: the last model read failed, so reads are backing off",
    "read_failed": "kept, but the model read failed; it stays waiting and is retried",
    "task": "read; became a task",
    "no_task": "read; the model found nothing you need to do",
    "quarantined": "read; the task the model proposed was malformed and was quarantined, not dropped",
}


def explain(config_dir, query, days=90):
    """What happened to the messages matching ``query`` (an item id, or words
    from a subject, sender or text), newest first: each with its history of
    fates across runs. Reads only local files."""
    q = str(query or "").strip().lower()
    if not q:
        return []
    try:
        import connections
        inbox = connections.recent_items(config_dir, days=days)
    except Exception:  # noqa: BLE001
        inbox = []
    matches = {}
    for i in inbox:
        blob = " ".join(str(i.get(k) or "") for k in ("id", "subject", "from", "title", "text", "summary",
                                                         "user_name", "channel", "key")).lower()
        if q in blob:
            matches[i.get("id")] = i
    hist = {}
    for r in runs(config_dir):
        for iid, row in (r.get("items") or {}).items():
            if iid in matches or q == iid.lower():
                hist.setdefault(iid, []).append(dict(row, run_id=r.get("run_id"), at=r.get("started"),
                                                     text=FATE_TEXT.get(row.get("fate"), row.get("fate"))))
    out = []
    for iid in set(matches) | set(hist):
        i = matches.get(iid) or {}
        label = i.get("subject") or i.get("title") or (i.get("text") or "")[:80] or iid
        h = hist.get(iid) or []
        out.append({"id": iid, "label": label, "from": i.get("from") or i.get("user_name") or "",
                    "date": i.get("date") or "", "history": h,
                    "verdict": h[-1]["text"] if h else
                    "fetched, but no traced check has looked at it yet (it predates tracing, or the "
                    "check that fetched it has not finished)"})
    out.sort(key=lambda x: x["date"], reverse=True)
    if not out:
        out.append({"id": None, "label": query, "history": [],
                    "verdict": "no fetched message matches. A direct connection never saw it: its account "
                               "is not connected directly, or it is older than the first sync window."})
    return out[:20]
