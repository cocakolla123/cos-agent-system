#!/usr/bin/env python3
"""AI OS append-only audit log (V2, milestone M8, issue #32). Stdlib only.

The approval queue (`approval-queue.md`) is a *live working file* — entries are
mutated in place and archived. For an immutable record of what actually happened
(who changed which entry from what to what, and when), this module keeps a
separate **append-only** JSONL log at ``<workspace>/audit-log.jsonl``. It is
never rewritten, only appended, so it survives archival/clearing of the queue and
gives a clean trail for debugging or compliance.

One line per event::

    {"ts": "2026-07-16T18:03:00Z", "entry_id": "PROJ-1:ticket_update",
     "from": "pending", "to": "approved", "actor": "dashboard", "detail": "..."}
"""

from __future__ import annotations

import json
import os

import graph  # for iso() timestamp helper

LOG_FILE = "audit-log.jsonl"


def record(workspace_dir, entry_id, to_status, from_status=None, actor="system",
           detail="", now=None):
    """Append one audit event. Never raises (best-effort logging)."""
    event = {
        "ts": graph.iso(now),
        "entry_id": entry_id,
        "from": from_status,
        "to": to_status,
        "actor": actor,
        "detail": detail,
    }
    try:
        os.makedirs(workspace_dir, exist_ok=True)
        with open(os.path.join(workspace_dir, LOG_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return event


def read_log(workspace_dir, entry_id=None, limit=None):
    """Read audit events (optionally filtered by entry_id), newest last.

    Tolerates a corrupt line rather than failing the whole read.
    """
    path = os.path.join(workspace_dir, LOG_FILE)
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry_id is None or ev.get("entry_id") == entry_id:
                out.append(ev)
    if limit is not None:
        out = out[-limit:]
    return out


if __name__ == "__main__":
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else "."
    for ev in read_log(ws):
        print("%s  %-28s %s -> %s  (%s)" % (
            ev["ts"], ev["entry_id"], ev.get("from"), ev["to"], ev["actor"]))
