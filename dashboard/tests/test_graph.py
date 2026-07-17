#!/usr/bin/env python3
"""Unit tests for the knowledge graph library (M1). Stdlib unittest only.

Run: python3 -m unittest discover -s template/dashboard/tests
 or: python3 template/dashboard/tests/test_graph.py
"""

import datetime as dt
import os
import sys
import tempfile
import unittest

# Import graph.py from the parent dashboard dir without any packaging.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402


def _t(day, hour=12):
    return dt.datetime(2026, 1, day, hour, 0, 0, tzinfo=dt.timezone.utc)


class TestIds(unittest.TestCase):
    def test_node_id_is_stable_and_slugged(self):
        a = graph.node_id("Employer", "Ticket", "CCS-123")
        b = graph.node_id("employer", "ticket", "ccs 123")
        self.assertEqual(a, b)
        self.assertEqual(a, "employer:ticket:ccs-123")

    def test_edge_key(self):
        self.assertEqual(
            graph.edge_key("a", "b", "owns"), "a|owns|b")

    def test_combine_confidence(self):
        self.assertAlmostEqual(graph.combine_confidence(0.6, 0.6), 0.84)
        self.assertEqual(graph.combine_confidence(0.5, 0), 0.5)
        self.assertEqual(graph.combine_confidence(0.5, 1), 1.0)
        # out-of-range inputs clamp before combining: 2->1.0 (certain), -1->0.0
        self.assertEqual(graph.combine_confidence(-1, -1), 0.0)
        self.assertEqual(graph.combine_confidence(2, 0), 1.0)


class TestUpsertDedup(unittest.TestCase):
    def test_upsert_dedups_by_id(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "CCS-1", confidence=0.6, now=_t(1))
        g.upsert_node("Ticket", "emp", "ccs 1", confidence=0.6, now=_t(2))
        self.assertEqual(len(g.nodes), 1)

    def test_second_upsert_updates_in_place(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "CCS-1", name="old",
                      attrs={"status": "open"}, source="jira",
                      confidence=0.6, now=_t(1))
        n = g.upsert_node("Ticket", "emp", "CCS-1", name="new",
                          attrs={"status": "closed", "owner": "mel"},
                          source="glean", confidence=0.6, now=_t(5))
        self.assertEqual(n["name"], "new")
        self.assertEqual(n["first_seen"], "2026-01-01T12:00:00Z")
        self.assertEqual(n["last_verified"], "2026-01-05T12:00:00Z")
        self.assertEqual(n["attrs"]["status"], "closed")
        self.assertEqual(n["attrs"]["owner"], "mel")
        self.assertAlmostEqual(n["confidence"], 0.84)  # noisy-OR reinforced
        self.assertEqual(n["source"], "jira, glean")   # sources unioned

    def test_upsert_edge_dedups_and_reinforces(self):
        g = graph.Graph()
        a = g.upsert_node("Person", "emp", "mel", now=_t(1))["id"]
        b = g.upsert_node("Ticket", "emp", "CCS-1", now=_t(1))["id"]
        g.upsert_edge(a, b, "owns", confidence=0.5, now=_t(1))
        e = g.upsert_edge(a, b, "owns", confidence=0.5, now=_t(2))
        self.assertEqual(len(g.edges), 1)
        self.assertAlmostEqual(e["confidence"], 0.75)


class TestQuery(unittest.TestCase):
    def setUp(self):
        self.g = graph.Graph()
        self.g.upsert_node("Ticket", "emp", "CCS-1",
                           attrs={"status": "open"}, now=_t(1))
        self.g.upsert_node("Ticket", "emp", "CCS-2",
                           attrs={"status": "closed"}, now=_t(1))
        self.g.upsert_node("Repository", "personal", "sideproj", now=_t(1))

    def test_filter_by_type(self):
        self.assertEqual(len(self.g.query(type_="Ticket")), 2)

    def test_filter_by_workspace(self):
        self.assertEqual(len(self.g.query(workspace="personal")), 1)

    def test_filter_by_attr_dict(self):
        res = self.g.query(type_="Ticket", where={"status": "open"})
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["attrs"]["status"], "open")

    def test_filter_by_callable(self):
        res = self.g.query(where=lambda n: n["type"] == "Repository")
        self.assertEqual(len(res), 1)

    def test_workspace_isolation(self):
        # A query scoped to one workspace never returns another's nodes.
        for n in self.g.query(workspace="emp"):
            self.assertEqual(n["workspace"], "emp")


class TestNeighborsAndMerge(unittest.TestCase):
    def test_neighbors_direction(self):
        g = graph.Graph()
        p = g.upsert_node("Person", "emp", "mel", now=_t(1))["id"]
        t = g.upsert_node("Ticket", "emp", "CCS-1", now=_t(1))["id"]
        g.upsert_edge(p, t, "owns", now=_t(1))
        self.assertEqual([n["id"] for n in g.neighbors(p, direction="out")], [t])
        self.assertEqual(g.neighbors(p, direction="in"), [])
        self.assertEqual([n["id"] for n in g.neighbors(t, direction="in")], [p])

    def test_merge_repoints_edges(self):
        g = graph.Graph()
        keep = g.upsert_node("Person", "emp", "mel-mccarthy", now=_t(1))["id"]
        dup = g.upsert_node("Person", "emp", "mmccarthy", now=_t(1))["id"]
        t = g.upsert_node("Ticket", "emp", "CCS-1", now=_t(1))["id"]
        g.upsert_edge(dup, t, "owns", now=_t(1))
        g.merge_nodes(keep, dup, now=_t(2))
        self.assertNotIn(dup, g.nodes)
        self.assertEqual(len(g.nodes), 2)  # keep + ticket
        # edge now points from keep, not dup
        self.assertEqual([n["id"] for n in g.neighbors(keep, direction="out")], [t])


class TestFreshness(unittest.TestCase):
    def test_is_stale(self):
        g = graph.Graph()
        n = g.upsert_node("Ticket", "emp", "CCS-1", now=_t(1))
        # 1 day later: fresh
        self.assertFalse(graph.is_stale(n, now=_t(2), max_age_days=14))
        # 30 days later: stale
        self.assertTrue(graph.is_stale(n, now=_t(1) + dt.timedelta(days=30),
                                       max_age_days=14))

    def test_stale_nodes_listing(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "OLD", now=_t(1))
        g.upsert_node("Ticket", "emp", "NEW", now=_t(1) + dt.timedelta(days=29))
        stale = g.stale_nodes(now=_t(1) + dt.timedelta(days=30), max_age_days=14)
        self.assertEqual([n["id"] for n in stale], ["emp:ticket:old"])


class TestPersistenceAndViews(unittest.TestCase):
    def test_roundtrip(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "CCS-1", attrs={"x": 1}, now=_t(1))
        a = g.upsert_node("Person", "emp", "mel", now=_t(1))["id"]
        b = g.nodes["emp:ticket:ccs-1"]["id"]
        g.upsert_edge(a, b, "owns", now=_t(1))
        with tempfile.TemporaryDirectory() as d:
            gdir = os.path.join(d, "graph")
            g.save(gdir)
            g2 = graph.Graph.load(gdir)
            self.assertEqual(g2.nodes.keys(), g.nodes.keys())
            self.assertEqual(g2.edges.keys(), g.edges.keys())
            self.assertEqual(g2.nodes["emp:person:mel"]["name"], "mel")

    def test_missing_dir_is_empty_graph(self):
        with tempfile.TemporaryDirectory() as d:
            g = graph.Graph.load(os.path.join(d, "nope"))
            self.assertEqual(len(g.nodes), 0)
            self.assertEqual(len(g.edges), 0)

    def test_save_is_deterministic(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "B", now=_t(1))
        g.upsert_node("Ticket", "emp", "A", now=_t(1))
        with tempfile.TemporaryDirectory() as d:
            gdir = os.path.join(d, "graph")
            g.save(gdir)
            with open(os.path.join(gdir, "nodes.jsonl")) as fh:
                first = fh.read()
            g.save(gdir)
            with open(os.path.join(gdir, "nodes.jsonl")) as fh:
                second = fh.read()
            self.assertEqual(first, second)
            # sorted by id -> A before B
            self.assertLess(first.index("ticket:a"), first.index("ticket:b"))

    def test_views_regen_idempotent(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "CCS-1", now=_t(1))
        g.upsert_node("Repository", "personal", "sideproj", now=_t(1))
        with tempfile.TemporaryDirectory() as d:
            gdir = os.path.join(d, "graph")
            g.save(gdir)
            g.render_views(gdir)
            snap1 = _snapshot_views(os.path.join(gdir, "views"))
            g.render_views(gdir)
            snap2 = _snapshot_views(os.path.join(gdir, "views"))
            self.assertEqual(snap1, snap2)
            self.assertIn("index.md", snap1)
            self.assertIn("emp.md", snap1)


def _snapshot_views(views_dir):
    out = {}
    for name in sorted(os.listdir(views_dir)):
        if name.endswith(".md"):
            with open(os.path.join(views_dir, name)) as fh:
                out[name] = fh.read()
    return out


if __name__ == "__main__":
    unittest.main(verbosity=2)
