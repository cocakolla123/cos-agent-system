#!/usr/bin/env python3
"""AI OS dashboard sections — graph-powered command-center views (V2, M6).

Turns the knowledge graph into the dashboard's live sections: Daily Priorities,
People Waiting, Blocked Work, Investigations, Projects, Meetings, Job
Applications, Freelance Work, Personal Projects — plus Objective (workstream)
timeline cards. Pure functions returning plain data, so they're unit-testable
without a browser; ``render_sections()`` produces an HTML block the existing
``server.py`` injects into the page **additively** (the V1 approval-queue/chat/
polling UI is untouched).

Degrade-not-crash contract: with no graph, every section is empty and
``render_sections`` returns "" — the dashboard renders exactly as it did in V1.

Attribute conventions a discovery module sets (all optional):
  - Ticket/Objective ``attrs['priority']`` in {high, medium, low}
  - anything ``attrs['blocked']`` truthy / ``attrs['status'] == 'blocked'``
  - Person/Ticket ``attrs['waiting_on_user']`` truthy
  - Document/anything ``attrs['job_application']`` truthy
  - ``attrs['client']`` truthy marks freelance work
  - Meeting ``attrs['when']`` ISO string for ordering
"""

from __future__ import annotations

import html as _html

import correlate
import graph as _graph
import workspaces as _ws

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _blocked(n):
    a = n.get("attrs", {}) or {}
    return bool(a.get("blocked")) or a.get("status") == "blocked"


def _truthy(n, key):
    return bool((n.get("attrs", {}) or {}).get(key))


def _pri(n):
    return _PRIORITY_RANK.get((n.get("attrs", {}) or {}).get("priority", "low"), 2)


def _item(n, sub=""):
    return {"id": n["id"], "title": n.get("name", n["id"]),
            "type": n.get("type"), "sub": sub,
            "meta": n.get("last_verified", ""), "stale": _graph.is_stale(n)}


# ---------------------------------------------------------------------------
# section data functions
# ---------------------------------------------------------------------------

def daily_priorities(g, ws=None, limit=8):
    """Open Objectives + high-signal Tickets, ranked by priority then freshness."""
    cands = g.query(type_="Objective", workspace=ws) + \
        [n for n in g.query(type_="Ticket", workspace=ws)
         if (n.get("attrs", {}) or {}).get("status") not in ("closed", "done")]
    cands.sort(key=lambda n: (_pri(n), n.get("last_verified", "")), reverse=False)
    return [_item(n, (n.get("attrs", {}) or {}).get("priority", "")) for n in cands[:limit]]


def people_waiting(g, ws=None):
    out = [_item(n, "waiting on you") for n in g.query(workspace=ws)
           if _truthy(n, "waiting_on_user")]
    return sorted(out, key=lambda x: x["title"])


def blocked_work(g, ws=None):
    return sorted((_item(n, "blocked") for n in g.query(workspace=ws) if _blocked(n)),
                  key=lambda x: x["title"])


def investigations(g, ws=None):
    inc = g.query(type_="Incident", workspace=ws)
    return sorted((_item(n, (n.get("attrs", {}) or {}).get("system", "incident"))
                   for n in inc), key=lambda x: x["meta"], reverse=True)


def projects(g, ws=None):
    out = g.query(type_="Project", workspace=ws) + g.query(type_="Repository", workspace=ws)
    return [_item(n) for n in sorted(out, key=lambda n: n["id"])]


def meetings(g, ws=None, limit=6):
    ms = g.query(type_="Meeting", workspace=ws)
    ms.sort(key=lambda n: (n.get("attrs", {}) or {}).get("when", n.get("last_seen", "")),
            reverse=True)
    return [_item(n, (n.get("attrs", {}) or {}).get("when", "")) for n in ms[:limit]]


def job_applications(g, ws=None):
    out = [n for n in g.query(workspace=ws)
           if _truthy(n, "job_application") or n.get("type") == "JobApplication"]
    return [_item(n, (n.get("attrs", {}) or {}).get("stage", "")) for n in
            sorted(out, key=lambda n: n["id"])]


def freelance_work(g, ws=None):
    out = [n for n in g.query(workspace=ws) if _truthy(n, "client")]
    return [_item(n, (n.get("attrs", {}) or {}).get("client", "")) for n in
            sorted(out, key=lambda n: n["id"])]


def personal_projects(g, ws=None):
    out = [n for n in (g.query(type_="Repository") + g.query(type_="Project"))
           if n["workspace"] == "personal" and (ws in (None, "personal"))]
    return [_item(n) for n in sorted(out, key=lambda n: n["id"])]


# The section registry: (label, function). Order = dashboard order.
SECTIONS = [
    ("Daily Priorities", daily_priorities),
    ("People Waiting", people_waiting),
    ("Blocked Work", blocked_work),
    ("Investigations", investigations),
    ("Projects", projects),
    ("Meetings", meetings),
    ("Job Applications", job_applications),
    ("Freelance Work", freelance_work),
    ("Personal Projects", personal_projects),
]


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def _esc(s):
    return _html.escape(str(s), quote=True)


def render_workspace_switcher(registry, active):
    """A small additive filter control (issue #16). Inert with <2 workspaces."""
    ids = registry.ids()
    if len(ids) < 2:
        return ""
    opts = ['<a href="?workspace=all"%s>All</a>' % (
        ' class="ws-active"' if active is None else "")]
    for wsid in ids:
        w = registry.get(wsid)
        label = _esc(w.get("label", wsid))
        cls = ' class="ws-active"' if active == wsid else ""
        opts.append('<a href="?workspace=%s"%s>%s</a>' % (_esc(wsid), cls, label))
    return ('<div class="ws-switcher" style="margin:8px 0;font-size:13px">'
            'Workspace: ' + " · ".join(opts) + "</div>")


def _render_section(label, items):
    if not items:
        return ""
    rows = []
    for it in items:
        stale = ' <span title="stale">⚠️</span>' if it.get("stale") else ""
        sub = ' <span class="sec-sub">%s</span>' % _esc(it["sub"]) if it["sub"] else ""
        rows.append('<li><span class="sec-type">%s</span> %s%s%s</li>' % (
            _esc(it.get("type", "")), _esc(it["title"]), sub, stale))
    return ('<section class="graph-section"><h3>%s <span class="sec-count">%d</span></h3>'
            '<ul>%s</ul></section>' % (_esc(label), len(items), "".join(rows)))


def _render_objectives(g, ws):
    objs = g.query(type_="Objective", workspace=ws)
    if not objs:
        return ""
    cards = []
    for o in sorted(objs, key=lambda n: n["id"]):
        steps = correlate.timeline(g, o["id"])
        chain = " → ".join('<span class="tl-step">%s: %s</span>' % (
            _esc(s.get("type")), _esc(s.get("name", s["id"]))) for s in steps)
        cards.append('<div class="objective-card"><div class="obj-title">%s</div>'
                     '<div class="obj-timeline">%s</div></div>' % (
                         _esc(o.get("name", o["id"])), chain))
    return ('<section class="graph-section objectives"><h3>Workstreams '
            '<span class="sec-count">%d</span></h3>%s</section>' % (
                len(objs), "".join(cards)))


def render_sections(g, registry=None, active=None):
    """Render the whole graph-powered block. Returns "" if the graph is empty."""
    if g is None or not g.nodes:
        return ""
    parts = []
    if registry is not None:
        parts.append(render_workspace_switcher(registry, active))
    parts.append(_render_objectives(g, active))
    for label, fn in SECTIONS:
        parts.append(_render_section(label, fn(g, active)))
    body = "".join(p for p in parts if p)
    if not body.strip():
        return ""
    return ('<div class="graph-command-center">'
            '<h2>Command Center <span class="cc-sub">(live from the knowledge graph)</span></h2>'
            + body + "</div>")


# M12: mtime-keyed graph cache — Graph.load re-reads both JSONL files per GET.
_GRAPH_CACHE = {"key": None, "graph": None}


def load_for_dashboard(workspace_dir, requested_ws=None):
    """Convenience for server.py: load graph + registry + resolve active ws.

    Returns ``(graph_or_None, registry, active_ws)``. Never raises — a missing or
    unreadable graph yields ``(None, empty_registry, None)`` so the dashboard
    degrades to its V1 view. The graph load is cached by (mtime, size) of both
    JSONL files, so unchanged graphs cost one stat per request.
    """
    import os
    reg = _ws.Registry.load(workspace_dir)
    active = _ws.resolve_active(reg, requested_ws)
    gdir = os.path.join(workspace_dir, "graph")
    key = []
    for name in (_graph.Graph.NODES_FILE, _graph.Graph.EDGES_FILE):
        try:
            st = os.stat(os.path.join(gdir, name))
            key.append((st.st_mtime_ns, st.st_size))
        except OSError:
            key.append(None)
    key = (gdir, tuple(key))
    if _GRAPH_CACHE["key"] == key:
        return _GRAPH_CACHE["graph"], reg, active
    try:
        g = _graph.Graph.load(gdir)
        if not g.nodes:
            g = None
    except Exception:
        g = None
    _GRAPH_CACHE["key"] = key
    _GRAPH_CACHE["graph"] = g
    return g, reg, active
