#!/usr/bin/env python3
"""Tests for the self-learning correction loop core (M9). Stdlib unittest."""

import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402
import learning  # noqa: E402


def _t(day, hour=12):
    return dt.datetime(2026, 7, day, hour, 0, 0, tzinfo=dt.timezone.utc)


class TestClassifier(unittest.TestCase):
    def test_detects_missing_email(self):
        h = learning.classify_feedback(
            "you're missing the email from Acme about the contract")
        self.assertIsNotNone(h)
        self.assertEqual(h["connector_hint"], "email")
        self.assertIn("acme", h["keywords"])

    def test_detects_wrong_ticket(self):
        h = learning.classify_feedback("that jira ticket status is wrong")
        self.assertIsNotNone(h)
        self.assertEqual(h["connector_hint"], "ticketing")

    def test_detects_not_showing(self):
        h = learning.classify_feedback(
            "why isn't yesterday's meeting showing on the dashboard")
        self.assertIsNotNone(h)
        self.assertEqual(h["connector_hint"], "calendar")

    def test_normal_question_does_not_classify(self):
        self.assertIsNone(learning.classify_feedback("what's on my calendar today?"))
        self.assertIsNone(learning.classify_feedback("summarize the Acme project"))
        self.assertIsNone(learning.classify_feedback(""))


class TestQueue(unittest.TestCase):
    def test_enqueue_pending_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            rec = learning.make_correction(
                "you missed the email from Acme", now=_t(1))
            learning.enqueue(d, rec)
            self.assertEqual(len(learning.pending(d)), 1)
            self.assertTrue(learning.resolve(d, rec["id"]))
            self.assertEqual(learning.pending(d), [])

    def test_resolve_unknown_id(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(learning.resolve(d, "nope"))

    def test_correction_id_deterministic_shape(self):
        rec = learning.make_correction("you missed the Acme email", now=_t(1))
        self.assertTrue(rec["id"].startswith("corr-"))
        self.assertEqual(rec["status"], "pending")


class TestDiagnose(unittest.TestCase):
    def _rec(self, text="you're missing the acme contract email"):
        return learning.make_correction(text, now=_t(2))

    def test_correlation_hypothesis_when_node_uncorrelated(self):
        g = graph.Graph()
        g.upsert_node("Document", "emp", "acme-contract",
                      name="Acme contract email", source="email", now=_t(1))
        f = learning.diagnose_checks(self._rec(), g)
        self.assertEqual(f[0]["hypothesis"], "correlation")
        self.assertTrue(f[0]["likely"])

    def test_normalization_when_node_correlated(self):
        g = graph.Graph()
        n = g.upsert_node("Document", "emp", "acme-contract",
                          name="Acme contract email", source="email", now=_t(1))
        o = g.upsert_node("Objective", "emp", "acme-deal", now=_t(1))
        g.upsert_edge(n["id"], o["id"], "part_of", now=_t(1))
        f = learning.diagnose_checks(self._rec(), g)
        self.assertEqual(f[0]["hypothesis"], "normalization")

    def test_connector_down(self):
        g = graph.Graph()
        pf = {"unavailable": [{"connector": "email", "error": "401"}]}
        f = learning.diagnose_checks(self._rec(), g, preflight_summary=pf)
        self.assertIn("connector_down", [x["hypothesis"] for x in f])

    def test_staleness_when_nothing_recent(self):
        g = graph.Graph()
        g.upsert_node("Document", "emp", "old-email", source="email", now=_t(1))
        f = learning.diagnose_checks(
            self._rec("you missed a brand new email from zzz"), g,
            last_research_ts="2026-07-05T00:00:00Z")
        self.assertIn("staleness", [x["hypothesis"] for x in f])

    def test_coverage_gap_when_no_trace(self):
        g = graph.Graph()
        f = learning.diagnose_checks(self._rec(), g)
        self.assertEqual(f[0]["hypothesis"], "coverage_gap")
        self.assertTrue(f[0]["likely"])


class TestLedger(unittest.TestCase):
    def test_record_and_recurring(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = learning.make_correction("you missed an email from A", now=_t(1))
            r2 = learning.make_correction("missing the email from B", now=_t(2))
            learning.record_outcome(d, r1, "coverage_gap", "widened folder scope",
                                    verified=True, now=_t(1))
            self.assertEqual(learning.recurring(d), [])  # once is not recurring
            learning.record_outcome(d, r2, "coverage_gap", "widened again",
                                    verified=True, now=_t(2))
            self.assertEqual(learning.recurring(d), ["email:coverage_gap"])


class TestGuardrails(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        for rel in ("commands", "dashboard"):
            os.makedirs(os.path.join(self.root, rel), exist_ok=True)

    def test_normal_module_allowed(self):
        self.assertTrue(learning.is_change_allowed(
            self.root, os.path.join(self.root, "dashboard", "research.py")))
        self.assertTrue(learning.is_change_allowed(
            self.root, "commands/cos-research.md"))

    def test_approval_surface_blocked(self):
        for rel in ("commands/cos-approve.md", "commands/cos-approve-confirmed.md",
                    "dashboard/audit.py", "dashboard/learning.py"):
            self.assertFalse(learning.is_change_allowed(self.root, rel), rel)

    def test_approval_policy_blocked_anywhere(self):
        self.assertFalse(learning.is_change_allowed(
            self.root, os.path.join(self.root, "dashboard", "workspace",
                                    "APPROVAL_POLICY.md")))

    def test_outside_template_blocked(self):
        self.assertFalse(learning.is_change_allowed(self.root, "/etc/hosts"))
        self.assertFalse(learning.is_change_allowed(
            self.root, os.path.join(self.root, "..", "other.py")))


class TestSnapshotRollback(unittest.TestCase):
    def test_snapshot_mutate_restore_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "module.py")
            with open(target, "w") as f:
                f.write("original = True\n")
            token = learning.snapshot(d, [target], now=_t(1))
            with open(target, "w") as f:
                f.write("broken syntax here(((\n")
            restored = learning.restore(d, token)
            self.assertEqual(restored, [os.path.abspath(target)])
            with open(target) as f:
                self.assertEqual(f.read(), "original = True\n")

    def test_discard_marks_kept(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "m.py")
            open(target, "w").write("x=1\n")
            token = learning.snapshot(d, [target], now=_t(1))
            marker = learning.discard(d, token)
            self.assertTrue(os.path.exists(marker))


class TestToggle(unittest.TestCase):
    def test_defaults_on(self):
        self.assertTrue(learning.self_learning_enabled({}))
        self.assertTrue(learning.self_modify_enabled({}))

    def test_master_switch_off_disables_both(self):
        cfg = {"self_learning": False, "self_modify_code": True}
        self.assertFalse(learning.self_learning_enabled(cfg))
        self.assertFalse(learning.self_modify_enabled(cfg))

    def test_code_subswitch(self):
        cfg = {"self_learning": True, "self_modify_code": False}
        self.assertTrue(learning.self_learning_enabled(cfg))
        self.assertFalse(learning.self_modify_enabled(cfg))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestGuardrailIntegrity(unittest.TestCase):
    def _root(self, d):
        os.makedirs(os.path.join(d, "commands"), exist_ok=True)
        os.makedirs(os.path.join(d, "dashboard"), exist_ok=True)
        for rel in learning.GUARDRAIL_PATHS:
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write("original %s\n" % rel)
        return d

    def test_baseline_then_clean(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            ws = os.path.join(d, "ws")
            learning.write_guardrail_baseline(ws, root, now=_t(1))
            drifted, has = learning.verify_guardrails(ws, root)
            self.assertTrue(has)
            self.assertEqual(drifted, [])

    def test_drift_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            ws = os.path.join(d, "ws")
            learning.write_guardrail_baseline(ws, root, now=_t(1))
            with open(os.path.join(root, "commands", "cos-approve.md"), "a") as f:
                f.write("tampered\n")
            drifted, has = learning.verify_guardrails(ws, root)
            self.assertTrue(has)
            self.assertEqual(drifted, ["commands/cos-approve.md"])

    def test_no_baseline_is_not_alarm(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            drifted, has = learning.verify_guardrails(os.path.join(d, "ws"), root)
            self.assertFalse(has)
            self.assertEqual(drifted, [])

    def test_rebaseline_clears_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            ws = os.path.join(d, "ws")
            learning.write_guardrail_baseline(ws, root, now=_t(1))
            with open(os.path.join(root, "dashboard", "audit.py"), "a") as f:
                f.write("changed\n")
            self.assertTrue(learning.verify_guardrails(ws, root)[0])
            learning.write_guardrail_baseline(ws, root, now=_t(2))
            self.assertEqual(learning.verify_guardrails(ws, root)[0], [])
