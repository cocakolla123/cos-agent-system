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


PRIORITIES = ("high", "medium", "low")
DEFAULT_PRIORITY = "medium"


def _ensure_priority(node):
    """Every Action carries a priority. Normalizes case ("High" -> "high");
    a missing or unknown value becomes DEFAULT_PRIORITY. Runs on the merged
    node, so a priority the user already set is never overwritten by a later
    record that simply omits it."""
    attrs = node.setdefault("attrs", {})
    p = str(attrs.get("priority") or "").strip().lower()
    attrs["priority"] = p if p in PRIORITIES else DEFAULT_PRIORITY


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
        if r["kind"] == "Action":
            _ensure_priority(node)
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
        c["provisional"] = c.get("provisional", set())
        if r.get("workspace"):
            c["provisional"].add(graph.slug(r["workspace"]))
        c["conf_sum"] += float(r.get("confidence", 1.0))
        c["n"] += 1

    proposals = []
    for wsid in sorted(clusters):
        c = clusters[wsid]
        kind = _top_vote(c["kind_votes"])
        confidence = round(c["conf_sum"] / max(c["n"], 1), 3)
        # M12: an org token that pulls together records whose provisional
        # workspaces disagree (e.g. a shared vendor org spanning employer and
        # freelance work) is a merge risk — cap confidence so the command
        # surfaces it for confirmation instead of adopting it silently.
        if len(c.get("provisional", set())) > 1:
            confidence = min(confidence, 0.6)
        proposals.append({
            "id": wsid,
            "kind": kind,
            "label": _label_for(wsid, kind),
            "members": sorted(set(c["members"])),
            "evidence": c["signals"],
            "confidence": confidence,
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


# ---------------------------------------------------------------------------
# Crawl reach — make an under-reaching connector announce itself
# ---------------------------------------------------------------------------

# Default floor the research command is instructed to cover per connector.
DEFAULT_WINDOW_FLOOR_DAYS = 90

# attrs keys that carry a real-world *evidence* date, newest-wins. Deliberately
# excludes the node-level 'last_verified': that is crawl recency, and confusing
# the two is the exact mistake is_dormant() exists to prevent.
EVIDENCE_DATE_KEYS = (
    "last_activity", "due", "due_on", "submitted", "completed_on",
    "concluded_on", "invited", "noticed", "suspended_noticed",
)


def window_audit(g, floor_days=DEFAULT_WINDOW_FLOOR_DAYS, now=None):
    """Per-source crawl reach: ``[{"source", "nodes", "declared_days",
    "observed_days", "oldest", "reach_days", "short"}]``, worst reach first.

    The companion to ``sections.coverage_report``. That one catches a section
    nothing ever fed; this one catches a section fed from **too narrow a slice
    of time** — a failure that produces a plausible, populated, wrong answer
    instead of a conspicuous blank, and so is strictly harder to notice.

    It exists because the prose fix didn't hold. A correction traced to Gmail's
    top-N collapsing to a ~2-day window was answered by instructing the crawl to
    cover at least 90 days and to record ``attrs['window_days']``. The next
    correction was the same class again: the oldest Gmail-derived node was one
    day old, `window_days` was recorded on precisely zero nodes, and two
    assessment obligations sitting 3 and 8 weeks back had been invisible the
    whole time. An instruction with nothing reading it is a comment, not a
    control — the same lesson ``is_dormant`` learned about ``likely_demo``.

    Two signals, declared beating observed:

    - ``declared_days`` — the largest ``attrs['window_days']`` any node from
      that source carries, i.e. what the crawl *claims* it covered.
    - ``observed_days`` — age of the oldest evidence date actually present.
      Only a lower bound (a genuinely quiet 90 days looks like a narrow crawl),
      which is why it never overrides a declaration.

    ``short`` is True when the source declared nothing at all — an undeclared
    reach is unknown, and unknown reach is the finding — or when it declared
    less than ``floor_days``. An undeclared source whose observed reach already
    clears the floor is not flagged: the evidence speaks for itself.
    """
    by_source = {}
    for node in g.nodes.values():
        for src in _sources_of(node):
            by_source.setdefault(src, []).append(node)

    out = []
    for src, nodes in by_source.items():
        declared = [n.get("attrs", {}).get("window_days") for n in nodes]
        declared = [d for d in declared if isinstance(d, (int, float))]
        declared_days = max(declared) if declared else None

        ages = [a for a in (_evidence_age_days(n, now=now) for n in nodes)
                if a is not None]
        observed_days = max(ages) if ages else None

        reach = declared_days
        if reach is None:
            reach = observed_days
        elif observed_days is not None:
            reach = max(reach, observed_days)

        if declared_days is None:
            short = not (observed_days is not None and observed_days >= floor_days)
        else:
            short = declared_days < floor_days

        out.append({
            "source": src,
            "nodes": len(nodes),
            "declared_days": declared_days,
            "observed_days": None if observed_days is None else round(observed_days, 1),
            "oldest": _oldest_evidence(nodes),
            "reach_days": None if reach is None else round(reach, 1),
            "short": short,
        })
    # worst (shortest known reach) first; unknown reach sorts worst of all.
    out.sort(key=lambda r: (not r["short"],
                            float("inf") if r["reach_days"] is None else r["reach_days"],
                            r["source"]))
    return out


def window_gaps(g, floor_days=DEFAULT_WINDOW_FLOOR_DAYS, now=None):
    """Just the sources that can't show they covered ``floor_days``."""
    return [r for r in window_audit(g, floor_days=floor_days, now=now)
            if r["short"]]


def _sources_of(node):
    """A node's contributing connectors. ``source`` is a comma-joined string
    once more than one module has touched the node (see graph._merge_sources),
    and a shared node must count against every crawl that fed it."""
    raw = node.get("source") or ""
    return [s.strip() for s in raw.split(",") if s.strip()] or ["unknown"]


def _evidence_dates(node):
    attrs = node.get("attrs", {}) or {}
    out = []
    for key in EVIDENCE_DATE_KEYS:
        parsed = graph._parse_iso(attrs.get(key))
        if parsed is not None:
            out.append(parsed)
    return out


def _evidence_age_days(node, now=None):
    dates = _evidence_dates(node)
    if not dates:
        return None
    age = (graph._utcnow(now) - min(dates)).total_seconds() / 86400.0
    return max(age, 0.0)


def _oldest_evidence(nodes):
    dates = [d for n in nodes for d in _evidence_dates(n)]
    return min(dates).date().isoformat() if dates else None


if __name__ == "__main__":
    import json
    import sys
    # tiny demo: read records JSON from stdin, print inferred workspaces
    recs = json.load(sys.stdin)
    print(json.dumps(infer_workspaces(recs), indent=2))
