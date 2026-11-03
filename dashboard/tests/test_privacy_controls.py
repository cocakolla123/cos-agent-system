"""Local data controls: permissions, retention, inventory, gitignore, and
PRIVACY.md matching the code's actual network and model calls."""

import datetime as dt
import glob
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.dirname(HERE)
ROOT = os.path.dirname(DASH)
sys.path.insert(0, DASH)

import privacy  # noqa: E402


def mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


class TestPermissions(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        old = os.umask(0o022)
        try:
            os.makedirs(os.path.join(self.d, "workspace", "graph"))
            os.makedirs(os.path.join(self.d, "inbox"))
            for f in ("config.json", "launchd-poll.log", "chat-log.md", "inbox/2026-10-27.jsonl",
                      "workspace/privacy-tokens.txt", "workspace/graph/nodes.jsonl"):
                open(os.path.join(self.d, f), "w").write("x\n")
        finally:
            os.umask(old)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_audit_finds_world_readable_data_and_fix_closes_it(self):
        bad = {os.path.relpath(p, self.d) for p, _ in privacy.audit_permissions(self.d)}
        self.assertTrue({"config.json", "launchd-poll.log", "workspace/privacy-tokens.txt",
                         "workspace/graph/nodes.jsonl", "inbox/2026-10-27.jsonl", "workspace"} <= bad)
        privacy.fix_permissions(self.d)
        self.assertEqual(privacy.audit_permissions(self.d), [])
        self.assertEqual(mode(os.path.join(self.d, "config.json")), 0o600)
        self.assertEqual(mode(os.path.join(self.d, "workspace")), 0o700)

    def test_inventory_lists_what_is_on_disk(self):
        paths = {r["path"] for r in privacy.inventory(self.d)}
        self.assertIn("config.json", paths)
        self.assertIn(os.path.join("inbox", "2026-10-27.jsonl"), paths)


class TestRetention(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "inbox"))
        for day in ("2026-09-01", "2026-10-01", "2026-10-30"):
            open(os.path.join(self.d, "inbox", day + ".jsonl"), "w").write("{}\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_old_inbox_days_are_deleted(self):
        out = privacy.enforce_retention(self.d, inbox_days=30, today=dt.date(2026, 11, 3))
        self.assertEqual(sorted(out["inbox_deleted"]), ["2026-09-01.jsonl", "2026-10-01.jsonl"])
        self.assertEqual(os.listdir(os.path.join(self.d, "inbox")), ["2026-10-30.jsonl"])

    def test_big_log_keeps_its_newest_lines(self):
        p = os.path.join(self.d, "research.log")
        with open(p, "w") as f:
            for k in range(5000):
                f.write("line %05d\n" % k)
        out = privacy.enforce_retention(self.d, log_max_bytes=1000, today=dt.date(2026, 11, 3))
        self.assertEqual(out["logs_trimmed"], ["research.log"])
        text = open(p).read()
        self.assertLessEqual(len(text), 1000)
        self.assertTrue(text.endswith("line 04999\n"))
        self.assertTrue(text.startswith("line "))            # cut at a line boundary
        self.assertEqual(mode(p), 0o600)


@unittest.skipUnless(shutil.which("git") and os.path.isdir(os.path.join(ROOT, ".git")), "needs the git checkout")
class TestNothingCommittable(unittest.TestCase):
    def test_every_runtime_data_file_is_gitignored(self):
        names = []
        for pattern, _what, _kept in privacy.DATA_FILES:
            names.append("dashboard/" + pattern.replace("*", "example"))
        names += ["dashboard/approval-queue.md", "dashboard/fix.log", "dashboard/pending.jsonl.tmp"]
        r = subprocess.run(["git", "check-ignore", "--no-index", *names], cwd=ROOT,
                           capture_output=True, text=True)
        ignored = set(r.stdout.split())
        self.assertEqual(sorted(set(names) - ignored), [], "runtime data that git would commit")


@unittest.skipUnless(shutil.which("rsync"), "needs rsync")
class TestPublishStaging(unittest.TestCase):
    def test_gitignored_data_is_never_staged(self):
        import publish
        src, dest = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(src, "dashboard", "inbox"))
            shutil.copy(os.path.join(ROOT, ".gitignore"), os.path.join(src, ".gitignore"))
            for f in ("dashboard/server.py", "dashboard/runs.jsonl", "dashboard/quarantine.jsonl",
                      "dashboard/inbox/2026-11-03.jsonl", "dashboard/connections.json",
                      "dashboard/approval-queue.md", "dashboard/research.log"):
                open(os.path.join(src, f), "w").write("x\n")
            r = subprocess.run(publish.rsync_command(src, dest), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            staged = {os.path.relpath(os.path.join(dp, f), dest)
                      for dp, _, fs in os.walk(dest) for f in fs}
            self.assertIn(os.path.join("dashboard", "server.py"), staged)
            self.assertEqual(sorted(x for x in staged if x.startswith("dashboard") and x != os.path.join(
                "dashboard", "server.py")), [])
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(dest, ignore_errors=True)


class TestPrivacyDocMatchesCode(unittest.TestCase):
    NET = re.compile(r"^\s*(?:import|from)\s+(?:urllib\.request|imaplib|http\.client|socket|smtplib)\b|urlopen\(",
                     re.M)
    SUB = re.compile(r"CLAUDE_BIN|[\"']claude[\"']|[\"']git[\"']|[\"']gh[\"']")

    def test_every_module_that_calls_out_is_documented(self):
        doc = open(os.path.join(ROOT, "PRIVACY.md")).read()
        undocumented = []
        for p in sorted(glob.glob(os.path.join(DASH, "*.py"))):
            src = open(p).read()
            if self.NET.search(src) or self.SUB.search(src):
                rel = "dashboard/" + os.path.basename(p)
                if "`%s`" % rel not in doc:
                    undocumented.append(rel)
        self.assertEqual(undocumented, [], "these modules call out but PRIVACY.md does not say so")

    def test_doc_lists_every_data_file(self):
        doc = open(os.path.join(ROOT, "PRIVACY.md")).read()
        for pattern in ("config.json", "connections.json", "secrets.json", "inbox/*.jsonl", "runs.jsonl",
                        "quarantine.jsonl", "workspace/privacy-tokens.txt"):
            self.assertIn("`%s`" % pattern, doc)


if __name__ == "__main__":
    unittest.main()
