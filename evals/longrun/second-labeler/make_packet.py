#!/usr/bin/env python3
"""Build the blind second-labeler packet for the realistic long-run world.

    python3 evals/longrun/second-labeler/make_packet.py <out_dir> <mapping.json> [--world full] [--only L] [--noise 300]

Two tasks, both from raw items only (no arc names, phenomena, stories or gold):

1. cases.jsonl: one case per arc, shuffled and renamed (case-01...). Each case
   holds the arc's source items plus their context: the whole Slack thread,
   the whole mail thread, every snapshot of the same Jira ticket or GitHub
   PR/issue, every version of the same doc or event. The labeler states, at
   C1 and at C2, whether an open obligation of the user's exists and its
   due date, priority (C1), workspace and direction.
2. noise.jsonl: a seeded sample of items that are in no arc but mention or
   address the user (where a missed task would hide). The labeler lists any
   that create an obligation on the user.

The arc-to-case mapping goes to a separate file the labeler never sees.
"""
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LR = os.path.dirname(HERE)
sys.path.insert(0, LR)
sys.path.insert(0, os.path.dirname(LR))
import build  # noqa: E402

SEED = 20261021
NOISE_N = 120


def context_key(i):
    c = i["connector"]
    if c == "slack":
        return ("slack", i["channel"], i.get("thread_ts") or i["id"])
    if c == "gmail":
        return ("gmail", i.get("threadId") or i["id"])
    if c == "jira":
        return ("jira", i["key"])
    if c == "github":
        return ("github", i["repo"], i["number"])
    if c == "drive":
        return ("drive", i["name"])
    if c == "calendar":
        return ("calendar", i.get("summary"), i.get("organizer"))
    return (c, i["id"])


def mentions_user(i, user):
    blob = json.dumps(i).lower()
    keys = [user["slack"], user["email"], user["name"].split()[0].lower()] + [
        e.lower() for e in user.get("other_emails", [])]
    if i["connector"] == "slack" and (i["channel"].startswith("D-") or i["channel"].startswith("mpdm-")):
        return True
    return any(k.lower() in blob for k in keys)


def main(out_dir, mapping_path, world="realistic", only=None, noise_n=NOISE_N):
    items, gold, meta = build.build(world)
    all_gold = gold
    if only:
        gold = [a for a in gold if a["id"].startswith(only)]
    by_ctx = {}
    for i in items:
        by_ctx.setdefault(context_key(i), []).append(i)
    by_id = {i["id"]: i for i in items}
    rng = random.Random(SEED)
    arcs = list(gold)
    rng.shuffle(arcs)
    os.makedirs(out_dir, exist_ok=True)
    mapping = {}
    arc_ids = set()
    with open(os.path.join(out_dir, "cases.jsonl"), "w") as f:
        for n, arc in enumerate(arcs, 1):
            case = "case-%02d" % n
            mapping[case] = arc["id"]
            ids = set()
            for s in arc["sources"]:
                ids.update(x["id"] for x in by_ctx[context_key(by_id[s])])
            arc_ids.update(ids)
            its = sorted((by_id[x] for x in ids), key=lambda x: (x["date"], x["id"]))
            f.write(json.dumps({"case": case, "items": its}) + "\n")
    for arc in all_gold:      # items of arcs left out of the cases are not noise either
        for sid in arc["sources"]:
            arc_ids.update(x["id"] for x in by_ctx[context_key(by_id[sid])])
    pool = [i for i in items if i["id"] not in arc_ids and i["date"] < meta["c2"] + "T23:59"
            and mentions_user(i, meta["user"])]
    sample = sorted(rng.sample(pool, min(noise_n, len(pool))), key=lambda x: (x["date"], x["id"]))
    with open(os.path.join(out_dir, "noise.jsonl"), "w") as f:
        for i in sample:
            f.write(json.dumps(i) + "\n")
    people = {"slack_users": meta["slack_users"], "user": meta["user"],
              "workspaces": meta["workspaces"], "c1": meta["today"], "c2": meta["c2"]}
    with open(os.path.join(out_dir, "world.json"), "w") as f:
        json.dump(people, f, indent=1)
    with open(mapping_path, "w") as f:
        json.dump(mapping, f, indent=1)
    print("cases", len(arcs), "noise sample", len(sample), "of pool", len(pool))


if __name__ == "__main__":
    # make_packet.py OUT MAPPING [--world full] [--only L] [--noise 300]
    a = sys.argv
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    main(a[1], a[2], world=opt("--world", "realistic"), only=opt("--only", None),
         noise_n=int(opt("--noise", NOISE_N)))
