"""Directive parsing/policy — the chats' only levers, extracted from server.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import directives  # noqa: E402


class _Recorder:
    def __init__(self, ok=True, msg="saved: status→dismissed"):
        self.calls = []
        self.ok, self.msg = ok, msg

    def update(self, entry_id, note=None, priority=None, status=None):
        self.calls.append({"entry_id": entry_id, "note": note,
                           "priority": priority, "status": status})
        return self.ok, self.msg


class TestChatDirectives(unittest.TestCase):
    def test_applies_and_strips_and_confirms(self):
        rec = _Recorder()
        out = directives.apply_chat_directives(
            "ws:action:x",
            'Fine, dropping it.\nCOS-ACTION: {"status": "dismissed"}',
            rec.update)
        self.assertEqual(rec.calls[0]["status"], "dismissed")
        self.assertNotIn("COS-ACTION", out)
        self.assertIn("✅", out)

    def test_id_inside_json_is_ignored_entry_id_pins(self):
        rec = _Recorder()
        directives.apply_chat_directives(
            "ws:action:mine",
            'COS-ACTION: {"id": "ws:action:other", "status": "done"}',
            rec.update)
        self.assertEqual(rec.calls[0]["entry_id"], "ws:action:mine")

    def test_invalid_status_and_priority_are_dropped(self):
        rec = _Recorder()
        out = directives.apply_chat_directives(
            "e", 'COS-ACTION: {"status": "obliterated", "priority": "urgent"}',
            rec.update)
        self.assertEqual(rec.calls, [])  # nothing valid -> no call
        self.assertNotIn("COS-ACTION", out)

    def test_malformed_json_is_stripped_not_applied(self):
        rec = _Recorder()
        out = directives.apply_chat_directives(
            "e", "COS-ACTION: {not json}", rec.update)
        self.assertEqual(rec.calls, [])
        self.assertNotIn("COS-ACTION", out)

    def test_update_exception_never_raises(self):
        def boom(*a, **k):
            raise RuntimeError("db locked")
        out = directives.apply_chat_directives(
            "e", 'COS-ACTION: {"status": "done"}', boom)
        self.assertNotIn("✅", out)


class TestAuthDirectives(unittest.TestCase):
    def test_enqueues_with_default_settings_url(self):
        calls = []
        out = directives.apply_auth_directives(
            'Connecting it.\nCOS-AUTH: {"id": "gmail-work", "reason": "2nd"}',
            lambda i, r, u: calls.append((i, r, u)) or {"id": i})
        self.assertEqual(calls[0][0], "gmail-work")
        self.assertEqual(calls[0][2], directives.CONNECTOR_SETTINGS_URL)
        self.assertIn("🔐", out)
        self.assertNotIn("COS-AUTH", out)

    def test_declined_account_enqueue_none_no_confirmation(self):
        out = directives.apply_auth_directives(
            'COS-AUTH: {"id": "gmail-x"}', lambda i, r, u: None)
        self.assertNotIn("🔐", out)

    def test_no_enqueue_fn_passthrough(self):
        text = 'COS-AUTH: {"id": "gmail-x"}'
        self.assertEqual(directives.apply_auth_directives(text, None), text)


if __name__ == "__main__":
    unittest.main()
