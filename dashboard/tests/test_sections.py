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
        self.assertIn("Workspace:",
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
