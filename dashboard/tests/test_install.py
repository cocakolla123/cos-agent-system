"""install.sh end to end, in a throwaway HOME and throwaway repos: install,
an edited command survives an update, update fast-forwards, a broken
release rolls itself back, --rollback returns to the earlier version, and
--uninstall removes only what it installed and never the user's data."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def py312():
    if sys.version_info >= (3, 12):
        return sys.executable
    for c in ("python3.14", "python3.13", "python3.12"):
        p = shutil.which(c)
        if p:
            return p
    return None


@unittest.skipUnless(shutil.which("git") and shutil.which("jq") and shutil.which("bash") and py312(),
                     "needs git, jq, bash and a Python 3.12+")
class TestInstaller(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.home = os.path.join(self.t, "home")
        os.makedirs(self.home)
        bindir = os.path.join(self.t, "bin")
        os.makedirs(bindir)
        claude = os.path.join(bindir, "claude")
        with open(claude, "w") as f:
            f.write("#!/bin/sh\necho 'claude 0.0 (fake)'\n")
        os.chmod(claude, 0o755)
        self.env = dict(os.environ, HOME=self.home, PATH=bindir + os.pathsep + os.environ["PATH"],
                        COS_PYTHON=py312(), CLAUDE_BIN=claude,
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@x.example",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@x.example")
        # a release repo holding the real install.sh, an origin, and the user's clone
        self.src = os.path.join(self.t, "src")
        os.makedirs(os.path.join(self.src, "commands"))
        os.makedirs(os.path.join(self.src, "dashboard"))
        shutil.copy(os.path.join(ROOT, "install.sh"), self.src)
        self.write("VERSION", "1.0.0\n")
        self.write("commands/cos.md", "cos v1\n")
        self.write("commands/cos-poll.md", "poll v1\n")
        self.write("dashboard/ok.py", "x = 1\n")
        self.git(self.src, "init", "-q", "-b", "main")
        self.commit("v1")
        self.git(self.t, "clone", "-q", "--bare", self.src, "origin.git")
        self.work = os.path.join(self.t, "work")
        self.git(self.t, "clone", "-q", os.path.join(self.t, "origin.git"), self.work)
        self.cmds = os.path.join(self.home, ".claude", "commands", "global")

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def write(self, rel, text):
        with open(os.path.join(self.src, rel), "w") as f:
            f.write(text)

    def git(self, cwd, *args):
        subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True, capture_output=True)

    def commit(self, msg):
        self.git(self.src, "add", "-A")
        self.git(self.src, "commit", "-q", "-m", msg)

    def release(self, msg):
        self.commit(msg)
        self.git(self.src, "push", "-q", os.path.join(self.t, "origin.git"), "main")

    def run_install(self, *flags):
        return subprocess.run(["bash", os.path.join(self.work, "install.sh"), *flags], cwd=self.work,
                              env=self.env, capture_output=True, text=True)

    def read(self, name):
        with open(os.path.join(self.cmds, name)) as f:
            return f.read()

    def head(self):
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.work, capture_output=True,
                              text=True).stdout.strip()

    def test_full_lifecycle(self):
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("ok       jq", r.stdout)
        self.assertEqual(self.read("cos-poll.md"), "poll v1\n")
        v1 = self.head()

        with open(os.path.join(self.cmds, "cos.md"), "w") as f:     # the user customizes a command
            f.write("my own cos\n")

        self.write("commands/cos.md", "cos v2\n")
        self.write("commands/cos-poll.md", "poll v2\n")
        self.write("VERSION", "1.1.0\n")
        self.release("v2")
        r = self.run_install("--update")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.read("cos-poll.md"), "poll v2\n")          # ours, unedited: updated
        self.assertEqual(self.read("cos.md"), "my own cos\n")            # theirs: never overwritten
        self.assertEqual(self.read("cos.md.new"), "cos v2\n")
        self.assertIn("kept your edited cos.md", r.stdout)

        r = self.run_install("--rollback")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.head(), v1)
        self.assertEqual(self.read("cos-poll.md"), "poll v1\n")
        self.assertEqual(self.read("cos.md"), "my own cos\n")

        data = os.path.join(self.work, "dashboard", "workspace")
        os.makedirs(data)
        with open(os.path.join(data, "approval-queue.md"), "w") as f:
            f.write("# my queue\n")
        r = self.run_install("--uninstall")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.cmds, "cos-poll.md")))
        self.assertEqual(self.read("cos.md"), "my own cos\n")            # edited: left in place
        self.assertTrue(os.path.exists(os.path.join(data, "approval-queue.md")))   # data untouched

    def test_a_release_that_does_not_compile_rolls_itself_back(self):
        self.assertEqual(self.run_install().returncode, 0)
        v1 = self.head()
        self.write("dashboard/ok.py", "def broken(:\n")
        self.release("broken")
        r = self.run_install("--update")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rolled back", r.stderr)
        self.assertIn("ok.py", r.stderr)                 # failed on the broken file, not the checker
        self.assertEqual(self.head(), v1)
        self.assertEqual(self.read("cos-poll.md"), "poll v1\n")

    def test_update_refuses_to_clobber_local_edits(self):
        self.assertEqual(self.run_install().returncode, 0)
        with open(os.path.join(self.work, "dashboard", "ok.py"), "w") as f:
            f.write("x = 2  # my tweak\n")
        self.write("commands/cos.md", "cos v2\n")
        self.release("v2")
        r = self.run_install("--update")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("local edits", r.stderr)
        with open(os.path.join(self.work, "dashboard", "ok.py")) as f:
            self.assertEqual(f.read(), "x = 2  # my tweak\n")

    def test_after_the_first_install_a_users_edit_is_kept(self):
        self.assertEqual(self.run_install().returncode, 0)        # the manifest now exists
        with open(os.path.join(self.cmds, "cos.md"), "w") as f:
            f.write("someone else's cos\n")
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.read("cos.md"), "someone else's cos\n")
        self.assertEqual(self.read("cos.md.new"), "cos v1\n")


    def test_a_pre_manifest_install_gets_its_stale_commands_replaced(self):
        os.makedirs(self.cmds)
        with open(os.path.join(self.cmds, "cos.md"), "w") as f:
            f.write("an old copy from before manifests\n")
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.read("cos.md"), "cos v1\n")                 # updated, not frozen
        self.assertEqual(self.read("cos.md.bak"), "an old copy from before manifests\n")
        with open(os.path.join(self.cmds, ".cos-manifest")) as f:
            self.assertIn("cos.md", f.read())

    def test_a_command_removed_upstream_is_retired(self):
        self.assertEqual(self.run_install().returncode, 0)
        os.remove(os.path.join(self.src, "commands", "cos-poll.md"))
        self.release("drop cos-poll")
        r = self.run_install("--update")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.cmds, "cos-poll.md")))

    def test_uninstall_leaves_no_new_files_behind(self):
        self.assertEqual(self.run_install().returncode, 0)
        with open(os.path.join(self.cmds, "cos.md"), "w") as f:
            f.write("mine\n")
        self.write("commands/cos.md", "cos v2\n")
        self.release("v2")
        self.assertEqual(self.run_install("--update").returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.cmds, "cos.md.new")))
        self.assertEqual(self.run_install("--uninstall").returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.cmds, "cos.md.new")))
        self.assertEqual(self.read("cos.md"), "mine\n")

if __name__ == "__main__":
    unittest.main()
