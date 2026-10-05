"""Hand-computed cases for the source-support checker and its date normalizer."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import support  # noqa: E402


class TestDates(unittest.TestCase):
    A = "2026-09-29T10:00:00Z"  # a Tuesday

    def test_iso(self):
        self.assertIn("2026-10-06",
                      support.dates_in_text("due 2026-10-06 sharp", self.A))

    def test_month_name_short_and_long(self):
        self.assertIn("2026-10-06", support.dates_in_text("by Oct 6", self.A))
        self.assertIn("2026-10-06",
                      support.dates_in_text("by October 6, 2026", self.A))
        self.assertIn("2026-10-06", support.dates_in_text("Oct. 6th", self.A))

    def test_unyeared_month_before_anchor_rolls_forward(self):
        # "Jan 5" said in late September means NEXT January
        self.assertIn("2027-01-05", support.dates_in_text("by Jan 5", self.A))

    def test_numeric_slash(self):
        self.assertIn("2026-10-06", support.dates_in_text("due 10/6", self.A))

    def test_relative_weekday_and_phrases(self):
        self.assertIn("2026-10-02",  # Friday after Tue Sep 29
                      support.dates_in_text("by Friday please", self.A))
        self.assertIn("2026-09-30", support.dates_in_text("tomorrow", self.A))
        self.assertIn("2026-10-02",
                      support.dates_in_text("end of week", self.A))
        self.assertIn("2026-09-30",
                      support.dates_in_text("end of month", self.A))

    def test_no_anchor_still_reads_absolute_dates(self):
        got = support.dates_in_text("due 2026-10-06 or Oct 7", "garbage")
        self.assertIn("2026-10-06", got)
        self.assertNotIn("2026-10-07", got)  # month form needs an anchor year


def act(name, note="", evidence="", due=None, blocked=None):
    attrs = {"note": note, "evidence": evidence}
    if due:
        attrs["due"] = due
    if blocked:
        attrs["blocked_on"] = blocked
    return {"id": "w:action:" + support.re.sub(r"\W+", "-", name.lower()),
            "name": name, "attrs": attrs}


SRC = {
    "em-001": {"id": "em-001", "connector": "email",
               "date": "2026-09-29T10:00:00Z",
               "subject": "Quarterly metrics deck",
               "body": "Please finish the quarterly metrics deck by Oct 6. "
                       "- Rowan Pierce"},
    "em-002": {"id": "em-002", "connector": "email",
               "date": "2026-09-27T10:00:00Z", "subject": "Lunch",
               "body": "tacos on thursday?"},
}


class TestCheckAction(unittest.TestCase):
    def test_fully_supported(self):
        v = support.check_action(
            act("Finish the quarterly metrics deck", evidence="em-001",
                due="2026-10-06", blocked="rowan.pierce"), SRC)
        self.assertTrue(v["ids_ok"])
        self.assertTrue(v["text_ok"])
        self.assertIs(v["due_ok"], True)
        self.assertIs(v["party_ok"], True)
        self.assertTrue(v["supported"])

    def test_nonexistent_cited_id_fails(self):
        v = support.check_action(
            act("Finish the quarterly metrics deck", evidence="em-999"), SRC)
        self.assertFalse(v["ids_ok"])
        self.assertFalse(v["supported"])

    def test_no_citation_at_all_fails(self):
        v = support.check_action(act("Finish the metrics deck"), SRC)
        self.assertFalse(v["ids_ok"])

    def test_unrelated_cited_text_fails_text_support(self):
        v = support.check_action(
            act("Renew the datacenter contract", evidence="em-002"), SRC)
        self.assertTrue(v["ids_ok"])
        self.assertFalse(v["text_ok"])
        self.assertFalse(v["supported"])

    def test_invented_due_date_fails_due_support(self):
        v = support.check_action(
            act("Finish the quarterly metrics deck", evidence="em-001",
                due="2026-10-09"), SRC)
        self.assertTrue(v["text_ok"])
        self.assertIs(v["due_ok"], False)
        self.assertFalse(v["supported"])

    def test_due_component_not_applicable_without_prediction(self):
        v = support.check_action(
            act("Finish the quarterly metrics deck", evidence="em-001"), SRC)
        self.assertIsNone(v["due_ok"])
        self.assertTrue(v["supported"])

    def test_party_fragment_match(self):
        v = support.check_action(
            act("Chase the deck review", note="waiting on Rowan",
                evidence="em-001", blocked="rowan"), SRC)
        self.assertIs(v["party_ok"], True)

    def test_party_absent_from_cited_source_fails(self):
        v = support.check_action(
            act("Finish the quarterly metrics deck", evidence="em-001",
                blocked="casey.wu"), SRC)
        self.assertIs(v["party_ok"], False)
        self.assertFalse(v["supported"])


if __name__ == "__main__":
    unittest.main()
