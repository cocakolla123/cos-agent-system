#!/usr/bin/env python3
"""AI OS config validator (V2, milestone M8, issue #30). Stdlib only.

`dashboard/config.json` drives tool grants, action tools, and domain detection.
A subtly-wrong config fails **silently** today: an invalid JSON file falls back
to defaults, and a tool-grant list missing its baseline (`Read,Agent` /
`Read,Edit,Agent`) produces a subprocess that can't dispatch agents and just does
nothing. This validator surfaces those problems as explicit errors/warnings
instead.

``validate(config, available_tools=None)`` returns a list of findings::

    [{"level": "error"|"warning", "field": "chat_tools", "message": "..."}]

An empty list means the config is clean. ``validate_file(path)`` also catches
JSON syntax errors (the silent-fallback case).
"""

from __future__ import annotations

import json
import os

# Each subprocess tool-grant is used standalone as the entire --allowedTools
# grant, so it must contain the baseline the role needs to function.
_BASELINE = {
    "chat_tools": {"Read", "Agent"},
    "revise_tools": {"Read", "Edit", "Agent"},
    "poll_tools": {"Read", "Edit", "Agent"},
    "base_tools": {"Read", "Edit", "Agent"},
    # research must be able to persist the graph (Write + a Bash grant, the
    # shipped default scopes it to python3) and scan the local FS (Glob/Grep)
    # — under dontAsk a missing grant is a silent no-op.
    "research_tools": {"Read", "Edit", "Write", "Glob", "Grep", "Agent"},
}


def _finding(level, field, message):
    return {"level": level, "field": field, "message": message}


def validate(config, available_tools=None):
    """Validate an already-parsed config dict. ``available_tools`` (optional) is
    the set of fully-qualified MCP tool names discovered on the deployment; when
    given, action_tools values are checked for existence."""
    findings = []
    if not isinstance(config, dict):
        return [_finding("error", "", "config is not a JSON object")]

    # 1. baseline tool grants
    for field, needed in _BASELINE.items():
        val = config.get(field)
        if val is None:
            continue  # a missing grant falls back to a safe default elsewhere
        grant = {t.strip() for t in str(val).split(",") if t.strip()}
        missing = needed - grant
        if missing:
            findings.append(_finding(
                "error", field,
                "missing baseline tool(s) %s — this subprocess can't dispatch "
                "agents and will silently do nothing" % ", ".join(sorted(missing))))

    # 1b. research needs SOME Bash grant; flag network-capable or unscoped
    # grants as broader than the shipped default (review finding, 2026-10-05).
    rt = config.get("research_tools")
    if rt is not None:
        grant = {t.strip() for t in str(rt).split(",") if t.strip()}
        if not any(g == "Bash" or g.startswith("Bash(") for g in grant):
            findings.append(_finding(
                "error", "research_tools",
                "no Bash grant at all — the crawl can't run graph.py and will "
                "silently persist nothing"))
    for field in ("research_tools", "poll_tools", "chat_tools", "learn_tools",
                  "revise_tools", "base_tools"):
        val = config.get(field)
        if val is None:
            continue
        grant = {t.strip() for t in str(val).split(",") if t.strip()}
        if "Bash" in grant:
            findings.append(_finding(
                "warn", field,
                "unscoped Bash grant — this subprocess can reach the network "
                "(curl etc.); the shipped default allows only dashboard/cos_tool.py"))
        for net in ("WebSearch", "WebFetch"):
            if net in grant:
                findings.append(_finding(
                    "warn", field,
                    net + " grants network access; not in the shipped default"))

    # 2. action_tools sanity
    at = config.get("action_tools")
    if at is not None:
        if not isinstance(at, dict):
            findings.append(_finding("error", "action_tools",
                                     "must be an object mapping action_type -> tool name"))
        else:
            for k, v in at.items():
                if not v or not str(v).strip():
                    findings.append(_finding("warning", "action_tools",
                                             "action_type '%s' maps to an empty tool" % k))
                elif available_tools is not None and v not in available_tools:
                    findings.append(_finding(
                        "warning", "action_tools",
                        "tool '%s' for action_type '%s' is not in the discovered "
                        "tool set" % (v, k)))

    # 3. connector accounts (M10) — delegated to accounts.py when present
    try:
        import accounts as _accounts
        findings.extend(_accounts.validate_accounts(config))
    except ImportError:  # pragma: no cover - accounts module optional
        pass

    # 4. live-refresh interval
    lrs = config.get("live_refresh_seconds")
    if lrs is not None:
        try:
            if int(lrs) < 5:
                findings.append(_finding("warning", "live_refresh_seconds",
                                         "very low interval (<5s) will hammer the server"))
        except (TypeError, ValueError):
            findings.append(_finding("error", "live_refresh_seconds",
                                     "must be an integer"))
    return findings


def validate_file(path, available_tools=None):
    """Validate a config file, catching the silent JSON-fallback case."""
    if not os.path.exists(path):
        return [_finding("warning", "", "no config.json — safe defaults apply")]
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return [_finding("error", "",
                         "invalid JSON (%s) — the dashboard silently falls back "
                         "to defaults" % e)]
    return validate(config, available_tools=available_tools)


def format_findings(findings):
    if not findings:
        return "config OK"
    return "\n".join("[%s] %s%s" % (
        f["level"].upper(), (f["field"] + ": ") if f["field"] else "", f["message"])
        for f in findings)


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    findings = validate_file(p)
    print(format_findings(findings))
    raise SystemExit(1 if any(f["level"] == "error" for f in findings) else 0)
