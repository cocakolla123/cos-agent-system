"""The privacy gate that publish.py enforces — the machine form of
cos-learn.md's "shared files stay generic" hard rule."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import privacy  # noqa: E402
import publish  # noqa: E402


class TestScanText(unittest.TestCase):
    def test_example_domains_pass(self):
        self.assertEqual(privacy.scan_text(
            "mail from jordan.kim@novabio.example and a@example.com", []), [])

    def test_real_provider_email_flagged(self):
        # assembled at runtime so this file itself passes the tree scan
        addr = "firstlast2020" + "@" + "gma" + "il.com"
        v = privacy.scan_text("contact %s today" % addr, [])
        self.assertEqual(v, [("email", addr)])

    def test_placeholder_local_at_real_provider_passes(self):
        self.assertEqual(privacy.scan_text("e.g. me@gmail.com or you@gmail.com", []), [])

    def test_corporate_domain_not_flagged_without_token(self):
        # unknown org domains are the token list's job, not the email rule's
        self.assertEqual(privacy.scan_text("ping dana@crestline.example x@acme.com", []), [])

    def test_token_match_is_case_insensitive_substring(self):
        v = privacy.scan_text("...the MegaCorp Industries thread...", ["megacorp"])
        self.assertEqual(len(v), 1)
        self.assertTrue(v[0][0].startswith("token:"))

    def test_large_money_flagged_in_markdown_only(self):
        text = "deposits totalling $45,077.77 that year"
        self.assertEqual(privacy.scan_text(text, [], is_markdown=False), [])
        v = privacy.scan_text(text, [], is_markdown=True)
        self.assertEqual(v, [("money", "$45,077.77")])

    def test_small_money_passes_in_markdown(self):
        self.assertEqual(privacy.scan_text(
            "a $0.51 eval run and a $120 bill", [], is_markdown=True), [])


class TestScanTree(unittest.TestCase):
    def test_walk_flags_and_skips_git(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git"))
            open(os.path.join(d, ".git", "x.md"), "w").write("$9,999,999")
            open(os.path.join(d, "lesson.md"), "w").write(
                "the Initech engagement paid $12,000")
            open(os.path.join(d, "ok.py"), "w").write("x = 1")
            found = privacy.scan_tree(d, ["initech"])
            self.assertEqual(sorted(found), ["lesson.md"])
            kinds = {k for k, _ in found["lesson.md"]}
            self.assertEqual(kinds, {"token:initech", "money"})

    def test_clean_tree_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.md"), "w").write("generic lesson, $3 fee")
            self.assertEqual(privacy.scan_tree(d, ["initech"]), {})


class TestTokens(unittest.TestCase):
    def test_load_tokens_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, privacy.TOKENS_FILENAME), "w").write(
                "# the deployment's own denylist\nInitech\n\n  megacorp  \n")
            self.assertEqual(privacy.load_tokens(d), ["initech", "megacorp"])

    def test_missing_file_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(privacy.load_tokens(d), [])


class TestPublishGating(unittest.TestCase):
    def test_unconfigured_deployment_is_a_noop(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = os.path.join(d, "config.json")
            open(cfg, "w").write("{}")
            ok, detail = publish.publish("msg", config_path=cfg)
            self.assertFalse(ok)
            self.assertIn("not configured", detail)

    def test_message_required(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = os.path.join(d, "config.json")
            open(cfg, "w").write(
                '{"publish": {"repo_url": "https://x.example/r.git"}}')
            ok, detail = publish.publish("  ", config_path=cfg)
            self.assertFalse(ok)
            self.assertIn("message", detail)

    def test_excludes_cover_the_personal_surfaces(self):
        for must in ("dashboard/workspace", "dashboard/config.json",
                     "dashboard/chat-log.md", "dashboard/entry-chat-log.json",
                     "tasks", "dashboard/publish-stage"):
            self.assertIn(must, publish.EXCLUDES)


if __name__ == "__main__":
    unittest.main()
