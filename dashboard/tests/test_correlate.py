#!/usr/bin/env python3
"""Tests for workstream correlation (M5). Stdlib unittest only."""

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402
import correlate  # noqa: E402


def _t(day, hour=12):
    return dt.datetime(2026, 5, day, hour, 0, 0, tzinfo=dt.timezone.utc)


def _cluster_graph():
    """A thread + meeting + ticket + PR that all reference ticket PROJ-1."""
    g = graph.Graph()
    g.upsert_node("Channel", "emp", "eng-thread",
                  attrs={"refs": ["PROJ-1"]}, now=_t(1, 9))
    g.upsert_node("Meeting", "emp", "sync-mtg",
                  attrs={"refs": ["PROJ-1"]}, now=_t(1, 10))
    g.upsert_node("Ticket", "emp", "PROJ-1", name="Fix routing",
                  attrs={"refs": ["PROJ-1"]}, now=_t(1, 11))
    g.upsert_node("PR", "emp", "gh-42",
                  attrs={"refs": ["PROJ-1"]}, now=_t(1, 12))
    # an unrelated ticket in same workspace
    g.upsert_node("Ticket", "emp", "OTHER-9", attrs={"refs": ["OTHER-9"]},
                  now=_t(1, 13))
    return g


class TestCorrelate(unittest.TestCase):
    def test_shared_ref_forms_one_objective(self):
        g = _cluster_graph()
        ids = correlate.correlate(g, now=_t(2))
        self.assertEqual(len(ids), 1)
        oid = ids[0]
        members = [n["id"] for n in correlate.timeline(g, oid)]
        self.assertEqual(len(members), 4)  # thread, meeting, ticket, PR
        self.assertNotIn("emp:ticket:other-9", members)

    def test_objective_name_prefers_ticket(self):
        g = _cluster_graph()
        oid = correlate.correlate(g, now=_t(2))[0]
        self.assertEqual(g.nodes[oid]["name"], "Fix routing")

    def test_timeline_ordering(self):
        g = _cluster_graph()
        oid = correlate.correlate(g, now=_t(2))[0]
        kinds = [n["type"] for n in correlate.timeline(g, oid)]
        self.assertEqual(kinds, ["Channel", "Meeting", "Ticket", "PR"])

    def test_single_shared_person_does_NOT_group(self):
        # One shared person is a weak signal — the user's manager touches
        # everything; merging on it collapses unrelated work (M12 fix).
        g = graph.Graph()
        g.upsert_node("Person", "emp", "mel", now=_t(1))
        g.upsert_node("Meeting", "emp", "m1", now=_t(1))
        g.upsert_node("Ticket", "emp", "T1", now=_t(1))
        g.upsert_edge("emp:meeting:m1", "emp:person:mel", "attends", now=_t(1))
        g.upsert_edge("emp:ticket:t1", "emp:person:mel", "owned_by", now=_t(1))
        self.assertEqual(correlate.correlate(g, now=_t(2)), [])

    def test_two_shared_people_group(self):
        g = graph.Graph()
        for p in ("mel", "sam"):
            g.upsert_node("Person", "emp", p, now=_t(1))
        g.upsert_node("Meeting", "emp", "m1", now=_t(1))
        g.upsert_node("Ticket", "emp", "T1", now=_t(1))
        for n, e in (("emp:meeting:m1", "attends"), ("emp:ticket:t1", "owned_by")):
            g.upsert_edge(n, "emp:person:mel", e, now=_t(1))
            g.upsert_edge(n, "emp:person:sam", e, now=_t(1))
        self.assertEqual(len(correlate.correlate(g, now=_t(2))), 1)

    def test_person_plus_ref_groups(self):
        g = graph.Graph()
        g.upsert_node("Person", "emp", "mel", now=_t(1))
        g.upsert_node("Meeting", "emp", "m1", attrs={"refs": ["T1"]}, now=_t(1))
        g.upsert_node("Ticket", "emp", "T1", attrs={"refs": ["T1"]}, now=_t(1))
        g.upsert_edge("emp:meeting:m1", "emp:person:mel", "attends", now=_t(1))
        g.upsert_edge("emp:ticket:t1", "emp:person:mel", "owned_by", now=_t(1))
        self.assertEqual(len(correlate.correlate(g, now=_t(2))), 1)

    def test_no_cross_workspace_objective(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "emp", "T1", attrs={"refs": ["X"]}, now=_t(1))
        g.upsert_node("Ticket", "personal", "P1", attrs={"refs": ["X"]},
                      now=_t(1))
        ids = correlate.correlate(g, now=_t(2))
        # same ref token but different workspaces -> never grouped together
        self.assertEqual(ids, [])  # neither reaches min_members within a ws

    def test_idempotent(self):
        g = _cluster_graph()
        ids1 = correlate.correlate(g, now=_t(2))
        n_nodes = len(g.nodes)
        n_edges = len(g.edges)
        ids2 = correlate.correlate(g, now=_t(3))
        self.assertEqual(ids1, ids2)                 # same objective id
        self.assertEqual(len(g.nodes), n_nodes)      # no new nodes
        self.assertEqual(len(g.edges), n_edges)      # no new edges

    def test_timeline_unknown_objective(self):
        g = graph.Graph()
        self.assertEqual(correlate.timeline(g, "nope"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
