#!/usr/bin/env python3
"""Tests for the multi-workspace model (M3). Stdlib unittest only."""

import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402
import workspaces  # noqa: E402


def _t(day):
    return dt.datetime(2026, 3, day, 12, 0, 0, tzinfo=dt.timezone.utc)


class TestRegistry(unittest.TestCase):
    def test_upsert_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            r = workspaces.Registry()
            r.upsert("Acme", kind="employer", label="Acme Corp",
                     connectors=["jira", "slack"])
            r.upsert("side", kind="personal")
            r.save(d)
            r2 = workspaces.Registry.load(d)
            self.assertEqual(r2.ids(), ["acme", "side"])
            self.assertEqual(r2.get("acme")["label"], "Acme Corp")
            self.assertEqual(r2.active, "acme")  # first upsert becomes active

    def test_missing_file_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            r = workspaces.Registry.load(d)
            self.assertEqual(r.ids(), [])
            self.assertIsNone(r.active)

    def test_strict_is_default(self):
        r = workspaces.Registry()
        r.upsert("emp", kind="employer")
        self.assertTrue(r.is_strict("emp"))
        r.upsert("home", kind="home", isolation="open")
        self.assertFalse(r.is_strict("home"))


class TestIsolation(unittest.TestCase):
    def _graph(self):
        g = graph.Graph()
        g.upsert_node("Person", "employer", "mel", now=_t(1))
        g.upsert_node("Ticket", "employer", "CCS-1", now=_t(1))
        g.upsert_node("Repository", "personal", "sideproj", now=_t(1))
        return g

    def test_detects_cross_workspace_edge(self):
        g = self._graph()
        # same-workspace edge: fine
        g.upsert_edge("employer:person:mel", "employer:ticket:ccs-1", "owns",
                      now=_t(1))
        # cross-workspace edge: employer person -> personal repo
        g.upsert_edge("employer:person:mel", "personal:repository:sideproj",
                      "contributes", now=_t(1))
        cross = workspaces.cross_workspace_edges(g)
        self.assertEqual(len(cross), 1)
        self.assertEqual(cross[0]["type"], "contributes")

    def test_violations_flag_unapproved_cross_links(self):
        g = self._graph()
        g.upsert_edge("employer:person:mel", "personal:repository:sideproj",
                      "contributes", now=_t(1))
        r = workspaces.Registry()
        r.upsert("employer", kind="employer")
        r.upsert("personal", kind="personal")
        self.assertEqual(len(workspaces.isolation_violations(g, r)), 1)
        # after explicit approval, no longer a violation
        workspaces.approve_link(g, "employer:person:mel",
                                "personal:repository:sideproj", "contributes")
        self.assertEqual(len(workspaces.isolation_violations(g, r)), 0)

    def test_open_workspace_not_a_violation(self):
        g = self._graph()
        g.upsert_node("Document", "home", "note", now=_t(1))
        g.upsert_edge("home:document:note", "personal:repository:sideproj",
                      "mentions", now=_t(1))
        r = workspaces.Registry()
        r.upsert("home", kind="home", isolation="open")
        r.upsert("personal", kind="personal", isolation="open")
        self.assertEqual(len(workspaces.isolation_violations(g, r)), 0)

    def test_query_isolation_holds(self):
        g = self._graph()
        for n in g.query(workspace="employer"):
            self.assertEqual(n["workspace"], "employer")
        self.assertEqual(len(g.query(workspace="personal")), 1)


class TestResolveActive(unittest.TestCase):
    def setUp(self):
        self.r = workspaces.Registry()
        self.r.upsert("employer", kind="employer")
        self.r.upsert("personal", kind="personal")

    def test_requested_wins(self):
        self.assertEqual(workspaces.resolve_active(self.r, "personal"),
                         "personal")

    def test_all_means_no_filter(self):
        self.assertIsNone(workspaces.resolve_active(self.r, "all"))

    def test_falls_back_to_active(self):
        self.assertEqual(workspaces.resolve_active(self.r, None), "employer")

    def test_unknown_request_falls_back(self):
        self.assertEqual(workspaces.resolve_active(self.r, "nope"), "employer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
