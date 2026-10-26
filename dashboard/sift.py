#!/usr/bin/env python3
"""Sift new items down to the ones that could need the user, without a model.

A daily check should not read every newsletter, CI message and other team's
ticket. Before any model sees a batch of new items, ``sift`` keeps an item
when one of these is true and drops it otherwise:

  direct      a DM or group DM; mail addressed to the user by a person; the
              user's own sent mail and messages
  mention     the user's handle, full name, an address, or a greeting by
              first name ("Hi Dana")
  thread      it belongs to a thread, ticket, PR, doc or event the user is in,
              or that an open task already came from
  assigned    a ticket or PR assigned to, reported by, or requesting review
              from the user; anything in the user's own repos
  broadcast   an @channel / @here, or mail to everyone that says it is
              required, in a channel or list the user is in
  task_ref    it names a ticket key (PLAT-322), PR (#430) or invoice number
              that an open task's name or sources contain
  platform    a platform notice that carries a person's words or an action on
              the user: "new message from", "invited you", "requested your
              review", "assigned to you", security alerts
  own_file    a doc the user owns

Everything else (bulk mail, bots, channel chatter, other people's tickets) is
dropped and counted by reason, so the check can say what it skipped. Rules use
only the user's identities and open tasks, never a list of senders, so they
work on any account. Items use the shape of the benchmark's connectors
(evals/longrun/BENCHMARK.md), which the direct fetchers also produce.
"""

from __future__ import annotations

import json
import re

PLATFORM = re.compile(
    r"new message from|sent you a message|messaged you|invited you|invited to interview|"
    r"you've been invited|requested your review|review requested|assigned to you|"
    r"mentioned you|replied to you|commented on your|security alert|secret scanning|"
    r"credential|access key|payment (released|received|sent)|you received \$|offer",
    re.I)
REQUIRED = re.compile(r"\b(everyone|all (staff|employees|engineers|hands)|mandatory|required|must)\b", re.I)
BULK_FROM = re.compile(r"no-?reply|do-?not-?reply|notifications?@|newsletter|digest|mailer|"
                       r"news@|deals@|promo|marketing@|bounce", re.I)
BULK_BODY = re.compile(r"unsubscribe|you are receiving this|manage (your )?preferences|"
                       r"view (it )?in (your )?browser", re.I)
# role addresses that machines send from (RFC 2142 and common practice), not people
ROLE = {"alerts", "alert", "service", "billing", "receipts", "orders", "order", "tracking", "support",
        "hello", "info", "team", "events", "members", "renewals", "notify", "notifications",
        "notification", "news", "newsletter", "marketing", "calendar", "updates", "account",
        "accounts-noreply", "statements", "security", "verify", "help", "contact", "store", "shop"}
KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{1,6}\b")
NUM_RE = re.compile(r"(?<![\w-])#\d{2,6}\b|\bINV-\d+\b", re.I)
DOMAIN_RE = re.compile(r"\b[a-z0-9][a-z0-9-]{1,40}\.(?:app|com|io|dev|blog|net|org|co|ai|example)\b", re.I)


def _addr(s):
    m = re.search(r"<([^>]+)>", s or "")
    return (m.group(1) if m else (s or "")).strip().lower()


def _text(i):
    c = i.get("connector")
    if c == "gmail":
        return "%s\n%s" % (i.get("subject") or "", i.get("body") or "")
    if c == "slack":
        return i.get("text") or ""
    if c == "jira":
        f = i.get("fields") or {}
        return " ".join([i.get("key") or "", f.get("summary") or "", f.get("description") or ""]
                        + [x.get("body") or "" for x in i.get("comments") or []])
    if c == "github":
        return " ".join([i.get("title") or "", i.get("body") or ""]
                        + [x.get("body") or "" for x in i.get("comments") or []])
    if c == "calendar":
        return "%s %s" % (i.get("summary") or "", i.get("description") or "")
    if c == "drive":
        return "%s %s" % (i.get("name") or "", i.get("content") or "")
    return json.dumps(i)


def thread_key(i):
    c = i.get("connector")
    if c == "slack":
        return ("slack", i.get("channel"), i.get("thread_ts") or i.get("id"))
    if c == "gmail":
        return ("gmail", i.get("threadId") or i.get("id"))
    if c == "jira":
        return ("jira", i.get("key"))
    if c == "github":
        return ("github", i.get("repo"), i.get("number"))
    if c == "drive":
        return ("drive", i.get("name"))
    if c == "calendar":
        return ("calendar", i.get("summary"), i.get("organizer"))
    return (c, i.get("id"))


class Sifter:
    def __init__(self, user, channels=None, open_tasks=None, known_items=None):
        """user: {"name", "email", "other_emails", "slack", "github"}.
        channels: Slack directory rows with is_member / is_muted.
        open_tasks: rows with "name" and "sources" (item ids).
        known_items: earlier items, so threads the user is in are known."""
        self.name = (user.get("name") or "").strip()
        self.first = self.name.split()[0] if self.name else ""
        self.emails = {e.lower() for e in [user.get("email")] + list(user.get("other_emails") or []) if e}
        self.slack = user.get("slack") or ""
        self.gh = user.get("github") or ""
        self.member = {c["name"] for c in channels or [] if c.get("is_member")}
        self.mention_re = re.compile(
            "|".join(x for x in [
                re.escape("@" + self.slack) + r"\b" if self.slack else "",
                re.escape(self.name) if self.name else "",
                r"\b(hi|hey|hello|dear|thanks|thank you),?\s+" + re.escape(self.first) + r"\b" if self.first else "",
                r"^" + re.escape(self.first) + r"\b[,:!]" if self.first else "",
                "|".join(re.escape(e) for e in self.emails)] if x), re.I | re.M)
        self.threads = set()
        self.task_threads = set()
        self.refs = set()
        by_id = {i["id"]: i for i in known_items or []}
        for i in known_items or []:
            if self._is_user(i) or self.mention_re.search(_text(i)):
                self.threads.add(thread_key(i))
        for t in open_tasks or []:
            text = t.get("name") or ""
            for s in t.get("sources") or []:
                if s in by_id:
                    self.task_threads.add(thread_key(by_id[s]))
                    text += " " + _text(by_id[s])
            self.refs |= {k.upper() for k in KEY_RE.findall(text)}
            self.refs |= {k.upper() for k in NUM_RE.findall(text)}
            own = {e.split("@")[-1] for e in self.emails}
            self.refs |= {d.upper() for d in DOMAIN_RE.findall(t.get("name") or "") if d.lower() not in own}

    def _is_user(self, i):
        c = i.get("connector")
        if c == "slack":
            return i.get("user") == self.slack
        if c == "gmail":
            return "SENT" in (i.get("labelIds") or []) or _addr(i.get("from")) in self.emails
        if c == "github":
            return i.get("user") == self.gh
        return False

    def reason(self, i):
        """The first reason to keep ``i``, or None to drop it."""
        c = i.get("connector")
        text = _text(i)
        tk = thread_key(i)
        if self._is_user(i):
            return "direct"
        if c == "slack" and str(i.get("channel", "")).startswith(("D-", "mpdm-", "D0", "G0")):
            return "direct"
        if self.mention_re.search(text):
            return "mention"
        if tk in self.threads:
            return "thread"
        if tk in self.task_threads:
            return "thread"
        refs = ({k.upper() for k in KEY_RE.findall(text)} | {k.upper() for k in NUM_RE.findall(text)}
                | {d.upper() for d in DOMAIN_RE.findall(text)})
        if refs & self.refs:
            return "task_ref"
        if c == "gmail":
            frm = i.get("from") or ""
            bulk = bool(BULK_FROM.search(frm) or BULK_BODY.search(i.get("body") or ""))
            if PLATFORM.search(i.get("subject") or ""):
                return "platform"
            to = {_addr(x) for x in (i.get("to") or []) + (i.get("cc") or [])}
            role = _addr(frm).split("@")[0] in ROLE
            if not bulk and not role and to & self.emails:
                return "direct"
            dom = {e.split("@")[-1] for e in self.emails}
            if _addr(frm).split("@")[-1] in dom and REQUIRED.search(text):
                return "broadcast"
            return None
        if c == "slack":
            t = i.get("text") or ""
            if ("@channel" in t or "@here" in t) and i.get("channel") in self.member and REQUIRED.search(t):
                return "broadcast"
            return None
        if c == "jira":
            f = i.get("fields") or {}
            people = {f.get("assignee"), f.get("reporter")} | set(f.get("watchers") or [])
            if self.name in people:
                return "assigned"
            for ch in i.get("changelog") or []:
                if self.name in (ch.get("from"), ch.get("to")):
                    return "assigned"
            return None
        if c == "github":
            if self.gh and (self.gh in (i.get("requested_reviewers") or []) or self.gh in (i.get("assignees") or [])
                            or str(i.get("repo", "")).startswith(self.gh + "/")):
                return "assigned"
            if PLATFORM.search(i.get("title") or ""):
                return "platform"
            return None
        if c == "calendar":
            blob = json.dumps([i.get("organizer"), i.get("attendees")]).lower()
            return "direct" if any(e in blob for e in self.emails) else None
        if c == "drive":
            if any((o or "").lower() in self.emails for o in i.get("owners") or []):
                return "own_file"
            return None
        return None

    def sift(self, items):
        kept, dropped = [], {}
        for i in items:
            r = self.reason(i)
            if r:
                kept.append(i)
                self.threads.add(thread_key(i))
            else:
                k = i.get("connector", "?")
                dropped[k] = dropped.get(k, 0) + 1
        return kept, dropped


def summary_line(kept, dropped):
    total = len(kept) + sum(dropped.values())
    return "kept %d of %d new items (%s skipped)" % (
        len(kept), total, ", ".join("%d %s" % (n, k) for k, n in sorted(dropped.items())) or "none")
