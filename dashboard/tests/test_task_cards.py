"""Approval cards live on their tasks in the Command Center, not in a second list."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import graph      # noqa: E402
import sections   # noqa: E402


def make_graph():
    g = graph.Graph()
    g.upsert_node("Action", "w", "pm", name="Write the postmortem",
                  attrs={"due": "2099-01-01", "priority": "high",
                         "next_step": "Outline: summary, timeline, root cause"})
    g.upsert_node("Action", "w", "tomas", name="Reply to Tomas",
                  attrs={"due": "2099-01-02", "priority": "medium"})
    return g


class TestBoard(unittest.TestCase):
    def test_card_goes_into_the_task_and_row_gets_a_chip(self):
        g = make_graph()
        used = set()
        out = sections.render_todo_board(g, attached={"w:action:tomas": [
            {"html": "<div class='card'>APPROVE-ME</div>", "label": "Draft ready"}]},
            used=used)
        self.assertEqual(used, {"w:action:tomas"})
        self.assertIn("Draft ready", out)
        self.assertIn('<template id="tdq-', out)
        self.assertIn("APPROVE-ME", out)
        # a task with no card shows its written next step instead
        self.assertIn('data-nextstep="Outline: summary, timeline, root cause"', out)

    def test_no_attached_cards_leaves_used_empty(self):
        used = set()
        sections.render_todo_board(make_graph(), used=used)
        self.assertEqual(used, set())


QUEUE = """# Approval queue

---

### q-tied
- status: pending
- action_type: message_send
- short_summary: Email to Tomas
- proposed_tool_call: gmail.send to Tomas with text: "hi"
- task: w:action:tomas
- context: answer

### q-old
- status: pending
- action_type: self_do
- short_summary: Outline for the postmortem
- proposed_tool_call: 1. Summary
  * 2. Timeline
- context: Task: Write the postmortem (due 2099-01-01).

### q-loose
- status: pending
- action_type: message_send
- short_summary: Something with no task
- proposed_tool_call: slack.send_message with text: "x"
- context: no task here
"""


@unittest.skipIf(sys.version_info < (3, 12), "server.py needs Python 3.12+")
class TestServer(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = server.COS_DIR
        server.COS_DIR = self.tmp.name
        with open(os.path.join(self.tmp.name, "approval-queue.md"), "w") as f:
            f.write(QUEUE)
        self.g = make_graph()

    def tearDown(self):
        self.server.COS_DIR = self.saved
        self.tmp.cleanup()

    def test_entries_find_their_task(self):
        es = {e["id"]: e for e in self.server.parse_approval_queue()}
        self.assertEqual(self.server.entry_task_id(es["q-tied"], self.g), "w:action:tomas")
        # older entries without a task field match by the task name in context
        self.assertEqual(self.server.entry_task_id(es["q-old"], self.g), "w:action:pm")
        self.assertIsNone(self.server.entry_task_id(es["q-loose"], self.g))

    def test_self_do_card_shows_the_draft_lines(self):
        es = {e["id"]: e for e in self.server.parse_approval_queue()}
        card = self.server.render_entry(es["q-old"])
        self.assertIn("1. Summary\n2. Timeline", card)
        self.assertIn("Mark handled", card)
        self.assertNotIn("Approve", card)

    def test_page_puts_tied_cards_on_tasks_only(self):
        attached = self.server.attach_to_tasks(self.server.parse_approval_queue(), self.g)
        self.assertEqual(set(attached), {"w:action:tomas", "w:action:pm"})
        self.assertEqual(attached["w:action:pm"][0]["label"], "Drafted for you")


if __name__ == "__main__":
    unittest.main()
