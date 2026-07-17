#!/usr/bin/env python3
"""AI OS research engine — ingest layer (V2, milestone M2). Stdlib only.

The research *command* (`commands/cos-research.md`) drives the read-only MCP
connectors and produces **normalized records**; this module turns those records
into knowledge-graph nodes + edges (via `graph.py`) and infers which workspace
each thing belongs to. Keeping the record→graph mapping here (not in the command
prose) makes it unit-testable with synthetic connector output, so the discovery
modules can be verified without a live connector.

A **record** is a plain dict::

    {
      "kind": "Ticket",              # a graph node type
      "workspace": "employer",       # provisional workspace id (may be refined)
      "key": "CCS-123",              # natural key, unique within (workspace, kind)
      "name": "Queue routing bug",   # display name (optional -> key)
      "attrs": {"status": "open", "org": "acme"},
      "source": "jira",              # connector that produced it
      "confidence": 0.9,             # 0..1
      "edges": [                     # optional outgoing edges
        {"to_kind": "Person", "to_key": "mel", "type": "owned_by",
         "to_workspace": "employer", "confidence": 0.8},
      ],
    }

Records are the *only* contract between a discovery module and the graph, so a
new connector just has to emit this shape.
"""

from __future__ import annotations

import graph


# Signals a discovery module can attach to hint the workspace kind. Advisory.
WORKSPACE_KIND_HINTS = {
    "employer", "freelance", "personal", "job-search", "school",
    "startup", "home", "property", "travel",
}


def record(kind, workspace, key, name=None, attrs=None, source=None,
           confidence=1.0, edges=None):
    """Build a normalized record (validates the minimum required fields)."""
    if not kind or not key:
        raise ValueError("record requires 'kind' and 'key'")
    return {
        "kind": kind,
        "workspace": workspace or "personal",
        "key": key,
        "name": name,
        "attrs": dict(attrs or {}),
        "source": source or "",
        "confidence": confidence,
        "edges": list(edges or []),
    }


def ingest(g, records, now=None):
    """Upsert a batch of records into graph ``g``. Returns counts.

    Idempotent by construction (graph upserts dedup by stable id), so running
    the same discovery twice adds no duplicates — only refreshes freshness and
    reinforces confidence. Edges whose endpoints aren't in this batch are still
    created (the endpoint node is expected from another module or a prior run);
    the target node is auto-created as a stub if unseen, so an edge is never
    silently dropped.
    """
    n_nodes = 0
    n_edges = 0
    for r in records:
        node = g.upsert_node(
            r["kind"], r["workspace"], r["key"],
            name=r.get("name"), attrs=r.get("attrs"),
            source=r.get("source"), confidence=r.get("confidence", 1.0),
            now=now)
        n_nodes += 1
        frm = node["id"]
        for e in r.get("edges", []):
            to_ws = e.get("to_workspace", r["workspace"])
            to_id = graph.node_id(to_ws, e["to_kind"], e["to_key"])
            if to_id not in g.nodes:
                # stub so the edge has a real endpoint; low confidence until
                # a discovery module observes the target directly.
                g.upsert_node(e["to_kind"], to_ws, e["to_key"],
                              source=r.get("source"),
                              confidence=min(0.5, e.get("confidence", 0.5)),
                              now=now)
                n_nodes += 1
            g.upsert_edge(frm, to_id, e["type"], source=r.get("source"),
                          confidence=e.get("confidence", 1.0), now=now)
            n_edges += 1
    return {"nodes": n_nodes, "edges": n_edges}


def infer_workspaces(records):
    """Cluster records into candidate workspaces — the 'ask only what you can't
    infer' step (issue #12).

    Grouping signal, in priority order:
      1. an explicit ``attrs['org']`` (employer/vendor/school domain) — one
         workspace per distinct org;
      2. the record's provisional ``workspace`` field;
      3. fallback to ``'personal'``.

    Returns a sorted list of proposals::

        {"id": <workspace id>, "kind": <hint or 'unknown'>, "label": <human>,
         "members": [<"kind:key">...], "evidence": {<signal>: <value>},
         "confidence": <0..1>}

    A proposal whose ``kind`` is ``'unknown'`` or whose members span mixed
    signals is what the command surfaces to the user; unambiguous ones need no
    question.
    """
    clusters = {}
    for r in records:
        attrs = r.get("attrs", {})
        org = (attrs.get("org") or "").strip()
        if org:
            wsid = graph.slug(org)
            signal = ("org", org)
        elif r.get("workspace"):
            wsid = graph.slug(r["workspace"])
            signal = ("workspace", r["workspace"])
        else:
            wsid = "personal"
            signal = ("default", "personal")
        c = clusters.setdefault(wsid, {
            "id": wsid, "members": [], "kind_votes": {}, "signals": {},
            "conf_sum": 0.0, "n": 0,
        })
        c["members"].append("%s:%s" % (r["kind"], r["key"]))
        kind_hint = attrs.get("workspace_kind") or _guess_kind(r)
        c["kind_votes"][kind_hint] = c["kind_votes"].get(kind_hint, 0) + 1
        c["signals"][signal[0]] = signal[1]
        c["conf_sum"] += float(r.get("confidence", 1.0))
        c["n"] += 1

    proposals = []
    for wsid in sorted(clusters):
        c = clusters[wsid]
        kind = _top_vote(c["kind_votes"])
        proposals.append({
            "id": wsid,
            "kind": kind,
            "label": _label_for(wsid, kind),
            "members": sorted(set(c["members"])),
            "evidence": c["signals"],
            "confidence": round(c["conf_sum"] / max(c["n"], 1), 3),
        })
    return proposals


def workspace_records(proposals):
    """Turn workspace proposals into Workspace-node records + membership edges,
    ready to feed back through ``ingest`` once confirmed."""
    out = []
    for p in proposals:
        edges = []
        for m in p["members"]:
            kind, _, key = m.partition(":")
            edges.append({"to_kind": kind, "to_key": key,
                          "to_workspace": p["id"], "type": "contains",
                          "confidence": p["confidence"]})
        out.append(record(
            "Workspace", p["id"], p["id"], name=p["label"],
            attrs={"kind": p["kind"]}, source="workspace-inference",
            confidence=p["confidence"], edges=edges))
    return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Node kinds → the workspace kind they most suggest when no org signal exists.
_KIND_FROM_NODETYPE = {
    "Repository": "personal",
    "Project": "personal",
    "Incident": "employer",
    "Deployment": "employer",
    "Ticket": "employer",
}


def _guess_kind(r):
    attrs = r.get("attrs", {})
    if attrs.get("job_application") or r.get("kind") == "JobApplication":
        return "job-search"
    if attrs.get("client"):
        return "freelance"
    return _KIND_FROM_NODETYPE.get(r.get("kind"), "unknown")


def _top_vote(votes):
    if not votes:
        return "unknown"
    # highest count, ties broken alphabetically for determinism; 'unknown' loses
    ranked = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    for k, _ in ranked:
        if k != "unknown":
            return k
    return "unknown"


def _label_for(wsid, kind):
    pretty = wsid.replace("-", " ").title()
    return pretty if kind == "unknown" else "%s (%s)" % (pretty, kind)


if __name__ == "__main__":
    import json
    import sys
    # tiny demo: read records JSON from stdin, print inferred workspaces
    recs = json.load(sys.stdin)
    print(json.dumps(infer_workspaces(recs), indent=2))
