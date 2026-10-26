#!/usr/bin/env python3
"""Score any system's task list against a Kestrel world, without this app.

    python3 evals/longrun/score_tasks.py TASKS.json --checkpoint c1 [--world full]
    python3 evals/longrun/score_tasks.py TASKS.json --checkpoint c2 [--world full] [--out score.json]

TASKS.json is the list of tasks your system says are open for Dana at that
checkpoint (C1 = 2026-10-13, after the first read; C2 = 2026-11-10, after four
weekly checks):

    [{"name": "Chase Fernhill Goods to release the milestone 1 payment",
      "workspace": "freelance",          # one of the world's workspace ids
      "due": "2026-10-24" or null,
      "priority": "high" | "medium" | "low",
      "waiting_on": "Fernhill Goods" or null,   # set when Dana is waiting on someone
      "sources": ["em-123456", ...],            # item ids the task came from
      "key": "fernhill-milestone-1-payment"}]   # optional short id; words in it count

Matching, due dates, priority, direction, duplicates, workspace isolation and
noise are scored by the same code as the app's own runs
(score_longrun.score_graph), so numbers are comparable.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import score_longrun          # noqa: E402  (puts dashboard/ on the path via evals/score.py)
import graph as graphlib      # noqa: E402
import build                  # noqa: E402


def tasks_to_graph(tasks, today):
    g = graphlib.Graph()
    now = graphlib._parse_iso(today)
    for k, t in enumerate(tasks):
        attrs = {"due": t.get("due"), "priority": t.get("priority"),
                 "blocked_on": t.get("waiting_on"), "status": t.get("status") or "open",
                 "evidence": list(t.get("sources") or [])}
        key = t.get("key") or "%s-%d" % (graphlib.slug(t.get("name") or "task")[:60], k)
        g.upsert_node("Action", t.get("workspace") or "unknown", key,
                      name=t.get("name") or "", attrs=attrs, now=now)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks")
    ap.add_argument("--checkpoint", choices=["c1", "c2"], required=True)
    ap.add_argument("--world", default="full", choices=sorted(build.DIRS))
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    wdir = build.DIRS[a.world]
    meta = json.load(open(os.path.join(wdir, "meta.json")))
    gold = json.load(open(os.path.join(wdir, "gold.json")))
    today = meta["today"] if a.checkpoint == "c1" else meta["c2"]
    g = tasks_to_graph(json.load(open(a.tasks)), today)
    res = score_longrun.score_graph(g, gold, a.checkpoint, today)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    s = res["summary"]
    for split in ("dev", "test"):
        x = s[split]
        print("%s %s: fully right %d of %d | open caught %d/%d, due %d/%d, direction %d/%d, "
              "priority %d/%d, duplicated %d | gone ok %d/%d | workspace leaks %d" % (
                  a.checkpoint, split, x["pass"], x["arcs"], *x["open_caught"], *x["due_ok"],
                  *x["direction_ok"], *x["priority_ok"], x["duplicated"], *x["absent_ok"],
                  x["isolation_violations"]))
    print("%s: planted instructions followed %d, tasks that match nothing %d, open tasks %d" % (
        a.checkpoint, s["injection_closed"], s["noise_fps"], res["open_actions"]))
    return res


if __name__ == "__main__":
    main()
