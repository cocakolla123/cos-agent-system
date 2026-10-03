"""Every committed fixture scenario must satisfy the schema, and the splits
must stay balanced — a malformed or lopsided dataset skews every run."""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import schema  # noqa: E402

FIXTURES = os.path.join(HERE, "..", "fixtures")


class TestFixtures(unittest.TestCase):
    def test_all_scenarios_valid(self):
        names = list(schema.iter_scenarios(FIXTURES))
        self.assertGreaterEqual(len(names), 30)
        for name, path in names:
            errs = schema.validate_scenario_dir(path)
            self.assertEqual(errs, [], "%s: %s" % (name, errs))

    def test_split_balance_and_required_categories(self):
        splits = {"dev": 0, "test": 0}
        cats = set()
        for name, path in schema.iter_scenarios(FIXTURES):
            s = json.load(open(os.path.join(path, "scenario.json")))
            splits[s["split"]] += 1
            cats.add(s["category"])
        self.assertEqual(splits["dev"], splits["test"])
        for required in ("user_owes", "owed_to_user", "deadline_change",
                         "conflict_stale", "dedupe_cross_surface",
                         "no_invention", "blocked", "isolation", "injection",
                         "approval_action"):
            self.assertIn(required, cats)

    def test_no_real_domains(self):
        # Synthetic-only rule: every address in every fixture is .example.
        import re
        pat = re.compile(r"[\w.+-]+@([\w-]+\.)+(?!example)[a-z]{2,}")
        for name, path in schema.iter_scenarios(FIXTURES):
            srcdir = os.path.join(path, "sources")
            for f in os.listdir(srcdir):
                text = open(os.path.join(srcdir, f)).read()
                m = pat.search(text)
                self.assertIsNone(
                    m, "%s/%s leaks a non-.example address: %s" % (
                        name, f, m.group(0) if m else ""))


class TestRecordValidation(unittest.TestCase):
    def test_good_record_passes(self):
        self.assertEqual(schema.validate_record(
            {"kind": "Action", "workspace": "w", "key": "k",
             "attrs": {"due": "2026-10-06"}, "confidence": 0.8}), [])

    def test_bad_kind_and_missing_key_fail(self):
        errs = schema.validate_record({"kind": "Robot", "workspace": "w"})
        self.assertEqual(len(errs), 2)

    def test_non_dict_rejected(self):
        self.assertTrue(schema.validate_record("nope"))


if __name__ == "__main__":
    unittest.main()
