#!/usr/bin/env python3
"""The daily check without Claude Code: fetch, sift, then one text-only model call.

    python3 dashboard/poll_direct.py CONFIG_DIR GRAPH_DIR [--dry-run]

1. connections.fetch_all: only what arrived since each source's bookmark.
2. sift.Sifter: keep what could need you (mentions, DMs, your threads, your
   tickets, refs to open tasks...), drop the rest without a model.
3. Nothing kept: print "<source>: nothing new" per source and stop. No model
   call, no cost.
4. Otherwise one model call on the kept items plus your open tasks, using the
   same instructions the benchmark measures (evals/instructions/longrun_v3.md),
   on whatever model Settings gives the poll_direct job: your Claude plan
   (claude -p with no tools) or any API key. The records go into the graph
   through research.ingest, the same path as every other run.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import connections        # noqa: E402
import sift               # noqa: E402
import graph as graphlib  # noqa: E402
import models             # noqa: E402

INSTRUCTIONS = os.path.join(ROOT, "evals", "instructions", "longrun_v3.md")
DIRECT_PREAMBLE = """## This run: a direct check (overrides the file and tool notes above)

There are no files and no tools in this run. The new items since the last check are
given below as JSON lines, already filtered to the ones that could concern the user
(mentions, direct messages, the user's threads, tickets and files, references to open
tasks). Treat them as the sources; the rest of the instructions apply to these lines.
The user's open tasks before this check are listed too: re-emit one with the same
workspace and key (a full record, with "kind") when an item changes or closes it. Output ONLY
the JSON array of records.
"""


def open_tasks(g, now):
    rows = []
    for n in g.query(type_="Action"):
        if not graphlib.is_open_action(n, now=now):
            continue
        a = n.get("attrs") or {}
        ev = a.get("evidence") or []
        rows.append({"workspace": n.get("workspace"), "key": n["id"].split(":action:", 1)[-1],
                     "name": n.get("name"), "sources": ev if isinstance(ev, list) else [ev],
                     "attrs": {k: a[k] for k in ("due", "priority", "blocked_on", "status") if k in a}})
    return rows


def build_prompt(instructions, frame, items, tasks):
    lines = "\n".join(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in items)
    return (instructions + "\n\n" + DIRECT_PREAMBLE + "\n## Scenario frame (trusted)\n```json\n"
            + json.dumps(frame, indent=1, sort_keys=True) + "\n```\n\n## Open tasks before this check\n```json\n"
            + json.dumps([dict({"kind": "Action"}, **{k: t[k] for k in ("workspace", "key", "name", "attrs")})
                         for t in tasks], indent=1)
            + "\n```\n\n## New items\n```jsonl\n" + lines + "\n```\n")


def extract_json_array(text):
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text or "", re.DOTALL)
    candidates = [m.group(1)] if m else []
    a, b = (text or "").find("["), (text or "").rfind("]")
    if a != -1 and b > a:
        candidates.append(text[a:b + 1])
    for c in candidates:
        try:
            v = json.loads(c)
            if isinstance(v, list):
                return v
        except ValueError:
            continue
    return None


def run_model(config_dir, prompt, claude_bin="claude"):
    """Text in, text out, on the poll_direct route. Returns (text, cost or None)."""
    r = models.route(config_dir, "poll_direct")
    if r["provider"] != "claude-code":
        return models.complete(config_dir, "poll_direct", prompt), None
    import usage
    # the prompt goes in on stdin: a day of items is longer than one argv string may be
    cmd = [claude_bin, "-p", "--tools", "", "--permission-mode", "dontAsk",
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'] + models.claude_args(config_dir, "poll_direct")
    res = usage.run(cmd, "poll_direct", config_dir, timeout=900, input=prompt)
    if res.returncode != 0:
        raise RuntimeError("claude failed: %s" % (res.stderr or res.stdout)[:300])
    return res.stdout, (res.record or {}).get("cost_usd")


def check(config_dir, graph_dir, dry_run=False, now=None, _fetch=None, _model=None):
    """One direct check. Returns a summary dict."""
    import datetime as _dt
    now = now or _dt.datetime.now(_dt.timezone.utc)
    fetched = (_fetch or connections.fetch_all)(config_dir)
    new = fetched["items"]
    g = graphlib.Graph.load(graph_dir) if os.path.isdir(graph_dir) else graphlib.Graph()
    tasks = open_tasks(g, now)
    user = connections.user_identity(config_dir)
    known = [i for i in connections.recent_items(config_dir) if i.get("id") not in {x["id"] for x in new}]
    kept, dropped = sift.Sifter(user, None, tasks, known).sift(new)
    out = {"fetched": fetched["per_source"], "new": len(new), "kept": len(kept), "dropped": dropped,
           "line": sift.summary_line(kept, dropped), "records": 0, "cost_usd": 0.0}
    if not kept:
        out["quiet"] = sorted(fetched["per_source"])
        return out
    if dry_run:
        out["dry_run"] = True
        return out
    ws = {}
    try:
        import workspaces
        reg = workspaces.Registry.load(os.path.dirname(graph_dir))
        ws = {wid: w.get("kind", wid) for wid, w in reg.workspaces.items()}
    except Exception:  # noqa: BLE001
        pass
    frame = {"user": user, "workspaces": ws or {"default": "employer"},
             "today": now.date().isoformat()}
    with open(INSTRUCTIONS) as f:
        prompt = build_prompt(f.read(), frame, kept, tasks)
    text, cost = (_model or run_model)(config_dir, prompt)
    recs = extract_json_array(text) or []
    import research
    research.ingest(g, recs, now=now)
    try:
        import correlate
        correlate.correlate(g, now=now)
    except Exception:  # noqa: BLE001
        pass
    if not dry_run:
        g.save(graph_dir)
    out.update({"records": len(recs), "cost_usd": cost})
    return out


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: poll_direct.py CONFIG_DIR GRAPH_DIR [--dry-run]\n")
        return 2
    res = check(argv[0], argv[1], dry_run="--dry-run" in argv)
    for sid, r in sorted(res["fetched"].items()):
        if not r.get("ok"):
            print("%s: error: %s" % (sid, r.get("error")))
    if res.get("quiet") is not None:
        for sid in res["quiet"]:
            print("%s: nothing new" % sid)
    print(res["line"] + (" · %d records" % res["records"] if res["records"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
