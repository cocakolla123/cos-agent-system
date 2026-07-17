#!/usr/bin/env python3
"""AI OS dynamic agent factory (V2, milestone M4). Stdlib only.

V1 generated a fixed role set gated by *connector presence*. V2 proposes only the
agents the **discovered workspace actually justifies** — read from the knowledge
graph. A Salesforce node cluster earns a Salesforce agent; job-search entities
earn a Job Search agent; personal repos earn a Project Builder agent; a domain
system with incidents/deployments earns an Investigation agent.

This module is pure: ``propose_agents(graph)`` -> a list of rich agent specs;
``render_agent_md(spec)`` -> the ``.md`` a deployment writes to
``~/.claude/agents/global/``. It never writes agents itself — the command that
calls it does, collision-safe and only after the user approves the proposal list
(see ``commands/setup.md``). Every proposed agent is **read/draft-only**: its
``forbidden_tools`` always include the mutating verbs, and it holds no send tool.

An agent spec (the richer V2 template, issue #17)::

    {name, workspace, model, mission, responsibilities[], allowed_tools[],
     forbidden_tools[], private_memory, shared_memory, approval_policy,
     escalation, inputs, outputs, confidence_requirements, evidence[],
     justification}
"""

from __future__ import annotations

import graph

# Verbs no generated specialist may ever hold — the security floor.
FORBIDDEN = [
    "send", "post", "reply", "comment", "transition", "merge", "create",
    "update", "delete", "deploy", "assign", "close",
]

# Always generated, regardless of evidence (V1 carried these forward).
_ALWAYS = [
    ("cos-knowledge", "sonnet",
     "Maintain the shared knowledge graph and workspace memory; the only writer.",
     ["Read the graph and workspace files",
      "Apply other agents' Memory update: text",
      "Keep source/confidence/freshness current; flag stale facts"]),
    ("cos-risk-quality", "opus",
     "Gate approval-category and never-autonomous output before it reaches the queue.",
     ["Check drafts against APPROVAL_POLICY.md",
      "Block never-autonomous actions; return a safe version",
      "Flag unsupported claims and sensitive info"]),
]

# Connector-category -> V1 fallback role, used only when the graph is empty.
_CONNECTOR_FALLBACK = {
    "messaging": ("cos-comms", "Triage and draft messages (draft-only, no send)."),
    "calendar": ("cos-calendar", "Meeting prep and conflict analysis (draft-only)."),
    "ticketing": ("cos-ticket-triage", "Prioritize the user's tickets (draft-only)."),
    "code": ("cos-code-review", "Review diffs/PRs (draft-only, never merges)."),
}


def propose_agents(g, connectors=None, registry=None):
    """Return a sorted, de-duplicated list of agent specs justified by the graph.

    ``connectors`` is only used as a **fallback** when the graph is empty, so a
    brand-new deployment still gets the V1 role set. When the graph has content,
    proposals are evidence-driven.
    """
    specs = {}
    for name, model, mission, resp in _ALWAYS:
        specs[name] = _spec(name, "shared", model, mission, resp,
                            evidence=["always generated"],
                            justification="Core to every deployment.")

    if not g.nodes:
        for cat, (name, mission) in sorted((connectors or {}).items()) \
                if isinstance(connectors, dict) else \
                [(c, _CONNECTOR_FALLBACK[c]) for c in sorted(connectors or [])
                 if c in _CONNECTOR_FALLBACK]:
            nm, ms = (name if isinstance(connectors, dict) else _CONNECTOR_FALLBACK[cat])
            specs.setdefault(nm, _spec(
                nm, "shared", "sonnet", ms, [ms],
                evidence=["connector present: %s" % cat],
                justification="Graph empty; connector-gated fallback (V1 behavior)."))
        return [specs[k] for k in sorted(specs)]

    # -- evidence-driven proposals -----------------------------------------
    for spec in _domain_system_agents(g):
        specs.setdefault(spec["name"], spec)
    for spec in _job_search_agents(g, registry):
        specs.setdefault(spec["name"], spec)
    for spec in _project_builder_agents(g):
        specs.setdefault(spec["name"], spec)

    return [specs[k] for k in sorted(specs)]


def _domain_system_agents(g):
    """One investigation agent per distinct external system in the graph.

    A 'system' is any node carrying ``attrs['system']`` (e.g. Salesforce,
    Genesys, Zendesk) — typically tickets, incidents, or deployments. Enough
    supporting nodes -> a dedicated specialist for that system.
    """
    by_system = {}
    for n in g.nodes.values():
        sysname = (n.get("attrs", {}) or {}).get("system")
        if sysname:
            by_system.setdefault(sysname, []).append(n)
    out = []
    for sysname in sorted(by_system):
        support = by_system[sysname]
        ws = _dominant_workspace(support)
        slug = graph.slug(sysname)
        out.append(_spec(
            "cos-%s" % slug, ws, "opus",
            "Investigate and analyze %s: state, incidents, root cause, and "
            "recommended (draft-only) fixes." % sysname,
            ["Investigate %s state and history" % sysname,
             "Root-cause incidents and correlate with tickets/deploys",
             "Produce a Background-info block for the dashboard's linked_domain",
             "Recommend fixes marked safe-to-do vs. needs-approval"],
            allowed_extra=["%s read/search tools" % sysname],
            evidence=["%d %s node(s) in workspace '%s'" % (len(support), sysname, ws)],
            justification="Workspace contains a %s cluster worth a dedicated "
                          "investigator." % sysname,
            confidence_req="State findings as Confirmed vs. Assumption; cite "
                           "the %s object/id for every claim." % sysname))
    return out


def _job_search_agents(g, registry):
    hit = any((n.get("attrs", {}) or {}).get("job_application")
              or n.get("type") == "JobApplication" for n in g.nodes.values())
    if not hit and registry is not None:
        hit = any(w.get("kind") == "job-search"
                  for w in registry.workspaces.values())
    if not hit:
        return []
    ws = next((n["workspace"] for n in g.nodes.values()
               if (n.get("attrs", {}) or {}).get("job_application")), "job-search")
    return [_spec(
        "cos-job-search", ws, "sonnet",
        "Track the user's job search: applications, stages, contacts, and "
        "follow-ups (draft-only).",
        ["Track applications and their stages",
         "Draft follow-ups and prep for interviews",
         "Surface deadlines and who is waiting on the user"],
        evidence=["job-search entities present"],
        justification="A job-search workspace/entities were discovered.")]


def _project_builder_agents(g):
    repos = [n for n in g.nodes.values()
             if n.get("type") in ("Repository", "Project")
             and _kindish(n["workspace"]) == "personal"]
    if not repos:
        return []
    ws = _dominant_workspace(repos)
    return [_spec(
        "cos-project-builder", ws, "sonnet",
        "Help plan and build the user's personal software projects (draft-only "
        "— proposes changes, never pushes).",
        ["Track personal repos/projects and their state",
         "Draft plans, issues, and next steps",
         "Suggest changes for the user to apply and approve"],
        allowed_extra=["code search / read tools"],
        evidence=["%d personal repo/project node(s)" % len(repos)],
        justification="Personal repositories/projects were discovered.")]


# ---------------------------------------------------------------------------
# spec construction + rendering
# ---------------------------------------------------------------------------

def _spec(name, workspace, model, mission, responsibilities, allowed_extra=None,
          evidence=None, justification="", confidence_req=None):
    return {
        "name": name,
        "workspace": workspace,
        "model": model,
        "mission": mission,
        "responsibilities": list(responsibilities),
        "allowed_tools": ["Read", "Grep", "Glob"] + list(allowed_extra or []),
        "forbidden_tools": list(FORBIDDEN),
        "private_memory": "agents/%s/memory.md" % name,
        "shared_memory": "the knowledge graph (workspace '%s') + SHARED_CONTEXT" % workspace,
        "approval_policy": "Drafts/recommends only; every external action is queued "
                           "for human approval. Never sends, posts, transitions, "
                           "merges, deploys, or deletes.",
        "escalation": "Flag to the orchestrator when confidence is low or an action "
                      "falls in APPROVAL_POLICY.md's never-autonomous list.",
        "inputs": "Orchestrator request + relevant graph context for workspace '%s'." % workspace,
        "outputs": "Analysis + draft(s) + a Memory update: section for cos-knowledge.",
        "confidence_requirements": confidence_req or
            "Separate Confirmed vs. Assumption; cite a source (id / file:line / "
            "link) for every claim; say so explicitly if a connector is unavailable.",
        "evidence": list(evidence or []),
        "justification": justification,
    }


def render_agent_md(spec):
    """Render an agent spec to its ``.md`` file content (frontmatter + body).

    Tool grants here are *categories* (e.g. "Salesforce read/search tools");
    ``/setup`` substitutes the exact fully-qualified MCP tool names discovered on
    the deployment before writing the file.
    """
    fm = [
        "---",
        "name: %s" % spec["name"],
        "description: %s" % spec["mission"],
        "model: %s" % spec["model"],
        "workspace: %s" % spec["workspace"],
        "tools: %s" % ", ".join(spec["allowed_tools"]),
        "---",
        "",
    ]
    body = [
        "# %s" % spec["name"],
        "",
        "## Mission",
        spec["mission"],
        "",
        "## Responsibilities",
    ]
    body += ["- %s" % r for r in spec["responsibilities"]]
    body += [
        "",
        "## Allowed tools",
        ", ".join(spec["allowed_tools"]),
        "",
        "## Forbidden tools",
        "Never hold or call any mutating tool: " + ", ".join(spec["forbidden_tools"]) + ".",
        "",
        "## Private memory",
        spec["private_memory"],
        "",
        "## Shared memory",
        spec["shared_memory"],
        "",
        "## Approval policy",
        spec["approval_policy"],
        "",
        "## Escalation rules",
        spec["escalation"],
        "",
        "## Inputs",
        spec["inputs"],
        "",
        "## Outputs",
        spec["outputs"],
        "",
        "## Confidence requirements",
        spec["confidence_requirements"],
        "",
        "## Why this agent exists",
        spec["justification"],
    ]
    if spec["evidence"]:
        body += ["", "_Evidence:_ " + "; ".join(spec["evidence"])]
    return "\n".join(fm + body).rstrip() + "\n"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dominant_workspace(nodes):
    counts = {}
    for n in nodes:
        counts[n["workspace"]] = counts.get(n["workspace"], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] \
        if counts else "shared"


def _kindish(workspace_id):
    # Cheap heuristic used only for the project-builder rule when no registry is
    # provided: treat a workspace literally named/kind 'personal' as personal.
    return "personal" if workspace_id == "personal" else workspace_id


if __name__ == "__main__":
    import json
    import sys
    g = graph.Graph.load(sys.argv[1]) if len(sys.argv) > 1 else graph.Graph()
    for s in propose_agents(g):
        print("%-22s %-12s %s" % (s["name"], s["workspace"], s["mission"]))
    if "--render" in sys.argv:
        print(json.dumps([s["name"] for s in propose_agents(g)]))
