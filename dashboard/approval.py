#!/usr/bin/env python3
"""Approval-queue rules enforced in code, not in model instructions.

Source content (mail, Slack, tickets, documents) reaches the queue only as
text inside a model's draft. Two things keep it data:

  writing   ``format_entry`` writes every field on one line (or, for a
            multi-line draft, as indented ``  * `` continuation lines), so
            text from a source can never start a ``### <id>`` header or a
            ``- status:`` line of its own. A new entry is always pending.
  approving ``approval_tool`` picks the single tool an approval may use from
            the STORED entry (its action_type and the account it was drafted
            from), never from the request, and refuses when that tool belongs
            to a different connector account.

Stdlib only; runs on Python 3.9 (poll_direct) and 3.12 (server).
"""

from __future__ import annotations

import re

_ID_UNSAFE = re.compile(r"[^A-Za-z0-9._:-]+")
_KEY = re.compile(r"^\w+$")
# one tool name, as Claude Code's --allowedTools reads it: no list, no
# pattern, no argument rule (a comma or "(...)" would widen the grant)
TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def one_line(value):
    """Any value as a single line: newlines and runs of space collapse."""
    return " ".join(str(value if value is not None else "").split())


def safe_id(value, limit=80):
    """An entry id that cannot carry a newline, a space or markup."""
    s = _ID_UNSAFE.sub("-", str(value or "")).strip("-")[:limit]
    return s or "entry"


def unique_id(base, taken):
    """``base`` made safe, with -2, -3... appended until it is not in
    ``taken`` (a set it is then added to). Two entries sharing an id would let
    an approval of one run the other's call."""
    base = safe_id(base)
    eid, n = base, 1
    while eid in taken:
        n += 1
        eid = "%s-%d" % (base, n)
    taken.add(eid)
    return eid


def queue_ids(text):
    """Every entry id in a queue file's text."""
    return {e["id"] for e in parse_queue(text)}


def multi_line(value):
    """A multi-line draft (an outline, steps): first line, then each further
    line indented as ``  * <line>``, which the parser folds back into the
    same field and which can never be read as a header or a new field."""
    lines = [one_line(l) for l in str(value or "").splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        return ""
    return lines[0] + "".join("\n  * " + l for l in lines[1:])


def format_entry(entry_id, fields, multiline=()):
    """One queue entry as text, starting with a newline. ``fields`` is an
    ordered dict; keys must be plain words. Keys in ``multiline`` keep their
    lines (indented); every other value is flattened to one line."""
    out = ["", "### " + safe_id(entry_id)]
    for k, v in fields.items():
        if not _KEY.match(str(k)):
            raise ValueError("bad queue field name: %r" % (k,))
        out.append("- %s: %s" % (k, multi_line(v) if k in multiline else one_line(v)))
    return "\n".join(out) + "\n"


def parse_queue(text):
    """'### <id>' + '- key: value' blocks after the first '---' line.
    Continuation lines fold into the prior field; a nested bullet keeps its
    own line. (The server's parse_blocks is this function.)"""
    parts = re.split(r"^---\s*$", text or "", maxsplit=1, flags=re.MULTILINE)
    text = parts[1] if len(parts) > 1 else (text or "")
    entries = []
    for block in re.split(r"^### ", text, flags=re.MULTILINE)[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        fields = {"id": lines[0].strip()}
        current = None
        for line in lines[1:]:
            m = re.match(r"^-\s*(\w+):\s*(.*)$", line)
            if m:
                current = m.group(1)
                fields[current] = m.group(2).strip()
            elif current and line.strip():
                stripped = line.strip()
                if stripped.startswith(("- ", "* ")) and fields[current]:
                    fields[current] += "\n" + stripped
                else:
                    fields[current] += " " + stripped
        entries.append(fields)
    return entries


# ---------------------------------------------------------------- approving

def _slug(v):
    return re.sub(r"[^a-z0-9]+", "-", str(v or "").strip().lower()).strip("-")


def _accounts(config):
    out = []
    for a in (config or {}).get("connector_accounts") or []:
        if isinstance(a, dict) and a.get("id"):
            out.append({"id": _slug(a["id"]), "account": str(a.get("account") or "").strip().lower(),
                        "tool_prefix": str(a.get("tool_prefix") or "")})
    return out


def entry_account(entry, config):
    """(reference, account) for the account an entry was drafted from.
    ``reference`` is what the entry says (its ``account`` field, slugged, or
    its ``account_address``); ``account`` is the matching connector account
    from config, or None."""
    ref = _slug(entry.get("account"))
    addr = str(entry.get("account_address") or "").strip().lower()
    accts = _accounts(config)
    hit = next((a for a in accts if ref and a["id"] == ref), None)
    if hit is None and addr:
        hit = next((a for a in accts if a["account"] and a["account"] == addr), None)
    return (ref or addr), hit


def owner_of(tool, config):
    """The connector account whose tool namespace ``tool`` is in, or None."""
    for a in _accounts(config):
        if a["tool_prefix"] and tool.startswith(a["tool_prefix"]):
            return a
    return None


def approval_tool(entry, config):
    """The single tool an approval of ``entry`` may run, as (tool, None), or
    (None, why) when it must not run. Everything is read from the stored
    entry and config; nothing comes from the request."""
    if not entry:
        return None, "no such entry"
    if entry.get("status") != "pending":
        return None, "entry is %s, not pending" % (entry.get("status") or "missing a status")
    at = entry.get("action_type") or ""
    spec = ((config or {}).get("action_tools") or {}).get(at)
    if not spec:
        return None, "no executable tool for action_type %r" % at
    ref, acct = entry_account(entry, config)
    if isinstance(spec, dict):
        # per-account tools: {"gmail-work": "mcp__gmail_work__send", ...}
        key = acct["id"] if acct else ref
        tool = spec.get(key) if key else spec.get("default")
        if not tool:
            return None, ("no %s tool is configured for account %r" % (at, key) if key
                          else "the entry does not say which account it was drafted from")
    else:
        tool = spec
    tool = str(tool).strip()
    if not TOOL_NAME.match(tool):
        return None, "action_tools[%r] must name exactly one tool, got %r" % (at, tool)
    # a tool in a configured account's namespace acts as that account; one
    # outside every namespace (a calendar tool, a single-account install's
    # sender) belongs to no account and crosses no boundary
    owner = owner_of(tool, config)
    if owner is not None and ref and owner["id"] != ref and (acct is None or acct["id"] != owner["id"]):
        return None, "%s belongs to %s, but the entry was drafted from %s" % (tool, owner["id"], ref)
    if owner is not None and not ref:
        bound = [a for a in _accounts(config) if a["tool_prefix"]]
        if len(bound) > 1:
            return None, ("%s belongs to %s, and the entry does not say which account it "
                          "was drafted from" % (tool, owner["id"]))
    return tool, None


def base_grant(base_tools):
    """The approval's non-sending helpers (Read, Edit...). An MCP tool here
    would be a second send tool next to the one the entry allows, so MCP
    entries are dropped."""
    out = []
    for t in str(base_tools or "").split(","):
        t = t.strip()
        if t and not t.startswith("mcp__") and t not in out:
            out.append(t)
    return out


def approval_grant(entry, config, base_tools):
    """The full --allowedTools value for approving ``entry``: (grant, None)
    or (None, why)."""
    tool, why = approval_tool(entry, config)
    if not tool:
        return None, why
    return ",".join([tool] + [t for t in base_grant(base_tools) if t != tool]), None
