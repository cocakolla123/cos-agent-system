#!/usr/bin/env python3
"""Pre-reconciliation agreement between the author's gold labels and the
independent second labeler. Commitments are aligned per story by (workspace,
owner) and then greedily by shared content words between the gold gist and
the labeler's description; the printout is reviewed by hand before any
reconciliation decision."""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "..", "fixtures")


def words(s):
    return {w for w in re.findall(r"[a-z0-9-]{3,}", (s or "").lower())}


def main(labels2_path):
    l2 = json.load(open(labels2_path))
    stats = {"stories": 0, "count_match": 0,
             "commit_pairs": 0, "due_match": 0, "owner_match": 0,
             "ws_match": 0, "blocked_match": 0,
             "gold_unmatched": 0, "l2_unmatched": 0,
             "forbidden_both": 0, "forbidden_gold_only": 0,
             "forbidden_l2_only": 0}
    disagreements = []
    for sid_ in sorted(os.listdir(FIXTURES)):
        sdir = os.path.join(FIXTURES, sid_)
        if not os.path.isdir(sdir):
            continue
        gold = json.load(open(os.path.join(sdir, "expected.json")))
        mine = gold.get("commitments", [])
        theirs = (l2.get(sid_) or {}).get("commitments", [])
        stats["stories"] += 1
        if len(mine) == len(theirs):
            stats["count_match"] += 1
        else:
            disagreements.append("%s: commitment COUNT gold=%d labeler=%d (%s)"
                                 % (sid_, len(mine), len(theirs),
                                    "; ".join(t.get("desc", "")[:60]
                                              for t in theirs) or "none"))
        used = set()
        for c in mine:
            best, score_ = None, 0
            for i, t in enumerate(theirs):
                if i in used:
                    continue
                s = len(words(" ".join(c["gist"])) & words(t.get("desc", "")))
                if s > score_:
                    best, score_ = i, s
            if best is None:
                stats["gold_unmatched"] += 1
                continue
            used.add(best)
            t = theirs[best]
            stats["commit_pairs"] += 1
            for key, mine_v, their_v in (
                    ("due", c.get("due"), t.get("due")),
                    ("owner", c.get("owner"), t.get("owner")),
                    ("ws", c.get("workspace"), t.get("workspace")),
                    ("blocked", bool(c.get("blocked_on")),
                     bool(t.get("blocked_on")))):
                if mine_v == their_v:
                    stats[key + "_match"] += 1
                else:
                    disagreements.append("%s: %s gold=%r labeler=%r (%s)" % (
                        sid_, key, mine_v, their_v, t.get("desc", "")[:60]))
        stats["l2_unmatched"] += len(theirs) - len(used)
        g_forb = len(gold.get("forbidden", []))
        t_forb = len((l2.get(sid_) or {}).get("must_not_appear", []))
        if g_forb and t_forb:
            stats["forbidden_both"] += 1
        elif g_forb:
            stats["forbidden_gold_only"] += 1
            disagreements.append("%s: gold has forbidden items, labeler has "
                                 "none" % sid_)
        elif t_forb:
            stats["forbidden_l2_only"] += 1
            disagreements.append("%s: labeler flagged must-not-appear, gold "
                                 "has none: %s" % (
                                     sid_, "; ".join(
                                         (l2.get(sid_) or {}).get(
                                             "must_not_appear", []))[:100]))
    print(json.dumps(stats, indent=1))
    print("\n== disagreements for hand review ==")
    for d in disagreements:
        print(" -", d)


if __name__ == "__main__":
    main(sys.argv[1])
