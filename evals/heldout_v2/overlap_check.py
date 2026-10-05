#!/usr/bin/env python3
"""Independence check: 8-word shingle Jaccard between every heldout_v2 source
body and every original fixture body. Threshold fixed in advance: the check
FAILS if any pair exceeds 0.20. Run before the label freeze."""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "fixtures")
NEW = os.path.join(HERE, "fixtures")
THRESHOLD = 0.20
K = 8


def bodies(root):
    out = {}
    for scen in sorted(os.listdir(root)):
        srcdir = os.path.join(root, scen, "sources")
        if not os.path.isdir(srcdir):
            continue
        for f in sorted(os.listdir(srcdir)):
            if not f.endswith(".json"):
                continue
            item = json.load(open(os.path.join(srcdir, f)))
            text = " ".join(str(item.get(k, "")) for k in
                            ("subject", "body", "text", "summary", "title"))
            text += " ".join(c.get("text", "")
                             for c in item.get("comments") or [])
            out["%s/%s" % (scen, f)] = text
    return out


def shingles(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i:i + K]) for i in range(max(len(words) - K + 1, 0))}


def main():
    old = {k: shingles(v) for k, v in bodies(OLD).items()}
    new = {k: shingles(v) for k, v in bodies(NEW).items()}
    worst = (0.0, None, None)
    for nk, ns in new.items():
        if not ns:
            continue
        for ok, os_ in old.items():
            if not os_:
                continue
            inter = len(ns & os_)
            if not inter:
                continue
            j = inter / float(len(ns | os_))
            if j > worst[0]:
                worst = (j, nk, ok)
    print("max 8-shingle Jaccard between new and old: %.4f" % worst[0])
    if worst[1]:
        print("  pair: %s vs %s" % (worst[1], worst[2]))
    if worst[0] > THRESHOLD:
        print("FAIL: exceeds the preregistered threshold %.2f" % THRESHOLD)
        raise SystemExit(1)
    print("PASS (threshold %.2f)" % THRESHOLD)


if __name__ == "__main__":
    main()
