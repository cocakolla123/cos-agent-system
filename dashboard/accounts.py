#!/usr/bin/env python3
"""AI OS multi-account connectors (V2.2, milestone M10). Stdlib only.

One MCP connection = one OAuth = one account. Multiple accounts on one machine
work by adding the same connector type as multiple **named instances**
(``gmail-personal``, ``gmail-work``), each with its own OAuth and its own
distinct fully-qualified tool names. This module is the testable core for
managing those instances:

  - the ``connector_accounts`` config schema + validation,
  - probe status (``account-status.json`` — written by `/cos-accounts`,
    rendered by the dashboard; never stores tokens, only status/identity),
  - workspace bindings (one account instance = one workspace = scoped grants),
  - instance detection from a discovered tool list (two gmail-ish servers →
    multi-account setup noticed automatically),
  - the **auth-request queue** behind the dashboard's popup: the only thing the
    system ever asks the user is authorization; ``declined`` is permanent and
    never re-asked.

The OAuth flow itself belongs to Claude's connector UI / the provider's consent
page — the dashboard initiates and confirms it, it never performs it.
"""

from __future__ import annotations

import json
import os

import graph

STATUS_FILE = "account-status.json"
AUTH_REQUESTS_FILE = "auth-requests.json"

KINDS = ["email", "messaging", "calendar", "ticketing", "docs", "code", "other"]

AUTH_OUTCOMES = ("authorized", "snoozed", "declined")


# ---------------------------------------------------------------------------
# Config schema + validation
# ---------------------------------------------------------------------------

def load_accounts(config):
    """Return the ``connector_accounts`` list (possibly empty), normalized."""
    out = []
    for a in (config or {}).get("connector_accounts", []) or []:
        if not isinstance(a, dict) or not a.get("id"):
            continue
        out.append({
            "id": graph.slug(a["id"]),
            "kind": a.get("kind", "other"),
            "label": a.get("label", a["id"]),
            "account": a.get("account", ""),
            "workspace": graph.slug(a["workspace"]) if a.get("workspace") else "",
            "tool_prefix": a.get("tool_prefix", ""),
            "probe_tool": a.get("probe_tool", ""),
        })
    return out


def validate_accounts(config, known_workspaces=None):
    """Findings in validate_config.py's shape: [{level, field, message}]."""
    findings = []
    raw = (config or {}).get("connector_accounts")
    if raw is None:
        return findings
    if not isinstance(raw, list):
        return [{"level": "error", "field": "connector_accounts",
                 "message": "must be a list of account objects"}]
    seen = set()
    for a in load_accounts(config):
        if a["id"] in seen:
            findings.append({"level": "error", "field": "connector_accounts",
                             "message": "duplicate account id '%s'" % a["id"]})
        seen.add(a["id"])
        if not a["tool_prefix"]:
            findings.append({
                "level": "error", "field": "connector_accounts",
                "message": "account '%s' has no tool_prefix — agents can't be "
                           "scoped to it" % a["id"]})
        if a["kind"] not in KINDS:
            findings.append({"level": "warning", "field": "connector_accounts",
                             "message": "account '%s' has unknown kind '%s'" %
                                        (a["id"], a["kind"])})
        if known_workspaces is not None and a["workspace"] and \
                a["workspace"] not in known_workspaces:
            findings.append({
                "level": "warning", "field": "connector_accounts",
                "message": "account '%s' bound to unknown workspace '%s'" %
                           (a["id"], a["workspace"])})
    return findings


def accounts_for_workspace(config, workspace):
    ws = graph.slug(workspace) if workspace else ""
    return [a for a in load_accounts(config) if a["workspace"] == ws]


def unbound_accounts(config):
    return [a for a in load_accounts(config) if not a["workspace"]]


# ---------------------------------------------------------------------------
# Probe status (account-status.json)
# ---------------------------------------------------------------------------

def read_status(dashboard_dir):
    return _read_json(os.path.join(dashboard_dir, STATUS_FILE), {})


def write_status(dashboard_dir, account_id, ok, identity="", error="", now=None):
    """Merge one probe result into the status file. Status only — no tokens."""
    path = os.path.join(dashboard_dir, STATUS_FILE)
    status = _read_json(path, {})
    status[account_id] = {
        "ok": bool(ok),
        "identity": identity,
        "error": "" if ok else (error or "unknown"),
        "checked_at": graph.iso(now),
    }
    _write_json(path, status)
    return status[account_id]


def summarize_accounts(config, status, declined_ids=None):
    """Dashboard rows + a one-line report.

    Each row: {id, kind, label, identity, workspace, state, checked_at}
    with state in connected | needs_auth | declined | unknown.
    """
    declined_ids = set(declined_ids or [])
    rows = []
    n_ok = n_bad = 0
    for a in load_accounts(config):
        st = (status or {}).get(a["id"], {})
        if a["id"] in declined_ids:
            state = "declined"
        elif not st:
            state = "unknown"
        elif st.get("ok"):
            state = "connected"
            n_ok += 1
        else:
            state = "needs_auth"
            n_bad += 1
        rows.append({
            "id": a["id"], "kind": a["kind"], "label": a["label"],
            "identity": st.get("identity") or a["account"] or "",
            "workspace": a["workspace"] or "(unbound)",
            "state": state,
            "checked_at": st.get("checked_at", ""),
            "error": st.get("error", ""),
        })
    if not rows:
        report = "no connector accounts configured"
    elif n_bad:
        report = "%d connected, %d need auth" % (n_ok, n_bad)
    else:
        report = "%d account(s) connected" % n_ok
    return rows, report


# ---------------------------------------------------------------------------
# Instance detection from a discovered tool list
# ---------------------------------------------------------------------------

_KIND_SIGNALS = [
    ("email", ("gmail", "mail", "thread", "inbox", "message_draft")),
    ("messaging", ("slack", "teams", "channel", "chat")),
    ("calendar", ("calendar", "event", "meeting")),
    ("ticketing", ("jira", "linear", "ticket", "issue")),
    ("docs", ("drive", "doc", "wiki", "notion", "file")),
    ("code", ("github", "gitlab", "repo", "pull")),
]


def detect_instances(tool_names):
    """Group fully-qualified MCP tool names by server prefix and guess kinds.

    Returns {kind: [prefixes...]} sorted; a kind with >=2 prefixes means the
    user has multiple accounts of that connector type — /setup and
    /cos-research use this to notice multi-account setups automatically.
    """
    by_prefix = {}
    for t in tool_names or []:
        if not t.startswith("mcp__"):
            continue
        parts = t.split("__")
        if len(parts) < 3:
            continue
        prefix = "__".join(parts[:2]) + "__"
        by_prefix.setdefault(prefix, []).append(parts[-1].lower())
    out = {}
    for prefix in sorted(by_prefix):
        blob = " ".join(by_prefix[prefix])
        kind = "other"
        for k, signals in _KIND_SIGNALS:
            if any(s in blob for s in signals):
                kind = k
                break
        out.setdefault(kind, []).append(prefix)
    return out


def multi_account_kinds(instances):
    """Kinds with two or more instances (the multi-account signal)."""
    return sorted(k for k, v in (instances or {}).items()
                  if k != "other" and len(v) >= 2)


# ---------------------------------------------------------------------------
# Auth-request queue (the dashboard popup's backend)
# ---------------------------------------------------------------------------

def _auth_path(dashboard_dir):
    return os.path.join(dashboard_dir, AUTH_REQUESTS_FILE)


def enqueue_auth_request(dashboard_dir, account_id, reason="", auth_url="",
                         now=None):
    """Queue an authorization ask (deduped by account id). Never enqueues a
    declined account — Refuse is permanent."""
    data = _read_json(_auth_path(dashboard_dir), {"requests": []})
    for r in data["requests"]:
        if r["id"] == account_id and r.get("outcome") == "declined":
            return None                      # permanently refused: never re-ask
    for r in data["requests"]:
        if r["id"] == account_id and r.get("outcome") in (None, "", "snoozed"):
            r["outcome"] = ""                # resurface a snoozed one
            r["reason"] = reason or r.get("reason", "")
            r["auth_url"] = auth_url or r.get("auth_url", "")
            _write_json(_auth_path(dashboard_dir), data)
            return r
    req = {"id": account_id, "reason": reason, "auth_url": auth_url,
           "outcome": "", "created": graph.iso(now)}
    data["requests"].append(req)
    _write_json(_auth_path(dashboard_dir), data)
    return req


def pending_auth_requests(dashboard_dir):
    data = _read_json(_auth_path(dashboard_dir), {"requests": []})
    return [r for r in data["requests"] if not r.get("outcome")]


def resolve_auth_request(dashboard_dir, account_id, outcome, now=None):
    """Record the user's popup choice. Returns the request or None."""
    if outcome not in AUTH_OUTCOMES:
        raise ValueError("outcome must be one of %s" % (AUTH_OUTCOMES,))
    data = _read_json(_auth_path(dashboard_dir), {"requests": []})
    for r in data["requests"]:
        if r["id"] == account_id:
            r["outcome"] = outcome
            r["resolved_at"] = graph.iso(now)
            _write_json(_auth_path(dashboard_dir), data)
            return r
    return None


def is_declined(dashboard_dir, account_id):
    data = _read_json(_auth_path(dashboard_dir), {"requests": []})
    return any(r["id"] == account_id and r.get("outcome") == "declined"
               for r in data["requests"])


def declined_ids(dashboard_dir):
    data = _read_json(_auth_path(dashboard_dir), {"requests": []})
    return sorted({r["id"] for r in data["requests"]
                   if r.get("outcome") == "declined"})


# ---------------------------------------------------------------------------
# shared
# ---------------------------------------------------------------------------

def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


if __name__ == "__main__":
    import sys
    dash = sys.argv[1] if len(sys.argv) > 1 else "."
    cfg = _read_json(os.path.join(dash, "config.json"), {})
    rows, report = summarize_accounts(cfg, read_status(dash),
                                      declined_ids(dash))
    print(report)
    for r in rows:
        print(" %-18s %-10s %-24s %-12s %s" % (
            r["id"], r["kind"], r["identity"], r["workspace"], r["state"]))
