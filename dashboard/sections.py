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
  - anything ``attrs['concluded']`` truthy (+ ``concluded_on``/``concluded_by``)
    marks work an explicit event declared over — dropped from current-work views
    however recently it was touched
  - ``Action`` nodes are obligations (the to-do list): ``attrs['due']`` ISO
    date/timestamp, ``attrs['status']`` (see ``graph.DONE_STATUSES``),
    ``attrs['priority']``, and ``attrs['evidence']`` naming where the obligation
    was stated. Tickets with a ``due_on`` join them in the same section.
"""

from __future__ import annotations

import html as _html

import correlate
import graph as _graph
import workspaces as _ws

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _blocked(n):
    # ``blocked_on`` is what /cos-research is told to record for an item
    # waiting on someone else, so it counts as blocked without a separate flag.
    a = n.get("attrs", {}) or {}
    return bool(a.get("blocked")) or a.get("status") == "blocked" or bool(a.get("blocked_on"))


def _blocked_label(n):
    on = (n.get("attrs", {}) or {}).get("blocked_on")
    return "waiting on %s" % on if on else "blocked"


def _truthy(n, key):
    return bool((n.get("attrs", {}) or {}).get(key))


def _pri(n):
    # same default as research.DEFAULT_PRIORITY and the task board
    return _PRIORITY_RANK.get((n.get("attrs", {}) or {}).get("priority", "medium"), 1)


def _url(n):
    a = n.get("attrs", {}) or {}
    for k in ("url", "view_url", "html_link", "permalink", "link"):
        v = a.get(k)
        if v and str(v).startswith("http"):
            return str(v)
    return ""


def _item(n, sub=""):
    return {"id": n["id"], "title": n.get("name", n["id"]),
            "type": n.get("type"), "sub": sub, "url": _url(n),
            "meta": n.get("last_verified", ""), "stale": _graph.is_stale(n),
            "dormant": _graph.is_dormant(n), "concluded": _graph.is_concluded(n),
            "overdue": _graph.is_overdue(n), "due_days": _graph.due_days(n)}


def _current(nodes):
    """Drop nodes that aren't live work from a section claiming to show it.

    The graph is a record of everything found, including history — a service
    club that ended in 2019, a finished school term, a demo project, a contract
    that was terminated last week. Those are worth keeping (the user may ask
    about them) but presenting them as live work is a wrong answer, not merely
    a noisy one. Sections that answer "what is going on now" filter here; the
    graph and its views still hold the lot.

    Two independent disqualifiers, and a section needs both (``is_current``):
    silence for long enough, or an explicit statement that the work is over.
    Recency cannot stand in for the second — a contract concluded a fortnight
    ago sits on documents edited a month ago, all of it perfectly fresh.
    """
    return [n for n in nodes if _graph.is_current(n)]


def _live_objective(g, n):
    """An Objective is only as current as the members it groups.

    This has to propagate up the correlation layer or it leaks: suppressing a
    dead project while still showing the workstream built over it just moves
    the wrong answer one card across. An Objective with no members left is
    judged on its own attrs.
    """
    if n.get("type") != "Objective":
        return True
    members = correlate.timeline(g, n["id"])
    return not members or any(_graph.is_current(m) for m in members)


# ---------------------------------------------------------------------------
# section data functions
# ---------------------------------------------------------------------------

def _days_label(n):
    """Human deadline phrase for an obligation, or its priority if undated."""
    days = _graph.due_days(n)
    if days is None:
        return (n.get("attrs", {}) or {}).get("priority", "")
    if days < 0:
        n_days = int(-days) + 1          # any part of a day late reads as a day
        return "overdue by %d day%s" % (n_days, "" if n_days == 1 else "s")
    if days < 1:
        return "due today"
    n_days = int(days)
    return "due in %d day%s" % (n_days, "" if n_days == 1 else "s")


def _action_rank(n):
    """Soonest-first, with undated obligations after dated ones by priority.

    Overdue items sort to the very top for free: their ``due_days`` is the most
    negative number in the set, and being late never demotes an obligation.
    """
    days = _graph.due_days(n)
    if days is None:
        return (1, _pri(n), n.get("name", n["id"]))
    return (0, days, n.get("name", n["id"]))


def next_actions(g, ws=None, limit=10):
    """**The to-do list** — what the user actually has to go and do.

    Every other section on this dashboard answers "what exists in your world":
    the projects, the documents, the workstreams, the people. That is an
    inventory, and an inventory is not an answer to "what should I do today" —
    a user looking at nine cards of correctly-discovered nouns still has to do
    the chief-of-staff's job themselves, which is the one job the system was
    supposed to do for them.

    So this section reads the obligations the discovery modules extract as
    ``Action`` nodes (see Step 1c of ``commands/cos-research.md``), plus the
    open dated tickets the trackers already give us, and ranks them by when
    they are actually due. It is deliberately first in SECTIONS: the answer
    goes at the top, and the supporting inventory goes underneath it.
    """
    out = [n for n in g.query(type_="Action", workspace=ws)
           if _graph.is_open_action(n)]
    for n in _current(g.query(type_="Ticket", workspace=ws)):
        attrs = n.get("attrs", {}) or {}
        if attrs.get("status") in ("closed", "done"):
            continue
        if _graph.due_days(n) is not None:
            out.append(n)
    out.sort(key=_action_rank)
    return [_item(n, _days_label(n)) for n in out[:limit]]


def daily_priorities(g, ws=None, limit=8):
    """Open Objectives + high-signal Tickets, ranked by priority then freshness."""
    cands = _current([n for n in g.query(type_="Objective", workspace=ws)
                      if _live_objective(g, n)]) + \
        [n for n in _current(g.query(type_="Ticket", workspace=ws))
         if (n.get("attrs", {}) or {}).get("status") not in ("closed", "done")]
    cands.sort(key=lambda n: (_pri(n), n.get("last_verified", "")), reverse=False)
    return [_item(n, (n.get("attrs", {}) or {}).get("priority", "")) for n in cands[:limit]]


def people_waiting(g, ws=None):
    out = [_item(n, "waiting on you") for n in _current(g.query(workspace=ws))
           if _truthy(n, "waiting_on_user")]
    return sorted(out, key=lambda x: x["title"])


def blocked_work(g, ws=None):
    return sorted((_item(n, _blocked_label(n)) for n in _current(g.query(workspace=ws)) if _blocked(n)),
                  key=lambda x: x["title"])


def investigations(g, ws=None):
    inc = _current(g.query(type_="Incident", workspace=ws))
    return sorted((_item(n, (n.get("attrs", {}) or {}).get("system", "incident"))
                   for n in inc), key=lambda x: x["meta"], reverse=True)


def projects(g, ws=None):
    out = _current(g.query(type_="Project", workspace=ws) +
                   g.query(type_="Repository", workspace=ws))
    return [_item(n) for n in sorted(out, key=lambda n: n["id"])]


def meetings(g, ws=None, limit=6):
    ms = g.query(type_="Meeting", workspace=ws)
    ms.sort(key=lambda n: (n.get("attrs", {}) or {}).get("when", n.get("last_seen", "")),
            reverse=True)
    return [_item(n, (n.get("attrs", {}) or {}).get("when", "")) for n in ms[:limit]]


def job_applications(g, ws=None):
    out = [n for n in _current(g.query(workspace=ws))
           if _truthy(n, "job_application") or n.get("type") == "JobApplication"]
    return [_item(n, (n.get("attrs", {}) or {}).get("stage", "")) for n in
            sorted(out, key=lambda n: n["id"])]


def freelance_work(g, ws=None):
    out = [n for n in _current(g.query(workspace=ws)) if _truthy(n, "client")]
    return [_item(n, (n.get("attrs", {}) or {}).get("client", "")) for n in
            sorted(out, key=lambda n: n["id"])]


def personal_projects(g, ws=None):
    out = [n for n in _current(g.query(type_="Repository") + g.query(type_="Project"))
           if n["workspace"] == "personal" and (ws in (None, "personal"))]
    return [_item(n) for n in sorted(out, key=lambda n: n["id"])]


# The section registry: (label, function). Order = dashboard order.
SECTIONS = [
    ("To-Do / Next Actions", next_actions),
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
# Coverage — make a silent pipeline gap announce itself
# ---------------------------------------------------------------------------

def coverage_report(g, ws=None):
    """How many items back each section: ``[{"section", "count"}]``.

    Two corrections in a row (the 2019 service club relics, and this dashboard
    having no to-do list) had the same root cause — a discovery module never
    collected something it should have — and both stayed invisible until the
    user happened to notice. They stayed invisible for a structural reason
    worth fixing rather than patching a third time: **an empty section and a
    section the pipeline never fed look exactly alike.** ``_render_section``
    drops an empty section entirely, so "you have nothing due" and "nothing has
    ever looked for what you have due" both render as blank space.

    This makes the difference legible. It does not decide which case a zero is
    — only the crawl knows that — it just refuses to let a zero pass silently,
    so ``/cos-research`` can report "Job Applications: 0" at the end of a run
    and a gap gets caught by the system instead of by the user.
    """
    out = []
    for label, fn in SECTIONS:
        try:
            count = len(fn(g, ws))
        except Exception:
            count = 0          # a broken section is a gap, not a crash
        out.append({"section": label, "count": count})
    return out


def unanswered_questions(g, ws=None):
    """Just the section labels with no data behind them."""
    return [r["section"] for r in coverage_report(g, ws) if r["count"] == 0]


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


def _slug_anchor(label):
    return "sec-" + "".join(c if c.isalnum() else "-" for c in label.lower())


def _render_title(it):
    """Item title, linked to its source when the node carries a URL."""
    t = _esc(it["title"])
    if it.get("url"):
        return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (
            _esc(it["url"]), t)
    return t


def _render_section(label, items):
    if not items:
        return ""
    rows = []
    for it in items:
        stale = ' <span title="stale">⚠️</span>' if it.get("stale") else ""
        late = ' <span title="overdue">🔴</span>' if it.get("overdue") else ""
        sub = ' <span class="sec-sub">%s</span>' % _esc(it["sub"]) if it["sub"] else ""
        rows.append('<li><span class="sec-type">%s</span> %s%s%s%s</li>' % (
            _esc(it.get("type", "")), _render_title(it), sub, late, stale))
    return ('<section class="graph-section" id="%s"><h3>%s <span class="sec-count">%d</span></h3>'
            '<ul>%s</ul></section>' % (
                _slug_anchor(label), _esc(label), len(items), "".join(rows)))


def _render_objectives(g, ws):
    """The Workstreams card — same currency test as every other current-work view.

    This card renders the correlation layer directly rather than going through
    SECTIONS, so it needs the filter applied explicitly; without it a workstream
    stays on the page as a headline card long after ``daily_priorities`` has
    stopped listing it, which is the louder of the two wrong answers.
    """
    objs = [o for o in _current(g.query(type_="Objective", workspace=ws))
            if _live_objective(g, o)]
    if not objs:
        return ""
    cards = []
    for o in sorted(objs, key=lambda n: n["id"]):
        steps = correlate.timeline(g, o["id"])
        # Decluttered card (first-run feedback): headline + the open Action if
        # the workstream has one, with the full item chain folded behind a
        # <details> so the card answers "what is this and what do I do" at a
        # glance instead of narrating every document title.
        open_actions = [s for s in steps if s.get("type") == "Action"
                        and _graph.is_open_action(s)]
        if open_actions:
            act = min(open_actions, key=_action_rank)
            next_line = ('<div class="obj-next">→ <a href="#%s">%s</a>'
                         '<span class="sec-sub"> %s</span></div>' % (
                             _slug_anchor("To-Do / Next Actions"),
                             _esc(act.get("name", act["id"])),
                             _esc(_days_label(act))))
        else:
            next_line = ('<div class="obj-next obj-next-none">no open action — '
                         '<a href="#%s">see to-dos</a></div>' %
                         _slug_anchor("To-Do / Next Actions"))
        chain = " → ".join('<span class="tl-step">%s: %s</span>' % (
            _esc(s.get("type")), _render_title(_item(s))) for s in steps)
        cards.append(
            '<div class="objective-card"><div class="obj-title">%s '
            '<span class="sec-sub">(%d items)</span></div>%s'
            '<details class="obj-details"><summary>linked items</summary>'
            '<div class="obj-timeline">%s</div></details></div>' % (
                _esc(o.get("name", o["id"])), len(steps), next_line, chain))
    return ('<section class="graph-section objectives"><h3>Workstreams '
            '<span class="sec-count">%d</span></h3>%s</section>' % (
                len(objs), "".join(cards)))


def _todo_row_data(g, n):
    """Everything the expand-modal needs, carried on data-* attributes (the V3
    apostrophe lesson: dynamic values ride datasets, never inline JS strings)."""
    a = n.get("attrs", {}) or {}
    return {
        "id": n["id"],
        "title": n.get("name", n["id"]),
        "note": str(a.get("note", "")),
        "evidence": str(a.get("evidence", "")),
        "priority": str(a.get("priority", "medium")),
        "due": str(a.get("due", "")),
        "ws": n.get("workspace", ""),
        "url": _url(n),
        "duelabel": _days_label(n),
        "overdue": "1" if _graph.is_overdue(n) else "",
    }


def render_todo_board(g, ws=None, limit=25):
    """The interactive to-do list (M13) — the live deployment's task-card UX
    ported onto Action nodes: a compact scrollable list, critical/overdue on
    top, each row expanding into a front-and-center modal with description,
    per-task chat, direct edit, mark-done, and priority control."""
    nodes = [n for n in g.query(type_="Action", workspace=ws)
             if _graph.is_open_action(n)]
    for n in _current(g.query(type_="Ticket", workspace=ws)):
        attrs = n.get("attrs", {}) or {}
        if attrs.get("status") in ("closed", "done"):
            continue
        if _graph.due_days(n) is not None:
            nodes.append(n)
    nodes.sort(key=_action_rank)
    if not nodes:
        return ""
    rows = []
    for n in nodes[:limit]:
        d = _todo_row_data(g, n)
        data = " ".join('data-%s="%s"' % (k, _esc(v)) for k, v in d.items())
        pri = d["priority"]
        badge = {"high": "🔺", "medium": "▪️", "low": "▫️"}.get(pri, "▪️")
        late = ' <span class="todo-late">%s</span>' % _esc(d["duelabel"]) \
            if d["overdue"] else (
                ' <span class="sec-sub">%s</span>' % _esc(d["duelabel"])
                if d["duelabel"] else "")
        rows.append(
            '<div class="todo-row todo-%s" %s onclick="todoOpen(this)">'
            '<span class="todo-badge">%s</span> %s%s</div>' % (
                _esc(pri), data, badge, _esc(d["title"]), late))
    # LinkedIn-Jobs pattern: compact card list on the left, the selected task
    # expanded big in a sticky detail pane beside it; first task auto-opens.
    detail = """
<div class="todo-detail" id="todoDetail">
  <div class="td-empty" id="tdEmpty">Select a task</div>
  <div id="tdBody" style="display:none">
    <input id="tmTitle" class="tm-title" />
    <div class="tm-meta"><span id="tmWs" class="ws-chip"></span>
      <span id="tmDue" class="sec-sub"></span>
      <a id="tmLink" target="_blank" rel="noopener" style="display:none">open source ↗</a></div>
    <div class="tm-controls">
      <select id="tmPriority">
        <option value="high">🔺 high priority</option><option value="medium">▪️ medium</option>
        <option value="low">▫️ low</option>
      </select>
      <button class="primary" onclick="todoDone()">✓ Mark done</button>
      <button class="small" onclick="todoSave()">Save changes</button>
    </div>
    <textarea id="tmNote" rows="5" placeholder="Description / notes..."></textarea>
    <div class="tm-evidence sec-sub" id="tmEvidence"></div>
    <div id="tmResult" class="result"></div>
    <div class="tm-chat">
      <div class="quick-line">Chat about this task</div>
      <div class="tm-chat-log" id="tmChatLog"></div>
      <div class="chat-input-row">
        <textarea id="tmChatInput" rows="2" placeholder="Ask about it, plan it, break it down..."></textarea>
        <button class="small" onclick="todoChat()">Send</button>
      </div>
    </div>
  </div>
</div>
<script>
let _todoId = null;
function todoOpen(el) {
  document.querySelectorAll(".todo-row").forEach(r => r.classList.remove("todo-selected"));
  el.classList.add("todo-selected");
  const d = el.dataset;
  _todoId = d.id;
  document.getElementById("tdEmpty").style.display = "none";
  document.getElementById("tdBody").style.display = "block";
  document.getElementById("tmTitle").value = d.title;
  document.getElementById("tmNote").value = d.note;
  document.getElementById("tmPriority").value = d.priority || "medium";
  document.getElementById("tmWs").textContent = d.ws;
  document.getElementById("tmDue").textContent = d.duelabel || (d.due ? ("due " + d.due) : "no deadline");
  document.getElementById("tmEvidence").textContent = d.evidence ? ("source: " + d.evidence) : "";
  const link = document.getElementById("tmLink");
  if (d.url) { link.href = d.url; link.style.display = "inline"; } else { link.style.display = "none"; }
  loadTodoChat(d.id);
  document.getElementById("tmResult").textContent = "";
  if (window.innerWidth < 980) {
    document.getElementById("todoDetail").scrollIntoView({behavior: "smooth"});
  }
}
async function todoSave() {
  const r = await post("/action-update", {id: _todoId,
    name: document.getElementById("tmTitle").value,
    note: document.getElementById("tmNote").value,
    priority: document.getElementById("tmPriority").value});
  document.getElementById("tmResult").textContent = r.message;
  setTimeout(() => location.reload(), 900);
}
async function todoDone() {
  const r = await post("/action-update", {id: _todoId, status: "done"});
  document.getElementById("tmResult").textContent = r.message;
  setTimeout(() => location.reload(), 900);
}
function escChat(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
async function fetchTodoChat(id) {
  try {
    const r = await fetch("/entry-chat-log?id=" + encodeURIComponent(id), {cache: "no-store"});
    return (await r.json()).messages || [];
  } catch (e) { return null; }
}
async function loadTodoChat(id) {
  const log = document.getElementById("tmChatLog");
  log.innerHTML = "";
  const msgs = await fetchTodoChat(id);
  if (_todoId !== id || !msgs || !msgs.length) return;
  log.innerHTML = msgs.map(m =>
    "<div class='tm-msg" + (m.role === "you" ? " tm-you" : "") + "'>" + escChat(m.text) + "</div>"
  ).join("");
  log.scrollTop = log.scrollHeight;
}
async function todoChat() {
  const input = document.getElementById("tmChatInput");
  const log = document.getElementById("tmChatLog");
  const msg = input.value.trim();
  if (!msg) return;
  const id = _todoId;
  const prior = ((await fetchTodoChat(id)) || []).length;
  log.innerHTML += "<div class='tm-msg tm-you'>" + escChat(msg) + "</div>";
  input.value = "";
  log.innerHTML += "<div class='tm-msg tm-thinking' id='tmThinking'>thinking… (a reply can take a minute)</div>";
  let reply = null;
  try {
    const r = await post("/entry-chat", {id: id, message: msg});
    reply = r.message;
  } catch (e) {
    // Safari aborts fetches at ~60s while the model is still thinking; the
    // server finishes and persists the reply anyway — poll the log for it.
    reply = await pollTodoReply(id, prior);
  }
  if (_todoId !== id) return;
  document.getElementById("tmThinking")?.remove();
  log.innerHTML += "<div class='tm-msg'>" +
    escChat(reply || "(no reply yet — reopen this task shortly)") + "</div>";
  log.scrollTop = log.scrollHeight;
}
async function pollTodoReply(id, prior) {
  for (let i = 0; i < 100; i++) {
    await new Promise(res => setTimeout(res, 3000));
    const msgs = await fetchTodoChat(id);
    if (msgs && msgs.length >= prior + 2 && msgs[msgs.length - 1].role === "assistant")
      return msgs[msgs.length - 1].text;
  }
  return null;
}
document.addEventListener("DOMContentLoaded", () => {
  const first = document.querySelector(".todo-row");
  if (first && window.innerWidth >= 980) todoOpen(first);
});
</script>"""
    return ('<section class="graph-section" id="%s"><h3>To-Do / Next Actions '
            '<span class="sec-count">%d</span></h3>'
            '<div class="quick-line">critical &amp; overdue on top — click a task to open it</div>'
            '<div class="todo-board"><div class="todo-list">%s</div>%s</div></section>' % (
                _slug_anchor("To-Do / Next Actions"), len(nodes),
                "".join(rows), detail))


def render_calendar(g, ws=None, today=None):
    """A small month calendar for the sidebar: dots on days with meetings or
    due obligations, today highlighted."""
    if g is None or not g.nodes:
        return ""
    import calendar as _cal
    import datetime as _dtm
    t = _dtm.date.fromisoformat(today) if today else _dtm.date.today()
    marks = {}
    for n in g.query(type_="Meeting", workspace=ws):
        when = str((n.get("attrs", {}) or {}).get("when", ""))[:10]
        if when:
            marks.setdefault(when, []).append("📅 " + n.get("name", "")[:40])
    for n in g.query(type_="Action", workspace=ws):
        if not _graph.is_open_action(n):
            continue
        due = str((n.get("attrs", {}) or {}).get("due", ""))[:10]
        if due:
            marks.setdefault(due, []).append("⏰ " + n.get("name", "")[:40])
    cal = _cal.Calendar(firstweekday=6)
    rows = ["<tr>" + "".join("<th>%s</th>" % d for d in
                             ("S", "M", "T", "W", "T", "F", "S")) + "</tr>"]
    for week in cal.monthdatescalendar(t.year, t.month):
        cells = []
        for day in week:
            iso = day.isoformat()
            cls = []
            if day.month != t.month:
                cls.append("cal-out")
            if day == t:
                cls.append("cal-today")
            if iso in marks:
                cls.append("cal-marked")
            title = _esc("; ".join(marks.get(iso, [])))
            cells.append('<td class="%s" title="%s">%d%s</td>' % (
                " ".join(cls), title, day.day,
                "<span class='cal-dot'>•</span>" if iso in marks else ""))
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div class="cal-box"><div class="cal-head">%s</div>'
            '<table class="cal">%s</table></div>' % (
                t.strftime("%B %Y"), "".join(rows)))


def render_today_brief(g, active=None, today=None):
    """The generated 'what does today look like' summary (first-run feedback:
    'there is no summary for today'). Composed, not crawled: overdue + due-today
    obligations, today's meetings, and the top priorities, each linking down
    into its section. Returns "" with no graph."""
    if g is None or not g.nodes:
        return ""
    import datetime as _dtm
    today = today or _dtm.date.today().isoformat()
    todos = next_actions(g, active, limit=50)
    overdue = [t for t in todos if t.get("overdue")]
    due_today = [t for t in todos if t.get("due_days") is not None
                 and 0 <= t["due_days"] < 1]
    meetings_today = [m for m in meetings(g, active, limit=20)
                      if str(m.get("sub", "")).startswith(today)]
    top = [t for t in todos if t not in overdue and t not in due_today][:3]
    parts = []
    if overdue:
        parts.append('<div class="tb-line tb-overdue">🔴 <strong>%d overdue:</strong> %s</div>' % (
            len(overdue), " · ".join(_render_title(t) for t in overdue[:4])))
    if due_today:
        parts.append('<div class="tb-line">⏰ <strong>Due today:</strong> %s</div>' % (
            " · ".join(_render_title(t) for t in due_today[:4])))
    if meetings_today:
        parts.append('<div class="tb-line">📅 <strong>Meetings:</strong> %s</div>' % (
            " · ".join(_render_title(m) for m in meetings_today[:4])))
    if top:
        parts.append('<div class="tb-line">▶ <strong>Next up:</strong> %s</div>' % (
            " · ".join(_render_title(t) for t in top)))
    if not parts:
        parts.append('<div class="tb-line">Nothing due or scheduled today — '
                     '<a href="#%s">see the full to-do list</a>.</div>' %
                     _slug_anchor("To-Do / Next Actions"))
    return '<div class="today-brief">%s</div>' % "".join(parts)


def render_sections(g, registry=None, active=None):
    """Render the whole graph-powered block. Returns "" if the graph is empty."""
    if g is None or not g.nodes:
        return ""
    parts = []
    if registry is not None:
        parts.append(render_workspace_switcher(registry, active))
    # M13: the task board is the front of the page (the answer), before the
    # workstream/inventory cards (the evidence) — LinkedIn-Jobs split view.
    parts.append(render_todo_board(g, active))
    parts.append(_render_objectives(g, active))
    for label, fn in SECTIONS:
        if label == "To-Do / Next Actions":
            continue  # rendered first, above
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
