"""The shipped tool grants must stay narrow. An outside review (2026-10-05)
found the research default granting unscoped Bash and WebSearch, which
contradicted the README's read-only claim: an unscoped Bash can curl, and
WebSearch is the network. These tests pin the narrowed defaults so the gap
cannot quietly reopen. They read source text and the example config, never
the live deployment's config.json."""

import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(HERE, "..")

NETWORK_TOOLS = ("WebSearch", "WebFetch")


def _tokens(grant):
    return [t.strip() for t in grant.split(",") if t.strip()]


def _grant_ok(name, grant, errs):
    toks = _tokens(grant)
    if "Bash" in toks:
        errs.append("%s grants unscoped Bash" % name)
    for t in toks:
        if t.startswith("Bash(") and not re.match(r"Bash\((python3|git):\*\)$", t):
            errs.append("%s grants Bash beyond python3/git: %s" % (name, t))
        if t in NETWORK_TOOLS:
            errs.append("%s grants network tool %s" % (name, t))
        if t.startswith("mcp__") and any(
                verb in t.lower() for verb in
                ("send", "delete", "create", "update", "trash", "forward",
                 "reply", "modify", "draft")):
            errs.append("%s grants mutating MCP tool %s" % (name, t))


class TestShippedDefaults(unittest.TestCase):
    def test_server_source_defaults_are_scoped(self):
        src = open(os.path.join(DASH, "server.py")).read()
        m = re.search(r'"research_tools",\s*\n?\s*"([^"]+)"\)', src)
        self.assertIsNotNone(m, "research default not found in server.py")
        errs = []
        _grant_ok("server.py research default", m.group(1), errs)
        d = re.search(r'"learn_tools": "([^"]+)"', src)
        _grant_ok("server.py learn default", d.group(1), errs)
        self.assertEqual(errs, [])

    def test_example_config_grants_are_scoped(self):
        cfg = json.load(open(os.path.join(DASH, "config.example.json")))
        errs = []
        for field in ("research_tools", "poll_tools", "chat_tools",
                      "learn_tools", "revise_tools", "base_tools"):
            if cfg.get(field):
                _grant_ok("config.example.json " + field, cfg[field], errs)
        self.assertEqual(errs, [])

    def test_research_default_still_carries_what_research_needs(self):
        src = open(os.path.join(DASH, "server.py")).read()
        m = re.search(r'"research_tools",\s*\n?\s*"([^"]+)"\)', src)
        toks = _tokens(m.group(1))
        for needed in ("Read", "Edit", "Write", "Glob", "Grep"):
            self.assertIn(needed, toks)
        self.assertTrue(any(t.startswith("Bash(") for t in toks),
                        "research needs a scoped Bash grant to run graph.py")

    def test_validator_flags_unscoped_bash_and_network(self):
        import sys
        sys.path.insert(0, DASH)
        import validate_config
        findings = validate_config.validate(
            {"research_tools": "Read,Edit,Write,Bash,Glob,Grep,Agent,WebSearch"})
        msgs = " | ".join(f["message"] for f in findings)
        self.assertIn("unscoped Bash", msgs)
        self.assertIn("WebSearch", msgs)

    def test_validator_errors_on_no_bash_at_all(self):
        import sys
        sys.path.insert(0, DASH)
        import validate_config
        findings = validate_config.validate(
            {"research_tools": "Read,Edit,Write,Glob,Grep,Agent"})
        self.assertTrue(any(f["level"] == "error" and
                            f["field"] == "research_tools"
                            for f in findings))


if __name__ == "__main__":
    unittest.main()
