#!/usr/bin/env python3
"""Build the held-out v2 fixtures from the story modules.

    python3 evals/heldout_v2/build.py          # writes fixtures/ + manifest
    python3 evals/heldout_v2/build.py --lock   # also (re)writes labels.lock.json

The lock is written exactly once, before any model run; the runner refuses to
score this set when an expected.json no longer matches the lock (see
PREREGISTRATION.md). Story content lives in stories_a.py / stories_b.py and
the world in world.py; see SPEC.md for the labeling rules."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import world                      # noqa: E402
from stories_a import STORIES_A   # noqa: E402
from stories_b import STORIES_B   # noqa: E402
import schema                     # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
LOCK = os.path.join(HERE, "labels.lock.json")

# 10 dev stories (available for future tuning), chosen to spread across
# phenomena; everything else is test and is never used for tuning.
DEV = {"p1-m1", "p1-m5", "p2-c1", "p2-c6", "p3-x2",
       "p4-o2", "p4-o6", "p5-d3", "p6-i1", "p6-i9"}


def main(write_lock=False):
    if os.path.isdir(FIXTURES):
        shutil.rmtree(FIXTURES)
    os.makedirs(FIXTURES)
    manifest = []
    for sid_, phen, builder in STORIES_A + STORIES_B:
        world.reset_ids()
        sources, exp, note = builder()
        split = "dev" if sid_ in DEV else "test"
        sdir = os.path.join(FIXTURES, sid_)
        os.makedirs(os.path.join(sdir, "sources"))
        scenario = {
            "id": sid_, "base_id": sid_, "category": phen, "split": split,
            "note": note, "today": world.TODAY, "user": world.USER,
            "workspaces": world.WORKSPACES,
        }
        json.dump(scenario, open(os.path.join(sdir, "scenario.json"), "w"),
                  indent=1, sort_keys=True)
        json.dump(exp, open(os.path.join(sdir, "expected.json"), "w"),
                  indent=1, sort_keys=True)
        for item in sources:
            json.dump(item, open(os.path.join(
                sdir, "sources", item["id"] + ".json"), "w"),
                indent=1, sort_keys=True)
        manifest.append({"id": sid_, "base_id": sid_, "category": phen,
                         "split": split, "sources": len(sources),
                         "gold_commitments": len(exp["commitments"])})
    json.dump(manifest, open(os.path.join(FIXTURES, "manifest.json"), "w"),
              indent=1)

    bad = 0
    for name, path in schema.iter_scenarios(FIXTURES):
        errs = schema.validate_scenario_dir(path)
        if errs:
            bad += 1
            print(name, "->", errs)
    dev = sum(1 for m in manifest if m["split"] == "dev")
    print("wrote %d stories (%d dev / %d test), schema %s" % (
        len(manifest), dev, len(manifest) - dev,
        "FAIL" if bad else "clean"))
    if bad:
        raise SystemExit(1)

    if write_lock:
        lock = {}
        for m in manifest:
            p = os.path.join(FIXTURES, m["id"], "expected.json")
            lock[m["id"]] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        json.dump({"note": "sha256 of every expected.json at freeze time; "
                           "the runner refuses to score this set on any "
                           "mismatch", "labels": lock},
                  open(LOCK, "w"), indent=1, sort_keys=True)
        print("lock written: %d label hashes" % len(lock))


if __name__ == "__main__":
    main(write_lock="--lock" in sys.argv)
