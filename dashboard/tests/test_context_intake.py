#!/usr/bin/env python3
"""Tests for the startup context intake (M11). Stdlib unittest only."""

import base64
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import context_intake as ci  # noqa: E402


def _t(day):
    return dt.datetime(2026, 9, day, 12, 0, 0, tzinfo=dt.timezone.utc)


class TestSaveText(unittest.TestCase):
    def test_saves_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            p = ci.save_text(d, "I work at Acme on the routing team", now=_t(1))
            self.assertTrue(p.endswith(".md"))
            with open(p) as f:
                self.assertIn("Acme", f.read())
            self.assertEqual(ci.pending_files(d), [p])

    def test_empty_text_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                ci.save_text(d, "   ")


class TestSaveFile(unittest.TestCase):
    def _b64(self, s=b"hello context"):
        return base64.b64encode(s).decode()

    def test_saves_allowed_types(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("notes.md", "notes.txt", "resume.pdf", "doc.docx"):
                p = ci.save_file(d, name, self._b64(), now=_t(1))
                self.assertTrue(os.path.exists(p))
            self.assertEqual(len(ci.pending_files(d)), 4)

    def test_rejects_other_types(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("script.sh", "app.exe", "noext"):
                with self.assertRaises(ValueError):
                    ci.save_file(d, name, self._b64())

    def test_rejects_bad_base64_and_empty(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                ci.save_file(d, "a.md", "!!!not-base64!!!")
            with self.assertRaises(ValueError):
                ci.save_file(d, "a.md", "")

    def test_rejects_oversize(self):
        with tempfile.TemporaryDirectory() as d:
            big = base64.b64encode(b"x" * (ci.MAX_FILE_BYTES + 1)).decode()
            with self.assertRaises(ValueError):
                ci.save_file(d, "big.txt", big)

    def test_path_traversal_neutralized(self):
        with tempfile.TemporaryDirectory() as d:
            p = ci.save_file(d, "../../etc/passwd.md", self._b64(), now=_t(1))
            # saved inside the inbox, name sanitized
            self.assertTrue(p.startswith(ci.inbox_dir(d)))
            self.assertNotIn("..", os.path.basename(p))

    def test_sanitize_filename(self):
        self.assertEqual(ci.sanitize_filename("../../x/y.md"), "y.md")
        self.assertEqual(ci.sanitize_filename("we?ird*na|me.txt"), "we_ird_na_me.txt")
        self.assertEqual(ci.sanitize_filename(""), "context")


class TestProcessing(unittest.TestCase):
    def test_mark_processed_moves(self):
        with tempfile.TemporaryDirectory() as d:
            p = ci.save_text(d, "ctx", now=_t(1))
            dest = ci.mark_processed(d, p)
            self.assertFalse(os.path.exists(p))
            self.assertTrue(os.path.exists(dest))
            self.assertEqual(ci.pending_files(d), [])  # processed/ not pending

    def test_duplicate_names_kept(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = ci.save_text(d, "a", now=_t(1))
            ci.mark_processed(d, p1)
            p2 = ci.save_text(d, "b", now=_t(1))  # same timestamp -> same name
            dest2 = ci.mark_processed(d, p2)
            self.assertTrue(os.path.exists(dest2))


class TestOffer(unittest.TestCase):
    def test_offer_only_fresh_and_undecided(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(ci.should_offer(d, graph_empty=True))
            self.assertFalse(ci.should_offer(d, graph_empty=False))
            ci.record_choice(d, "skipped", now=_t(1))
            self.assertFalse(ci.should_offer(d, graph_empty=True))

    def test_choice_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            ci.record_choice(d, "provided", now=_t(1))
            self.assertEqual(ci.get_choice(d), "provided")
            with self.assertRaises(ValueError):
                ci.record_choice(d, "maybe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
