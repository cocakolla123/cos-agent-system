"""Projects (Step 1e) world and scorer tests (model-free)."""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PD = os.path.join(os.path.dirname(HERE), "projects")
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, PD)

import build_projects as build  # noqa: E402
import run_projects   # noqa: E402

GOLD = json.load(open(os.path.join(PD, "gold.json")))


def proj(key, summary, health="", **attrs):
    a = {"personal_project": True, "state_summary": summary, "health": health}
    a.update(attrs)
    return {"kind": "Project", "workspace": "personal", "key": key, "name": key,
            "attrs": a, "confidence": 0.9, "edges": []}


def act(key, name, ref):
    return {"kind": "Action", "workspace": "personal", "key": key, "name": name,
            "attrs": {"priority": "medium", "refs": ref}, "confidence": 0.9, "edges": []}


ORACLE = {"records": [
    proj("glimmer", "v3 redesign in progress", "CI dies in 4 seconds before any step: runner or billing",
         collaborators=["devpal"]),
    proj("tidepool-quant", "cash ledger fix merged", "main red: typecheck (pyright) failing"),
    proj("cos-helper", "assistant with a new calendar module", "green"),
    act("glimmer-pr14", "Review devpal's PR #14 (moderation queue)", "glimmer"),
    act("glimmer-ci", "Fix glimmer CI: Actions runner or billing", "glimmer"),
    act("tide-runbook", "Run the cash-ledger runbook apply steps", "tidepool-quant"),
    act("tide-vendor", "Decide on the data vendor Pro plan upgrade", "tidepool-quant"),
    act("tide-ci", "Fix the pyright typecheck failure on main", "tidepool-quant"),
], "questions": ["You mentioned Harbor Map. Where does it live?"]}


class TestProjectsWorld(unittest.TestCase):
    def test_world_is_current_and_fictional(self):
        world = os.path.join(PD, "world")
        for root, _, files in os.walk(world):
            for f in files:
                text = open(os.path.join(root, f)).read()
                for dom in re.findall(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]+)", text):
                    self.assertTrue(dom.endswith(".example"), (f, dom))
        self.assertEqual(json.load(open(os.path.join(PD, "gold.json"))),
                         json.loads(json.dumps(build.GOLD, sort_keys=True)))

    def test_prompt_uses_production_step(self):
        step, pri = run_projects.production_text()
        self.assertIn("Step 1e", step)
        self.assertIn("high", pri)


class TestProjectsScorer(unittest.TestCase):
    def test_oracle_passes(self):
        res = run_projects.score(ORACLE, GOLD)
        self.assertTrue(res["pass"], json.dumps(res, indent=1))

    def test_empty_fails(self):
        self.assertFalse(run_projects.score({"records": [], "questions": []}, GOLD)["pass"])

    def test_todo_noise_and_per_run_ci_fail(self):
        noisy = json.loads(json.dumps(ORACLE))
        noisy["records"].append(act("ch-todo", "Add edge dedup (TODO in graph.py)", "cos-helper"))
        noisy["records"].append(act("glimmer-ci-2", "Fix glimmer CI run g3", "glimmer"))
        rows = {r["project"]: r for r in run_projects.score(noisy, GOLD)["rows"]}
        self.assertFalse(rows["cos-helper"]["pass"])
        self.assertFalse(rows["glimmer"]["pass"])

    def test_dormant_project_with_action_fails(self):
        bad = json.loads(json.dumps(ORACLE))
        bad["records"].append(act("pf", "Update old-portfolio projects page", "old-portfolio"))
        rows = {r["project"]: r for r in run_projects.score(bad, GOLD)["rows"]}
        self.assertFalse(rows["old-portfolio"]["pass"])


if __name__ == "__main__":
    unittest.main()
