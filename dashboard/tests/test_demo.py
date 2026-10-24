"""The public demo is built only from fictional data and never acts."""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEMO = os.path.join(ROOT, "demo")
sys.path.insert(0, DEMO)

import build_demo      # noqa: E402
import export_static   # noqa: E402

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]+)")


class TestDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = build_demo.build()

    def test_state_is_fictional(self):
        for root, _, files in os.walk(self.state):
            for f in files:
                text = open(os.path.join(root, f), errors="replace").read()
                for dom in EMAIL.findall(text):
                    self.assertTrue(dom.endswith(".example"), (f, dom))

    def test_config_is_demo_and_grants_nothing(self):
        cfg = json.load(open(os.path.join(self.state, "config.json")))
        self.assertTrue(cfg["demo"])
        self.assertEqual(cfg["demo_today"], build_demo.TODAY)
        for k in ("base_tools", "chat_tools", "revise_tools", "poll_tools"):
            self.assertEqual(cfg[k], "Read")
        self.assertFalse(cfg["self_modify_code"])

    def test_graph_is_the_recorded_run(self):
        # identical except attrs.last_activity, which the demo adds from the
        # world's own item dates (the recorded run predates that field)
        def load(d):
            out = {}
            for line in open(os.path.join(d, "nodes.jsonl")):
                n = json.loads(line)
                for k in ("last_activity", "importance", "importance_reason", "kind"):
                    (n.get("attrs") or {}).pop(k, None)
                out[n["id"]] = n
            return out
        src = load(build_demo.SOURCE_GRAPH)
        dst = load(os.path.join(self.state, "workspace", "graph"))
        self.assertEqual(src, dst)

    def test_saved_chat_replies_come_from_the_graph(self):
        resp = json.load(open(os.path.join(self.state, "responses.json")))
        self.assertIn("computed from the graph", resp["/chat"]["urgent"])

    def test_every_open_task_has_a_pending_next_step(self):
        sys.path.insert(0, os.path.join(ROOT, "dashboard"))
        import graph
        os.environ["COS_FIXED_NOW"] = build_demo.TODAY + "T16:00:00Z"
        try:
            g = graph.Graph.load(os.path.join(self.state, "workspace", "graph"))
            open_ = {n["id"] for n in g.nodes.values()
                     if n["type"] == "Action" and graph.is_open_action(n)}
        finally:
            os.environ.pop("COS_FIXED_NOW", None)
        text = open(os.path.join(self.state, "workspace", "approval-queue.md")).read()
        blocks = text.split("\n### ")[2:]
        tied = {re.search(r"^- task: (.+)$", b, re.M).group(1) for b in blocks
                if "- status: pending" in b and "- task: " in b}
        self.assertEqual(open_ - tied, set())

    def test_static_pages_have_no_reload_and_local_links(self):
        page = ('<html><head></head><a href="?workspace=all">All</a>'
                '<a href="?workspace=job-search">J</a><script>location.reload()</script>')
        out = export_static.staticize(page, "<script>shim</script>")
        self.assertNotIn("location.reload(", out)
        self.assertIn('href="index.html"', out)
        self.assertIn('href="ws-job-search.html"', out)
        self.assertTrue(out.startswith("<html><head>\n<script>shim</script>"))


if __name__ == "__main__":
    unittest.main()
