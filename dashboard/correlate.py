#!/usr/bin/env python3
"""AI OS workstream correlation (V2, milestone M5). Stdlib only.

Instead of showing a Slack thread, a Jira ticket, a meeting, and a PR as four
unrelated items, decide when they belong to the **same objective** and bind them
into one ``Objective`` (workstream) node. The dashboard then renders an objective
as a single timeline card (Slack -> meeting -> ticket -> PR -> next action).

Correlation is deterministic and **workspace-respecting**: nodes are only ever
grouped within the same workspace, so isolation (M3) is never violated.

Two correlatable nodes are grouped when they share any of:
  - an explicit reference token (``attrs['refs']`` — e.g. a ticket key a meeting
    or PR references),
  - an explicit subject key (``attrs['subject']`` — exact match),
  - a participant (both are connected to the same Person node).

Objective ids are stable across runs (derived from the smallest shared token or
member id), so re-running upserts the same Objective + edges rather than making
new ones — safe for the poll loop.
"""

from __future__ import annotations

import graph

# Node types that can belong to a workstream.
CORRELATABLE = {"Channel", "Ticket", "Meeting", "PR", "Document", "Incident"}

# The order a timeline reads in (earliest kind of activity first).
_TIMELINE_ORDER = ["Channel", "Meeting", "Ticket", "PR", "Deployment",
                   "Document", "Incident"]


def _signature(g, node):
    """Return the set of grouping tokens for a node (refs, subject, participants)."""
    sig = set()
    attrs = node.get("attrs", {}) or {}
    for ref in attrs.get("refs", []) or []:
        sig.add("ref:" + graph.slug(ref))
    if attrs.get("subject"):
        sig.add("subj:" + graph.slug(attrs["subject"]))
    for nb in g.neighbors(node["id"]):
        if nb.get("type") == "Person":
            sig.add("person:" + nb["id"])
    return sig


def correlate(g, now=None, min_members=2):
    """Find workstreams and materialize ``Objective`` nodes + ``part_of`` edges.

    Returns the list of Objective node ids created or refreshed. Idempotent.
    """
    # group correlatable nodes by workspace
    by_ws = {}
    for n in g.nodes.values():
        if n.get("type") in CORRELATABLE:
            by_ws.setdefault(n["workspace"], []).append(n)

    objective_ids = []
    for ws in sorted(by_ws):
        nodes = sorted(by_ws[ws], key=lambda x: x["id"])
        sigs = {n["id"]: _signature(g, n) for n in nodes}
        uf = _UnionFind(n["id"] for n in nodes)
        # Strong tokens (explicit refs/subjects) union directly. Person tokens
        # alone are weak — one shared attendee/owner (e.g. the user's manager,
        # who touches everything) must NOT merge unrelated work into a single
        # mega-objective. Rule: union on a shared strong token, or on >= 2
        # shared person tokens between a pair.
        token_to_node = {}
        for nid in sorted(sigs):
            for tok in sorted(sigs[nid]):
                if tok.startswith("person:"):
                    continue
                if tok in token_to_node:
                    uf.union(token_to_node[tok], nid)
                else:
                    token_to_node[tok] = nid
        person_groups = {}
        for nid in sorted(sigs):
            for tok in sorted(sigs[nid]):
                if tok.startswith("person:"):
                    person_groups.setdefault(tok, []).append(nid)
        pair_person_counts = {}
        for tok in sorted(person_groups):
            members = person_groups[tok]
            for i, a in enumerate(members):
                for b in members[i + 1:]:
                    key = (a, b)
                    pair_person_counts[key] = pair_person_counts.get(key, 0) + 1
                    if pair_person_counts[key] >= 2:
                        uf.union(a, b)
        # build components
        comps = {}
        for nid in sorted(sigs):
            comps.setdefault(uf.find(nid), []).append(nid)
        for members in comps.values():
            if len(members) < min_members:
                continue
            objective_ids.append(
                _materialize(g, ws, sorted(members), sigs, now=now))
    return objective_ids


def _materialize(g, ws, members, sigs, now=None):
    # stable natural key: smallest shared ref token if any, else smallest member
    shared = set.intersection(*[sigs[m] for m in members]) if members else set()
    refkeys = sorted(t for t in shared if t.startswith("ref:") or t.startswith("subj:"))
    if refkeys:
        natural = refkeys[0].split(":", 1)[1]
    else:
        natural = graph.slug(members[0].split(":")[-1])
    name = _objective_name(g, members, natural)
    obj = g.upsert_node("Objective", ws, natural, name=name,
                        attrs={"members": len(members)},
                        source="correlation", confidence=0.7, now=now)
    for m in members:
        g.upsert_edge(m, obj["id"], "part_of", source="correlation",
                      confidence=0.7, now=now)
    return obj["id"]


def _objective_name(g, members, natural):
    # prefer a member's subject, else a Ticket/Objective-ish name, else the key
    for m in members:
        subj = (g.nodes[m].get("attrs", {}) or {}).get("subject")
        if subj:
            return subj
    for m in members:
        if g.nodes[m].get("type") == "Ticket":
            return g.nodes[m].get("name", natural)
    return "Workstream: %s" % natural


def timeline(g, objective_id):
    """Return an objective's member nodes ordered for a timeline card (issue #22).

    Ordered by kind (`Channel -> Meeting -> Ticket -> PR -> ...`) then by
    ``last_seen`` within a kind. Returns ``[]`` for an unknown objective.
    """
    if objective_id not in g.nodes:
        return []
    members = g.neighbors(objective_id, edge_type="part_of", direction="in")
    order = {k: i for i, k in enumerate(_TIMELINE_ORDER)}

    def _key(n):
        return (order.get(n.get("type"), len(_TIMELINE_ORDER)),
                n.get("last_seen", ""), n["id"])

    return sorted(members, key=_key)


class _UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # deterministic: smaller id becomes root
            lo, hi = sorted((ra, rb))
            self.parent[hi] = lo


if __name__ == "__main__":
    import sys
    g = graph.Graph.load(sys.argv[1]) if len(sys.argv) > 1 else graph.Graph()
    ids = correlate(g)
    print("objectives: %d" % len(ids))
    for oid in ids:
        print(" ", oid, "->", [n["id"] for n in timeline(g, oid)])
