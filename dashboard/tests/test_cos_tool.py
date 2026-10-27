"""cos_tool.py: the only commands the research and account jobs may run."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import cos_tool   # noqa: E402
import graph      # noqa: E402


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cos_tool.main(list(argv))
    return code, (json.loads(out.getvalue()) if out.getvalue().strip() else None), err.getvalue()


class TestCosTool(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp()
        self.g = os.path.join(self.ws, "graph")
        self.cfg = os.path.join(self.ws, "config.json")
        os.environ["COS_CONFIG"] = self.cfg
        with open(self.cfg, "w") as f:
            json.dump({"connector_accounts": [{"id": "gmail-work", "kind": "email"}]}, f)

    def tearDown(self):
        os.environ.pop("COS_CONFIG", None)

    def write(self, name, obj):
        p = os.path.join(self.ws, name)
        with open(p, "w") as f:
            json.dump(obj, f)
        return p

    def test_ingest_validates_locks_and_renders(self):
        recs = [{"kind": "Action", "workspace": "work", "key": "send-deck", "name": "Send the deck",
                 "attrs": {"due": "2026-10-30"}},
                {"kind": "Action", "name": "no key"}]
        code, out, _ = run("ingest", self.g, self.write("r.json", recs))
        self.assertEqual((code, out["ingested"], out["invalid"]), (0, 1, 1))
        self.assertIsNotNone(graph.Graph.load(self.g).get("work:action:send-deck"))
        self.assertTrue(os.path.isdir(os.path.join(self.g, "views")))

    def test_refuses_bad_input(self):
        self.assertEqual(run("ingest", self.g, os.path.join(self.ws, "missing.json"))[0], 1)
        with open(os.path.join(self.ws, "bad.json"), "w") as f:
            f.write("not json")
        self.assertEqual(run("ingest", self.g, os.path.join(self.ws, "bad.json"))[0], 1)
        self.assertEqual(run("ingest", self.ws, self.write("r.json", []))[0], 1)   # not a graph/ dir
        self.assertEqual(run("python3", "-c", "print(1)")[0], 2)
        self.assertEqual(run()[0], 2)

    def test_context_done_moves_only_inbox_files(self):
        inbox = os.path.join(self.ws, "context-inbox")
        os.makedirs(inbox)
        p = os.path.join(inbox, "notes.txt")
        with open(p, "w") as f:
            f.write("Acme is a client")
        self.assertEqual(run("context-done", self.ws, self.cfg)[0], 1)       # outside the inbox
        code, out, _ = run("context-done", self.ws, p)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out["moved_to"]))

    def test_accounts(self):
        code, out, _ = run("accounts-add", self.write("e.json", {"id": "slack-work", "kind": "messaging",
                                                                 "token": "xoxp-should-not-be-kept"}))
        self.assertEqual(code, 0)
        cfg = json.load(open(self.cfg))
        self.assertEqual([a["id"] for a in cfg["connector_accounts"]], ["gmail-work", "slack-work"])
        self.assertNotIn("token", json.dumps(cfg))
        self.assertEqual(run("accounts-bind", "slack-work", "Work")[1]["workspace"], "work")
        self.assertEqual(run("accounts-auth", "gmail-work", "--url", "javascript:alert(1)")[0], 1)
        self.assertEqual(run("accounts-status", "gmail-work", "maybe")[0], 1)
        ids = [a["id"] for a in run("accounts-list")[1]]
        self.assertEqual(ids, ["gmail-work", "slack-work"])


if __name__ == "__main__":
    unittest.main()
