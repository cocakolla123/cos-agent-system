#!/usr/bin/env python3
"""Tests for the research ingest layer (M2). Stdlib unittest only."""

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402
import research  # noqa: E402


def _t(day):
    return dt.datetime(2026, 2, day, 12, 0, 0, tzinfo=dt.timezone.utc)


class TestRecord(unittest.TestCase):
    def test_requires_kind_and_key(self):
        with self.assertRaises(ValueError):
            research.record("Ticket", "emp", "")
        with self.assertRaises(ValueError):
            research.record("", "emp", "K")

    def test_defaults_workspace_to_personal(self):
        r = research.record("Repository", None, "sideproj")
        self.assertEqual(r["workspace"], "personal")


class TestIngest(unittest.TestCase):
    def test_ingest_nodes_and_edges(self):
        g = graph.Graph()
        recs = [
            research.record("Ticket", "emp", "CCS-1", name="bug",
                            attrs={"status": "open"}, source="jira",
                            confidence=0.9,
                            edges=[{"to_kind": "Person", "to_key": "mel",
                                    "type": "owned_by", "confidence": 0.8}]),
            research.record("Person", "emp", "mel", name="Mel", source="jira"),
        ]
        counts = research.ingest(g, recs, now=_t(1))
        self.assertEqual(len(g.nodes), 2)          # ticket + person (no dup stub)
        self.assertEqual(len(g.edges), 1)
        self.assertGreaterEqual(counts["edges"], 1)
        # edge points ticket -> person
        t = g.nodes["emp:ticket:ccs-1"]["id"]
        self.assertEqual([n["id"] for n in g.neighbors(t, direction="out")],
                         ["emp:person:mel"])

    def test_edge_to_unseen_target_creates_stub(self):
        g = graph.Graph()
        recs = [research.record("Ticket", "emp", "CCS-2",
                                edges=[{"to_kind": "Person", "to_key": "ghost",
                                        "type": "owned_by"}])]
        research.ingest(g, recs, now=_t(1))
        self.assertIn("emp:person:ghost", g.nodes)   # stub created, edge kept
        self.assertLessEqual(g.nodes["emp:person:ghost"]["confidence"], 0.5)

    def test_ingest_is_idempotent(self):
        g = graph.Graph()
        recs = [research.record("Ticket", "emp", "CCS-1", source="jira")]
        research.ingest(g, recs, now=_t(1))
        research.ingest(g, recs, now=_t(2))
        self.assertEqual(len(g.nodes), 1)            # no duplicate
        self.assertEqual(g.nodes["emp:ticket:ccs-1"]["last_verified"],
                         "2026-02-02T12:00:00Z")     # freshness advanced


class TestWorkspaceInference(unittest.TestCase):
    def test_org_signal_clusters(self):
        recs = [
            research.record("Ticket", "prov", "T1", attrs={"org": "Acme"}),
            research.record("Repository", "prov", "R1", attrs={"org": "Acme"}),
            research.record("Repository", "prov", "R2", attrs={"org": "Acme"}),
        ]
        props = research.infer_workspaces(recs)
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["id"], "acme")
        self.assertEqual(len(props[0]["members"]), 3)

    def test_multiple_workspaces_stay_separate(self):
        recs = [
            research.record("Ticket", "employer", "T1", attrs={"org": "Acme"}),
            research.record("Repository", "personal", "sideproj"),
            research.record("Document", "school", "essay",
                            attrs={"workspace_kind": "school"}),
        ]
        props = research.infer_workspaces(recs)
        ids = sorted(p["id"] for p in props)
        self.assertEqual(ids, ["acme", "personal", "school"])

    def test_job_search_kind_guess(self):
        recs = [research.record("Document", "js", "app-1",
                                attrs={"job_application": True})]
        props = research.infer_workspaces(recs)
        self.assertEqual(props[0]["kind"], "job-search")

    def test_freelance_kind_guess(self):
        recs = [research.record("Project", "fl", "clientwork",
                                attrs={"client": "BigCo"})]
        props = research.infer_workspaces(recs)
        self.assertEqual(props[0]["kind"], "freelance")

    def test_workspace_records_roundtrip(self):
        recs = [research.record("Repository", "personal", "sideproj")]
        props = research.infer_workspaces(recs)
        ws_recs = research.workspace_records(props)
        g = graph.Graph()
        research.ingest(g, recs, now=_t(1))
        research.ingest(g, ws_recs, now=_t(1))
        # Workspace node created + contains-edge to the repo
        self.assertIn("personal:workspace:personal", g.nodes)
        wsid = g.nodes["personal:workspace:personal"]["id"]
        members = [n["id"] for n in g.neighbors(wsid, edge_type="contains",
                                                direction="out")]
        self.assertIn("personal:repository:sideproj", members)


if __name__ == "__main__":
    unittest.main(verbosity=2)
