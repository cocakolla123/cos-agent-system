"""set_status flips one entry's status in place and keeps every entry intact."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

QUEUE = """# Approval queue

---

### a-1
- status: pending
- action_type: message_send
- short_summary: first

### b-2
- status: pending
- action_type: ticket_update
- short_summary: second
"""


@unittest.skipIf(sys.version_info < (3, 12), "server.py needs Python 3.12+")
class TestSetStatus(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = server.COS_DIR
        server.COS_DIR = self.tmp.name
        with open(os.path.join(self.tmp.name, "approval-queue.md"), "w") as f:
            f.write(QUEUE)

    def tearDown(self):
        self.server.COS_DIR = self.saved
        self.tmp.cleanup()

    def test_flip_keeps_headers_and_other_entries(self):
        self.assertTrue(self.server.set_status("b-2", "rejected", note="not needed"))
        entries = {e["id"]: e for e in self.server.parse_blocks(
            open(os.path.join(self.tmp.name, "approval-queue.md")).read())}
        self.assertEqual(set(entries), {"a-1", "b-2"})
        self.assertEqual(entries["b-2"]["status"], "rejected")
        self.assertEqual(entries["b-2"]["dashboard_note"], "not needed")
        self.assertEqual(entries["a-1"]["status"], "pending")
        self.assertEqual(entries["a-1"]["short_summary"], "first")

    def test_first_entry(self):
        self.assertTrue(self.server.set_status("a-1", "approved"))
        entries = {e["id"]: e for e in self.server.parse_blocks(
            open(os.path.join(self.tmp.name, "approval-queue.md")).read())}
        self.assertEqual(entries["a-1"]["status"], "approved")
        self.assertEqual(entries["b-2"]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
