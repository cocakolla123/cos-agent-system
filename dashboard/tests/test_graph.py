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


class TestDormancy(unittest.TestCase):
    """Source activity (attrs['last_activity']) vs. crawl recency (last_verified).

    Regression guard for the stale-container correction: a 2019 Key
    Club calendar re-read by tonight's poll is maximally fresh and entirely
    inactive, and the dashboard showed it as a current project.
    """

    NOW = dt.datetime(2026, 9, 12, 12, 0, 0, tzinfo=dt.timezone.utc)

    def test_freshly_crawled_relic_is_fresh_but_dormant(self):
        g = graph.Graph()
        n = g.upsert_node("Project", "volunteer", "district-9-north",
                          attrs={"last_activity": "2019-08-02"}, now=self.NOW)
        self.assertFalse(graph.is_stale(n, now=self.NOW))
        self.assertTrue(graph.is_dormant(n, now=self.NOW))

    def test_recent_activity_is_not_dormant(self):
        g = graph.Graph()
        n = g.upsert_node("Project", "work", "live",
                          attrs={"last_activity": "2026-08-20"}, now=self.NOW)
        self.assertFalse(graph.is_dormant(n, now=self.NOW))

    def test_explicit_dormant_flag_wins_without_a_date(self):
        g = graph.Graph()
        n = g.upsert_node("Project", "travel", "empty-cal",
                          attrs={"dormant": True}, now=self.NOW)
        self.assertTrue(graph.is_dormant(n, now=self.NOW))

    def test_no_activity_evidence_is_not_dormant(self):
        """Absence of evidence must not suppress: most nodes never set one."""
        g = graph.Graph()
        n = g.upsert_node("Ticket", "work", "T-9", now=self.NOW)
        self.assertIsNone(graph.activity_days(n, now=self.NOW))
        self.assertFalse(graph.is_dormant(n, now=self.NOW))

    def test_activity_days_measures_the_source_not_the_crawl(self):
        g = graph.Graph()
        n = g.upsert_node("Project", "grad-school", "asu-2023-ssem1",
                          attrs={"last_activity": "2023-08-26"}, now=self.NOW)
        self.assertAlmostEqual(graph.freshness_days(n, now=self.NOW), 0.0, places=1)
        self.assertGreater(graph.activity_days(n, now=self.NOW), 1000)


class TestConcluded(unittest.TestCase):
    """An explicit ending, vs. the two time-based predicates.

    Regression guard for the concluded-engagement correction: the ClientCo
    Life Tasks contract concluded 2026-08-27 on documents last edited
    2026-08-04. Both dates are recent, so neither staleness nor dormancy can
    ever reach this — only the announcement can.
    """

    NOW = dt.datetime(2026, 9, 12, 12, 0, 0, tzinfo=dt.timezone.utc)

    def test_concluded_work_is_fresh_and_active_and_still_not_current(self):
        g = graph.Graph()
        n = g.upsert_node("Document", "clientco", "life-tasks-guide",
                          attrs={"last_activity": "2026-08-04",
                                 "concluded": True,
                                 "concluded_on": "2026-08-27"}, now=self.NOW)
        self.assertFalse(graph.is_stale(n, now=self.NOW))
        self.assertFalse(graph.is_dormant(n, now=self.NOW))
        self.assertTrue(graph.is_concluded(n))
        self.assertFalse(graph.is_current(n, now=self.NOW))

    def test_terminal_status_concludes(self):
        g = graph.Graph()
        for status in ("concluded", "Terminated", "  offboarded  "):
            n = g.upsert_node("Project", "work", graph.slug(status),
                              attrs={"status": status}, now=self.NOW)
            self.assertTrue(graph.is_concluded(n), status)

    def test_ordinary_lifecycle_words_do_not_conclude(self):
        """'done'/'closed'/'completed' are normal, and handled elsewhere."""
        g = graph.Graph()
        for status in ("open", "done", "closed", "completed", "in-progress"):
            n = g.upsert_node("Ticket", "work", graph.slug(status),
                              attrs={"status": status}, now=self.NOW)
            self.assertFalse(graph.is_concluded(n), status)

    def test_no_status_evidence_is_not_concluded(self):
        """Same asymmetry as dormancy: suppression needs positive evidence."""
        g = graph.Graph()
        n = g.upsert_node("Project", "work", "live", now=self.NOW)
        self.assertFalse(graph.is_concluded(n))
        self.assertTrue(graph.is_current(n, now=self.NOW))

    def test_dormant_still_fails_is_current(self):
        """is_current must keep honouring the older predicate, not replace it."""
        g = graph.Graph()
        n = g.upsert_node("Project", "volunteer", "district-9-north",
                          attrs={"last_activity": "2019-08-02"}, now=self.NOW)
        self.assertFalse(graph.is_concluded(n))
        self.assertFalse(graph.is_current(n, now=self.NOW))


class TestObligations(unittest.TestCase):
    """Action nodes — "what must I do", which no entity predicate can answer.

    Regression guard for corr-20260912T103414-to-do-lists-dashboard: the graph
    held 88 correctly-discovered nodes and zero obligations, so the dashboard
    could only ever show an inventory.
    """

    NOW = dt.datetime(2026, 9, 12, 12, 0, 0, tzinfo=dt.timezone.utc)

    def _action(self, key, **attrs):
        g = graph.Graph()
        return g.upsert_node("Action", "job-search", key, attrs=attrs,
                             now=self.NOW)

    def test_due_days_counts_down_and_goes_negative(self):
        soon = self._action("a", due="2026-09-18T23:59:00-07:00")
        self.assertAlmostEqual(graph.due_days(soon, now=self.NOW), 6.79, places=1)
        self.assertFalse(graph.is_overdue(soon, now=self.NOW))
        late = self._action("b", due="2026-09-01")
        self.assertLess(graph.due_days(late, now=self.NOW), 0)
        self.assertTrue(graph.is_overdue(late, now=self.NOW))

    def test_undated_obligation_is_still_open(self):
        """None means 'no deadline known', never 'nothing to do'."""
        n = self._action("pay-amf")
        self.assertIsNone(graph.due_days(n, now=self.NOW))
        self.assertFalse(graph.is_overdue(n, now=self.NOW))
        self.assertTrue(graph.is_open_action(n, now=self.NOW))

    def test_overdue_action_stays_open(self):
        """Being late makes an action more urgent, never finished."""
        n = self._action("payments-app", due="2026-08-01")
        self.assertTrue(graph.is_overdue(n, now=self.NOW))
        self.assertTrue(graph.is_open_action(n, now=self.NOW))

    def test_done_statuses_close_an_action(self):
        for status in ("done", "Submitted", "  PAID  "):
            n = self._action(graph.slug(status), status=status)
            self.assertFalse(graph.is_open_action(n, now=self.NOW), status)

    def test_satisfied_on_hold_delegated_close_an_action(self):
        for status in ("satisfied", "on_hold", "on-hold", "On Hold",
                       "delegated"):
            n = self._action(graph.slug(status), status=status)
            self.assertFalse(graph.is_open_action(n, now=self.NOW), status)

    def test_outcome_statuses_conclude(self):
        """An application or invitation that ended (rejected, not selected,
        withdrawn, declined, expired) is over, not open."""
        for status in ("rejected", "Not_Selected", "withdrawn", "declined", "expired"):
            n = self._action(graph.slug(status), status=status)
            self.assertTrue(graph.is_concluded(n), status)
            self.assertFalse(graph.is_open_action(n, now=self.NOW), status)

    def test_unknown_status_leaves_an_action_open(self):
        n = self._action("pending", status="pending")
        self.assertTrue(graph.is_open_action(n, now=self.NOW))

    def test_done_status_does_not_conclude_other_node_types(self):
        """DONE_STATUSES is for Actions only — it must not leak into
        is_concluded, where 'closed'/'done' are ordinary lifecycle."""
        g = graph.Graph()
        n = g.upsert_node("Document", "work", "spec", attrs={"status": "done"},
                          now=self.NOW)
        self.assertFalse(graph.is_concluded(n))
        self.assertTrue(graph.is_current(n, now=self.NOW))

    def test_empty_value_does_not_erase_but_clear_attrs_does(self):
        g = graph.Graph()
        g.upsert_node("Action", "work", "a1",
                      attrs={"due": "2026-10-01", "blocked_on": "legal"}, now=self.NOW)
        g.upsert_node("Action", "work", "a1", attrs={"blocked_on": None}, now=self.NOW)
        n = g.nodes[graph.node_id("work", "Action", "a1")]
        self.assertEqual(n["attrs"]["blocked_on"], "legal")
        g.upsert_node("Action", "work", "a1",
                      attrs={"clear_attrs": ["blocked_on"], "note": "send it"},
                      now=self.NOW)
        self.assertNotIn("blocked_on", n["attrs"])
        self.assertNotIn("clear_attrs", n["attrs"])
        self.assertEqual(n["attrs"]["due"], "2026-10-01")
        self.assertEqual(n["attrs"]["note"], "send it")

    def test_non_action_is_never_an_open_action(self):
        g = graph.Graph()
        n = g.upsert_node("Document", "work", "spec", now=self.NOW)
        self.assertFalse(graph.is_open_action(n, now=self.NOW))

    def test_due_on_is_accepted_as_well_as_due(self):
        """Trackers already emit 'due_on'; don't make them rewrite it."""
        n = self._action("ticketish", due_on="2026-09-20")
        self.assertGreater(graph.due_days(n, now=self.NOW), 0)


class TestDemoIsNotWork(unittest.TestCase):
    """A vendor's onboarding sample ships with plausible near-term due dates,
    so the activity clock can never catch it — only the flag can."""

    NOW = dt.datetime(2026, 9, 12, 12, 0, 0, tzinfo=dt.timezone.utc)

    def test_likely_demo_is_dormant_despite_a_future_due_date(self):
        g = graph.Graph()
        n = g.upsert_node("Ticket", "personal", "asana-task-1", name="Task 1",
                          attrs={"likely_demo": True, "status": "open",
                                 "due_on": "2026-09-16"}, now=self.NOW)
        self.assertIsNone(graph.activity_days(n, now=self.NOW))
        self.assertTrue(graph.is_dormant(n, now=self.NOW))
        self.assertFalse(graph.is_current(n, now=self.NOW))

    def test_a_real_ticket_with_a_due_date_stays_current(self):
        g = graph.Graph()
        n = g.upsert_node("Ticket", "work", "T-9", attrs={"due_on": "2026-09-16"},
                          now=self.NOW)
        self.assertTrue(graph.is_current(n, now=self.NOW))


def _snapshot_views(views_dir):
    out = {}
    for name in sorted(os.listdir(views_dir)):
        if name.endswith(".md"):
            with open(os.path.join(views_dir, name)) as fh:
                out[name] = fh.read()
    return out


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestEffectivePriority(unittest.TestCase):
    NOW = graph._parse_iso("2026-10-13T12:00:00Z")

    def _n(self, **attrs):
        return {"type": "Action", "attrs": attrs}

    def test_due_within_three_days_or_overdue_is_high(self):
        for due in ("2026-10-16", "2026-10-13", "2026-10-01",
                    "2026-10-16T23:59:00-07:00"):
            self.assertEqual(graph.effective_priority(
                self._n(priority="medium", due=due), now=self.NOW), "high", due)

    def test_further_out_or_undated_keeps_stored(self):
        self.assertEqual(graph.effective_priority(
            self._n(priority="medium", due="2026-10-17"), now=self.NOW), "medium")
        self.assertEqual(graph.effective_priority(
            self._n(priority="low"), now=self.NOW), "low")
        self.assertEqual(graph.effective_priority(self._n(), now=self.NOW), "medium")

    def test_same_item_rises_as_the_date_nears(self):
        n = self._n(priority="medium", due="2026-11-03")
        self.assertEqual(graph.effective_priority(n, now=self.NOW), "medium")
        self.assertEqual(graph.effective_priority(
            n, now=graph._parse_iso("2026-11-01T09:00:00Z")), "high")

    def test_user_set_priority_is_never_overridden(self):
        n = self._n(priority="low", priority_source="user", due="2026-10-14")
        self.assertEqual(graph.effective_priority(n, now=self.NOW), "low")


class TestDateOnlyDue(unittest.TestCase):
    def test_date_only_deadline_is_due_today_until_the_day_ends(self):
        n = {"type": "Action", "attrs": {"due": "2026-10-13"}}
        afternoon = graph._parse_iso("2026-10-13T16:00:00Z").astimezone()
        days = graph.due_days(n, now=afternoon)
        self.assertGreaterEqual(days, 0)
        self.assertLess(days, 1)
        self.assertFalse(graph.is_overdue(n, now=afternoon))
        next_day = afternoon + __import__("datetime").timedelta(days=1)
        self.assertTrue(graph.is_overdue(n, now=next_day))


class TestRankKey(unittest.TestCase):
    """The to-do order weighs deadline, priority and recent activity."""
    NOW = graph._parse_iso("2026-10-13T16:00:00Z")

    def node(self, name, due=None, act=None, pri="medium", **extra):
        attrs = dict(priority=pri, **extra)
        if due:
            attrs["due"] = due
        if act:
            attrs["last_activity"] = act
        return {"id": name, "type": "Action", "name": name, "attrs": attrs}

    def order(self, nodes):
        return [n["name"] for n in sorted(nodes, key=lambda n: graph.rank_key(n, now=self.NOW))]

    def test_long_overdue_and_quiet_goes_last(self):
        old = self.node("postmortem", due="2026-07-31", act="2026-07-21")
        soon = self.node("reply", due="2026-10-14", act="2026-10-08")
        later = self.node("plan", due="2026-11-20", act="2026-10-01")
        self.assertTrue(graph.is_gone_quiet(old, now=self.NOW))
        self.assertEqual(self.order([old, later, soon]), ["reply", "plan", "postmortem"])

    def test_long_overdue_but_recently_chased_stays_up(self):
        chased = self.node("rca", due="2026-09-05", act="2026-10-12")
        self.assertFalse(graph.is_gone_quiet(chased, now=self.NOW))
        later = self.node("plan", due="2026-11-20")
        self.assertEqual(self.order([later, chased]), ["rca", "plan"])

    def test_due_today_beats_two_weeks_late(self):
        today = self.node("today", due="2026-10-13", act="2026-10-08")
        late = self.node("late", due="2026-09-30", act="2026-09-29")
        self.assertEqual(self.order([late, today]), ["today", "late"])

    def test_no_activity_date_goes_quiet_only_after_30_days(self):
        self.assertFalse(graph.is_gone_quiet(self.node("a", due="2026-09-20"), now=self.NOW))
        self.assertTrue(graph.is_gone_quiet(self.node("b", due="2026-09-01"), now=self.NOW))

    def test_user_priority_keeps_it_out_of_gone_quiet(self):
        n = self.node("kept", due="2026-07-31", act="2026-07-21", priority_source="user")
        self.assertFalse(graph.is_gone_quiet(n, now=self.NOW))


class TestImportance(unittest.TestCase):
    """The shown priority is importance apart from the date."""
    NOW = graph._parse_iso("2026-10-13T16:00:00Z")

    def node(self, **attrs):
        return {"id": "a", "type": "Action", "name": "a", "attrs": attrs,
                "last_seen": "2026-10-13T00:00:00Z"}

    def test_date_driven_high_shows_medium(self):
        n = self.node(priority="high", due="2026-10-14")
        self.assertEqual(graph.effective_priority(n, now=self.NOW), "high")
        self.assertEqual(graph.importance(n, now=self.NOW), "medium")

    def test_high_far_from_its_date_stays_high(self):
        self.assertEqual(graph.importance(self.node(priority="high", due="2026-11-30"), now=self.NOW), "high")
        self.assertEqual(graph.importance(self.node(priority="high"), now=self.NOW), "high")

    def test_recorded_importance_and_user_choice_win(self):
        self.assertEqual(graph.importance(self.node(priority="high", due="2026-10-14",
                                                    importance="high"), now=self.NOW), "high")
        self.assertEqual(graph.importance(self.node(priority="low", importance="high",
                                                    priority_source="user"), now=self.NOW), "low")
