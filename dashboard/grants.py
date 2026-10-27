#!/usr/bin/env python3
"""The research crawl's tool grant, built from where this install lives.

The crawl and the account probe read untrusted content (mail, chat, tickets,
repos). An audit (2026-10-27) pointed out that the old grant's Bash(python3:*)
is a whole interpreter: a crawl steered by a malicious message could read any
file or reach the network through it. The grant is now:

  Read, Glob, Grep, Agent, ToolSearch     reading
  Edit(//<workspace>/**)                  editing, only inside the workspace
  Write(//<workspace>/**)                 creating files, only inside the workspace
                                          (the Edit rule alone left the Write TOOL
                                          unloaded: usage.py derives --tools from
                                          grant names, so a crawl could not stage
                                          its record batch; observed 2026-10-27)
  Bash(python3 <dashboard>/cos_tool.py:*) the fixed graph and account operations

An existing config's broad entries (Bash, Write, Edit, Bash(...)) are replaced;
the read-only MCP tools /setup appended to it are kept. ``research_broad_grant:
true`` in config.json keeps the configured grant exactly, on purpose.
"""

from __future__ import annotations

import os

READ = ["Read", "Glob", "Grep", "Agent", "ToolSearch"]
BROAD = set(READ) | {"Edit", "Write"}


def research_base(cos_dir, cos_tool):
    return READ + ["Edit(/%s/**)" % os.path.abspath(cos_dir),
                   "Write(/%s/**)" % os.path.abspath(cos_dir),
                   "Bash(python3 %s:*)" % os.path.abspath(cos_tool)]


def research_grant(cfg, cos_dir, cos_tool):
    base = research_base(cos_dir, cos_tool)
    configured = [t.strip() for t in str((cfg or {}).get("research_tools") or "").split(",") if t.strip()]
    if (cfg or {}).get("research_broad_grant"):
        return ",".join(configured) or ",".join(base)
    extra = [t for t in configured
             if t not in BROAD and not t.startswith(("Bash", "Edit(", "Write("))]
    return ",".join(base + [t for t in extra if t not in base])
