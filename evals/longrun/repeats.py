#!/usr/bin/env python3
"""Error bars over repeated long-run runs.

    python3 evals/longrun/repeats.py

Groups saved runs by setup (run ids sharing a prefix before -rN) and reports,
per checkpoint and split, the pass count of each run, the mean and the range,
plus the arcs that did not pass in every run (the unstable ones).
"""
import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results", "longrun")

SETUPS = {
    "default model, v3": ["lrr-v3"] + ["lrr-v3-r%d" % i for i in range(2, 6)],
    "Haiku 4.5, v3": ["lrr-v3-haiku", "lrr-v3-haiku-r2", "lrr-v3-haiku-r3"],
    "default crawl + Haiku polls, v3": ["lrr-v3-mixed-haikupolls-r%d" % i for i in (1, 2, 3)],
    "full world (142k items), default model, v3": ["lrf-v3"] + ["lrf-v3-r%d" % i for i in range(2, 6)],
}


def load(run, cp):
    p = os.path.join(RESULTS, run, "score_%s.json" % cp)
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    out = {}
    for name, runs in SETUPS.items():
        got = {r: {cp: load(r, cp) for cp in ("c1", "c2")} for r in runs}
        got = {r: v for r, v in got.items() if v["c1"] and v["c2"]}
        print("## %s (%d runs: %s)" % (name, len(got), ", ".join(got)))
        out[name] = {"runs": list(got)}
        for cp in ("c1", "c2"):
            for split in ("dev", "test"):
                for key in ("pass", "pass_eff"):
                    vals = [got[r][cp]["summary"][split][key] for r in got]
                    n = got[next(iter(got))][cp]["summary"][split]["arcs"] if got else 0
                    if not vals:
                        continue
                    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
                    print("  %s %s %-8s %s  mean %.1f/%d  sd %.1f  range %d-%d" % (
                        cp, split, key, vals, statistics.mean(vals), n, sd, min(vals), max(vals)))
                    out[name]["%s_%s_%s" % (cp, split, key)] = {"values": vals, "of": n}
            fails = {}
            for r in got:
                for a in got[r][cp]["arcs"]:
                    if not a.get("pass_eff", a["pass"]):
                        fails.setdefault(a["id"], []).append(r)
            unstable = {a: len(v) for a, v in sorted(fails.items())}
            print("  %s arcs failing in some run (failed runs / %d): %s" % (cp, len(got), unstable))
            out[name]["%s_failures" % cp] = unstable
        costs = []
        for r in got:
            steps = json.load(open(os.path.join(RESULTS, r, "steps.json")))
            costs.append(round(sum(s["cost_usd"] or 0 for s in steps if not
                                   (s["step"] == "c1" and "mixed" in r)), 2))
        print("  cost per run ($, mixed counts polls only):", costs)
        out[name]["cost"] = costs
    json.dump(out, open(os.path.join(RESULTS, "repeats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
