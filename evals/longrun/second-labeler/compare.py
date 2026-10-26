#!/usr/bin/env python3
"""Agreement between the author's gold and the blind second labeler.

    python3 evals/longrun/second-labeler/compare.py <packet_dir> <mapping.json> [--world full]

Computed before any reconciliation. Per arc and checkpoint: state (open vs
absent), and for arcs both call open: due date, priority (C1), workspace and
direction. Gists are printed for disagreements so each can be read; matching
gists is left to the reader, not to keywords. Also lists the noise items the
labeler flagged as obligations.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LR = os.path.dirname(HERE)
sys.path.insert(0, LR)
sys.path.insert(0, os.path.dirname(LR))
import build  # noqa: E402


def first(items):
    return (items or [{}])[0]


def main(packet, mapping_path, world="realistic"):
    _, gold, _ = build.build(world)
    gold = {a["id"]: a for a in gold}
    mapping = json.load(open(mapping_path))
    lab = json.load(open(os.path.join(packet, "labels2-cases.json")))["cases"]
    noise = json.load(open(os.path.join(packet, "labels2-noise.json")))["noise"]
    rows, tally = [], {}

    def count(k, ok):
        t = tally.setdefault(k, [0, 0])
        t[0] += bool(ok)
        t[1] += 1

    for case, arc_id in sorted(mapping.items()):
        arc = gold[arc_id]
        for cp in ("c1", "c2"):
            g = arc.get(cp)
            if g is None:
                continue
            l = (lab.get(case) or {}).get(cp) or {}
            gs, ls = g["state"], l.get("state")
            count("%s state" % cp, gs == ls)
            row = {"arc": arc_id, "case": case, "cp": cp, "split": arc["split"],
                   "phenomenon": arc["phenomenon"], "gold": gs, "labeler": ls}
            diffs = []
            if gs != ls:
                diffs.append("state")
            if gs == "open" and ls == "open":
                li = first(l.get("items"))
                extra = len(l.get("items") or []) - 1
                if extra > 0:
                    diffs.append("labeler has %d more open item(s)" % extra)
                for k, gv, lv in (("due", g.get("due"), li.get("due")),
                                  ("workspace", g.get("workspace"), li.get("workspace")),
                                  ("owner", g.get("owner"), li.get("owner"))):
                    count("%s %s" % (cp, k), gv == lv)
                    if gv != lv:
                        diffs.append("%s %s vs %s" % (k, gv, lv))
                if cp == "c1" and g.get("priority"):
                    count("c1 priority", g["priority"] == li.get("priority"))
                    if g["priority"] != li.get("priority"):
                        diffs.append("priority %s vs %s (%s)" % (g["priority"], li.get("priority"), li.get("rule")))
                row["gold_gist"] = " ".join(g.get("gist") or [])
                row["labeler_gist"] = li.get("gist")
            elif ls == "absent":
                row["labeler_why"] = l.get("why")
            elif ls == "open":
                row["labeler_gist"] = first(l.get("items")).get("gist")
            row["diffs"] = diffs
            rows.append(row)
    print("## Agreement before reconciliation\n")
    for k, (a, n) in sorted(tally.items()):
        print("- %s: %d of %d" % (k, a, n))
    print("\n## Disagreements\n")
    for r in rows:
        if r["diffs"]:
            print("- %s %s (%s, %s): %s" % (r["arc"], r["cp"], r["split"], r["phenomenon"],
                                            "; ".join(r["diffs"])))
            for k in ("gold_gist", "labeler_gist", "labeler_why"):
                if r.get(k):
                    print("    %s: %s" % (k, r[k]))
    print("\n## Noise items the labeler flagged as obligations (%d of the sample)\n" % len(noise))
    for n in noise:
        print("- %s (%s, due %s, %s): %s" % (n["id"], n.get("workspace"), n.get("due"),
                                            n.get("confidence"), n.get("gist")))
    json.dump({"tally": tally, "rows": rows, "noise": noise},
              open(os.path.join(os.path.dirname(os.path.abspath(packet)), "agreement.json"), "w"), indent=1)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], world=a[a.index("--world") + 1] if "--world" in a else "realistic")
