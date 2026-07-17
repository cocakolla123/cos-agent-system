#!/usr/bin/env python3
"""Tests for multi-account connectors (M10). Stdlib unittest only."""

import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import accounts  # noqa: E402
import factory  # noqa: E402
import graph  # noqa: E402


def _t(day):
    return dt.datetime(2026, 8, day, 12, 0, 0, tzinfo=dt.timezone.utc)


TWO_GMAILS = {
    "connector_accounts": [
        {"id": "gmail-personal", "kind": "email", "label": "Personal Gmail",
         "account": "me@gmail.com", "workspace": "personal",
         "tool_prefix": "mcp__gmail_personal__",
         "probe_tool": "mcp__gmail_personal__search_threads"},
        {"id": "gmail-work", "kind": "email", "label": "Work Gmail",
         "account": "me@acme.com", "workspace": "employer",
         "tool_prefix": "mcp__gmail_work__",
         "probe_tool": "mcp__gmail_work__search_threads"},
    ]
}


class TestSchema(unittest.TestCase):
    def test_load_normalizes(self):
        accs = accounts.load_accounts(TWO_GMAILS)
        self.assertEqual([a["id"] for a in accs], ["gmail-personal", "gmail-work"])
        self.assertEqual(accs[1]["workspace"], "employer")

    def test_validate_clean(self):
        self.assertEqual(accounts.validate_accounts(
            TWO_GMAILS, known_workspaces={"personal", "employer"}), [])

    def test_validate_duplicate_and_missing_prefix(self):
        cfg = {"connector_accounts": [
            {"id": "a", "kind": "email", "tool_prefix": ""},
            {"id": "a", "kind": "email", "tool_prefix": "mcp__x__"},
        ]}
        f = accounts.validate_accounts(cfg)
        msgs = " ".join(x["message"] for x in f)
        self.assertIn("duplicate", msgs)
        self.assertIn("tool_prefix", msgs)

    def test_validate_unknown_workspace_warns(self):
        f = accounts.validate_accounts(TWO_GMAILS, known_workspaces={"personal"})
        self.assertTrue(any("unknown workspace" in x["message"] for x in f))

    def test_workspace_lookup_and_unbound(self):
        self.assertEqual(
            [a["id"] for a in accounts.accounts_for_workspace(TWO_GMAILS, "employer")],
            ["gmail-work"])
        cfg = {"connector_accounts": [{"id": "x", "tool_prefix": "mcp__x__"}]}
        self.assertEqual([a["id"] for a in accounts.unbound_accounts(cfg)], ["x"])


class TestStatus(unittest.TestCase):
    def test_write_read_merge(self):
        with tempfile.TemporaryDirectory() as d:
            accounts.write_status(d, "gmail-personal", True,
                                  identity="me@gmail.com", now=_t(1))
            accounts.write_status(d, "gmail-work", False, error="401", now=_t(1))
            st = accounts.read_status(d)
            self.assertTrue(st["gmail-personal"]["ok"])
            self.assertEqual(st["gmail-work"]["error"], "401")

    def test_summarize_states(self):
        with tempfile.TemporaryDirectory() as d:
            accounts.write_status(d, "gmail-personal", True,
                                  identity="me@gmail.com", now=_t(1))
            accounts.write_status(d, "gmail-work", False, error="401", now=_t(1))
            rows, report = accounts.summarize_accounts(
                TWO_GMAILS, accounts.read_status(d))
            states = {r["id"]: r["state"] for r in rows}
            self.assertEqual(states["gmail-personal"], "connected")
            self.assertEqual(states["gmail-work"], "needs_auth")
            self.assertIn("1 connected, 1 need auth", report)

    def test_summarize_declined_wins(self):
        rows, _ = accounts.summarize_accounts(TWO_GMAILS, {},
                                              declined_ids=["gmail-work"])
        states = {r["id"]: r["state"] for r in rows}
        self.assertEqual(states["gmail-work"], "declined")
        self.assertEqual(states["gmail-personal"], "unknown")


class TestDetectInstances(unittest.TestCase):
    def test_two_gmail_prefixes_flagged(self):
        tools = ["mcp__gmail_personal__search_threads",
                 "mcp__gmail_personal__create_draft",
                 "mcp__gmail_work__search_threads",
                 "mcp__jira__search_issues"]
        inst = accounts.detect_instances(tools)
        self.assertEqual(len(inst["email"]), 2)
        self.assertEqual(accounts.multi_account_kinds(inst), ["email"])

    def test_single_instance_not_flagged(self):
        inst = accounts.detect_instances(["mcp__gmail__search_threads"])
        self.assertEqual(accounts.multi_account_kinds(inst), [])

    def test_non_mcp_ignored(self):
        self.assertEqual(accounts.detect_instances(["Read", "Edit"]), {})


class TestAuthQueue(unittest.TestCase):
    def test_enqueue_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            accounts.enqueue_auth_request(d, "gmail-work", reason="r1", now=_t(1))
            accounts.enqueue_auth_request(d, "gmail-work", reason="r2", now=_t(2))
            self.assertEqual(len(accounts.pending_auth_requests(d)), 1)

    def test_snooze_resurfaces(self):
        with tempfile.TemporaryDirectory() as d:
            accounts.enqueue_auth_request(d, "gmail-work", now=_t(1))
            accounts.resolve_auth_request(d, "gmail-work", "snoozed", now=_t(1))
            self.assertEqual(accounts.pending_auth_requests(d), [])
            accounts.enqueue_auth_request(d, "gmail-work", now=_t(2))
            self.assertEqual(len(accounts.pending_auth_requests(d)), 1)

    def test_declined_is_permanent(self):
        with tempfile.TemporaryDirectory() as d:
            accounts.enqueue_auth_request(d, "gmail-work", now=_t(1))
            accounts.resolve_auth_request(d, "gmail-work", "declined", now=_t(1))
            self.assertTrue(accounts.is_declined(d, "gmail-work"))
            # re-enqueue attempt is refused
            self.assertIsNone(accounts.enqueue_auth_request(d, "gmail-work",
                                                            now=_t(2)))
            self.assertEqual(accounts.pending_auth_requests(d), [])
            self.assertEqual(accounts.declined_ids(d), ["gmail-work"])

    def test_authorized_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            accounts.enqueue_auth_request(d, "gmail-work", now=_t(1))
            r = accounts.resolve_auth_request(d, "gmail-work", "authorized",
                                              now=_t(1))
            self.assertEqual(r["outcome"], "authorized")
            self.assertEqual(accounts.pending_auth_requests(d), [])

    def test_bad_outcome_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                accounts.resolve_auth_request(d, "x", "maybe")


class TestFactoryPerAccountAgents(unittest.TestCase):
    def test_two_accounts_two_agents_disjoint_grants(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "T-1", now=_t(1))  # non-empty graph
        specs = factory.propose_agents(
            g, accounts=accounts.load_accounts(TWO_GMAILS))
        names = [s["name"] for s in specs]
        self.assertIn("cos-comms-personal", names)
        self.assertIn("cos-comms-employer", names)
        pers = [s for s in specs if s["name"] == "cos-comms-personal"][0]
        work = [s for s in specs if s["name"] == "cos-comms-employer"][0]
        pers_tools = " ".join(pers["allowed_tools"])
        work_tools = " ".join(work["allowed_tools"])
        # isolation: each grant contains ONLY its own account's prefix
        self.assertIn("mcp__gmail_personal__", pers_tools)
        self.assertNotIn("mcp__gmail_work__", pers_tools)
        self.assertIn("mcp__gmail_work__", work_tools)
        self.assertNotIn("mcp__gmail_personal__", work_tools)
        self.assertEqual(pers["workspace"], "personal")
        self.assertEqual(work["workspace"], "employer")

    def test_no_accounts_no_per_account_agents(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "T-1", now=_t(1))
        names = [s["name"] for s in factory.propose_agents(g)]
        self.assertFalse(any(n.startswith("cos-comms-") for n in names))


class TestConfigExample(unittest.TestCase):
    def test_config_example_valid_and_clean(self):
        path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "config.example.json")
        with open(path) as f:
            cfg = json.load(f)
        # accounts section (if present) validates clean
        self.assertFalse([x for x in accounts.validate_accounts(cfg)
                          if x["level"] == "error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
