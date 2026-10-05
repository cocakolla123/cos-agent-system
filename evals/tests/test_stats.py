"""Hand-computed cases for the bootstrap/permutation instruments."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import stats  # noqa: E402


def row(sid, tp, fp, fn, base=None):
    return {"scenario": sid, "base_id": base or sid, "tp": tp, "fp": fp,
            "fn": fn, "split": "test"}


class TestMicroF1(unittest.TestCase):
    def test_hand_computed(self):
        rows = [row("a", 1, 0, 0), row("b", 1, 1, 1)]
        # tp=2 fp=1 fn=1 -> P=2/3 R=2/3 -> F1=2/3
        self.assertAlmostEqual(stats._micro_f1(rows), 2 / 3.0)

    def test_empty_predictions_perfect_when_no_gold(self):
        self.assertEqual(stats._micro_f1([row("a", 0, 0, 0)]), 1.0)


class TestBootstrap(unittest.TestCase):
    def test_identical_rows_give_degenerate_ci(self):
        rows = [row(str(i), 1, 1, 1) for i in range(10)]
        f1, lo, hi = stats.bootstrap_ci(rows, n_boot=500, seed=1)
        self.assertAlmostEqual(f1, 0.5)
        self.assertAlmostEqual(lo, 0.5)
        self.assertAlmostEqual(hi, 0.5)

    def test_ci_brackets_point_and_is_deterministic(self):
        rows = [row(str(i), 1, 0, 0) for i in range(8)] + [row("x", 0, 2, 2)]
        a = stats.bootstrap_ci(rows, n_boot=1000, seed=42)
        b = stats.bootstrap_ci(rows, n_boot=1000, seed=42)
        self.assertEqual(a, b)
        f1, lo, hi = a
        self.assertLessEqual(lo, f1)
        self.assertLessEqual(f1, hi)
        self.assertLess(lo, hi)


class TestPermutation(unittest.TestCase):
    def test_identical_runs_diff_zero_p_one(self):
        rows = [row(str(i), 1, 0, 0) for i in range(6)]
        diff, p = stats.paired_permutation(rows, list(rows), n_perm=400, seed=3)
        self.assertEqual(diff, 0.0)
        self.assertEqual(p, 1.0)

    def test_consistent_large_gap_is_significant(self):
        a = [row(str(i), 1, 0, 0) for i in range(12)]          # perfect
        b = [row(str(i), 0, 1, 1) for i in range(12)]          # all wrong
        diff, p = stats.paired_permutation(a, b, n_perm=2000, seed=3)
        self.assertAlmostEqual(diff, 1.0)
        self.assertLess(p, 0.01)

    def test_single_scenario_flip_is_not_significant(self):
        a = [row(str(i), 1, 0, 0) for i in range(10)]
        b = [row(str(i), 1, 0, 0) for i in range(9)] + [row("9", 0, 1, 1)]
        _, p = stats.paired_permutation(a, b, n_perm=2000, seed=3)
        self.assertGreater(p, 0.05)

    def test_pairs_by_scenario_id_not_order(self):
        a = [row("x", 1, 0, 0), row("y", 0, 1, 1)]
        b = list(reversed(a))
        diff, _ = stats.paired_permutation(a, b, n_perm=100, seed=3)
        self.assertEqual(diff, 0.0)


def _triple(rows):
    """Three cast rotations of each story: same counts, same base_id."""
    out = []
    for r in rows:
        for suf in ("", "-b", "-c"):
            out.append(row(r["scenario"] + suf, r["tp"], r["fp"], r["fn"],
                           base=r["scenario"]))
    return out


class TestClusterUnit(unittest.TestCase):
    def test_base_of_strips_rotation_suffix_when_missing(self):
        r = {"scenario": "injection-1-b"}
        self.assertEqual(stats.base_of(r), "injection-1")
        self.assertEqual(stats.base_of({"scenario": "injection-1",
                                        "base_id": "injection-1"}),
                         "injection-1")

    def test_copying_a_story_three_times_changes_nothing_at_story_level(self):
        # 8 perfect stories + 1 bad story. At the story level, tripling every
        # story into rotations must leave point and interval IDENTICAL; at the
        # fixture level the interval narrows, which is exactly the
        # overconfidence the outside review flagged.
        base = [row("s%d" % i, 1, 0, 0) for i in range(8)] + [row("bad", 0, 2, 2)]
        tripled = _triple(base)
        one = stats.cluster_bootstrap_ci(base, n_boot=2000, seed=11)
        three = stats.cluster_bootstrap_ci(tripled, n_boot=2000, seed=11)
        self.assertEqual(one, three)
        _, lo1, hi1 = stats.bootstrap_ci(base, n_boot=2000, seed=11)
        _, lo3, hi3 = stats.bootstrap_ci(tripled, n_boot=2000, seed=11)
        self.assertLess(hi3 - lo3, hi1 - lo1)  # fixture CI narrows: too confident

    def test_cluster_permutation_exact_two_clusters_hand_computed(self):
        # A perfect on both stories (pooled F1 1.0); B fails both completely
        # (pooled F1 0.0). Observed diff 1.0. The 4 exact assignments give
        # |diff| = 1, 0, 0, 1 (single swaps mix one good and one bad story
        # into EACH side, pooled F1 0.5 both, diff 0). So p = 2/4 exactly.
        a = [row("x", 1, 0, 0), row("y", 1, 0, 0)]
        b = [row("x", 0, 1, 1), row("y", 0, 1, 1)]
        diff, p, k, exact = stats.cluster_paired_permutation(a, b)
        self.assertTrue(exact)
        self.assertEqual(k, 2)
        self.assertAlmostEqual(diff, 1.0)
        self.assertEqual(p, 0.5)

    def test_identical_cluster_cannot_add_significance(self):
        # Story x is identical in both runs; only y differs. Swapping x
        # changes nothing, so every assignment reproduces |observed| and
        # p = 1.0: one differing story is never significant.
        a = [row("x", 1, 0, 0), row("y", 1, 0, 0)]
        b = [row("x", 1, 0, 0), row("y", 0, 1, 1)]
        diff, p, k, exact = stats.cluster_paired_permutation(a, b)
        self.assertAlmostEqual(diff, 0.5)
        self.assertEqual(p, 1.0)

    def test_tripling_rotations_does_not_shrink_cluster_p(self):
        a = [row("s%d" % i, 1, 0, 0) for i in range(6)]
        b = [row("s%d" % i, 0, 1, 1) for i in range(6)]
        _, p_one, k1, _ = stats.cluster_paired_permutation(a, b)
        _, p_three, k3, _ = stats.cluster_paired_permutation(
            _triple(a), _triple(b))
        self.assertEqual(k1, k3)          # still 6 units of evidence
        self.assertEqual(p_one, p_three)  # story-level p unchanged
        # fixture-level p DOES shrink on the tripled data: the overconfidence
        _, p_fix = stats.paired_permutation(_triple(a), _triple(b),
                                            n_perm=4000, seed=5)
        self.assertLess(p_fix, p_three)

    def test_identical_runs_cluster_p_one(self):
        a = _triple([row("s%d" % i, 1, 0, 0) for i in range(4)])
        diff, p, k, exact = stats.cluster_paired_permutation(a, list(a))
        self.assertEqual((diff, p, k, exact), (0.0, 1.0, 4, True))


if __name__ == "__main__":
    unittest.main()
