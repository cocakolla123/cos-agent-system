"""Bug fix to PR flow: worktree, tests run by the system, approval, never merge."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import codefix  # noqa: E402

BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
TEST = ("import unittest\nfrom calc import add\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")
TEST_CMD = "%s -m unittest -q test_calc" % sys.executable


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class TestCodeFix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.remote = os.path.join(root, "remote.git")
        self.repo = os.path.join(root, "repo")
        self.ws = os.path.join(root, "ws")
        os.makedirs(self.ws)
        sh(root, "git", "init", "-q", "--bare", self.remote)
        sh(root, "git", "init", "-q", "-b", "main", self.repo)
        for k, v in (("user.email", "t@test.example"), ("user.name", "t")):
            sh(self.repo, "git", "config", k, v)
        with open(os.path.join(self.repo, "calc.py"), "w") as f:
            f.write(BUGGY)
        with open(os.path.join(self.repo, "test_calc.py"), "w") as f:
            f.write(TEST)
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-q", "-m", "init")
        # a relative remote path, as in a local mirror: must resolve from the repo
        sh(self.repo, "git", "remote", "add", "origin", "../remote.git")
        sh(self.repo, "git", "push", "-q", "origin", "main")
        # a fake gh that records its arguments and prints a PR URL
        self.gh_log = os.path.join(root, "gh.log")
        self.gh = os.path.join(root, "gh")
        with open(self.gh, "w") as f:
            f.write("#!/bin/sh\necho \"$@\" >> %s\necho https://github.example/o/r/pull/7\n"
                    % self.gh_log)
        os.chmod(self.gh, os.stat(self.gh).st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.tmp.cleanup()

    def _fix(self, content=FIXED):
        fix = codefix.prepare(self.repo, "add subtracts", self.ws)
        with open(os.path.join(fix["worktree"], "calc.py"), "w") as f:
            f.write(content)
        return fix

    def test_passing_fix_is_queued_and_approval_opens_a_pr(self):
        fix = self._fix()
        self.assertEqual(fix["branch"], "cos/fix-add-subtracts")
        e = codefix.finalize(fix, TEST_CMD, "Fix add() subtracting", "add() returned a - b.",
                             "kestrel:action:add-bug", self.ws)
        self.assertEqual(e["status"], "pending")
        self.assertEqual(e["test_exit"], "0")
        self.assertIn("+    return a + b", codefix.read_diff(e))
        queue = open(os.path.join(self.ws, "approval-queue.md")).read()
        self.assertIn("### fix-add-subtracts", queue)
        self.assertIn("- action_type: code_fix", queue)
        # the user's main checkout is untouched
        self.assertEqual(open(os.path.join(self.repo, "calc.py")).read(), BUGGY)
        url = codefix.open_pr(e, gh=self.gh)
        self.assertEqual(url, "https://github.example/o/r/pull/7")
        heads = subprocess.run(["git", "ls-remote", "--heads", self.remote],
                               capture_output=True, text=True).stdout
        self.assertIn("refs/heads/cos/fix-add-subtracts", heads)
        with open(self.gh_log) as f:
            calls = [l for l in f.read().splitlines() if l.startswith("pr ")]
        # exactly one gh call, and it is "pr create"
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith("pr create --base main --head cos/fix-add-subtracts"))
        # main on the remote did not move
        main = subprocess.run(["git", "rev-parse", "main"], cwd=self.remote,
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(main, e["base_commit"])

    def test_failing_fix_is_visible_but_not_approvable(self):
        fix = self._fix(content="def add(a, b):\n    return a * b\n")
        e = codefix.finalize(fix, TEST_CMD, "Wrong fix", "", "t", self.ws)
        self.assertEqual(e["status"], "failed")
        self.assertNotEqual(e["test_exit"], "0")
        self.assertIn("tests failed", e["execution_result"])
        with self.assertRaises(codefix.FixError):
            codefix.open_pr(dict(e, status="pending"), gh=self.gh)
        self.assertFalse(os.path.exists(self.gh_log))

    def test_no_changes_is_refused(self):
        fix = codefix.prepare(self.repo, "nothing", self.ws)
        with self.assertRaises(codefix.FixError):
            codefix.finalize(fix, TEST_CMD, "t", "", "t", self.ws)

    def test_merge_commands_are_refused(self):
        for cmd in (["gh", "pr", "merge", "7"], ["git", "merge", "x"], ["gh", "api", "x"]):
            with self.assertRaises(codefix.FixError):
                codefix._run(cmd, self.repo)

    def test_open_pr_rechecks_the_entry(self):
        fix = self._fix()
        e = codefix.finalize(fix, TEST_CMD, "Fix", "", "t", self.ws)
        for bad in ({"status": "approved"}, {"action_type": "message_send"},
                    {"branch": "main"}, {"branch": "cos/fix-x; rm -rf /"}):
            with self.assertRaises(codefix.FixError):
                codefix.open_pr(dict(e, **bad), gh=self.gh)
        self.assertFalse(os.path.exists(self.gh_log))


    def test_only_the_tested_commit_can_be_pushed(self):
        fix = self._fix()
        e = codefix.finalize(fix, TEST_CMD, "Fix", "", "t", self.ws)
        self.assertRegex(e["tested_commit"], r"^[0-9a-f]{40}$")
        # a commit added after the tests passed
        with open(os.path.join(fix["worktree"], "extra.py"), "w") as f:
            f.write("x = 1\n")
        sh(fix["worktree"], "git", "add", "-A")
        sh(fix["worktree"], "git", "commit", "-q", "-m", "later")
        with self.assertRaises(codefix.FixError):
            codefix.open_pr(e, gh=self.gh)
        with self.assertRaises(codefix.FixError):
            codefix.open_pr(dict(e, tested_commit=""), gh=self.gh)
        self.assertFalse(os.path.exists(self.gh_log))

    def test_test_command_runs_without_a_shell_or_secrets(self):
        for bad in ("bash -c 'make test'", "sh run.sh", ""):
            with self.assertRaises(codefix.FixError):
                codefix.test_argv(bad)
        self.assertEqual(codefix.test_argv("python3 -m pytest -q 'a b'"), ["python3", "-m", "pytest", "-q", "a b"])
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-secret"
        try:
            probe = "%s -c \"import os,sys; sys.exit(3 if 'ANTHROPIC_API_KEY' in os.environ else 0)\"" % sys.executable
            code, _ = codefix.run_tests(self.repo, probe)
        finally:
            del os.environ["ANTHROPIC_API_KEY"]
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
