#!/usr/bin/env python3
"""Score saved heldout_v2 runs for PRIORITY, as a separate post-run pass.

    python3 evals/heldout_v2/score_priority.py hv2-v2-haiku hv2-v1 ...

Rules: PRIORITY_RULES.md. Labels: priority/labels.json (frozen by
priority/priority.lock.json, reconciled with an independent labeler, see
priority/RECONCILIATION.md). Uses the corrected task list (CORRECTIONS.md),
so p6-i5 has two tasks. Only tasks the model got right (matched pairs) are
scored. No model call; nothing frozen is modified.

Two views per pair:
- stated: the priority the model wrote (missing counts as wrong);
- shown:  what the dashboard shows after ingest (missing -> medium).
"""

import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import run               # noqa: E402
import score             # noqa: E402
import score_corrected   # noqa: E402

LEVEL = {"high": 0, "medium": 1, "low": 2}


def load_labels():
    path = os.path.join(HERE, "priority", "labels.json")
    lock = json.load(open(os.path.join(HERE, "priority", "priority.lock.json")))
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != lock["labels.json"]:
        raise SystemExit("priority lock violation: labels.json changed")
    return json.load(open(path))


def stated_priorities(raw):
    """key -> priority exactly as the model emitted it (None if absent)."""
    text = (raw.get("envelope") or {}).get("result") or ""
    recs, _ = run.extract_json_array(text)
    out = {}
    for r in recs or []:
        if isinstance(r, dict) and r.get("kind") == "Action" and r.get("key"):
            p = str((r.get("attrs") or {}).get("priority") or "").strip().lower()
            out[str(r["key"])] = p or None
    return out


def score_run(rid, fx, labels, split="test"):
    raw_dir = os.path.join(run.RESULTS, "raw", rid)
    rows = []
    for f in sorted(os.listdir(raw_dir)):
        if not f.endswith(".json") or f == "meta.json":
            continue
        raw = json.load(open(os.path.join(raw_dir, f)))
        sid = raw["scenario"]
        sdir = os.path.join(fx, sid)
        scn = json.load(open(os.path.join(sdir, "scenario.json")))
        if scn["split"] != split:
            continue
        gold = json.load(open(os.path.join(sdir, "expected.json")))
        recs, _ = run.extract_json_array(
            (raw.get("envelope") or {}).get("result") or "")
        valid = [r for r in recs or [] if not run.schema.validate_record(r)]
        g = score.build_graph(valid, today=scn.get("today"))
        actions = score.open_actions(g)
        pairs, _, _ = score.match_commitments(gold["commitments"], actions)
        stated = stated_priorities(raw)
        for p in pairs:
            tid = "%s#%d" % (sid, p["gold"])
            node = g.nodes[p["pred"]]
            key = node["id"].split(":action:", 1)[-1]
            want = labels[tid]["priority"]
            st = next((v for k, v in stated.items()
                       if run.score.graphlib.slug(k) == key), None)
            shown = (node.get("attrs") or {}).get("priority")
            rows.append({"task": tid, "want": want, "stated": st,
                         "shown": shown})
    return rows


def summarize(rows):
    n = len(rows)

    def acc(field):
        ok = sum(1 for r in rows if r[field] == r["want"])
        off2 = sum(1 for r in rows if r[field] in LEVEL
                   and abs(LEVEL[r[field]] - LEVEL[r["want"]]) == 2)
        return ok, off2
    s_ok, s_off2 = acc("stated")
    v_ok, v_off2 = acc("shown")
    missing = sum(1 for r in rows if r["stated"] not in LEVEL)
    under = sum(1 for r in rows if r["shown"] in LEVEL
                and LEVEL[r["shown"]] > LEVEL[r["want"]])
    over = sum(1 for r in rows if r["shown"] in LEVEL
               and LEVEL[r["shown"]] < LEVEL[r["want"]])
    by_level = {}
    for lv in LEVEL:
        sub = [r for r in rows if r["want"] == lv]
        by_level[lv] = [sum(1 for r in sub if r["shown"] == lv), len(sub)]
    return {"pairs": n, "stated_exact": [s_ok, n], "stated_off_by_two": s_off2,
            "missing_priority": missing, "shown_exact": [v_ok, n],
            "shown_off_by_two": v_off2, "shown_too_low": under,
            "shown_too_high": over, "shown_correct_by_level": by_level}


def main(run_ids):
    labels = load_labels()
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        fx = score_corrected.corrected_fixtures(tmp)
        for rid in run_ids:
            rows = score_run(rid, fx, labels)
            out[rid] = {"summary": summarize(rows), "rows": rows}
            print(rid, json.dumps(out[rid]["summary"]))
    path = os.path.join(run.RESULTS, "heldout_v2-priority.json")
    json.dump(out, open(path, "w"), indent=1, sort_keys=True)
    print("->", path)


if __name__ == "__main__":
    main(sys.argv[1:])
