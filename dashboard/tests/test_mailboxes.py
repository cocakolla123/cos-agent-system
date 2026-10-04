"""Mailbox-flow logic extracted from server.py. The subprocess edges
(claude mcp, the OAuth spawn) are injected, so every step decision is
testable without touching the network or the real ~/.gmail-mcp."""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mailboxes  # noqa: E402


class TestNames(unittest.TestCase):
    def test_slugging(self):
        self.assertEqual(mailboxes.mailbox_server_name("Work Email!"),
                         "gmail-work-email")
        self.assertEqual(mailboxes.mailbox_server_name("  asu  "), "gmail-asu")
        self.assertEqual(mailboxes.mailbox_server_name(""), "")
        self.assertEqual(mailboxes.mailbox_server_name("---"), "")

    def test_token_path_is_per_instance(self):
        a = mailboxes.mailbox_token_path("gmail-a")
        b = mailboxes.mailbox_token_path("gmail-b")
        self.assertNotEqual(a, b)


class TestFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.multiple(
            mailboxes,
            GMAIL_MCP_DIR=self.tmp.name,
            GMAIL_KEYS_PATH=os.path.join(self.tmp.name, "gcp-oauth.keys.json"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_empty_name_errors(self):
        st = mailboxes.add_mailbox("  ")
        self.assertEqual(st["step"], "error")

    def test_missing_keys_stops_before_registration_or_auth(self):
        spawned = []
        with mock.patch.object(mailboxes, "_mcp_registered",
                               return_value=False), \
             mock.patch.object(mailboxes.subprocess, "run") as run:
            st = mailboxes.add_mailbox(
                "work", spawn_auth=lambda cmd, env: spawned.append(cmd))
        self.assertEqual(st["step"], "needs_keys")
        run.assert_not_called()      # no `claude mcp add` attempted
        self.assertEqual(spawned, [])  # no OAuth spawned

    def test_auth_started_when_keys_present(self):
        open(os.path.join(self.tmp.name, "gcp-oauth.keys.json"), "w").write("{}")
        spawned = []
        with mock.patch.object(mailboxes, "_mcp_registered", return_value=True):
            st = mailboxes.add_mailbox(
                "work", spawn_auth=lambda cmd, env: spawned.append((cmd, env)))
        self.assertEqual(st["step"], "auth_started")
        self.assertEqual(len(spawned), 1)
        cmd, env = spawned[0]
        self.assertIn("auth", cmd)
        self.assertIn("credentials-gmail-work.json",
                      env["GMAIL_CREDENTIALS_PATH"])

    def test_connected_runs_hook_once_token_exists(self):
        open(os.path.join(self.tmp.name, "gcp-oauth.keys.json"), "w").write("{}")
        open(os.path.join(self.tmp.name, "credentials-gmail-work.json"),
             "w").write("{}")
        hooks = []
        with mock.patch.object(mailboxes, "_mcp_registered", return_value=True):
            st = mailboxes.add_mailbox("work", on_connected=hooks.append)
        self.assertEqual(st["step"], "connected")
        self.assertEqual(hooks, ["gmail-work"])

    def test_default_token_adopted_for_instance(self):
        # upstream auth wrote the default path; status claims it
        open(os.path.join(self.tmp.name, "credentials.json"), "w").write("{}")
        with mock.patch.object(mailboxes, "_mcp_registered", return_value=False):
            st = mailboxes.mailbox_status("work")
        self.assertTrue(st["authorized"])
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp.name, "credentials-gmail-work.json")))

    def test_read_only_tool_subset_never_mutating(self):
        for t in mailboxes.GMAIL_MCP_READ_TOOLS:
            for bad in ("send", "delete", "modify", "draft", "trash"):
                self.assertNotIn(bad, t)


if __name__ == "__main__":
    unittest.main()
