#!/usr/bin/env python3
"""Tests for M8 hardening: validator, audit log, preflight. Stdlib unittest."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audit  # noqa: E402
import preflight  # noqa: E402
import validate_config as vc  # noqa: E402


class TestValidator(unittest.TestCase):
    def test_clean_config(self):
        cfg = {"chat_tools": "Read,Agent", "revise_tools": "Read,Edit,Agent",
               "poll_tools": "Read,Edit,Agent", "base_tools": "Read,Edit,Agent"}
        self.assertEqual(vc.validate(cfg), [])

    def test_missing_baseline_is_error(self):
        cfg = {"chat_tools": "Read"}  # missing Agent
        f = vc.validate(cfg)
        self.assertTrue(any(x["level"] == "error" and x["field"] == "chat_tools"
                            for x in f))

    def test_unknown_action_tool_warns(self):
        cfg = {"action_tools": {"message_send": "mcp__x__send"}}
        f = vc.validate(cfg, available_tools={"mcp__y__other"})
        self.assertTrue(any(x["level"] == "warning" and x["field"] == "action_tools"
                            for x in f))

    def test_empty_action_tool_warns(self):
        f = vc.validate({"action_tools": {"message_send": ""}})
        self.assertTrue(any(x["field"] == "action_tools" for x in f))

    def test_bad_live_refresh(self):
        self.assertTrue(any(x["level"] == "error"
                            for x in vc.validate({"live_refresh_seconds": "soon"})))
        self.assertTrue(any(x["level"] == "warning"
                            for x in vc.validate({"live_refresh_seconds": 1})))

    def test_invalid_json_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "config.json")
            with open(p, "w") as f:
                f.write("{ not json ]")
            findings = vc.validate_file(p)
            self.assertTrue(any(x["level"] == "error" for x in findings))

    def test_missing_file_is_warning_not_error(self):
        with tempfile.TemporaryDirectory() as d:
            findings = vc.validate_file(os.path.join(d, "nope.json"))
            self.assertTrue(findings and findings[0]["level"] == "warning")


class TestAudit(unittest.TestCase):
    def test_append_and_read(self):
        with tempfile.TemporaryDirectory() as d:
            audit.record(d, "E1:ticket_update", "approved", from_status="pending",
                         actor="dashboard")
            audit.record(d, "E1:ticket_update", "failed", from_status="approved",
                         actor="system", detail="api error")
            all_ev = audit.read_log(d)
            self.assertEqual(len(all_ev), 2)
            self.assertEqual(all_ev[0]["to"], "approved")
            self.assertEqual(all_ev[1]["detail"], "api error")

    def test_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            audit.record(d, "E1", "approved")
            first = open(os.path.join(d, audit.LOG_FILE)).read()
            audit.record(d, "E2", "rejected")
            second = open(os.path.join(d, audit.LOG_FILE)).read()
            # original line is still present verbatim (never rewritten)
            self.assertTrue(second.startswith(first))

    def test_filter_by_entry(self):
        with tempfile.TemporaryDirectory() as d:
            audit.record(d, "A", "approved")
            audit.record(d, "B", "rejected")
            self.assertEqual(len(audit.read_log(d, entry_id="A")), 1)

    def test_tolerates_corrupt_line(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, audit.LOG_FILE), "w") as f:
                f.write("not json\n")
                f.write(json.dumps({"entry_id": "X", "to": "approved"}) + "\n")
            self.assertEqual(len(audit.read_log(d)), 1)


class TestPreflight(unittest.TestCase):
    def test_all_reachable(self):
        s = preflight.summarize([{"connector": "jira", "ok": True},
                                 {"connector": "slack", "ok": True}])
        self.assertEqual(s["available"], ["jira", "slack"])
        self.assertEqual(s["unavailable"], [])
        self.assertTrue(preflight.should_continue(s))

    def test_some_unavailable_reported(self):
        s = preflight.summarize([{"connector": "jira", "ok": True},
                                 {"connector": "slack", "ok": False,
                                  "error": "401"}])
        self.assertEqual([u["connector"] for u in s["unavailable"]], ["slack"])
        self.assertIn("unavailable", s["report"])
        self.assertTrue(preflight.should_continue(s))  # jira still works

    def test_none_reachable_stops(self):
        s = preflight.summarize([{"connector": "jira", "ok": False, "error": "x"}])
        self.assertFalse(preflight.should_continue(s))

    def test_empty(self):
        s = preflight.summarize([])
        self.assertEqual(s["report"], "no connectors to probe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
