#!/usr/bin/env python3
"""Chat directives — the chats' only levers on system state. Stdlib only.

The dashboard's chats run as subprocesses with ZERO write tools; their only
way to change anything is to end a reply with a directive line that the
SERVER parses and applies through its own audited paths:

- ``COS-ACTION: {"status": "dismissed", ...}`` — the per-task chat updating
  the task under discussion (and only that task — any id in the JSON is
  ignored by design).
- ``COS-AUTH: {"id": "gmail-work", "reason": ...}`` — either chat raising
  the dashboard's authorization popup for a connector account.

Both appliers take their effect functions as parameters (``update_node``,
``enqueue_auth``), so this module stays import-light and the parsing +
policy (allowed statuses/priorities, id pinning, line stripping, the visible
confirmation suffix) is unit-testable without the server.
"""

from __future__ import annotations

import json
import re

_COS_ACTION_RE = re.compile(r"^\s*COS-ACTION:\s*(\{.*\})\s*$", re.MULTILINE)
_COS_AUTH_RE = re.compile(r"^\s*COS-AUTH:\s*(\{.*\})\s*$", re.MULTILINE)

DIRECTIVE_STATUSES = frozenset({"done", "dismissed", "open"})
DIRECTIVE_PRIORITIES = frozenset({"high", "medium", "low"})

CONNECTOR_SETTINGS_URL = "https://claude.ai/settings/connectors"


def apply_chat_directives(entry_id, output, update_node):
    """Parse and apply COS-ACTION lines. ``update_node(entry_id, note=...,
    priority=..., status=...) -> (ok, message)`` is the server's locked,
    audited updater. Returns the reply text with directive lines stripped
    and a visible confirmation appended for every applied change."""
    applied = []
    for m in _COS_ACTION_RE.finditer(output):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        status = str(d.get("status") or "").strip().lower() or None
        if status not in DIRECTIVE_STATUSES:
            status = None
        priority = str(d.get("priority") or "").strip().lower() or None
        if priority not in DIRECTIVE_PRIORITIES:
            priority = None
        note = d.get("note") if isinstance(d.get("note"), str) else None
        if not (status or priority or note):
            continue
        try:
            ok, msg = update_node(entry_id, note=note, priority=priority,
                                  status=status)
        except Exception as exc:
            ok, msg = False, "directive failed: %r" % (exc,)
        if ok and msg != "no changes":
            applied.append(msg)
    cleaned = _COS_ACTION_RE.sub("", output).strip()
    if applied:
        cleaned = (cleaned + "\n\n" if cleaned else "") + "✅ " + "; ".join(applied)
    return cleaned


def apply_auth_directives(output, enqueue_auth):
    """Parse and apply COS-AUTH lines. ``enqueue_auth(account_id, reason,
    auth_url) -> request-or-None`` is accounts.enqueue_auth_request bound to
    the dashboard dir (returns None for permanently-declined accounts, which
    are therefore never re-asked). Returns the cleaned reply text."""
    if enqueue_auth is None:
        return output
    queued = []
    for m in _COS_AUTH_RE.finditer(output):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        account_id = str(d.get("id") or "").strip()
        if not account_id:
            continue
        try:
            req = enqueue_auth(account_id, str(d.get("reason") or ""),
                               str(d.get("auth_url") or "") or CONNECTOR_SETTINGS_URL)
        except Exception:
            continue
        if req is not None:
            queued.append(account_id)
    cleaned = _COS_AUTH_RE.sub("", output).strip()
    if queued:
        cleaned = ((cleaned + "\n\n" if cleaned else "")
                   + "🔐 authorization popup raised for: " + ", ".join(queued))
    return cleaned
