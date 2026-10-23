#!/usr/bin/env python3
"""Tests for graph-powered dashboard sections (M6). Stdlib unittest only."""

import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402
import research  # noqa: E402
import sections  # noqa: E402
import workspaces  # noqa: E402


def _t(day):
    return dt.datetime(2026, 6, day, 12, 0, 0, tzinfo=dt.timezone.utc)


def _rich_graph():
    g = graph.Graph()
    g.upsert_node("Ticket", "employer", "T-1", name="Ship feature",
                  attrs={"priority": "high", "status": "open"}, now=_t(1))
    g.upsert_node("Ticket", "employer", "T-2", name="Old bug",
                  attrs={"priority": "low", "status": "open", "blocked": True},
                  now=_t(1))
    g.upsert_node("Person", "employer", "mel", name="Mel",
                  attrs={"waiting_on_user": True}, now=_t(1))
    g.upsert_node("Incident", "employer", "INC-1",
                  attrs={"system": "Salesforce"}, now=_t(1))
    g.upsert_node("Repository", "personal", "sideproj", name="sideproj", now=_t(1))
    g.upsert_node("Meeting", "employer", "sync", attrs={"when": "2026-06-02T10:00:00Z"},
                  now=_t(1))
    g.upsert_node("Document", "job-search", "app-1", name="Acme SWE",
                  attrs={"job_application": True, "stage": "applied"}, now=_t(1))
    g.upsert_node("Project", "freelance", "clientsite", name="Client site",
                  attrs={"client": "BigCo"}, now=_t(1))
    return g


class TestSectionData(unittest.TestCase):
    def setUp(self):
        self.g = _rich_graph()

    def test_daily_priorities_high_first(self):
        items = sections.daily_priorities(self.g)
        titles = [i["title"] for i in items]
        self.assertIn("Ship feature", titles)
        self.assertLess(titles.index("Ship feature"), titles.index("Old bug"))

    def test_people_waiting(self):
        self.assertEqual([i["title"] for i in sections.people_waiting(self.g)],
                         ["Mel"])

    def test_blocked_work(self):
        self.assertEqual([i["title"] for i in sections.blocked_work(self.g)],
                         ["Old bug"])

    def test_blocked_on_counts_as_blocked(self):
        self.g.upsert_node("Action", "job-search", "chase", name="Recruiter call",
                           attrs={"blocked_on": "the recruiter"}, now=_t(1))
        items = {i["title"]: i for i in sections.blocked_work(self.g)}
        self.assertEqual(items["Recruiter call"]["sub"], "waiting on the recruiter")
        self.assertIn("Old bug", items)

    def test_rejected_application_leaves_lists(self):
        self.g.upsert_node("Action", "job-search", "rej", name="Rejected role",
                           attrs={"job_application": True, "status": "rejected"},
                           now=_t(1))
        self.assertNotIn("Rejected role",
                         [i["title"] for i in sections.job_applications(self.g)])
        self.assertNotIn("Rejected role",
                         [i["title"] for i in sections.next_actions(self.g)])

    def test_investigations(self):
        self.assertEqual(len(sections.investigations(self.g)), 1)

    def test_job_applications(self):
        items = sections.job_applications(self.g)
        self.assertEqual(items[0]["sub"], "applied")

    def test_freelance(self):
        self.assertEqual(sections.freelance_work(self.g)[0]["sub"], "BigCo")

    def test_personal_projects(self):
        self.assertEqual([i["title"] for i in sections.personal_projects(self.g)],
                         ["sideproj"])

    def test_personal_project_shows_state(self):
        self.g.upsert_node("Project", "side", "app", name="Photo app",
                           attrs={"personal_project": True,
                                  "state_summary": "redesign in progress",
                                  "health": "CI red since Oct 20"}, now=_t(1))
        items = {i["title"]: i for i in sections.personal_projects(self.g)}
        self.assertEqual(items["Photo app"]["sub"],
                         "redesign in progress · CI red since Oct 20")
        self.assertIn("sideproj", items)
        self.assertNotIn("Photo app",
                         [i["title"] for i in sections.personal_projects(self.g, "personal")])

    def test_workspace_filter_isolates(self):
        # scoped to employer -> no personal repo in projects
        titles = [i["title"] for i in sections.projects(self.g, ws="employer")]
        self.assertNotIn("sideproj", titles)


class TestRender(unittest.TestCase):
    def test_empty_graph_renders_nothing(self):
        self.assertEqual(sections.render_sections(graph.Graph()), "")
        self.assertEqual(sections.render_sections(None), "")

    def test_render_contains_sections_and_escapes(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "T-1",
                      name="<script>alert(1)</script>",
                      attrs={"priority": "high", "status": "open"}, now=_t(1))
        html = sections.render_sections(g)
        self.assertIn("Command Center", html)
        self.assertIn("Daily Priorities", html)
        self.assertNotIn("<script>alert(1)</script>", html)  # escaped
        self.assertIn("&lt;script&gt;", html)

    def test_switcher_inert_below_two(self):
        reg = workspaces.Registry()
        reg.upsert("employer", kind="employer")
        self.assertEqual(sections.render_workspace_switcher(reg, "employer"), "")
        reg.upsert("personal", kind="personal")
        self.assertIn('aria-label="Workspace"',
                      sections.render_workspace_switcher(reg, "employer"))

    def test_objective_card_rendered(self):
        g = graph.Graph()
        import correlate
        g.upsert_node("Channel", "employer", "th", attrs={"refs": ["T-1"]}, now=_t(1))
        g.upsert_node("Ticket", "employer", "T-1", name="Fix",
                      attrs={"refs": ["T-1"]}, now=_t(1))
        correlate.correlate(g, now=_t(2))
        html = sections.render_sections(g)
        self.assertIn("Workstreams", html)
        self.assertIn("obj-timeline", html)

    def test_load_for_dashboard_missing_graph(self):
        with tempfile.TemporaryDirectory() as d:
            g, reg, active = sections.load_for_dashboard(d)
            self.assertIsNone(g)
            self.assertEqual(reg.ids(), [])
            self.assertIsNone(active)

    def test_load_for_dashboard_reads_graph(self):
        with tempfile.TemporaryDirectory() as d:
            g = _rich_graph()
            g.save(os.path.join(d, "graph"))
            reg = workspaces.Registry()
            reg.upsert("employer", kind="employer")
            reg.upsert("personal", kind="personal")
            reg.save(d)
            g2, reg2, active = sections.load_for_dashboard(d, "personal")
            self.assertIsNotNone(g2)
            self.assertEqual(active, "personal")


class TestDormantSuppression(unittest.TestCase):
    """Sections that claim to show *current* work must drop history.

    Regression guard for the stale-container correction.
    """

    def _g(self):
        g = _rich_graph()
        g.upsert_node("Project", "volunteer", "district-9-north",
                      name="District 9 North",
                      attrs={"last_activity": "2019-08-02"}, now=_t(1))
        g.upsert_node("Project", "personal", "asana-demo", name="Vendor starter project",
                      attrs={"dormant": True}, now=_t(1))
        return g

    def test_dormant_project_is_not_a_current_project(self):
        ids = [i["id"] for i in sections.projects(self._g())]
        self.assertNotIn("volunteer:project:district-9-north", ids)

    def test_live_projects_still_listed(self):
        ids = [i["id"] for i in sections.projects(self._g())]
        self.assertIn("freelance:project:clientsite", ids)
        self.assertIn("personal:repository:sideproj", ids)

    def test_dormant_demo_dropped_from_personal_projects(self):
        ids = [i["id"] for i in sections.personal_projects(self._g())]
        self.assertNotIn("personal:project:asana-demo", ids)
        self.assertIn("personal:repository:sideproj", ids)

    def test_objective_over_only_dormant_members_is_not_a_priority(self):
        g = self._g()
        g.upsert_node("Objective", "personal", "asana-starter",
                      name="Workstream: asana-starter", now=_t(1))
        g.upsert_edge("personal:project:asana-demo",
                      "personal:objective:asana-starter", "part_of", now=_t(1))
        ids = [i["id"] for i in sections.daily_priorities(g)]
        self.assertNotIn("personal:objective:asana-starter", ids)

    def test_objective_with_one_live_member_survives(self):
        g = self._g()
        g.upsert_node("Objective", "personal", "mixed", now=_t(1))
        g.upsert_edge("personal:project:asana-demo",
                      "personal:objective:mixed", "part_of", now=_t(1))
        g.upsert_edge("personal:repository:sideproj",
                      "personal:objective:mixed", "part_of", now=_t(1))
        ids = [i["id"] for i in sections.daily_priorities(g)]
        self.assertIn("personal:objective:mixed", ids)

    def test_items_expose_the_dormant_flag(self):
        for i in sections.projects(self._g()):
            self.assertIn("dormant", i)
            self.assertFalse(i["dormant"])


class TestConcludedSuppression(unittest.TestCase):
    """Explicitly-ended work must leave the current-work views immediately.

    Regression guard for the concluded-engagement correction: everything
    here is recent enough to pass every freshness and dormancy check, which is
    exactly why the dashboard kept showing it.
    """

    def _g(self):
        g = _rich_graph()
        g.upsert_node("Document", "clientco", "life-tasks-guide",
                      name="Feather Life Tasks — Workflow Guide",
                      attrs={"modified": "2026-08-04", "concluded": True,
                             "concluded_on": "2026-08-27",
                             "concluded_by": "gmail:1a0452f7b074ec93"}, now=_t(1))
        g.upsert_node("Objective", "clientco", "life-tasks-feather",
                      name="Workstream: life-tasks-feather",
                      attrs={"concluded": True}, now=_t(1))
        g.upsert_edge("clientco:document:life-tasks-guide",
                      "clientco:objective:life-tasks-feather", "part_of", now=_t(1))
        # a live workstream alongside it, so the tests prove the filter is
        # selective rather than just emptying the card
        g.upsert_node("Objective", "employer", "ship-feature",
                      name="Workstream: ship-feature", now=_t(1))
        g.upsert_edge("employer:ticket:t-1", "employer:objective:ship-feature",
                      "part_of", now=_t(1))
        return g

    def test_concluded_objective_is_not_a_daily_priority(self):
        ids = [i["id"] for i in sections.daily_priorities(self._g())]
        self.assertNotIn("clientco:objective:life-tasks-feather", ids)

    def test_objective_over_only_concluded_members_is_not_a_priority(self):
        """Even unmarked itself, a workstream is only as live as its members."""
        g = self._g()
        g.nodes["clientco:objective:life-tasks-feather"]["attrs"].pop("concluded")
        ids = [i["id"] for i in sections.daily_priorities(g)]
        self.assertNotIn("clientco:objective:life-tasks-feather", ids)

    def test_concluded_workstream_card_is_not_rendered(self):
        html = sections.render_sections(self._g())
        self.assertNotIn("life-tasks-feather", html)

    def test_live_workstream_card_still_rendered(self):
        html = sections.render_sections(self._g())
        self.assertIn("Workstreams", html)
        self.assertIn("ship-feature", html)

    def test_items_expose_the_concluded_flag(self):
        for i in sections.projects(self._g()):
            self.assertIn("concluded", i)
            self.assertFalse(i["concluded"])


class TestNextActions(unittest.TestCase):
    """The to-do list.

    Regression guard for corr-20260912T103414-to-do-lists-dashboard: every
    section rendered nouns, so a user asking "what do I need to do?" got an
    inventory of documents and workstream cards instead of an answer.
    """

    NOW = dt.datetime(2026, 9, 12, 12, 0, 0, tzinfo=dt.timezone.utc)

    def _g(self):
        g = graph.Graph()
        # _days_label reads the real clock, so a hardcoded due date flips
        # from "due in" to "overdue by" the day it passes — keep this one
        # relative to today (it broke exactly that way once).
        soon = (dt.datetime.now(dt.timezone.utc)
                + dt.timedelta(days=6)).strftime("%Y-%m-%dT23:59:00+00:00")
        g.upsert_node("Action", "job-search", "vendor-a-assessment",
                      name="Take the Vendor-A coding assessment",
                      attrs={"due": soon,
                             "priority": "high"}, now=self.NOW)
        g.upsert_node("Action", "personal", "payments-balance",
                      name="Pay a payments app negative balance ($205.60)",
                      attrs={"due": "2026-08-15", "priority": "high"},
                      now=self.NOW)
        g.upsert_node("Action", "job-search", "lapsed-cert",
                      name="Renew the lapsed certification",
                      attrs={"priority": "high"}, now=self.NOW)
        g.upsert_node("Action", "job-search", "already-sent",
                      name="Submit availability form",
                      attrs={"status": "submitted"}, now=self.NOW)
        # a vendor onboarding sample with a plausible near-term due date
        g.upsert_node("Ticket", "personal", "asana-demo", name="Task 1",
                      attrs={"likely_demo": True, "status": "open",
                             "due_on": "2026-09-15"}, now=self.NOW)
        # an ordinary entity: fresh, active, and not a to-do
        g.upsert_node("Document", "job-search", "tracker",
                      name="Job Applications Tracker", now=self.NOW)
        return g

    def test_soonest_due_then_undated_then_gone_quiet(self):
        titles = [i["title"] for i in sections.next_actions(self._g())]
        self.assertEqual(titles, [
            "Take the Vendor-A coding assessment",     # due in 6 days
            "Renew the lapsed certification",   # undated, high
            # over 30 days late with no activity on record: still listed,
            # in the "gone quiet, still needed?" group at the end
            "Pay a payments app negative balance ($205.60)",
        ])

    def test_recently_late_stays_on_top(self):
        g = self._g()
        late = (dt.datetime.now(dt.timezone.utc)
                - dt.timedelta(days=2)).strftime("%Y-%m-%d")
        g.upsert_node("Action", "personal", "fresh-late", name="Reply to the landlord",
                      attrs={"due": late, "priority": "medium"}, now=self.NOW)
        titles = [i["title"] for i in sections.next_actions(g)]
        self.assertEqual(titles[0], "Reply to the landlord")

    def test_satisfied_obligation_is_off_the_list(self):
        ids = [i["id"] for i in sections.next_actions(self._g())]
        self.assertNotIn("job-search:action:already-sent", ids)

    def test_demo_task_never_reaches_the_todo_list(self):
        """The exact junk the inventory used to surface as a priority."""
        ids = [i["id"] for i in sections.next_actions(self._g())]
        self.assertNotIn("personal:ticket:asana-demo", ids)

    def test_plain_documents_are_not_todos(self):
        ids = [i["id"] for i in sections.next_actions(self._g())]
        self.assertNotIn("job-search:document:tracker", ids)

    def test_deadline_is_spelled_out_for_the_reader(self):
        by_id = {i["id"]: i for i in sections.next_actions(self._g())}
        self.assertIn("overdue by",
                      by_id["personal:action:payments-balance"]["sub"])
        self.assertTrue(by_id["personal:action:payments-balance"]["overdue"])
        self.assertIn("due in",
                      by_id["job-search:action:vendor-a-assessment"]["sub"])

    def test_real_dated_ticket_is_included(self):
        g = self._g()
        g.upsert_node("Ticket", "employer", "T-7", name="Ship the fix",
                      attrs={"status": "open", "due_on": "2026-09-14"},
                      now=self.NOW)
        ids = [i["id"] for i in sections.next_actions(g)]
        self.assertIn("employer:ticket:t-7", ids)

    def test_workspace_filter_applies(self):
        ids = [i["id"] for i in sections.next_actions(self._g(), ws="personal")]
        self.assertEqual(ids, ["personal:action:payments-balance"])

    def test_todo_section_renders_first(self):
        g = self._g()
        # an undated priority, so Daily Priorities is non-empty and actually
        # renders (empty sections are omitted) — and so the ordering assertion
        # below has two real sections to compare
        g.upsert_node("Ticket", "employer", "T-5", name="Ship feature",
                      attrs={"priority": "high", "status": "open"},
                      now=self.NOW)
        html = sections.render_sections(g)
        self.assertIn("To-Do / Next Actions", html)
        self.assertLess(html.index("To-Do / Next Actions"),
                        html.index("Daily Priorities"))

    def test_empty_graph_still_degrades_to_nothing(self):
        self.assertEqual(sections.next_actions(graph.Graph()), [])


class TestCoverageReport(unittest.TestCase):
    """A zero must be visible, because 'nothing due' and 'nothing ever looked'
    render identically. Escalation for the recurring unknown:coverage_gap
    signature."""

    def test_report_covers_every_section(self):
        report = sections.coverage_report(_rich_graph())
        self.assertEqual([r["section"] for r in report],
                         [label for label, _ in sections.SECTIONS])
        self.assertTrue(all("count" in r for r in report))

    def test_empty_graph_reports_every_section_unanswered(self):
        self.assertEqual(sections.unanswered_questions(graph.Graph()),
                         [label for label, _ in sections.SECTIONS])

    def test_populated_sections_are_not_flagged(self):
        unanswered = sections.unanswered_questions(_rich_graph())
        self.assertNotIn("Blocked Work", unanswered)
        self.assertNotIn("People Waiting", unanswered)

    def test_missing_todos_are_flagged_as_unanswered(self):
        """The exact gap that reached the user unannounced."""
        self.assertIn("To-Do / Next Actions",
                      sections.unanswered_questions(_rich_graph()))

    def test_a_broken_section_counts_as_a_gap_not_a_crash(self):
        original = sections.SECTIONS[:]
        def boom(g, ws=None):
            raise RuntimeError("connector exploded")
        sections.SECTIONS.append(("Exploding", boom))
        try:
            self.assertIn("Exploding",
                          sections.unanswered_questions(_rich_graph()))
        finally:
            sections.SECTIONS[:] = original


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestItemStaleMeansFreshness(unittest.TestCase):
    """item['stale'] is crawl freshness (graph.is_stale), not 'gone quiet'."""
    def test_long_overdue_but_freshly_seen_is_not_stale(self):
        g = graph.Graph()
        n = g.upsert_node("Action", "w", "old", name="Old ask",
                          attrs={"due": "2020-01-01"})
        it = sections._item(n)
        self.assertFalse(it["stale"])
        self.assertTrue(graph.is_gone_quiet(n))
