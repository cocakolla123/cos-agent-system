"""Long-run world and scorer tests (model-free)."""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LR = os.path.join(os.path.dirname(HERE), "longrun")
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, LR)

import build             # noqa: E402
import score_longrun     # noqa: E402
import research          # noqa: E402
import graph as graphlib  # noqa: E402

ITEMS, GOLD, META = build.build("easy")


def oracle_records(cp, prev=None):
    """A perfect answer at checkpoint cp. At c2, arcs that closed get their
    c1 key re-emitted with status done, like an incremental poll would."""
    recs = []
    for arc in GOLD:
        st = arc.get(cp)
        before = (prev or {}).get(arc["id"])
        if st and st["state"] == "open":
            recs.append({"kind": "Action", "workspace": st["workspace"], "key": arc["id"],
                         "name": " ".join(st["gist"]), "confidence": 0.9, "edges": [],
                         "source": "oracle",
                         "attrs": {"due": st["due"], "priority": st["priority"] or "medium",
                                   "blocked_on": st["blocked_on"],
                                   "evidence": " ".join(arc["sources"])}})
        elif before and before["state"] == "open":
            recs.append({"kind": "Action", "workspace": before["workspace"],
                         "key": arc["id"], "name": " ".join(before["gist"]),
                         "confidence": 0.9, "edges": [], "source": "oracle",
                         "attrs": {"status": "done"}})
    return recs


def ingest(g, recs, today):
    research.ingest(g, recs, now=graphlib._parse_iso(today))
    return g


class TestWorld(unittest.TestCase):
    def test_deterministic_and_locked(self):
        a = build.build("easy")
        self.assertEqual(json.dumps(a[0]), json.dumps(ITEMS))
        self.assertEqual(json.dumps(a[1]), json.dumps(GOLD))

    def test_only_example_domains(self):
        blob = json.dumps([ITEMS, META])
        for dom in re.findall(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]+)", blob):
            self.assertTrue(dom.endswith(".example"), dom)
        for host in re.findall(r"https?://([^/\s\"]+)", blob):
            self.assertTrue(host.endswith(".example"), host)

    def test_arc_sources_exist_and_ids_unique(self):
        ids = [i["id"] for i in ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        for arc in GOLD:
            for s in arc["sources"]:
                self.assertIn(s, ids, arc["id"])

    def test_every_phenomenon_has_dev_and_test(self):
        by = {}
        for arc in GOLD:
            by.setdefault(arc["phenomenon"], set()).add(arc["split"])
        for p, splits in by.items():
            self.assertEqual(splits, {"dev", "test"}, p)

    def test_gists_are_multiword(self):
        for arc in GOLD:
            for cp in ("c1", "c2"):
                st = arc.get(cp)
                if st and st["state"] == "open":
                    self.assertGreaterEqual(len(st["gist"]), 2, arc["id"])


class TestScorer(unittest.TestCase):
    def test_oracle_passes_everything_at_c1_and_c2(self):
        g = ingest(graphlib.Graph(), oracle_records("c1"), META["today"])
        r1 = score_longrun.score_graph(g, GOLD, "c1", META["today"])
        failing = [a["id"] for a in r1["arcs"] if not a["pass"]]
        self.assertEqual(failing, [])
        self.assertEqual(r1["noise_fps"], [])
        self.assertEqual(r1["isolation"], [])
        prev = {a["id"]: a.get("c1") for a in GOLD}
        g = ingest(g, oracle_records("c2", prev), META["c2"])
        r2 = score_longrun.score_graph(g, GOLD, "c2", META["c2"])
        self.assertEqual([a["id"] for a in r2["arcs"] if not a["pass"]], [])
        self.assertEqual(r2["noise_fps"], [])

    def test_empty_answer_catches_nothing_and_keeps_absent(self):
        r = score_longrun.score_graph(graphlib.Graph(), GOLD, "c1", META["today"])
        for a in r["arcs"]:
            self.assertEqual(a["pass"], a["expect"] == "absent", a["id"])

    def test_wrong_priority_and_due_fail(self):
        recs = oracle_records("c1")
        for rec in recs:
            if rec["key"] == "D01":
                rec["attrs"]["priority"] = "low"
            if rec["key"] == "D04":
                rec["attrs"]["due"] = "2026-08-28"
        g = ingest(graphlib.Graph(), recs, META["today"])
        r = {a["id"]: a for a in score_longrun.score_graph(g, GOLD, "c1", META["today"])["arcs"]}
        self.assertFalse(r["D01"]["priority_ok"])
        self.assertFalse(r["D04"]["due_ok"])
        self.assertTrue(r["D06"]["pass"])

    def test_wrong_workspace_is_isolation_violation(self):
        recs = oracle_records("c1")
        for rec in recs:
            if rec["key"] == "T21":
                rec["workspace"] = "kestrel"
        g = ingest(graphlib.Graph(), recs, META["today"])
        r = score_longrun.score_graph(g, GOLD, "c1", META["today"])
        t21 = [a for a in r["arcs"] if a["id"] == "T21"][0]
        self.assertFalse(t21["caught"])
        self.assertTrue(t21["wrong_workspace"])
        self.assertTrue(any(v["arc"] == "T21" for v in r["isolation"]))

    def test_injected_close_is_counted(self):
        recs = oracle_records("c1")
        doc = [a for a in GOLD if a["id"] == "T13"][0]["sources"][0]
        for rec in recs:
            if rec["key"] == "D04":
                rec["attrs"]["status"] = "done"
                rec["attrs"]["evidence"] += " " + doc
        g = ingest(graphlib.Graph(), recs, META["today"])
        r = score_longrun.score_graph(g, GOLD, "c1", META["today"])
        self.assertEqual(len(r["injection_closed"]), 1)


if __name__ == "__main__":
    unittest.main()


class TestRealisticWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.gold, cls.meta = build.build("realistic")

    def test_only_example_domains(self):
        blob = json.dumps([self.items, self.meta])
        for dom in set(re.findall(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]+)", blob)):
            self.assertTrue(dom.endswith(".example"), dom)

    def test_oracle_passes_everything(self):
        global GOLD
        saved = GOLD
        GOLD = self.gold
        try:
            g = ingest(graphlib.Graph(), oracle_records("c1"), self.meta["today"])
            r1 = score_longrun.score_graph(g, self.gold, "c1", self.meta["today"])
            self.assertEqual([a["id"] for a in r1["arcs"] if not a["pass"]], [])
            prev = {a["id"]: a.get("c1") for a in self.gold}
            g = ingest(g, oracle_records("c2", prev), self.meta["c2"])
            r2 = score_longrun.score_graph(g, self.gold, "c2", self.meta["c2"])
            self.assertEqual([a["id"] for a in r2["arcs"] if not a["pass"]], [])
            self.assertEqual(r2["noise_fps"], [])
        finally:
            GOLD = saved

    def test_volume_is_realistic(self):
        hist = [i for i in self.items if i["date"] < self.meta["today"]]
        slack = [i for i in hist if i["connector"] == "slack"]
        chans = {i["channel"] for i in slack}
        self.assertGreater(len(slack), 5000)
        self.assertGreater(len(chans), 100)
        muted = [c for c in self.meta["slack_channels"] if c["is_muted"]]
        self.assertGreater(len(muted), 10)
