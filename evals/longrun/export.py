#!/usr/bin/env python3
"""Export a Kestrel world as a plain benchmark folder anyone can use.

    python3 evals/longrun/export.py OUT_DIR [--world full]

Writes:
  world.json            Dana's identities and accounts, workspaces, the Slack
                        directory, channels, and the two checkpoints
  first-read.jsonl      every item before C1 (2026-10-13): the first crawl
  weekly/2026-10-13.jsonl ... 2026-11-03.jsonl
                        one file per weekly check, the items of that week only
  answers/dev.json      answer key for the DEV half (tune on this)
  answers/test.json     answer key for the TEST half (report on this; do not
                        tune on it)
  training/dev-tasks.jsonl
                        one line per DEV task: its source items with their
                        thread context, a sample of nearby noise from the same
                        accounts, and the expected answer at C1. For
                        fine-tuning or few-shot prompts. Built from DEV only.
  README.md             the format, how to score, and the rules

Score a system's output with evals/longrun/score_tasks.py.
"""

import json
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "second-labeler"))

import build          # noqa: E402
import replay         # noqa: E402
import make_packet    # noqa: E402  (context_key: same thread grouping as the labeler)

NOISE_PER_TASK = 40


def jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def answer(arc, cp):
    st = arc.get(cp)
    if st is None:
        return None
    if st["state"] == "absent":
        return {"state": "gone", "match_any": st["gists"]}
    out = {"state": "open", "match": st["gist"], "workspace": st["workspace"], "due": st["due"],
           "waiting_on_someone": st["owner"] == "counterparty"}
    if cp == "c1":
        out["priority"] = st["priority"]
    return out


def main(out, kind="full"):
    items, gold, meta = build.build(kind)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    world = {k: meta[k] for k in ("user", "workspaces", "today", "c2", "future_weeks",
                                  "history_start", "slack_users", "slack_channels") if k in meta}
    world["checkpoints"] = {"c1": meta["today"], "c2": meta["c2"]}
    json.dump(world, open(os.path.join(out, "world.json"), "w"), indent=1, ensure_ascii=False)
    for st in replay.steps(meta):
        rows = [i for i in items if st["lo"] <= i["date"] < st["hi"]]
        name = "first-read.jsonl" if st["name"] == "c1" else os.path.join("weekly", st["lo"] + ".jsonl")
        jsonl(os.path.join(out, name), rows)
    for split in ("dev", "test"):
        ans = [{"id": a["id"], "kind": a["phenomenon"], "sources": a["sources"],
                "c1": answer(a, "c1"), "c2": answer(a, "c2")} for a in gold if a["split"] == split]
        os.makedirs(os.path.join(out, "answers"), exist_ok=True)
        json.dump(ans, open(os.path.join(out, "answers", split + ".json"), "w"), indent=1)

    # training rows from DEV only
    by_ctx, by_id = {}, {i["id"]: i for i in items}
    for i in items:
        by_ctx.setdefault(make_packet.context_key(i), []).append(i)
    arc_ids = {s for a in gold for s in a["sources"]}
    rng = random.Random(20261026)
    rows = []
    for a in gold:
        if a["split"] != "dev" or a.get("c1") is None:
            continue
        ids = set()
        for s in a["sources"]:
            ids.update(x["id"] for x in by_ctx[make_packet.context_key(by_id[s])])
        own = [by_id[x] for x in ids if by_id[x]["date"] < meta["today"]]
        if not own:
            continue
        accts = {(i["connector"], i.get("account") or i.get("channel")) for i in own}
        pool = [i for i in items if i["date"] < meta["today"] and i["id"] not in arc_ids
                and (i["connector"], i.get("account") or i.get("channel")) in accts]
        noise = rng.sample(pool, min(NOISE_PER_TASK, len(pool)))
        mixed = sorted(own + noise, key=lambda x: (x["date"], x["id"]))
        rows.append({"task": a["id"], "today": meta["today"], "items": mixed,
                     "expected": answer(a, "c1")})
    jsonl(os.path.join(out, "training", "dev-tasks.jsonl"), rows)
    shutil.copy(os.path.join(HERE, "BENCHMARK.md"), os.path.join(out, "README.md"))
    n_first = sum(1 for i in items if i["date"] < meta["today"])
    print("exported %s: %d items (%d before the first read), %d dev and %d test tasks, %d training rows"
          % (kind, len(items), n_first, sum(a["split"] == "dev" for a in gold),
             sum(a["split"] == "test" for a in gold), len(rows)))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[a.index("--world") + 1] if "--world" in a else "full")
