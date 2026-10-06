#!/usr/bin/env python3
"""Score saved heldout_v2 runs against CORRECTED labels, as a separate pass.

    python3 evals/heldout_v2/score_corrected.py hv2-v2-haiku hv2-v1 ...

The frozen fixtures and labels.lock.json are never touched. Corrected labels
live in corrections/<story>/expected.json and are themselves frozen by
corrections/corrections.lock.json (see CORRECTIONS.md). This script verifies
that lock, builds a temporary fixtures copy with the corrected labels
overlaid (and a matching temporary lock, so the runner's own lock check
still runs), and writes results/<run_id>-corrected.{json,md}. No model call.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = os.path.dirname(HERE)
sys.path.insert(0, EVALS)

import run     # noqa: E402
import schema  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
CORR = os.path.join(HERE, "corrections")


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def corrected_fixtures(tmp):
    lock = json.load(open(os.path.join(HERE, "labels.lock.json")))
    corr_lock = json.load(open(os.path.join(CORR, "corrections.lock.json")))
    run.verify_label_lock(FIXTURES)          # the frozen set is still intact
    root = os.path.join(tmp, "heldout_v2_corrected")
    fx = os.path.join(root, "fixtures")
    shutil.copytree(FIXTURES, fx)
    for sid, digest in corr_lock["labels"].items():
        src = os.path.join(CORR, sid, "expected.json")
        if _sha(src) != digest:
            raise SystemExit("corrections lock violation: %s" % sid)
        shutil.copy(src, os.path.join(fx, sid, "expected.json"))
        lock["labels"][sid] = digest
        errs = schema.validate_scenario_dir(os.path.join(fx, sid))
        if errs:
            raise SystemExit("corrected label invalid: %s: %s" % (sid, errs))
    json.dump(lock, open(os.path.join(root, "labels.lock.json"), "w"))
    return fx


def main(run_ids):
    with tempfile.TemporaryDirectory() as tmp:
        fx = corrected_fixtures(tmp)
        for rid in run_ids:
            raw_dir = os.path.join(run.RESULTS, "raw", rid)
            meta = json.load(open(os.path.join(raw_dir, "meta.json")))
            meta = dict(meta, fixtures=fx, labels="corrected (CORRECTIONS.md)")
            summary = run.summarize(run.score_raw(raw_dir, meta), meta)
            summary["meta"]["fixtures"] = "evals/heldout_v2 + corrections/"
            base = os.path.join(run.RESULTS, rid + "-corrected")
            run.write_report(summary, base)
            print("corrected labels: %s -> %s.md" % (rid, base))


if __name__ == "__main__":
    main(sys.argv[1:])
