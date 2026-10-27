#!/usr/bin/env python3
"""The fixed operations the research and account jobs may run, and nothing else.

    python3 <dashboard>/cos_tool.py <command> [args]

The research crawl and the account probe read untrusted content (mail, chat,
tickets, repos), so they are not given a Python interpreter. Their whole Bash
grant is this one script: each command below does one known thing to the
graph or the account files, takes JSON from a file the job wrote in its
workspace, and prints JSON. No command runs code from its input, opens the
network, or touches a path outside the graph, workspace or account files.

Graph
  ingest GRAPH_DIR RECORDS.json       validate, upsert, correlate, render (one locked step)
  render GRAPH_DIR                    regenerate the markdown views
  coverage GRAPH_DIR                  items behind each dashboard section
  window-audit GRAPH_DIR              how far back each source's evidence reaches
  infer-workspaces RECORDS.json       cluster records into candidate workspaces
  ingest-workspaces GRAPH_DIR PROPOSALS.json
                                      persist confirmed workspaces
  workspace-connect WS_DIR WORKSPACE CONNECTOR
                                      add a connector to a workspace in the registry
User context
  context-pending WS_DIR              files waiting in context-inbox/
  context-done WS_DIR FILE            move one into processed/ (kept, never deleted)
Accounts (dashboard/config.json, account-status.json, auth-requests.json)
  accounts-list                       configured connector accounts
  accounts-detect TOOLS.json          instances in a list of MCP tool names
  accounts-add ENTRY.json             add one connector_accounts entry
  accounts-bind ID WORKSPACE          set an account's workspace
  accounts-status ID ok|failed [--identity X] [--error X]
  accounts-declined ID                true if the user refused it (never ask again)
  accounts-auth ID [--reason X] [--url X]
                                      queue an authorization popup
  accounts-summary                    one-line summary
  agents-propose GRAPH_DIR            agent specs the graph justifies
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import graph  # noqa: E402

MAX_INPUT = 20_000_000


class ToolError(Exception):
    pass


def _json_file(path):
    if not os.path.isfile(path):
        raise ToolError("no such file: %s" % path)
    if os.path.getsize(path) > MAX_INPUT:
        raise ToolError("input too large: %s" % path)
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except ValueError as e:
            raise ToolError("not JSON: %s (%s)" % (path, e))


def _graph_dir(p):
    p = os.path.abspath(p)
    if os.path.basename(p) != "graph":
        raise ToolError("a graph directory is named graph/: %s" % p)
    return p


def _config_path():
    return os.environ.get("COS_CONFIG") or os.path.join(HERE, "config.json")


def _config():
    try:
        with open(_config_path(), encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def _save_config(cfg):
    path = _config_path()
    with graph.file_lock(path):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)


def _flag(args, name, default=""):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def cmd_ingest(gdir, rec_path):
    import poll_direct
    import research
    gdir = _graph_dir(gdir)
    recs = _json_file(rec_path)
    if not isinstance(recs, list):
        raise ToolError("records must be a JSON array")
    good = [r for r in recs if not poll_direct.record_problems(r)]
    with graph.transaction(gdir):
        g = graph.Graph.load(gdir)
        counts = research.ingest(g, good)
        try:
            import correlate
            correlate.correlate(g)
        except Exception:  # noqa: BLE001  (correlation is optional)
            pass
        g.save(gdir)
        g.render_views(gdir)
    return {"ingested": len(good), "invalid": len(recs) - len(good), "counts": counts}


def cmd_render(gdir):
    gdir = _graph_dir(gdir)
    with graph.transaction(gdir):
        g = graph.Graph.load(gdir)
        paths = g.render_views(gdir)
    return {"rendered": len(paths)}


def cmd_coverage(gdir):
    import sections
    return sections.coverage_report(graph.Graph.load(_graph_dir(gdir)))


def cmd_window_audit(gdir):
    import research
    return research.window_audit(graph.Graph.load(_graph_dir(gdir)))


def cmd_infer_workspaces(rec_path):
    import research
    return research.infer_workspaces(_json_file(rec_path))


def cmd_ingest_workspaces(gdir, prop_path):
    import research
    gdir = _graph_dir(gdir)
    recs = research.workspace_records(_json_file(prop_path))
    with graph.transaction(gdir):
        g = graph.Graph.load(gdir)
        counts = research.ingest(g, recs)
        g.save(gdir)
    return {"workspaces": len(recs), "counts": counts}


def cmd_workspace_connect(ws_dir, wsid, connector):
    import workspaces
    ws_dir = os.path.abspath(ws_dir)
    reg = workspaces.Registry.load(ws_dir)
    w = reg.get(wsid) or {}
    reg.upsert(wsid, connectors=list(w.get("connectors") or []) + [connector])
    reg.save(ws_dir)
    return reg.get(wsid)


def cmd_context_pending(ws_dir):
    import context_intake
    return context_intake.pending_files(os.path.abspath(ws_dir))


def cmd_context_done(ws_dir, path):
    import context_intake
    ws_dir = os.path.abspath(ws_dir)
    real = os.path.realpath(path)
    inbox = os.path.realpath(context_intake.inbox_dir(ws_dir))
    if os.path.dirname(real) != inbox:
        raise ToolError("not a file in %s" % inbox)
    return {"moved_to": context_intake.mark_processed(ws_dir, real)}


def cmd_accounts_list():
    import accounts
    return accounts.load_accounts(_config())


def cmd_accounts_detect(tools_path):
    import accounts
    names = _json_file(tools_path)
    if not isinstance(names, list) or not all(isinstance(x, str) for x in names):
        raise ToolError("expected a JSON array of tool names")
    inst = accounts.detect_instances(names)
    return {"instances": inst, "multi_account_kinds": accounts.multi_account_kinds(inst)}


ENTRY_FIELDS = ("id", "kind", "label", "account", "workspace", "tool_prefix", "probe_tool")


def cmd_accounts_add(entry_path):
    e = _json_file(entry_path)
    if not isinstance(e, dict) or not e.get("id"):
        raise ToolError("an account entry needs an id")
    e = {k: str(e[k]) for k in ENTRY_FIELDS if e.get(k) is not None}
    cfg = _config()
    rows = [a for a in cfg.get("connector_accounts") or [] if a.get("id") != e["id"]]
    cfg["connector_accounts"] = rows + [e]
    _save_config(cfg)
    return e


def cmd_accounts_bind(aid, wsid):
    cfg = _config()
    for a in cfg.get("connector_accounts") or []:
        if a.get("id") == aid:
            a["workspace"] = graph.slug(wsid)
            _save_config(cfg)
            return a
    raise ToolError("no account %s" % aid)


def cmd_accounts_status(aid, state, *rest):
    import accounts
    if state not in ("ok", "failed"):
        raise ToolError("state is ok or failed")
    return accounts.write_status(HERE, aid, state == "ok", identity=_flag(rest, "--identity"),
                                 error=_flag(rest, "--error"))


def cmd_accounts_declined(aid):
    import accounts
    return {"declined": accounts.is_declined(HERE, aid)}


def cmd_accounts_auth(aid, *rest):
    import accounts
    url = _flag(rest, "--url")
    if url and not url.startswith("https://"):
        raise ToolError("an auth link must be https")
    return accounts.enqueue_auth_request(HERE, aid, reason=_flag(rest, "--reason"), auth_url=url)


def cmd_accounts_summary():
    import accounts
    cfg = _config()
    return accounts.summarize_accounts(cfg, accounts.read_status(HERE))


def cmd_agents_propose(gdir):
    import accounts
    import factory
    g = graph.Graph.load(_graph_dir(gdir))
    return factory.propose_agents(g, accounts=accounts.load_accounts(_config()))


COMMANDS = {
    "ingest": (cmd_ingest, 2), "render": (cmd_render, 1), "coverage": (cmd_coverage, 1),
    "window-audit": (cmd_window_audit, 1), "infer-workspaces": (cmd_infer_workspaces, 1),
    "ingest-workspaces": (cmd_ingest_workspaces, 2), "workspace-connect": (cmd_workspace_connect, 3),
    "context-pending": (cmd_context_pending, 1), "context-done": (cmd_context_done, 2),
    "accounts-list": (cmd_accounts_list, 0), "accounts-detect": (cmd_accounts_detect, 1),
    "accounts-add": (cmd_accounts_add, 1), "accounts-bind": (cmd_accounts_bind, 2),
    "accounts-status": (cmd_accounts_status, 2), "accounts-declined": (cmd_accounts_declined, 1),
    "accounts-auth": (cmd_accounts_auth, 1), "accounts-summary": (cmd_accounts_summary, 0),
    "agents-propose": (cmd_agents_propose, 1),
}


def main(argv):
    os.umask(0o077)
    if not argv or argv[0] not in COMMANDS:
        sys.stderr.write(__doc__)
        return 2
    fn, n = COMMANDS[argv[0]]
    args = argv[1:]
    if len(args) < n:
        sys.stderr.write("%s needs %d argument(s)\n" % (argv[0], n))
        return 2
    try:
        out = fn(*args)
    except TypeError:
        sys.stderr.write("wrong arguments for %s\n" % argv[0])
        return 2
    except ToolError as e:
        sys.stderr.write("error: %s\n" % e)
        return 1
    print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
