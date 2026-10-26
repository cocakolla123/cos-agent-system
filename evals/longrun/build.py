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
full:      the realistic world plus everything else on a real person's
           accounts (world_life.py): over 100,000 items before the first
           crawl, spam, personal mail, CI bots, other teams' work. Same arcs
           and answers. Item ids are shuffled so they say nothing about
           which items belong to an arc (evals/longrun/world_full/)
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
import world_life   # noqa: E402
import arcs_life    # noqa: E402
import copy         # noqa: E402
import random       # noqa: E402
import re           # noqa: E402
sys.path.insert(0, os.path.dirname(HERE))
import score        # noqa: E402  (the gist matcher)

DIRS = {"easy": os.path.join(HERE, "world"),
        "realistic": os.path.join(HERE, "world_realistic"),
        "full": os.path.join(HERE, "world_full")}
ID_RE = re.compile(r"^(em|sl|jr|gh|cal|doc)-\d+$")


def _gists(g):
    out = []
    for cp in ("c1", "c2"):
        c = g.get(cp) or {}
        if c.get("gist"):
            out.append(c["gist"])
        out += c.get("gists") or []
    return [x for x in out if x]


def _text(item):
    return json.dumps({k: v for k, v in item.items() if k not in ("id", "connector", "date")},
                      ensure_ascii=False).lower()


def guard_life(items, first_life, gold):
    """Drop life-layer items that match any arc gist, and replies to them."""
    life_ids = {i["id"] for i in items[first_life:]}
    gists = [x for g in gold for x in _gists(g)]
    drop = set()
    for i in items[first_life:]:
        t = _text(i)
        if any(score._gist_score(x, t) >= score.MATCH_THRESHOLD for x in gists):
            drop.add(i["id"])
    drop |= {i["id"] for i in items if i["id"] in life_ids and i.get("thread_ts") in drop}
    return [i for i in items if i["id"] not in drop], len(drop)


def shuffle_ids(items, gold, seed):
    """Give every item a random id of its connector's prefix; remap references."""
    rng = random.Random(seed)
    used, mapping = set(), {}
    for i in items:
        p = i["id"].split("-")[0]
        while True:
            new = "%s-%06d" % (p, rng.randint(0, 999999))
            if new not in used:
                break
        used.add(new)
        mapping[i["id"]] = new

    def remap(v):
        if isinstance(v, str):
            return mapping.get(v, v) if ID_RE.match(v) else v
        if isinstance(v, list):
            return [remap(x) for x in v]
        if isinstance(v, dict):
            return {k: remap(x) for k, x in v.items()}
        return v
    return [remap(i) for i in items], [remap(g) for g in gold]


def build(kind="easy"):
    s = world.Store()
    world.recurring(s)
    world.noise(s, world.HISTORY_START, world.C2, seed=20261013)
    chans = None
    arc_list = list(arcs.ARCS)
    if kind in ("realistic", "full"):
        chans = world_scale.scale(s, world.HISTORY_START, world.C2, seed=20261014)
        arc_list += arcs_hard.HARD_ARCS
    first_life = len(s.items)
    if kind == "full":
        world_life.life(s, world.HISTORY_START, world.C2, seed=20261015)
        arc_list += arcs_life.LIFE_ARCS
    end_life = len(s.items)
    gold = []
    for aid, split, phen, fn in arc_list:
        g = fn(s)
        g.update({"id": aid, "split": split, "phenomenon": phen})
        gold.append(g)
    items = s.items
    dropped = 0
    if kind == "full":
        life_part, dropped = guard_life(items[:end_life], first_life, gold)
        items = life_part + items[end_life:]
        items, gold = shuffle_ids(items, gold, seed=20261016)
    items = sorted(items, key=lambda i: (i["date"], i["id"]))
    users = [{"id": h, "real_name": n, "email": e, "title": t}
             for h, (n, e, t) in world.PEOPLE.items()]
    users.append({"id": "alex.brennan", "real_name": "Alex Brennan",
                  "email": "alex.brennan@northwind.example",
                  "title": "Operations Lead, Northwind Clinics (external, shared channel)"})
    if kind in ("realistic", "full"):
        extra = world_scale.EXTRA_PEOPLE + ([h for h in world_life.MORE if h not in world_scale.EXTRA_PEOPLE]
                                            if kind == "full" else [])
        users += [{"id": h, "real_name": h, "email": h + "@kestrel.example",
                   "title": "Engineer"} for h in extra]
    if kind == "full":
        chans = chans + [{"name": c, "is_member": True, "is_muted": c in ("#ci", "#builds"),
                          "kind": "life"} for c in world_life.LIFE_CHANNELS]
    user, workspaces = world.USER, world.WORKSPACES
    if kind == "full":
        user = copy.deepcopy(world.USER)
        user["other_emails"] = user["other_emails"] + [arcs_life.FREELANCE, arcs_life.OLD]
        workspaces = dict(world.WORKSPACES, freelance="freelance")
    meta = {"world": kind, "slack_channels": chans, "user": user, "workspaces": workspaces,
            "today": world.TODAY, "history_start": world.HISTORY_START,
            "future_weeks": world.FUTURE_WEEKS, "c2": world.C2,
            "slack_users": users}
    if kind == "full":
        meta["guard_dropped"] = dropped
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
