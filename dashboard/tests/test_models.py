"""Bring-your-own-model: tier routing, key storage, and each provider's wire format."""

import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import models  # noqa: E402


class Fake(BaseHTTPRequestHandler):
    """Answers like OpenAI-style and Gemini endpoints; records requests."""
    seen = []

    def log_message(self, *a):
        pass

    def _reply(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        Fake.seen.append(("GET", self.path, dict(self.headers), None))
        if self.path.endswith("/models") and "goog" in str(dict(self.headers)).lower():
            self._reply({"models": [
                {"name": "models/gem-a", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/embed-x", "supportedGenerationMethods": ["embedContent"]}]})
        else:
            self._reply({"data": [{"id": "m-small"}, {"id": "m-big"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.seen.append(("POST", self.path, dict(self.headers), body))
        if ":generateContent" in self.path:
            self._reply({"candidates": [{"content": {"parts": [{"text": "gem says hi"}]}}]})
        else:
            self._reply({"choices": [{"message": {"content": "oa says hi"}}]})


class Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class FakeAnthropic:
    """Stands in for anthropic.Anthropic: records create() kwargs."""
    def __init__(self):
        self.calls = []
        outer = self

        class Msgs:
            def create(self, **kw):
                outer.calls.append(("messages", kw))
                return type("R", (), {"stop_reason": "end_turn", "content": [Block("claude hi")]})

        class Beta:
            messages = Msgs()

        class Models:
            def list(self):
                return [type("M", (), {"id": "claude-haiku-5-5"}),
                        type("M", (), {"id": "claude-opus-5-5"})]

        self.messages = Msgs()
        self.beta = Beta()
        self.models = Models()


class TestModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % cls.srv.server_port
        for p in ("OPENAI", "GEMINI", "OPENROUTER", "OLLAMA"):
            os.environ["COS_%s_BASE_URL" % p] = base

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in ("OPENAI", "GEMINI", "OPENROUTER", "OLLAMA"):
            os.environ.pop("COS_%s_BASE_URL" % p, None)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        Fake.seen = []
        for env in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
            os.environ.pop(env, None)

    def tearDown(self):
        self.tmp.cleanup()

    def set_tiers(self, **tiers):
        full = {t: {"provider": "claude-code", "model": ""} for t in models.TIERS}
        for t, (p, m) in tiers.items():
            full[t] = {"provider": p, "model": m}
        models.save(self.d, full)

    def test_default_is_claude_code_with_no_model_flag(self):
        self.assertEqual(models.route(self.d, "chat")["provider"], "claude-code")
        self.assertEqual(models.claude_args(self.d, "research"), [])

    def test_subscription_tiers_pass_model_to_the_cli(self):
        models.save(self.d, models.PRESETS["subscription"])
        self.assertEqual(models.claude_args(self.d, "research"), ["--model", "opus"])
        self.assertEqual(models.claude_args(self.d, "chat"), ["--model", "haiku"])
        self.assertEqual(models.claude_args(self.d, "approve"), [])   # never routed

    def test_tool_jobs_stay_on_claude_code(self):
        self.set_tiers(deep=("openai", "m-big"), light=("openai", "m-small"))
        r = models.route(self.d, "research")
        self.assertEqual(r["provider"], "claude-code")
        self.assertIn("account access", r["note"])
        self.assertTrue(models.uses_api(self.d, "chat"))
        self.assertFalse(models.uses_api(self.d, "poll"))

    def test_keys_are_private_and_never_reported(self):
        models.save_key(self.d, "openai", "sk-test-123")
        mode = stat.S_IMODE(os.stat(os.path.join(self.d, "secrets.json")).st_mode)
        self.assertEqual(mode, 0o600)
        st = models.key_status(self.d)
        self.assertEqual(st["openai"], "saved")
        self.assertNotIn("sk-test", json.dumps(st))
        models.save_key(self.d, "openai", "")
        self.assertEqual(models.key_status(self.d)["openai"], "none")
        with self.assertRaises(models.ModelError):
            models.save_key(self.d, "ollama", "x")

    def test_openai_chat_format_and_key_header(self):
        self.set_tiers(light=("openai", "m-small"))
        models.save_key(self.d, "openai", "sk-abc")
        out = models.complete(self.d, "chat", "hello", system="be brief",
                              history=[{"role": "user", "content": "earlier"},
                                       {"role": "assistant", "content": "ok"}])
        self.assertEqual(out, "oa says hi")
        _, path, headers, body = Fake.seen[-1]
        self.assertTrue(path.endswith("/chat/completions"))
        self.assertEqual(headers.get("Authorization"), "Bearer sk-abc")
        self.assertEqual(body["model"], "m-small")
        self.assertEqual([m["role"] for m in body["messages"]],
                         ["system", "user", "assistant", "user"])

    def test_missing_key_is_a_clear_error(self):
        self.set_tiers(light=("openai", "m-small"))
        with self.assertRaises(models.ModelError) as e:
            models.complete(self.d, "chat", "hi")
        self.assertIn("no OpenAI API key", str(e.exception))

    def test_ollama_needs_no_key(self):
        self.set_tiers(light=("ollama", "llama-x"))
        self.assertEqual(models.complete(self.d, "chat", "hi"), "oa says hi")
        self.assertNotIn("Authorization", Fake.seen[-1][2])

    def test_gemini_format(self):
        self.set_tiers(standard=("gemini", "gem-a"))
        models.save_key(self.d, "gemini", "g-key")
        out = models.complete(self.d, "revise", "fix it", system="sys",
                              history=[{"role": "assistant", "content": "draft"}])
        self.assertEqual(out, "gem says hi")
        _, path, headers, body = Fake.seen[-1]
        self.assertIn("/models/gem-a:generateContent", path)
        self.assertEqual(headers.get("X-Goog-Api-Key"), "g-key")
        self.assertEqual([c["role"] for c in body["contents"]], ["model", "user"])
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "sys")
        self.assertEqual(models.list_models(self.d, "gemini"), ["gem-a"])

    def test_anthropic_uses_effort_and_fallbacks(self):
        self.set_tiers(deep=("anthropic", "claude-opus-5-5"), light=("anthropic", "claude-haiku-5-5"))
        fake = FakeAnthropic()
        self.assertEqual(models.complete(self.d, "chat", "hi", _client=fake), "claude hi")
        kw = fake.calls[-1][1]
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertEqual(kw["output_config"], {"effort": "low"})
        self.assertNotIn("fallbacks", kw)
        models.save(self.d, {"light": {"provider": "anthropic", "model": "claude-opus-5-5"},
                             "standard": {"provider": "claude-code", "model": ""},
                             "deep": {"provider": "claude-code", "model": ""}})
        models.complete(self.d, "chat", "hi", _client=fake)
        kw = fake.calls[-1][1]
        self.assertEqual(kw["fallbacks"], "default")
        self.assertEqual(kw["betas"], ["server-side-fallback-2026-07-01"])
        self.assertEqual(models.list_models(self.d, "anthropic", _client=fake),
                         ["claude-haiku-5-5", "claude-opus-5-5"])

    def test_list_and_test(self):
        models.save_key(self.d, "openrouter", "or-key")
        self.assertEqual(models.list_models(self.d, "openrouter"), ["m-big", "m-small"])
        self.assertEqual(models.test(self.d, "openrouter", "m-big"), "oa says hi")
        # test() does not change saved settings
        self.assertEqual(models.load(self.d)["tiers"]["light"]["provider"], "claude-code")

    def test_save_rejects_bad_input(self):
        with self.assertRaises(models.ModelError):
            models.save(self.d, {"light": {"provider": "nope", "model": "x"}})
        with self.assertRaises(models.ModelError):
            models.save(self.d, {"light": {"provider": "openai", "model": "a b"}})


@unittest.skipIf(sys.version_info < (3, 12), "server.py needs Python 3.12+")
class TestServerWiring(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = server.DASHBOARD_DIR, server.DEMO
        server.DASHBOARD_DIR = self.tmp.name
        server.DEMO = False

    def tearDown(self):
        self.server.DASHBOARD_DIR, self.server.DEMO = self.saved
        self.tmp.cleanup()

    def test_cli_calls_get_the_tier_model(self):
        self.assertEqual(self.server.model_args("research"), [])
        models.save(self.tmp.name, models.PRESETS["subscription"])
        self.assertEqual(self.server.model_args("research"), ["--model", "opus"])
        self.assertEqual(self.server.model_args("approve"), [])
        self.assertFalse(self.server.api_route("chat"))

    def test_api_route_and_settings_panel(self):
        models.save(self.tmp.name, {"light": {"provider": "openai", "model": "m-small"},
                                    "standard": {"provider": "claude-code", "model": ""},
                                    "deep": {"provider": "openai", "model": "m-big"}})
        self.assertTrue(self.server.api_route("chat"))
        self.assertFalse(self.server.api_route("research"))   # needs connectors
        html_ = self.server.render_models_section()
        self.assertIn("<h2>Models</h2>", html_)
        self.assertIn('value="m-small"', html_)
        self.assertIn("still run on Claude Code", html_)

    def test_demo_never_routes(self):
        models.save(self.tmp.name, models.PRESETS["subscription"])
        self.server.DEMO = True
        self.assertEqual(self.server.model_args("research"), [])


if __name__ == "__main__":
    unittest.main()
