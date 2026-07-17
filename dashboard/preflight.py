#!/usr/bin/env python3
"""AI OS connector auth preflight (V2, milestone M8, issue #33). Stdlib only.

Before `/cos-research` or `/setup` crawls a connector, it makes one cheap
read-only probe per connector so an auth failure or outage is reported
explicitly — never mistaken for "no results found". The *probe* itself is done by
the command (it needs the live MCP tools); this module holds the pure,
unit-testable part: turning probe outcomes into an available/unavailable summary
the command reports and stores.

A probe result is ``{"connector": "jira", "ok": bool, "error": "..."}``.
"""

from __future__ import annotations


def summarize(results):
    """Split probe results into available/unavailable and build a report.

    Returns ``{"available": [...], "unavailable": [{connector, error}...],
    "report": "<one-line human summary>"}``.
    """
    available = sorted(r["connector"] for r in results if r.get("ok"))
    unavailable = sorted(
        ({"connector": r["connector"], "error": r.get("error", "unknown")}
         for r in results if not r.get("ok")),
        key=lambda r: r["connector"])
    if not results:
        report = "no connectors to probe"
    elif not unavailable:
        report = "all %d connector(s) reachable" % len(available)
    else:
        report = "%d reachable, %d unavailable (%s)" % (
            len(available), len(unavailable),
            ", ".join(r["connector"] for r in unavailable))
    return {"available": available, "unavailable": unavailable, "report": report}


def should_continue(summary):
    """Research proceeds as long as at least one connector is reachable."""
    return bool(summary["available"])


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(summarize(json.load(sys.stdin)), indent=2))
