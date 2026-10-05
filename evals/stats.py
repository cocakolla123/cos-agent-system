#!/usr/bin/env python3
"""Statistical comparison of two eval runs. Stdlib only, seeded, deterministic.

    python3 evals/stats.py results/A.json results/B.json --split test

The unit of evidence is the BASE STORY, not the fixture. The dataset is 36
hand-authored stories, each instantiated in three cast rotations; the
rotations share plot, labels, and failure modes, so treating them as
independent samples overstates confidence (an outside review caught exactly
that in this repo's first reports). Default instruments:

- cluster bootstrap 95% CI: resample base stories with replacement, carrying
  every fixture of a drawn story together, recompute pooled micro-F1;
- cluster paired permutation test: swap WHOLE stories between the two runs;
  with 20 or fewer story clusters every one of the 2^k assignments is
  enumerated exactly (2^18 = 262,144 on the current test split).

Fixture-level versions remain behind --unit fixture, labeled
anti-conservative, only for comparison against the older reports.
"""

from __future__ import annotations

import argparse
import json
import random


def base_of(row):
    """The statistical unit. Cast rotations of one story are the same
    evidence three times, so they must move together in every resample."""
    bid = row.get("base_id")
    if bid:
        return bid
    sid = row["scenario"]
    return sid[:-2] if sid.endswith(("-b", "-c")) else sid


def _clusters(rows):
    by = {}
    for r in rows:
        by.setdefault(base_of(r), []).append(r)
    return [by[k] for k in sorted(by)]


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


def cluster_bootstrap_ci(rows, n_boot=10000, seed=7, alpha=0.05):
    """(point, lo, hi) for micro-F1 under STORY-level bootstrap: base stories
    are resampled with replacement and every fixture of a drawn story comes
    along. This is the default unit; see the module docstring for why."""
    rng = random.Random(seed)
    clusters = _clusters(rows)
    k = len(clusters)
    samples = []
    for _ in range(n_boot):
        draw = []
        for _ in range(k):
            draw.extend(clusters[rng.randrange(k)])
        samples.append(_micro_f1(draw))
    samples.sort()
    lo = samples[int((alpha / 2) * n_boot)]
    hi = samples[min(int((1 - alpha / 2) * n_boot), n_boot - 1)]
    return _micro_f1(rows), lo, hi


def _f1_from(tp, fp, fn):
    p = tp / float(tp + fp) if (tp + fp) else 1.0
    r = tp / float(tp + fn) if (tp + fn) else 1.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def cluster_paired_permutation(rows_a, rows_b, n_perm=10000, seed=7):
    """(observed_diff, p_value, n_clusters, exact) for micro-F1(A) - micro-F1(B),
    swapping WHOLE base stories between runs. With <= 20 clusters every one of
    the 2^k assignments is enumerated exactly; above that, sampled."""
    by_a = {r["scenario"]: r for r in rows_a}
    by_b = {r["scenario"]: r for r in rows_b}
    ids = sorted(set(by_a) & set(by_b))
    groups = {}
    for i in ids:
        groups.setdefault(base_of(by_a[i]), []).append(i)
    names = sorted(groups)
    k = len(names)
    # per-cluster (tp, fp, fn) totals for each side
    tri = []
    for name in names:
        a = [0, 0, 0]
        b = [0, 0, 0]
        for i in groups[name]:
            for j, key in enumerate(("tp", "fp", "fn")):
                a[j] += by_a[i][key]
                b[j] += by_b[i][key]
        tri.append((tuple(a), tuple(b)))

    def diff_for(swap_mask_bits):
        ta = [0, 0, 0]
        tb = [0, 0, 0]
        for ci in range(k):
            a, b = tri[ci]
            if swap_mask_bits[ci]:
                a, b = b, a
            for j in range(3):
                ta[j] += a[j]
                tb[j] += b[j]
        return _f1_from(*ta) - _f1_from(*tb)

    observed = diff_for([0] * k)
    exact = k <= 20
    hits = 0
    if exact:
        total = 1 << k
        for mask in range(total):
            bits = [(mask >> ci) & 1 for ci in range(k)]
            if abs(diff_for(bits)) >= abs(observed) - 1e-12:
                hits += 1
        p = hits / float(total)
    else:
        rng = random.Random(seed)
        for _ in range(n_perm):
            bits = [rng.randrange(2) for _ in range(k)]
            if abs(diff_for(bits)) >= abs(observed) - 1e-12:
                hits += 1
        p = hits / float(n_perm)
    return observed, p, k, exact


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
    ap.add_argument("--unit", default="story", choices=("story", "fixture"),
                    help="story (default): base stories are the unit of "
                         "evidence. fixture: treats cast rotations of one "
                         "story as independent, which OVERSTATES confidence; "
                         "kept only for comparison with older reports.")
    args = ap.parse_args()
    (la, ra), (lb, rb) = _load(args.run_a, args.split), _load(args.run_b, args.split)
    for label, rows in ((la, ra), (lb, rb)):
        if args.unit == "story":
            f1, lo, hi = cluster_bootstrap_ci(rows, n_boot=args.boot)
            n = len({base_of(r) for r in rows})
            unit = "stories"
        else:
            f1, lo, hi = bootstrap_ci(rows, n_boot=args.boot)
            n, unit = len(rows), "fixtures (anti-conservative)"
        print("%-40s n=%d %s  micro-F1 %.3f  [%.3f, %.3f] 95%% CI"
              % (label, n, unit, f1, lo, hi))
    if args.unit == "story":
        diff, p, k, exact = cluster_paired_permutation(ra, rb, n_perm=args.boot)
        print("paired diff (A-B) %.4f   two-sided p = %.4f  "
              "(%s; %d story clusters, %s)" % (
                  diff, p,
                  "significant at 0.05" if p < 0.05 else "NOT significant",
                  k, "exact enumeration" if exact else "sampled"))
    else:
        diff, p = paired_permutation(ra, rb, n_perm=args.boot)
        print("paired diff (A-B) %.4f   two-sided p = %.4f  (%s; fixture "
              "level, anti-conservative)" % (
                  diff, p,
                  "significant at 0.05" if p < 0.05 else "NOT significant"))


if __name__ == "__main__":
    main()
