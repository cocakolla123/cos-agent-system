#!/usr/bin/env python3
"""Tests for the dynamic agent factory (M4). Stdlib unittest only."""

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph  # noqa: E402
import factory  # noqa: E402


def _t(day):
    return dt.datetime(2026, 4, day, 12, 0, 0, tzinfo=dt.timezone.utc)


def _names(specs):
    return sorted(s["name"] for s in specs)


class TestAlwaysAndFallback(unittest.TestCase):
    def test_always_generates_core_two(self):
        specs = factory.propose_agents(graph.Graph())
        self.assertIn("cos-knowledge", _names(specs))
        self.assertIn("cos-risk-quality", _names(specs))

    def test_empty_graph_uses_connector_fallback(self):
        specs = factory.propose_agents(
            graph.Graph(), connectors=["messaging", "ticketing"])
        names = _names(specs)
        self.assertIn("cos-comms", names)
        self.assertIn("cos-ticket-triage", names)
        # justification flags it as fallback
        comms = [s for s in specs if s["name"] == "cos-comms"][0]
        self.assertIn("fallback", comms["justification"].lower())


class TestEvidenceDriven(unittest.TestCase):
    def test_salesforce_cluster_earns_agent(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "SF-1",
                      attrs={"system": "Salesforce"}, now=_t(1))
        g.upsert_node("Incident", "employer", "INC-9",
                      attrs={"system": "Salesforce"}, now=_t(1))
        specs = factory.propose_agents(g)
        self.assertIn("cos-salesforce", _names(specs))
        sf = [s for s in specs if s["name"] == "cos-salesforce"][0]
        self.assertEqual(sf["workspace"], "employer")
        self.assertEqual(sf["model"], "opus")
        self.assertTrue(sf["evidence"])

    def test_distinct_systems_earn_distinct_agents(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "SF-1",
                      attrs={"system": "Salesforce"}, now=_t(1))
        g.upsert_node("Ticket", "employer", "GEN-1",
                      attrs={"system": "Flowmetrics"}, now=_t(1))
        names = _names(factory.propose_agents(g))
        self.assertIn("cos-salesforce", names)
        self.assertIn("cos-flowmetrics", names)

    def test_job_search_agent(self):
        g = graph.Graph()
        g.upsert_node("Document", "job-search", "app-1",
                      attrs={"job_application": True}, now=_t(1))
        self.assertIn("cos-job-search", _names(factory.propose_agents(g)))

    def test_project_builder_agent(self):
        g = graph.Graph()
        g.upsert_node("Repository", "personal", "sideproj", now=_t(1))
        self.assertIn("cos-project-builder", _names(factory.propose_agents(g)))

    def test_no_spurious_agents(self):
        # A lone employer ticket with no system/system-cluster earns no
        # domain agent (only the always-two).
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "T-1", now=_t(1))
        self.assertEqual(_names(factory.propose_agents(g)),
                         ["cos-knowledge", "cos-risk-quality"])


class TestSpecAndRender(unittest.TestCase):
    def _sf_spec(self):
        g = graph.Graph()
        g.upsert_node("Ticket", "employer", "SF-1",
                      attrs={"system": "Salesforce"}, now=_t(1))
        return [s for s in factory.propose_agents(g)
                if s["name"] == "cos-salesforce"][0]

    def test_spec_has_full_template(self):
        s = self._sf_spec()
        for field in ("mission", "responsibilities", "allowed_tools",
                      "forbidden_tools", "private_memory", "shared_memory",
                      "approval_policy", "escalation", "inputs", "outputs",
                      "confidence_requirements"):
            self.assertIn(field, s)
            self.assertTrue(s[field])

    def test_read_draft_only(self):
        s = self._sf_spec()
        # no mutating verb in allowed tools; all forbidden verbs listed
        joined = " ".join(s["allowed_tools"]).lower()
        for verb in ("send", "merge", "deploy", "delete"):
            self.assertNotIn(verb, joined)
            self.assertIn(verb, s["forbidden_tools"])

    def test_render_markdown(self):
        md = factory.render_agent_md(self._sf_spec())
        self.assertTrue(md.startswith("---\nname: cos-salesforce"))
        for section in ("## Mission", "## Responsibilities", "## Forbidden tools",
                        "## Approval policy", "## Confidence requirements",
                        "## Why this agent exists"):
            self.assertIn(section, md)
        self.assertTrue(md.endswith("\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
