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
    def test_server_learn_default_is_scoped(self):
        src = open(os.path.join(DASH, "server.py")).read()
        d = re.search(r'"learn_tools": "([^"]+)"', src)
        errs = []
        _grant_ok("server.py learn default", d.group(1), errs)
        self.assertEqual(errs, [])

    def test_research_grant_runs_only_cos_tool_and_writes_only_the_workspace(self):
        import sys
        sys.path.insert(0, DASH)
        import grants
        g = _tokens(grants.research_grant({}, "/home/u/cos/ws", "/home/u/cos/dashboard/cos_tool.py"))
        self.assertEqual(g, ["Read", "Glob", "Grep", "Agent", "ToolSearch", "Edit(//home/u/cos/ws/**)",
                             "Bash(python3 /home/u/cos/dashboard/cos_tool.py:*)"])
        self.assertFalse(any(t in ("Bash", "Write", "Edit", "Bash(python3:*)") for t in g))

    def test_old_broad_config_is_narrowed_and_mcp_reads_kept(self):
        import sys
        sys.path.insert(0, DASH)
        import grants
        old = {"research_tools": "Read,Edit,Write,Bash(python3:*),Glob,Grep,Agent,ToolSearch,"
                                 "mcp__gmail__search_threads,Bash,Write(/x/**)"}
        g = _tokens(grants.research_grant(old, "/w", "/d/cos_tool.py"))
        self.assertIn("mcp__gmail__search_threads", g)
        for t in ("Bash", "Write", "Edit", "Bash(python3:*)", "Write(/x/**)"):
            self.assertNotIn(t, g)
        # on purpose, the old grant can be kept
        kept = grants.research_grant(dict(old, research_broad_grant=True), "/w", "/d/cos_tool.py")
        self.assertIn("Bash(python3:*)", _tokens(kept))

    def test_example_config_grants_are_scoped(self):
        cfg = json.load(open(os.path.join(DASH, "config.example.json")))
        errs = []
        for field in ("research_tools", "poll_tools", "chat_tools",
                      "learn_tools", "revise_tools", "base_tools"):
            if cfg.get(field):
                _grant_ok("config.example.json " + field, cfg[field], errs)
        self.assertEqual(errs, [])

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
        # only when the configured list is used as it is (research_broad_grant)
        findings = validate_config.validate(
            {"research_tools": "Read,Edit,Write,Glob,Grep,Agent", "research_broad_grant": True})
        self.assertTrue(any(f["level"] == "error" and
                            f["field"] == "research_tools"
                            for f in findings))
        # otherwise the server builds the grant, and an empty list is fine
        self.assertEqual(validate_config.validate({"research_tools": ""}), [])


if __name__ == "__main__":
    unittest.main()
