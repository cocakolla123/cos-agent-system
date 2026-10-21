#!/usr/bin/env python3
"""Generate a Kestrel world: items.json (every connector item, sorted by
date), gold.json (each arc's state at C1 and C2), meta.json, and
world.lock.json (sha256 of all three). Deterministic.

    python3 evals/longrun/build.py [--world easy|realistic]          # writes
    python3 evals/longrun/build.py [--world easy|realistic] --check  # verify

easy:      51 arcs over light background noise (evals/longrun/world/)
realistic: the easy arcs + 36 harder arcs, ~140 Slack channels with
           thousands of messages, hundreds of other people's Jira tickets,
           notification-heavy email (evals/longrun/world_realistic/)
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import world        # noqa: E402
import arcs         # noqa: E402
import arcs_hard    # noqa: E402
import world_scale  # noqa: E402

DIRS = {"easy": os.path.join(HERE, "world"),
        "realistic": os.path.join(HERE, "world_realistic")}


def build(kind="easy"):
    s = world.Store()
    world.recurring(s)
    world.noise(s, world.HISTORY_START, world.C2, seed=20261013)
    chans = None
    arc_list = list(arcs.ARCS)
    if kind == "realistic":
        chans = world_scale.scale(s, world.HISTORY_START, world.C2, seed=20261014)
        arc_list += arcs_hard.HARD_ARCS
    gold = []
    for aid, split, phen, fn in arc_list:
        g = fn(s)
        g.update({"id": aid, "split": split, "phenomenon": phen})
        gold.append(g)
    items = sorted(s.items, key=lambda i: (i["date"], i["id"]))
    users = [{"id": h, "real_name": n, "email": e, "title": t}
             for h, (n, e, t) in world.PEOPLE.items()]
    users.append({"id": "alex.brennan", "real_name": "Alex Brennan",
                  "email": "alex.brennan@northwind.example",
                  "title": "Operations Lead, Northwind Clinics (external, shared channel)"})
    if kind == "realistic":
        users += [{"id": h, "real_name": h, "email": h + "@kestrel.example",
                   "title": "Engineer"} for h in world_scale.EXTRA_PEOPLE]
    meta = {"world": kind, "slack_channels": chans, "user": world.USER, "workspaces": world.WORKSPACES,
            "today": world.TODAY, "history_start": world.HISTORY_START,
            "future_weeks": world.FUTURE_WEEKS, "c2": world.C2,
            "slack_users": users}
    return items, gold, meta


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main():
    kind = sys.argv[sys.argv.index("--world") + 1] if "--world" in sys.argv else "easy"
    OUT = DIRS[kind]
    items, gold, meta = build(kind)
    blobs = {"items.json": dump(items), "gold.json": dump(gold), "meta.json": dump(meta)}
    lock = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in blobs.items()}
    if "--from-lock" in sys.argv:
        # regenerate a world whose items are not committed; must match its lock
        old = json.load(open(os.path.join(OUT, "world.lock.json")))
        if old != lock:
            raise SystemExit("regenerated world does not match its lock")
        for k, v in blobs.items():
            open(os.path.join(OUT, k), "w").write(v)
        print("regenerated %s world from code, matches lock" % kind)
        return
    if "--check" in sys.argv:
        old = json.load(open(os.path.join(OUT, "world.lock.json")))
        bad = [k for k in lock if old.get(k) != lock[k]]
        on_disk = [k for k in blobs
                   if hashlib.sha256(open(os.path.join(OUT, k), "rb").read()).hexdigest()
                   != old.get(k)]
        if bad or on_disk:
            raise SystemExit("world differs from lock: %s %s" % (bad, on_disk))
        print("world matches lock")
        return
    os.makedirs(OUT, exist_ok=True)
    for k, v in blobs.items():
        open(os.path.join(OUT, k), "w").write(v)
    open(os.path.join(OUT, "world.lock.json"), "w").write(dump(lock))
    by = {}
    for i in items:
        by[i["connector"]] = by.get(i["connector"], 0) + 1
    hist = sum(1 for i in items if i["date"] < world.TODAY)
    print("items %d (history %d, future %d) by connector %s; arcs %d" % (
        len(items), hist, len(items) - hist, by, len(gold)))


if __name__ == "__main__":
    main()
