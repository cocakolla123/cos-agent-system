"""Per-run tracing: every check leaves one line saying what it did and what
happened to each item, with no message text or secrets in it, and a user
can ask why a message was missed without opening raw files."""

import datetime as dt
import json
import os
import stat
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import poll_direct  # noqa: E402
import runtrace     # noqa: E402
import usage        # noqa: E402
from test_ingest_safety import REC, Base, slack  # noqa: E402

NOON = dt.datetime(2026, 10, 27, 20, 0, tzinfo=dt.timezone.utc)


def model(recs):
    return lambda d, p, job="poll_direct": (json.dumps(recs), 0.02)


class TestRunTrace(Base):
    def last(self):
        return runtrace.runs(self.dir)[-1]

    def test_a_read_records_every_item_fate(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?"),
                        slack(2, "lunch anyone", ch="#random", user="bo")]]
        out = poll_direct.check(self.dir, self.gdir, now=NOON, draft=False, _model=model([REC]))
        r = self.last()
        self.assertEqual(r["run_id"], out["run_id"])
        self.assertEqual(r["outcome"], "read")
        self.assertEqual(r["items"]["sl-1"]["fate"], "task")
        self.assertEqual(r["items"]["sl-1"]["records"], ["Action:q4-numbers"])
        self.assertEqual(r["items"]["sl-2"]["fate"], "dropped")
        self.assertEqual(r["sources"]["work"]["ok"], True)
        self.assertEqual([s["name"] for s in r["steps"]], ["fetch_and_sift", "model_read", "ingest"])
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.dir, runtrace.RUNS_FILE)).st_mode), 0o600)

    def test_the_trace_holds_no_message_text_or_secret(self):
        self.served = [[slack(1, "Dana the vault phrase is PLUM-ORCHID-77, token xoxp-1234567890-abcdef")]]
        with self.assertRaises(poll_direct.ExtractionError):
            poll_direct.check(self.dir, self.gdir, now=NOON, draft=False,
                              _model=lambda d, p, job="poll_direct": ("not json xoxp-999999-leak", 0))
        raw = open(os.path.join(self.dir, runtrace.RUNS_FILE)).read()
        for leak in ("PLUM-ORCHID-77", "xoxp-1234567890", "xoxp-999999", "vault phrase"):
            self.assertNotIn(leak, raw)
        r = self.last()
        self.assertEqual(r["outcome"], "failed")
        self.assertEqual(r["items"]["sl-1"]["fate"], "read_failed")

    def test_a_delayed_item_says_it_is_waiting_for_the_batch(self):
        early = dt.datetime(2026, 10, 28, 7, 42, tzinfo=dt.timezone.utc)   # before the first batch
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        poll_direct.check(self.dir, self.gdir, now=early, scan=True, draft=False, _model=model([REC]))
        r = self.last()
        self.assertEqual(r["outcome"], "queued")
        self.assertEqual(r["items"]["sl-1"]["fate"], "waiting")

    def test_a_reread_is_traced_as_a_duplicate(self):
        msg = slack(1, "Dana can you send the Q4 numbers by Friday?")
        self.served = [[msg]]
        poll_direct.check(self.dir, self.gdir, now=NOON, draft=False, _model=model([REC]))
        self.served = [[msg]]                                  # the source hands it back again
        poll_direct.check(self.dir, self.gdir, now=NOON, draft=False, _model=model([]))
        self.assertEqual(self.last()["items"]["sl-1"]["fate"], "duplicate")

    def test_a_quarantined_record_marks_its_item(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        bad = {"kind": "Action", "name": "no key", "attrs": {"evidence": ["sl-1"]}}
        poll_direct.check(self.dir, self.gdir, now=NOON, draft=False, _model=model([bad]))
        self.assertEqual(self.last()["items"]["sl-1"]["fate"], "quarantined")

    def test_explain_answers_by_words_from_the_message(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?"),
                        slack(2, "lunch anyone", ch="#random", user="bo")]]
        poll_direct.check(self.dir, self.gdir, now=NOON, draft=False, _model=model([REC]))
        lunch = runtrace.explain(self.dir, "lunch")
        self.assertEqual(lunch[0]["id"], "sl-2")
        self.assertIn("skipped by the free sift", lunch[0]["verdict"])
        q4 = runtrace.explain(self.dir, "q4 numbers")
        self.assertEqual(q4[0]["verdict"], "read; became a task")
        nothing = runtrace.explain(self.dir, "no such message anywhere")
        self.assertIn("never saw it", nothing[0]["verdict"])

    def test_model_calls_inside_a_run_carry_its_id(self):
        with runtrace.start(self.dir, "unit") as run:
            rec = usage.record(self.dir, "poll_direct", {"total_cost_usd": 0.05,
                                                         "usage": {"input_tokens": 10, "output_tokens": 5}})
        self.assertEqual(rec["run_id"], run.run_id)
        self.assertEqual(self.last()["model"]["calls"], 1)
        outside = usage.record(self.dir, "poll_direct", {"total_cost_usd": 0.01})
        self.assertNotIn("run_id", outside)


class TestRedact(unittest.TestCase):
    def test_masks_credentials_and_addresses(self):
        s = runtrace.redact("auth failed for dana@work.example with Bearer abcdefghijklmnop "
                            "and xoxp-123-456 at https://u:pw@host/x?token=zzz github_pat_ABC123")
        for leak in ("dana@work.example", "abcdefghijklmnop", "xoxp-123-456", "u:pw@", "zzz", "ABC123"):
            self.assertNotIn(leak, s)


if __name__ == "__main__":
    unittest.main()
