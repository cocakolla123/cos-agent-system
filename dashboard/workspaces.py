#!/usr/bin/env python3
"""AI OS multi-workspace model (V2, milestone M3). Stdlib only.

Supports multiple simultaneous, **isolated** workspaces — employer, freelance,
personal, job-search, school, startup, home, property, travel — so confidential
information never mixes. Every graph node/edge already carries a ``workspace``
(see ``graph.py``); this module adds the registry, isolation checking, and the
active-workspace resolution the dashboard filter uses.

Registry file ``<workspace>/workspaces.json``::

    {
      "active": "employer",           # optional default filter
      "workspaces": [
        {"id": "employer", "kind": "employer", "label": "Acme",
         "connectors": ["jira", "slack"], "isolation": "strict"}
      ]
    }

Missing file -> empty registry (safe default; the dashboard shows all nodes).
"""

from __future__ import annotations

import json
import os

import graph

KINDS = [
    "employer", "freelance", "personal", "job-search", "school",
    "startup", "home", "property", "travel",
]

# ``strict`` (default): no cross-workspace edge unless explicitly approved.
# ``open``: cross-workspace edges allowed (e.g. a single-user home lab).
ISOLATION_MODES = ("strict", "open")


class Registry:
    def __init__(self, active=None, workspaces=None):
        self.active = active
        self.workspaces = {w["id"]: w for w in (workspaces or [])}

    # -- persistence --------------------------------------------------------

    @classmethod
    def load(cls, ws_dir):
        path = _registry_path(ws_dir)
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()
        return cls(active=data.get("active"),
                   workspaces=data.get("workspaces", []))

    def save(self, ws_dir):
        os.makedirs(ws_dir, exist_ok=True)
        path = _registry_path(ws_dir)
        data = {"active": self.active,
                "workspaces": [self.workspaces[k] for k in sorted(self.workspaces)]}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)

    # -- mutation -----------------------------------------------------------

    def upsert(self, id_, kind=None, label=None, connectors=None,
               isolation="strict"):
        wsid = graph.slug(id_)
        if kind is not None and kind not in KINDS:
            # advisory, not fatal — keep unknown kinds so callers aren't blocked
            pass
        if isolation not in ISOLATION_MODES:
            isolation = "strict"
        w = self.workspaces.get(wsid, {"id": wsid})
        if kind is not None:
            w["kind"] = kind
        if label is not None:
            w["label"] = label
        if connectors is not None:
            w["connectors"] = sorted(set(connectors))
        w.setdefault("isolation", isolation)
        w["isolation"] = w.get("isolation", isolation)
        self.workspaces[wsid] = w
        if self.active is None:
            self.active = wsid
        return w

    # -- query --------------------------------------------------------------

    def ids(self):
        return sorted(self.workspaces)

    def get(self, id_):
        return self.workspaces.get(graph.slug(id_))

    def is_strict(self, id_):
        w = self.get(id_)
        return not w or w.get("isolation", "strict") == "strict"


def _registry_path(ws_dir):
    return os.path.join(ws_dir, "workspaces.json")


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------

def cross_workspace_edges(g):
    """Return edges whose endpoints live in different workspaces.

    (An edge is stored without its own workspace; its workspace-ness is defined
    by its endpoints.) Dangling edges — an endpoint not in the graph — are
    skipped, since their workspace can't be determined.
    """
    out = []
    for e in g.edges.values():
        a = g.nodes.get(e["from"])
        b = g.nodes.get(e["to"])
        if not a or not b:
            continue
        if a.get("workspace") != b.get("workspace"):
            out.append(e)
    return out


def isolation_violations(g, registry):
    """Cross-workspace edges that are NOT explicitly approved and touch at least
    one ``strict`` workspace. These are the leaks the system must refuse to draw
    on its own — a link across a confidentiality boundary needs user approval.
    """
    bad = []
    for e in cross_workspace_edges(g):
        if e.get("attrs", {}).get("approved_link") or e.get("approved_link"):
            continue
        a = g.nodes[e["from"]]
        b = g.nodes[e["to"]]
        if registry.is_strict(a["workspace"]) or registry.is_strict(b["workspace"]):
            bad.append(e)
    return bad


def approve_link(g, from_id, to_id, edge_type):
    """Mark a specific cross-workspace edge as user-approved (idempotent)."""
    key = graph.edge_key(from_id, to_id, edge_type)
    e = g.edges.get(key)
    if e is not None:
        e["approved_link"] = True
    return e


# ---------------------------------------------------------------------------
# Active-workspace resolution (used by the dashboard filter, issue #16)
# ---------------------------------------------------------------------------

def resolve_active(registry, requested=None):
    """Pick the workspace to display.

    Priority: an explicit ``requested`` (query-param) that exists → the
    registry's ``active`` → ``None`` (meaning "all workspaces / no filter").
    Returns a valid workspace id or ``None``.
    """
    if requested:
        wsid = graph.slug(requested)
        if wsid in registry.workspaces or wsid == "all":
            return None if wsid == "all" else wsid
    if registry.active and registry.active in registry.workspaces:
        return registry.active
    return None
