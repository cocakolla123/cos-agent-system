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

    def _action_pri(self, g, key):
        return g.nodes["emp:action:" + key]["attrs"].get("priority")

    def test_action_without_priority_gets_default(self):
        g = graph.Graph()
        research.ingest(g, [research.record("Action", "emp", "a1",
                                            name="send deck")], now=_t(1))
        self.assertEqual(self._action_pri(g, "a1"), research.DEFAULT_PRIORITY)

    def test_action_priority_is_normalized_and_unknown_defaults(self):
        g = graph.Graph()
        research.ingest(g, [
            research.record("Action", "emp", "a1", attrs={"priority": " High "}),
            research.record("Action", "emp", "a2", attrs={"priority": "urgent"}),
        ], now=_t(1))
        self.assertEqual(self._action_pri(g, "a1"), "high")
        self.assertEqual(self._action_pri(g, "a2"), research.DEFAULT_PRIORITY)

    def test_existing_priority_survives_a_record_that_omits_it(self):
        g = graph.Graph()
        research.ingest(g, [research.record("Action", "emp", "a1",
                                            attrs={"priority": "low"})],
                        now=_t(1))
        research.ingest(g, [research.record("Action", "emp", "a1",
                                            name="send deck")], now=_t(2))
        self.assertEqual(self._action_pri(g, "a1"), "low")

    def test_non_action_gets_no_priority(self):
        g = graph.Graph()
        research.ingest(g, [research.record("Ticket", "emp", "T-1")], now=_t(1))
        self.assertNotIn("priority", g.nodes["emp:ticket:t-1"]["attrs"])


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


class TestWindowAudit(unittest.TestCase):
    """Crawl-reach detection: a source fed from too narrow a slice of time."""

    NOW = dt.datetime(2026, 9, 12, 12, 0, 0, tzinfo=dt.timezone.utc)

    def _graph(self, recs):
        g = graph.Graph()
        research.ingest(g, recs, now=self.NOW)
        return g

    def _row(self, audit, source):
        return next(r for r in audit if r["source"] == source)

    def test_declared_window_below_floor_is_short(self):
        g = self._graph([research.record(
            "Action", "js", "a1", attrs={"window_days": 2}, source="gmail")])
        row = self._row(research.window_audit(g, now=self.NOW), "gmail")
        self.assertEqual(row["declared_days"], 2)
        self.assertTrue(row["short"])

    def test_declared_window_at_floor_is_not_short(self):
        g = self._graph([research.record(
            "Action", "js", "a1", attrs={"window_days": 90}, source="gmail")])
        row = self._row(research.window_audit(g, now=self.NOW), "gmail")
        self.assertFalse(row["short"])

    def test_undeclared_window_is_short_even_when_nodes_exist(self):
        """The regression this exists for: the crawl recorded no window_days at
        all, so its reach is unknown — and unknown reach is the finding."""
        g = self._graph([research.record(
            "Action", "js", "a1", attrs={"last_activity": "2026-09-11"},
            source="gmail")])
        row = self._row(research.window_audit(g, now=self.NOW), "gmail")
        self.assertIsNone(row["declared_days"])
        self.assertTrue(row["short"])

    def test_undeclared_but_observed_reach_clears_floor(self):
        g = self._graph([research.record(
            "Action", "js", "old", attrs={"last_activity": "2026-01-01"},
            source="gmail")])
        row = self._row(research.window_audit(g, now=self.NOW), "gmail")
        self.assertFalse(row["short"])
        self.assertEqual(row["oldest"], "2026-01-01")

    def test_declaration_beats_a_quiet_observed_window(self):
        """A genuinely quiet 90 days must not read as a narrow crawl."""
        g = self._graph([research.record(
            "Action", "js", "a1",
            attrs={"window_days": 90, "last_activity": "2026-09-11"},
            source="gmail")])
        row = self._row(research.window_audit(g, now=self.NOW), "gmail")
        self.assertFalse(row["short"])
        self.assertEqual(row["reach_days"], 90)

    def test_last_verified_is_not_evidence(self):
        """Crawl recency must never count as reach — the is_dormant lesson."""
        g = self._graph([research.record("Action", "js", "a1", source="gmail")])
        row = self._row(research.window_audit(g, now=self.NOW), "gmail")
        self.assertIsNone(row["observed_days"])
        self.assertIsNone(row["oldest"])
        self.assertTrue(row["short"])

    def test_multi_source_node_counts_against_every_connector(self):
        g = self._graph([research.record(
            "Action", "js", "a1", attrs={"window_days": 90},
            source="gmail, indeed")])
        audit = research.window_audit(g, now=self.NOW)
        self.assertEqual({r["source"] for r in audit}, {"gmail", "indeed"})
        self.assertFalse(self._row(audit, "indeed")["short"])

    def test_window_gaps_lists_only_short_sources(self):
        g = self._graph([
            research.record("Action", "js", "a1",
                            attrs={"window_days": 90}, source="gmail"),
            research.record("Action", "js", "a2",
                            attrs={"window_days": 3}, source="notion"),
        ])
        gaps = research.window_gaps(g, now=self.NOW)
        self.assertEqual([r["source"] for r in gaps], ["notion"])

    def test_worst_reach_sorts_first(self):
        g = self._graph([
            research.record("Action", "js", "a1",
                            attrs={"window_days": 30}, source="notion"),
            research.record("Action", "js", "a2",
                            attrs={"window_days": 2}, source="gmail"),
            research.record("Action", "js", "a3",
                            attrs={"window_days": 90}, source="asana"),
        ])
        audit = research.window_audit(g, now=self.NOW)
        self.assertEqual([r["source"] for r in audit],
                         ["gmail", "notion", "asana"])

    def test_empty_graph_audits_clean(self):
        self.assertEqual(research.window_audit(graph.Graph()), [])


class TestOrphanObligations(unittest.TestCase):
    """A verb stored as an adjective on a noun is a dropped obligation.

    The to-do list reads Action nodes and nothing else, so an obligation
    recorded as attrs on an entity (``blocked_on``, ``stage: awaiting-…``) is
    in the graph and still absent from the list. These pin the control that
    catches it, after the prose-only version of the rule let the same miss
    through twice.
    """

    NOW = dt.datetime(2026, 3, 1, 12, 0, 0, tzinfo=dt.timezone.utc)

    def _ingest(self, kind, key, attrs, name=None, ws="pipeline"):
        g = graph.Graph()
        counts = research.ingest(g, [research.record(
            kind, ws, key, name=name, attrs=attrs, source="email")],
            now=self.NOW)
        return g, counts

    def test_blocked_on_a_noun_mints_the_missing_action(self):
        g, counts = self._ingest("JobApplication", "vendor-role",
                                 {"blocked_on": "the recruiter",
                                  "stage": "awaiting-reply",
                                  "last_activity": "2026-02-20"},
                                 name="Vendor — platform role")
        self.assertEqual(counts["derived_actions"], 1)
        act = g.nodes["pipeline:action:vendor-role-followup"]
        self.assertEqual(act["type"], "Action")
        self.assertTrue(graph.is_open_action(act, now=self.NOW))
        self.assertEqual(act["attrs"]["blocked_on"], "the recruiter")
        self.assertEqual(act["attrs"]["derived_from"],
                         "pipeline:jobapplication:vendor-role")
        self.assertIn("the recruiter", act["name"])

    def test_a_narrative_blocked_on_stays_out_of_the_title(self):
        # Modules write a *state* here as well as a party; "Follow up with
        # the PR is closed and unresolved — X" is not a task title.
        g, _ = self._ingest("Project", "insight",
                            {"blocked_on": "PR closed, unresolved"},
                            name="Insight — task authoring")
        act = g.nodes["pipeline:action:insight-followup"]
        self.assertEqual(act["name"], "Follow up — Insight — task authoring")
        self.assertEqual(act["attrs"]["blocked_on"], "PR closed, unresolved")

    def test_derived_action_links_back_to_its_source(self):
        g, _ = self._ingest("JobApplication", "vendor-role",
                            {"blocked_on": "the recruiter"})
        out = g.neighbors("pipeline:action:vendor-role-followup",
                          edge_type="relates_to", direction="out")
        self.assertEqual([n["id"] for n in out],
                         ["pipeline:jobapplication:vendor-role"])

    def test_awaiting_stage_alone_is_enough(self):
        g, counts = self._ingest("Ticket", "req-7", {"stage": "Awaiting-Panel"})
        self.assertEqual(counts["derived_actions"], 1)
        self.assertIn("pipeline:action:req-7-followup", g.nodes)

    def test_an_action_carrying_blocked_on_mints_nothing(self):
        # blocked_on on an Action is the rule working, not failing.
        g, counts = self._ingest("Action", "chase-vendor",
                                 {"blocked_on": "the recruiter"})
        self.assertEqual(counts["derived_actions"], 0)
        self.assertEqual(len(g.query(type_="Action")), 1)

    def test_a_plain_noun_mints_nothing(self):
        g, counts = self._ingest("Document", "spec", {"status": "open"})
        self.assertEqual(counts["derived_actions"], 0)
        self.assertEqual(g.query(type_="Action"), [])

    def test_concluded_work_owes_nothing(self):
        g, counts = self._ingest("JobApplication", "closed-role",
                                 {"blocked_on": "the recruiter",
                                  "concluded": True,
                                  "concluded_on": "2026-02-25"})
        self.assertEqual(counts["derived_actions"], 0)
        self.assertEqual(g.query(type_="Action"), [])

    def test_derivation_invents_no_deadline_and_no_status(self):
        g, _ = self._ingest("JobApplication", "vendor-role",
                            {"blocked_on": "the recruiter"})
        attrs = g.nodes["pipeline:action:vendor-role-followup"]["attrs"]
        self.assertNotIn("due", attrs)
        self.assertNotIn("status", attrs)
        self.assertEqual(attrs["priority"], research.DEFAULT_PRIORITY)

    def test_rederiving_is_idempotent(self):
        recs = [research.record("JobApplication", "pipeline", "vendor-role",
                                attrs={"blocked_on": "the recruiter"},
                                source="email")]
        g = graph.Graph()
        first = research.ingest(g, recs, now=self.NOW)
        second = research.ingest(g, recs, now=self.NOW)
        self.assertEqual(first["derived_actions"], 1)
        self.assertEqual(second["derived_actions"], 0)
        self.assertEqual(len(g.query(type_="Action")), 1)

    def test_a_derived_task_marked_done_is_not_resurrected(self):
        """The regression that would make the control worse than the bug."""
        recs = [research.record("JobApplication", "pipeline", "vendor-role",
                                attrs={"blocked_on": "the recruiter"},
                                source="email")]
        g = graph.Graph()
        research.ingest(g, recs, now=self.NOW)
        act = g.nodes["pipeline:action:vendor-role-followup"]
        act["attrs"]["status"] = "done"
        research.ingest(g, recs, now=self.NOW)
        self.assertEqual(act["attrs"]["status"], "done")
        self.assertFalse(graph.is_open_action(act, now=self.NOW))

    def test_orphan_obligations_audits_the_whole_graph(self):
        g = graph.Graph()
        g.upsert_node("JobApplication", "pipeline", "a",
                      attrs={"blocked_on": "them"}, now=self.NOW)
        g.upsert_node("Document", "pipeline", "b", now=self.NOW)
        orphans = research.orphan_obligations(g, now=self.NOW)
        self.assertEqual([n["id"] for n, _ in orphans],
                         ["pipeline:jobapplication:a"])
        research.derive_orphan_actions(g, now=self.NOW)
        self.assertEqual(research.orphan_obligations(g, now=self.NOW), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestUserPriorityKept(unittest.TestCase):
    def test_later_crawl_does_not_overwrite_hand_set_priority(self):
        g = graph.Graph()
        research.ingest(g, [research.record("Action", "w", "a", name="x",
                                            attrs={"priority": "medium"})])
        nid = graph.node_id("w", "Action", "a")
        g.nodes[nid]["attrs"].update(priority="low", priority_source="user")
        research.ingest(g, [research.record("Action", "w", "a", name="x",
                                            attrs={"priority": "high", "due": "2026-10-20"})])
        a = g.nodes[nid]["attrs"]
        self.assertEqual(a["priority"], "low")
        self.assertEqual(a["due"], "2026-10-20")
