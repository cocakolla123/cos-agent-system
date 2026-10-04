#!/usr/bin/env python3
"""Statistical comparison of two eval runs. Stdlib only, seeded, deterministic.

    python3 evals/stats.py results/A.json results/B.json --split test

Two instruments, both scenario-level resampling so correlated errors within a
scenario never inflate confidence:

- **Bootstrap 95% CI** on each run's micro-F1 (resample scenarios with
  replacement, recompute pooled F1).
- **Paired permutation test** on the micro-F1 difference: per scenario, swap
  the two runs' (tp, fp, fn) with p=0.5 and recompute the pooled difference;
  the two-sided p-value is the share of permuted |diffs| >= the observed
  |diff|. This is the honest answer to "is 0.909 vs 0.875 real or noise?" —
  the question the first 18-scenario test split couldn't answer.
"""

from __future__ import annotations

import argparse
import json
import random


def _micro_f1(rows):
    tp = sum(r["tp"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    fn = sum(r["fn"] for r in rows)
    p = tp / float(tp + fp) if (tp + fp) else 1.0
    r = tp / float(tp + fn) if (tp + fn) else 1.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def bootstrap_ci(rows, n_boot=10000, seed=7, alpha=0.05):
    """(point, lo, hi) for micro-F1 under scenario-level bootstrap."""
    rng = random.Random(seed)
    k = len(rows)
    samples = []
    for _ in range(n_boot):
        draw = [rows[rng.randrange(k)] for _ in range(k)]
        samples.append(_micro_f1(draw))
    samples.sort()
    lo = samples[int((alpha / 2) * n_boot)]
    hi = samples[min(int((1 - alpha / 2) * n_boot), n_boot - 1)]
    return _micro_f1(rows), lo, hi


def paired_permutation(rows_a, rows_b, n_perm=10000, seed=7):
    """(observed_diff, p_value) for micro-F1(A) - micro-F1(B), paired by
    scenario id. Scenarios present in only one run are excluded."""
    by_a = {r["scenario"]: r for r in rows_a}
    by_b = {r["scenario"]: r for r in rows_b}
    ids = sorted(set(by_a) & set(by_b))
    pairs = [(by_a[i], by_b[i]) for i in ids]
    observed = _micro_f1([p[0] for p in pairs]) - _micro_f1([p[1] for p in pairs])
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        pa, pb = [], []
        for a, b in pairs:
            if rng.random() < 0.5:
                a, b = b, a
            pa.append(a)
            pb.append(b)
        if abs(_micro_f1(pa) - _micro_f1(pb)) >= abs(observed) - 1e-12:
            hits += 1
    return observed, hits / float(n_perm)


def _load(path, split):
    data = json.load(open(path))
    rows = [r for r in data["scenarios"] if split in ("all", r["split"])]
    label = data["meta"].get("run_id", path)
    return label, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    ap.add_argument("--split", default="test", choices=("dev", "test", "all"))
    ap.add_argument("--boot", type=int, default=10000)
    args = ap.parse_args()
    (la, ra), (lb, rb) = _load(args.run_a, args.split), _load(args.run_b, args.split)
    for label, rows in ((la, ra), (lb, rb)):
        f1, lo, hi = bootstrap_ci(rows, n_boot=args.boot)
        print("%-40s n=%d  micro-F1 %.3f  [%.3f, %.3f] 95%% CI"
              % (label, len(rows), f1, lo, hi))
    diff, p = paired_permutation(ra, rb, n_perm=args.boot)
    print("paired diff (A-B) %.4f   two-sided p = %.4f  (%s)" % (
        diff, p, "significant at 0.05" if p < 0.05 else "NOT significant"))


if __name__ == "__main__":
    main()
