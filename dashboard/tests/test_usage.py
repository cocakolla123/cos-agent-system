"""Every model call: only the job's tools sent, capped, logged, and the daily budget held."""

import json
import os
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import usage  # noqa: E402

ENVELOPE = {"result": "done", "total_cost_usd": 0.0123, "duration_ms": 900, "num_turns": 2,
            "usage": {"input_tokens": 5, "output_tokens": 40, "cache_read_input_tokens": 3000,
                      "cache_creation_input_tokens": 1000},
            "modelUsage": {"claude-sonnet-5-5": {}}}


class TestUsage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        # a fake claude that prints a JSON envelope and records its arguments
        self.fake = os.path.join(self.d, "claude")
        with open(self.fake, "w") as f:
            f.write("#!/bin/sh\necho \"$@\" > %s/args.txt\necho '%s'\n"
                    % (self.d, json.dumps(ENVELOPE)))
        os.chmod(self.fake, os.stat(self.fake).st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_granted_builtins_are_sent(self):
        self.assertEqual(usage.builtin_tools("Read,Edit,Agent,mcp__slack__read"),
                         ["Read", "Edit", "Agent", "ToolSearch"])
        self.assertEqual(usage.builtin_tools("Read,Bash(python3:*),Glob"), ["Read", "Bash", "Glob"])
        cmd = usage.prepare(["claude", "-p", "x", "--allowedTools", "Read,Agent",
                             "--output-format", "text"], "chat", self.d)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "Read,Agent")
        self.assertEqual(cmd[cmd.index("--output-format") + 1], "json")
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "0.50")

    def test_run_returns_text_and_logs_cost(self):
        res = usage.run([self.fake, "-p", "hi", "--allowedTools", "Read"], "poll", self.d)
        self.assertEqual(res.stdout, "done")
        args = open(os.path.join(self.d, "args.txt")).read()
        self.assertIn("--tools Read ", args)
        s = usage.summary(self.d)
        self.assertEqual(s["calls"], 1)
        self.assertAlmostEqual(s["today"], 0.0123)
        self.assertEqual(s["by_job"]["poll"]["tokens"], 4045)

    def test_daily_budget_stops_new_work_but_not_approvals(self):
        usage.save_budget(self.d, 0.01)
        usage.run([self.fake, "-p", "hi", "--allowedTools", "Read"], "poll", self.d)
        blocked = usage.run([self.fake, "-p", "again", "--allowedTools", "Read"], "chat", self.d)
        self.assertEqual(blocked.returncode, 3)
        self.assertIn("budget is used up", blocked.stdout)
        ok = usage.run([self.fake, "-p", "approve", "--allowedTools", "Read"], "approve", self.d)
        self.assertEqual(ok.stdout, "done")
        usage.save_budget(self.d, None)
        self.assertIsNone(usage.budget(self.d)["daily_usd"])

    def test_cli_over_budget_exit_code(self):
        self.assertEqual(usage.main(["over-budget", self.d]), 1)
        usage.save_budget(self.d, 0.01)
        usage.record(self.d, "poll", ENVELOPE)
        with self.assertRaises(ValueError):
            usage.save_budget(self.d, 0.001)
        self.assertEqual(usage.main(["over-budget", self.d]), 0)


if __name__ == "__main__":
    unittest.main()
