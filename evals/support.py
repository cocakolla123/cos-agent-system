#!/usr/bin/env python3
"""Source-support check: does the cited source actually SUPPORT the item?

The original citation metric only asked whether a gold source id appears as a
substring of ``attrs.evidence``. That is an id-presence check, not a support
check. This module checks, for every predicted open Action:

1. cited ids exist:   every source-id-shaped token in ``attrs.evidence``
                      names a file in the scenario's ``sources/``;
2. text support:      the action's own name+note content words appear in the
                      union of the cited sources' text;
3. due support:       a predicted due date is stated by some cited source,
                      in any of: ISO form, "Oct 6" / "October 6" (with or
                      without a year), "10/6", or a relative phrase such as
                      "by Friday", "tomorrow", "end of week", resolved
                      against that source's OWN date;
4. party support:     the ``blocked_on`` person, when predicted, appears in a
                      cited source (name fragment, handle, or address).

Checker v2 (2026-10-05, same day, after the mandated 30-item hand check):
v1 agreed with the human judgment on only 8 of 30 sampled verdicts; every
miss was mechanical, not semantic. Three disclosed fixes, applied uniformly
and re-reported next to the v1 numbers: (a) header fields (from, to, user,
channel, assignee, author, attendees) are part of a source's text, since
parties live there; (b) text support is computed on the action's NAME (the
claim itself), not the model's explanatory note, with tokens of length >= 3;
(c) the date normalizer resolves "within/in N days|weeks" durations.

Decision rules, fixed in advance of any rescoring (2026-10-05):
- content words = lowercased alphanumeric tokens of length >= 3 from the
  action's NAME (fallback: note when the name is empty), minus stopwords;
- TEXT_SUPPORT_THRESHOLD = 0.5 (at least half the content words must appear
  in the cited text);
- an action with no content words after filtering counts as text-unsupported;
- components 3 and 4 apply only when a due date / blocked_on is predicted;
  "supported" overall means every applicable component passed;
- paraphrase can defeat the keyword overlap, so the checker's verdicts are
  themselves audited by hand on a sample and the agreement rate is reported
  next to every number (see the results report).
"""

from __future__ import annotations

import datetime
import re

CHECKER_VERSION = 2
TEXT_SUPPORT_THRESHOLD = 0.5

SOURCE_ID_RE = re.compile(r"\b(?:em|sl|tk|cal|doc|pr)-\d{3}\b")

_STOP = {
    "with", "from", "this", "that", "them", "they", "have", "has", "the",
    "and", "for", "about", "your", "their", "will", "been", "into", "when",
    "send", "sent", "needs", "need", "task", "action", "item", "follow",
    "complete", "finish", "before", "after", "until", "reply", "respond",
    "you", "are", "not", "was", "her", "his", "its", "per", "via", "due",
    "get", "all", "still", "awaiting", "await",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,}")

MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ("January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"))}
for _m in list(MONTHS):
    MONTHS[_m[:3]] = MONTHS[_m]

WEEKDAYS = {d.lower(): i for i, d in enumerate(
    ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
     "Sunday"))}
for _d in list(WEEKDAYS):
    WEEKDAYS[_d[:3]] = WEEKDAYS[_d]


def content_words(text):
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOP}


def source_text(item):
    parts = []
    # headers included (checker v2): parties live in from/to/user/channel
    for k in ("subject", "body", "text", "summary", "title", "name",
              "from", "user", "channel", "assignee", "author", "key",
              "repo"):
        v = item.get(k)
        if v:
            parts.append(str(v))
    for k in ("to", "attendees"):
        for v in item.get(k) or []:
            parts.append(str(v))
    for c in item.get("comments") or []:
        parts.append(str(c.get("author", "")))
        parts.append(str(c.get("text", "")))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# date normalizer
# ---------------------------------------------------------------------------

def _next_weekday(anchor, wd, strict=True):
    delta = (wd - anchor.weekday()) % 7
    if delta == 0 and strict:
        delta = 7
    return anchor + datetime.timedelta(days=delta)


def dates_in_text(text, anchor_iso):
    """All calendar dates a text states, as ISO strings, resolving relative
    phrases against ``anchor_iso`` (the source's own date)."""
    out = set()
    low = (text or "").lower()
    try:
        anchor = datetime.date.fromisoformat(str(anchor_iso)[:10])
    except ValueError:
        anchor = None

    for m in re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})\b", low):
        try:
            out.add(datetime.date(int(m.group(1)), int(m.group(2)),
                                  int(m.group(3))).isoformat())
        except ValueError:
            pass

    # "Oct 6", "October 6, 2026", "Oct. 6th"
    for m in re.finditer(
            r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(20\d{2}))?\b",
            low):
        mon = MONTHS.get(m.group(1))
        if not mon:
            continue
        day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else (anchor.year if anchor else None)
        if year is None:
            continue
        try:
            d = datetime.date(year, mon, day)
        except ValueError:
            continue
        # an un-yeared month that lands far before the anchor means next year
        if not m.group(3) and anchor and (anchor - d).days > 180:
            d = datetime.date(year + 1, mon, day)
        out.add(d.isoformat())

    # numeric 10/6 (US order, this dataset's convention), anchor year
    if anchor:
        for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})\b", low):
            try:
                out.add(datetime.date(anchor.year, int(m.group(1)),
                                      int(m.group(2))).isoformat())
            except ValueError:
                pass

        if "today" in low:
            out.add(anchor.isoformat())
        if "tomorrow" in low:
            out.add((anchor + datetime.timedelta(days=1)).isoformat())
        if re.search(r"\bend of (the )?(this )?week\b|\beow\b", low):
            out.add(_next_weekday(anchor, WEEKDAYS["friday"], strict=False)
                    .isoformat())
        if re.search(r"\bend of (the )?month\b", low):
            nxt = (anchor.replace(day=28) + datetime.timedelta(days=4))
            out.add((nxt - datetime.timedelta(days=nxt.day)).isoformat())
        # durations: "within two weeks", "in 3 days" (checker v2)
        nums = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        for m in re.finditer(r"\b(?:within|in)\s+(\d{1,2}|%s)\s+"
                             r"(day|week)s?\b" % "|".join(nums), low):
            n = nums.get(m.group(1)) or int(m.group(1))
            days = n * (7 if m.group(2) == "week" else 1)
            out.add((anchor + datetime.timedelta(days=days)).isoformat())
        for m in re.finditer(r"\b(?:by|on|before|this|next)\s+"
                             r"(monday|tuesday|wednesday|thursday|friday|"
                             r"saturday|sunday)\b", low):
            out.add(_next_weekday(anchor, WEEKDAYS[m.group(1)],
                                  strict=False).isoformat())
    return out


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------

def check_action(action_node, sources_by_id):
    """Verdict dict for one predicted open Action node."""
    attrs = action_node.get("attrs", {}) or {}
    evidence = str(attrs.get("evidence") or "")
    cited = sorted(set(SOURCE_ID_RE.findall(evidence)))
    ids_ok = bool(cited) and all(c in sources_by_id for c in cited)
    cited_items = [sources_by_id[c] for c in cited if c in sources_by_id]
    cited_text = " ".join(source_text(i) for i in cited_items).lower()

    # the claim is the NAME; the note is the model's commentary (checker v2)
    words = content_words(action_node.get("name")
                          or str(attrs.get("note") or ""))
    hits = {w for w in words if w in cited_text}
    overlap = len(hits) / float(len(words)) if words else 0.0
    text_ok = bool(cited_items) and bool(words) and overlap >= TEXT_SUPPORT_THRESHOLD

    due = str(attrs.get("due") or "")[:10] or None
    due_ok = None
    if due:
        stated = set()
        for item in cited_items:
            stated |= dates_in_text(source_text(item), item.get("date", ""))
        due_ok = due in stated

    party = str(attrs.get("blocked_on") or "").strip()
    party_ok = None
    if party:
        frags = [f for f in re.split(r"[^a-z0-9]+", party.lower()) if len(f) >= 3]
        party_ok = bool(frags) and all(f in cited_text for f in frags) \
            if cited_items else False
        if frags and cited_items and not party_ok:
            # any one fragment (surname, handle, org) in the cited text passes
            party_ok = any(f in cited_text for f in frags)

    applicable = [ids_ok, text_ok] + [x for x in (due_ok, party_ok)
                                      if x is not None]
    return {
        "action": action_node["id"],
        "cited_ids": cited,
        "ids_ok": ids_ok,
        "text_overlap": round(overlap, 3),
        "text_ok": text_ok,
        "due_ok": due_ok,
        "party_ok": party_ok,
        "supported": all(applicable),
        "checker": CHECKER_VERSION,
    }


def check_scenario(open_action_nodes, sources_by_id):
    return [check_action(a, sources_by_id) for a in open_action_nodes]
