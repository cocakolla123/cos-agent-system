"""Hand-computed cases for the bootstrap/permutation instruments."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import stats  # noqa: E402


def row(sid, tp, fp, fn):
    return {"scenario": sid, "tp": tp, "fp": fp, "fn": fn, "split": "test"}


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


if __name__ == "__main__":
    unittest.main()
