#!/usr/bin/env python3
"""AI OS knowledge graph — file-based store + library (V2, milestone M1).

The single source of truth that the research engine writes and that the agent
factory, workstream correlation, dashboard, and poll all read. Deliberately
matches the rest of this template: Python stdlib only, all state in plain files,
every path passed in (no hardcoded home-dir), git-friendly.

Storage layout (under a graph dir, by default ``<workspace>/graph/``)::

    graph/
      nodes.jsonl   one JSON object per node, sorted by id
      edges.jsonl   one JSON object per edge, sorted by key
      views/*.md    human-readable rendered views (regenerated, idempotent)

Node schema (issue #1)::

    {id, type, workspace, name, attrs{}, source, confidence,
     first_seen, last_seen, last_verified}

  - ``id`` = ``<workspace>:<type>:<natural-key>`` (see ``node_id``) so an upsert
    of the same real-world thing always lands on the same record -> dedup by
    construction; a second observation updates freshness/confidence in place and
    never creates a duplicate.
  - ``confidence`` in [0, 1]. Independent observations combine via noisy-OR.
  - ``first_seen`` / ``last_seen`` / ``last_verified`` are ISO-8601 UTC strings.

Edge schema::

    {id, from, to, type, source, confidence, first_seen, last_seen}

  - ``id`` = ``<from>|<type>|<to>`` (see ``edge_key``).

Node types (extensible — this is the V2 vocabulary, not a hard enum):
Workspace, Project, Repository, Channel, Ticket, Meeting, PR, Deployment,
Document, Person, Incident, Decision, Objective.

All functions that stamp time take an optional ``now`` (a ``datetime``) so callers
can make runs deterministic and tests can assert exact timestamps.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import re


@contextlib.contextmanager
def file_lock(path):
    """Advisory exclusive lock via a ``.lock`` sidecar (fcntl.flock).

    V2 has several writers (server threads, poll/learn/probe subprocesses) on
    shared files; this serializes read-modify-write cycles so a status flip
    can't be lost to a concurrent rewrite. No-op where fcntl is unavailable
    (Windows) — behavior there stays last-write-wins, as before.
    """
    lock_path = str(path) + ".lock"
    try:
        import fcntl
    except ImportError:  # pragma: no cover - non-POSIX
        yield
        return
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def transaction(graph_dir):
    """The lock every load-change-save of a graph holds, start to finish.

    ``save`` alone only keeps two writers from interleaving a file; a writer
    that loaded earlier would still overwrite the other's change. Hold this
    around the whole cycle (the dashboard's task edits, a check's ingest, the
    research tool) so each one starts from the latest saved graph. Not
    re-entrant: do not nest it for the same graph."""
    return file_lock(os.path.join(graph_dir, "txn"))


# ---------------------------------------------------------------------------
# Vocabulary (advisory — upsert does not reject unknown types, so research
# modules can introduce new ones without editing this file first).
# ---------------------------------------------------------------------------

NODE_TYPES = [
    "Workspace", "Project", "Repository", "Channel", "Ticket", "Meeting",
    "PR", "Deployment", "Document", "Person", "Incident", "Decision",
    "Objective", "Action",
]

# Default staleness horizon used by is_stale()/stale_nodes() when the caller
# does not override it. A node not re-verified within this many days is stale.
DEFAULT_MAX_AGE_DAYS = 14

# Default dormancy horizon used by is_dormant(). Measured against the node's
# *source activity* (attrs['last_activity']), not against crawl recency — see
# activity_days(). A year of real-world silence means history, not current work.
DEFAULT_MAX_IDLE_DAYS = 365

# attrs['status'] values that assert an engagement is over. Deliberately narrow:
# only words that can only mean "this ended". "closed"/"done"/"completed" are
# excluded — a completed document or a closed ticket is normal lifecycle, and
# sections.py already handles Ticket status separately. Outcome words for an
# application or an invitation ("rejected", "not selected", "withdrawn",
# "declined", "expired") end it just as surely; a first run on a real job-search
# inbox recorded a rejection as status "rejected" and it stayed on the to-do list.
TERMINAL_STATUSES = frozenset(
    {"concluded", "ended", "terminated", "offboarded", "cancelled", "canceled",
     "rejected", "not selected", "withdrawn", "declined", "expired"})

# attrs['status'] values that mean an **Action** no longer needs doing. Read
# only by is_open_action(), never by is_concluded() — the distinction is the
# whole point: "done" on a Document or a Ticket is ordinary lifecycle (see
# TERMINAL_STATUSES above), but "done" on an obligation is the one word that
# takes it off the to-do list. "satisfied", "on hold" and "delegated" also
# close it: the user has nothing left to do on it (heldout_v2 runs showed
# models writing these for correctly handled items that then stayed open).
# Matching ignores case and treats "_"/"-" as spaces ("on_hold" == "on hold").
DONE_STATUSES = frozenset(
    {"done", "completed", "complete", "submitted", "resolved", "paid",
     "closed", "dismissed", "satisfied", "on hold", "delegated"})


def _norm_status(status):
    return " ".join(status.replace("_", " ").replace("-", " ").lower().split())


# ---------------------------------------------------------------------------
# Time + id helpers
# ---------------------------------------------------------------------------

def _utcnow(now=None):
    """Return a timezone-aware UTC datetime; accept an injected ``now``."""
    if now is None:
        # The public demo freezes the clock at its world's "today" so a
        # fictional October reads the same whenever someone opens it.
        fixed = os.environ.get("COS_FIXED_NOW")
        if fixed:
            parsed = _parse_iso(fixed)
            if parsed is not None:
                return parsed
        return _dt.datetime.now(_dt.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=_dt.timezone.utc)
    return now.astimezone(_dt.timezone.utc)


def iso(now=None):
    """ISO-8601 UTC timestamp string, second precision, ``Z`` suffix."""
    return _utcnow(now).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s):
    """Parse an ISO timestamp written by ``iso()`` back to aware UTC datetime."""
    if not s:
        return None
    try:
        return _dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=_dt.timezone.utc)
    except (ValueError, TypeError):
        # Be lenient about anything reasonably ISO-shaped — including the
        # date-only form discovery modules use for attrs['last_activity'].
        # Always return *aware* UTC: a naive result here would blow up every
        # caller that subtracts it from _utcnow().
        try:
            parsed = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=_dt.timezone.utc)


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def slug(value):
    """Normalize an arbitrary string into a stable, id-safe natural key.

    Lowercased, non-alphanumerics collapsed to ``-``, trimmed. Deterministic so
    the same real-world identifier always maps to the same node id.
    """
    s = _SLUG_RE.sub("-", str(value).strip().lower()).strip("-")
    return s or "unknown"


def node_id(workspace, type_, natural_key):
    """Stable node id: ``<workspace>:<type>:<slug(natural_key)>``.

    ``workspace`` and ``type`` are slugged too, so ids are collision-resistant
    and dedup happens by construction on upsert.
    """
    return "%s:%s:%s" % (slug(workspace), slug(type_), slug(natural_key))


def edge_key(frm, to, type_):
    """Stable edge id: ``<from>|<type>|<to>``."""
    return "%s|%s|%s" % (frm, slug(type_), to)


def combine_confidence(a, b):
    """Combine two independent confidences via noisy-OR, clamped to [0, 1].

    Two weak observations of the same fact should reinforce, never cancel:
    ``combine(0.6, 0.6) == 0.84``. Idempotent at the extremes
    (``combine(x, 0) == x``, ``combine(x, 1) == 1``).
    """
    a = _clamp01(a)
    b = _clamp01(b)
    return _clamp01(1.0 - (1.0 - a) * (1.0 - b))


def _clamp01(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if x < 0 else 1.0 if x > 1 else x


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class Graph:
    """In-memory view over the on-disk JSONL store.

    Not thread-safe; callers (single-writer, like the rest of this system —
    ``cos-knowledge``) load, mutate, and save.
    """

    NODES_FILE = "nodes.jsonl"
    EDGES_FILE = "edges.jsonl"
    VIEWS_DIR = "views"

    def __init__(self):
        self.nodes = {}   # id -> node dict
        self.edges = {}   # edge_key -> edge dict

    # -- persistence --------------------------------------------------------

    @classmethod
    def load(cls, graph_dir):
        """Load a graph from ``graph_dir``. Missing files -> empty graph."""
        g = cls()
        g.nodes = _read_jsonl(os.path.join(graph_dir, cls.NODES_FILE), "id")
        g.edges = _read_jsonl(os.path.join(graph_dir, cls.EDGES_FILE), "id")
        return g

    def save(self, graph_dir):
        """Persist deterministically (sorted, sorted keys) for clean diffs.
        Serialized against concurrent savers via file_lock."""
        os.makedirs(graph_dir, mode=0o700, exist_ok=True)
        with file_lock(os.path.join(graph_dir, "graph")):
            _write_jsonl(os.path.join(graph_dir, self.NODES_FILE),
                         [self.nodes[k] for k in sorted(self.nodes)])
            _write_jsonl(os.path.join(graph_dir, self.EDGES_FILE),
                         [self.edges[k] for k in sorted(self.edges)])

    # -- mutation -----------------------------------------------------------

    def upsert_node(self, type_, workspace, natural_key, name=None,
                    attrs=None, source=None, confidence=1.0, now=None):
        """Insert or merge a node, keyed by ``node_id``.

        On a repeat observation: ``first_seen`` is preserved; ``last_seen`` and
        ``last_verified`` advance; ``attrs`` are shallow-merged (new keys win,
        non-empty values replace empties); ``confidence`` combines via
        noisy-OR; ``source`` accumulates into a comma-joined set. Returns the
        stored node.
        """
        nid = node_id(workspace, type_, natural_key)
        ts = iso(now)
        attrs = dict(attrs or {})
        existing = self.nodes.get(nid)
        if existing is None:
            node = {
                "id": nid,
                "type": type_,
                "workspace": slug(workspace),
                "name": name if name is not None else str(natural_key),
                "attrs": attrs,
                "source": source or "",
                "confidence": _clamp01(confidence),
                "first_seen": ts,
                "last_seen": ts,
                "last_verified": ts,
            }
            self.nodes[nid] = node
            return node
        # merge in place
        if name:
            existing["name"] = name
        existing["attrs"] = _merge_attrs(existing.get("attrs", {}), attrs)
        existing["source"] = _merge_sources(existing.get("source", ""), source)
        existing["confidence"] = combine_confidence(
            existing.get("confidence", 0.0), confidence)
        existing["last_seen"] = ts
        existing["last_verified"] = ts
        existing.setdefault("first_seen", ts)
        return existing

    def upsert_edge(self, frm, to, type_, source=None, confidence=1.0,
                    now=None):
        """Insert or merge a directed edge, keyed by ``edge_key``."""
        key = edge_key(frm, to, type_)
        ts = iso(now)
        existing = self.edges.get(key)
        if existing is None:
            edge = {
                "id": key,
                "from": frm,
                "to": to,
                "type": type_,
                "source": source or "",
                "confidence": _clamp01(confidence),
                "first_seen": ts,
                "last_seen": ts,
            }
            self.edges[key] = edge
            return edge
        existing["source"] = _merge_sources(existing.get("source", ""), source)
        existing["confidence"] = combine_confidence(
            existing.get("confidence", 0.0), confidence)
        existing["last_seen"] = ts
        existing.setdefault("first_seen", ts)
        return existing

    def merge_nodes(self, keep_id, dup_id, now=None):
        """Fold ``dup_id`` into ``keep_id`` and re-point every incident edge.

        Used when two ids turn out to be the same real thing (e.g. a person
        discovered under two handles). Confidence/attrs/sources merge; edges
        touching ``dup_id`` are rewritten to ``keep_id`` (and re-deduped by key).
        Returns the surviving node, or ``None`` if either id is unknown.
        """
        keep = self.nodes.get(keep_id)
        dup = self.nodes.get(dup_id)
        if keep is None or dup is None or keep_id == dup_id:
            return keep
        ts = iso(now)
        keep["attrs"] = _merge_attrs(keep.get("attrs", {}), dup.get("attrs", {}))
        keep["source"] = _merge_sources(keep.get("source", ""), dup.get("source", ""))
        keep["confidence"] = combine_confidence(
            keep.get("confidence", 0.0), dup.get("confidence", 0.0))
        keep["last_seen"] = ts
        keep["last_verified"] = ts
        # earliest first_seen wins
        first = [s for s in (keep.get("first_seen"), dup.get("first_seen")) if s]
        if first:
            keep["first_seen"] = min(first)
        # re-point edges
        for key in list(self.edges):
            e = self.edges[key]
            if e["from"] != dup_id and e["to"] != dup_id:
                continue
            self.edges.pop(key)
            frm = keep_id if e["from"] == dup_id else e["from"]
            to = keep_id if e["to"] == dup_id else e["to"]
            if frm == to:
                continue  # drop self-loops created by the merge
            self.upsert_edge(frm, to, e["type"], e.get("source"),
                             e.get("confidence", 1.0), now=now)
        self.nodes.pop(dup_id, None)
        return keep

    # -- query --------------------------------------------------------------

    def get(self, nid):
        return self.nodes.get(nid)

    def query(self, type_=None, workspace=None, where=None):
        """Return nodes filtered by type, workspace, and an attr predicate.

        ``where`` is either a dict of ``attr -> value`` (all must match) or a
        callable ``node -> bool``. Results are sorted by id for determinism.
        """
        ws = slug(workspace) if workspace else None
        out = []
        for nid in sorted(self.nodes):
            n = self.nodes[nid]
            if type_ is not None and n.get("type") != type_:
                continue
            if ws is not None and n.get("workspace") != ws:
                continue
            if where is not None and not _match_where(n, where):
                continue
            out.append(n)
        return out

    def neighbors(self, nid, edge_type=None, direction="both"):
        """Return neighbor nodes of ``nid`` along matching edges.

        ``direction`` is ``"out"``, ``"in"``, or ``"both"``. Unknown neighbor
        ids (dangling edges) are skipped. Sorted by id.
        """
        found = {}
        for e in self.edges.values():
            if edge_type is not None and e.get("type") != edge_type:
                continue
            other = None
            if e["from"] == nid and direction in ("out", "both"):
                other = e["to"]
            elif e["to"] == nid and direction in ("in", "both"):
                other = e["from"]
            if other and other in self.nodes:
                found[other] = self.nodes[other]
        return [found[k] for k in sorted(found)]

    # -- freshness ----------------------------------------------------------

    def stale_nodes(self, now=None, max_age_days=DEFAULT_MAX_AGE_DAYS):
        """All nodes not verified within ``max_age_days`` (sorted by id)."""
        return [self.nodes[k] for k in sorted(self.nodes)
                if is_stale(self.nodes[k], now=now, max_age_days=max_age_days)]

    # -- rendering ----------------------------------------------------------

    def render_views(self, graph_dir):
        """Write ``views/*.md`` — one file per workspace + an ``index.md``.

        Idempotent: identical graph state produces byte-identical files, so a
        no-op regeneration yields no git diff. Returns the list of paths written.
        """
        views_dir = os.path.join(graph_dir, self.VIEWS_DIR)
        os.makedirs(views_dir, exist_ok=True)
        workspaces = sorted({n.get("workspace", "unknown")
                             for n in self.nodes.values()})
        written = []

        index = ["# Knowledge graph", "",
                 "_Generated view — do not edit; regenerated from the graph._", "",
                 "- Nodes: %d" % len(self.nodes),
                 "- Edges: %d" % len(self.edges),
                 "- Workspaces: %d" % len(workspaces), ""]
        if workspaces:
            index.append("## Workspaces")
            for ws in workspaces:
                count = sum(1 for n in self.nodes.values()
                            if n.get("workspace") == ws)
                index.append("- [%s](%s.md) — %d nodes" % (ws, ws, count))
            index.append("")
        index_path = os.path.join(views_dir, "index.md")
        _write_text(index_path, "\n".join(index).rstrip() + "\n")
        written.append(index_path)

        for ws in workspaces:
            path = os.path.join(views_dir, "%s.md" % ws)
            _write_text(path, self._render_workspace(ws))
            written.append(path)
        return written

    def _render_workspace(self, ws):
        lines = ["# Workspace: %s" % ws, "",
                 "_Generated view — regenerated from the graph._", ""]
        by_type = {}
        for n in self.nodes.values():
            if n.get("workspace") != ws:
                continue
            by_type.setdefault(n.get("type", "Unknown"), []).append(n)
        for type_ in sorted(by_type):
            lines.append("## %s (%d)" % (type_, len(by_type[type_])))
            for n in sorted(by_type[type_], key=lambda x: x["id"]):
                conf = n.get("confidence", 0.0)
                stale = " ⚠️stale" if is_stale(n) else ""
                src = n.get("source", "")
                src = " · _%s_" % src if src else ""
                lines.append("- **%s** (conf %.2f, seen %s)%s%s" % (
                    n.get("name", n["id"]), conf,
                    n.get("last_verified", "?"), stale, src))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Freshness (module-level so poll/dashboard can call without a Graph instance)
# ---------------------------------------------------------------------------

def is_stale(node, now=None, max_age_days=DEFAULT_MAX_AGE_DAYS):
    """True if ``node`` was last verified more than ``max_age_days`` ago."""
    last = _parse_iso(node.get("last_verified") or node.get("last_seen"))
    if last is None:
        return True
    age = _utcnow(now) - last
    return age > _dt.timedelta(days=max_age_days)


def freshness_days(node, now=None):
    """Age of a node in days since it was last verified (float), or ``None``."""
    last = _parse_iso(node.get("last_verified") or node.get("last_seen"))
    if last is None:
        return None
    return (_utcnow(now) - last).total_seconds() / 86400.0


def activity_days(node, now=None):
    """Age in days of the node's *underlying evidence*, or ``None`` if unknown.

    Distinct from ``freshness_days``, and the distinction matters: freshness
    answers "when did the crawler last look at this", activity answers "when did
    the real-world thing last actually happen". A 2019 calendar re-read by
    tonight's poll is maximally *fresh* and totally *inactive*, so freshness
    alone can never tell a live project from a relic. Discovery modules record
    the latter as ``attrs['last_activity']`` (ISO date or timestamp).
    """
    last = _parse_iso((node.get("attrs", {}) or {}).get("last_activity"))
    if last is None:
        return None
    return (_utcnow(now) - last).total_seconds() / 86400.0


def is_dormant(node, now=None, max_idle_days=DEFAULT_MAX_IDLE_DAYS):
    """True if the node is history rather than current work.

    Three ways to be dormant: a discovery module said so outright
    (``attrs['dormant']``), it is vendor sample data (``attrs['likely_demo']``),
    or its newest real-world activity is older than ``max_idle_days``. A node
    with no ``last_activity`` at all is **not** dormant — most node kinds never
    record one, and silently hiding them would trade a false-positive problem
    for a worse false-negative one. Suppression needs positive evidence of age,
    not just absence of evidence.

    ``likely_demo`` is checked here rather than left to each caller because a
    demo is never dormant *by date*: the vendor's onboarding sample ships with
    plausible near-term due dates (the Asana starter project's "Task 1" is due
    next week, forever), so the activity clock reads it as live work. The
    research module already states the rule — "a demo is not work" — and this
    is where that statement has to be enforced to bind.
    """
    attrs = node.get("attrs", {}) or {}
    if attrs.get("dormant") or attrs.get("likely_demo"):
        return True
    age = activity_days(node, now=now)
    return age is not None and age > max_idle_days


def is_concluded(node):
    """True if something explicitly declared this work over.

    The third question in the set, and not answerable by either of the others.
    ``is_stale`` asks "when did we last look", ``is_dormant`` asks "when did
    this last happen" — both infer from *silence*, so both need time to pass
    before they say anything. A concluded engagement is an *assertion*: a
    termination email, a closed contract, an offboarding notice. It is loud,
    dated, and immediate, and it routinely lands on work whose evidence is days
    old and whose activity clock will not trip for another year.

    Recorded by discovery modules as ``attrs['concluded']`` (with
    ``concluded_on`` / ``concluded_by`` carrying the date and the evidence) or
    as an unambiguous ``attrs['status']`` — see TERMINAL_STATUSES.
    """
    a = node.get("attrs", {}) or {}
    if a.get("concluded"):
        return True
    status = a.get("status")
    return isinstance(status, str) and _norm_status(status) in TERMINAL_STATUSES


def is_current(node, now=None, max_idle_days=DEFAULT_MAX_IDLE_DAYS):
    """True if ``node`` can honestly be presented as live work.

    The single predicate "current work" views should ask. Work is current until
    it has either gone quiet long enough (dormant) or been declared finished
    (concluded); either one alone disqualifies it.
    """
    return not is_dormant(node, now=now, max_idle_days=max_idle_days) \
        and not is_concluded(node)


# ---------------------------------------------------------------------------
# Obligations — "what must I do", as opposed to "what exists"
# ---------------------------------------------------------------------------
#
# The three predicates above all answer questions about a *thing*: is it fresh,
# is it active, is it over. None of them can answer the question a chief of
# staff exists to answer — **what do I have to do next?** — because that is not
# a property of an entity at all. A document, a repo and a workstream can every
# one of them be fresh, active and unconcluded while the user still owes
# nothing. Meanwhile the assessment due on Friday is not an entity the crawler
# would ever have minted a node for.
#
# So obligations are their own node type (``Action``) with their own clock
# (``attrs['due']``) and their own end state (DONE_STATUSES). Discovery modules
# emit them; sections.next_actions() ranks them.


def due_days(node, now=None):
    """Days until ``attrs['due']`` — negative when overdue, ``None`` if undated.

    An undated obligation is still an obligation ("pay the AMF", no deadline
    stated), so callers must treat ``None`` as "no deadline known", never as
    "nothing to do".
    """
    attrs = node.get("attrs", {}) or {}
    # 'due_on' is what the tracker connectors already emit (Asana, and the
    # shape most issue trackers expose), so accept it rather than making every
    # module rewrite a field it already has right.
    raw = attrs.get("due") or attrs.get("due_on")
    due = _parse_iso(raw)
    if due is None:
        return None
    if isinstance(raw, str) and _DATE_ONLY_RE.match(raw.strip()):
        # "due 2026-10-13" means by the end of that day, local time; read as
        # midnight UTC it showed as overdue on the morning it was due
        day = _dt.date.fromisoformat(raw.strip())
        due = _dt.datetime.combine(day + _dt.timedelta(days=1), _dt.time()).astimezone()
    return (due - _utcnow(now)).total_seconds() / 86400.0


PRIORITY_LEVELS = ("high", "medium", "low")
# Rule H1 in commands/cos-research.md: overdue or due within this many days
# is high, whoever asked. It is pure date math, so it is computed here every
# time the dashboard asks rather than frozen when the item was extracted.
HIGH_WITHIN_DAYS = 3


def days_until_due(node, now=None):
    """Whole calendar days from today to the due date (negative if past),
    ``None`` if undated. The due date is read in its own time zone, so a
    deadline of "Oct 16, 11:59 PM PT" is Oct 16, not Oct 17."""
    attrs = node.get("attrs", {}) or {}
    due = _parse_iso(attrs.get("due") or attrs.get("due_on"))
    if due is None:
        return None
    return (due.date() - _utcnow(now).date()).days


def effective_priority(node, now=None):
    """The priority to show and rank by today.

    An item extracted three weeks before its deadline is rightly medium then
    and wrongly medium the week it is due: the stored value is a snapshot.
    This keeps the stored value as the floor and applies H1 on top: overdue
    or due within HIGH_WITHIN_DAYS calendar days is high. A priority the user
    set by hand (``attrs.priority_source == "user"``) is never overridden.
    """
    attrs = node.get("attrs", {}) or {}
    stored = str(attrs.get("priority") or "").strip().lower()
    if stored not in PRIORITY_LEVELS:
        stored = "medium"
    if attrs.get("priority_source") == "user":
        return stored
    days = days_until_due(node, now=now)
    if days is not None and days <= HIGH_WITHIN_DAYS:
        return "high"
    return stored


# Ranking: how urgent a task is today, not just how late it is. A task 74
# days overdue that nobody has mentioned since July is not today's top item;
# one due tomorrow, or one someone chased yesterday, is.
STALE_OVERDUE_DAYS = 14     # this late, and
STALE_QUIET_DAYS = 14       # nothing heard for this long: gone quiet
STALE_UNKNOWN_DAYS = 30     # with no activity date, this late is gone quiet
RECENT_ACTIVITY_DAYS = 2    # mentioned this recently: surfaces near the top


def is_gone_quiet(node, now=None):
    """Long overdue and gone quiet: probably dropped, worth one "still
    needed?" check rather than the top of the list. A priority the user set
    by hand keeps a task out of this group."""
    attrs = node.get("attrs", {}) or {}
    if attrs.get("priority_source") == "user":
        return False
    days = due_days(node, now=now)
    if days is None or days >= -STALE_OVERDUE_DAYS:
        return False
    quiet = activity_days(node, now=now)
    if quiet is None:
        return days < -STALE_UNKNOWN_DAYS
    return quiet > STALE_QUIET_DAYS


def rank_key(node, now=None):
    """Sort key for the to-do list, most urgent first.

    0. Now: due within HIGH_WITHIN_DAYS or recently late (not gone quiet), or
       anything mentioned in the last RECENT_ACTIVITY_DAYS. Higher priority
       first, then closest to its deadline on either side, with a fresh
       mention counting as three days closer.
    1. Coming up: due within two weeks, or undated and high.
    2. Later: everything else open, by deadline then priority.
    3. Gone quiet: long overdue with no recent activity, most recently
       active first.
    """
    # within an urgency group, what matters (importance) comes first
    pri = PRIORITY_LEVELS.index(importance(node, now=now))
    days = days_until_due(node, now=now)     # calendar days, as rule H1 counts
    quiet = activity_days(node, now=now)
    name = node.get("name", node.get("id", ""))
    if is_gone_quiet(node, now=now):
        return (3, quiet if quiet is not None else 1e9, pri, name)
    recent = quiet is not None and quiet <= RECENT_ACTIVITY_DAYS
    if (days is not None and days <= HIGH_WITHIN_DAYS) or recent:
        # nearest to its deadline first, whichever side of it: due today and
        # just missed outrank two weeks late; a fresh mention counts as 3 days
        closeness = abs(days) if days is not None else HIGH_WITHIN_DAYS
        if recent:
            closeness -= HIGH_WITHIN_DAYS
        return (0, pri, closeness, days if days is not None else 1e6, name)
    if (days is not None and days <= 14) or (days is None and pri == 0):
        return (1, days if days is not None else 1e6, pri, name)
    return (2, days if days is not None else 1e6, pri, name)


def importance(node, now=None):
    """The priority to *show*: how much a task matters, apart from when it is due.

    The research rules mark anything overdue or due within HIGH_WITHIN_DAYS
    as high (rule H1), so a stored "high" is often only the due date said
    twice, and on a busy list nearly everything turns high. The date column
    and the ranking already carry urgency, so the label carries importance:

    - a priority the user set by hand is shown as set;
    - a stored "high" counts only when the deadline was more than
      HIGH_WITHIN_DAYS away when it was recorded (or there was none), so
      the date cannot have been the reason: a manager or a client asked,
      security work, "ASAP";
    - a date-driven "high" shows as "medium"; medium and low show as stored.

    When research recorded ``attrs.importance`` (with a reason), that wins
    over the stored-priority inference. ``effective_priority`` (stored + H1)
    stays what ranking and the evals use.
    """
    attrs = node.get("attrs", {}) or {}
    stored = str(attrs.get("priority") or "").strip().lower()
    if stored not in PRIORITY_LEVELS:
        stored = "medium"
    if attrs.get("priority_source") == "user":
        return stored
    # research records importance itself when it can (attrs.importance)
    imp = str(attrs.get("importance") or "").strip().lower()
    if imp in PRIORITY_LEVELS:
        return imp
    if stored != "high":
        return stored
    due = _parse_iso(attrs.get("due") or attrs.get("due_on"))
    if due is None:
        return "high"
    seen = _parse_iso(node.get("last_seen") or node.get("first_seen")) or _utcnow(now)
    return "high" if (due.date() - seen.date()).days > HIGH_WITHIN_DAYS else "medium"


def is_overdue(node, now=None):
    """True if this obligation had a deadline and it has passed."""
    days = due_days(node, now=now)
    return days is not None and days < 0


def is_open_action(node, now=None):
    """True if ``node`` is an obligation the user still has to act on.

    Open means: it is an Action, nothing has declared it finished, and it is
    otherwise current. Note the deliberate asymmetry with ``is_overdue`` — a
    missed deadline makes an action *more* urgent, never less, so an overdue
    action stays open until something says it was actually done.
    """
    if node.get("type") != "Action":
        return False
    status = (node.get("attrs", {}) or {}).get("status")
    if isinstance(status, str) and _norm_status(status) in DONE_STATUSES:
        return False
    return is_current(node, now=now)


# ---------------------------------------------------------------------------
# Internal file + merge helpers
# ---------------------------------------------------------------------------

def _read_jsonl(path, key_field):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # tolerate a corrupt line rather than lose the file
            k = obj.get(key_field)
            if k:
                out[k] = obj
    return out


def _private_open(tmp):
    """Graph files hold account content: readable by the owner only."""
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    return os.fdopen(fd, "w", encoding="utf-8")


def _write_jsonl(path, objects):
    tmp = path + ".tmp"
    with _private_open(tmp) as f:
        for obj in objects:
            f.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _write_text(path, text):
    tmp = path + ".tmp"
    with _private_open(tmp) as f:
        f.write(text)
    os.replace(tmp, path)


def _merge_attrs(base, incoming):
    """Shallow-merge attrs: incoming non-empty values win; keep existing else.

    Empty values never erase (a partial record must not wipe what another
    module knew), so removal is explicit: ``clear_attrs: ["blocked_on",
    "due"]`` deletes those keys. Without it a waiting-on that ended, or a
    deadline that was withdrawn, could never leave the node (found by the
    long-run eval, evals/longrun/CORRECTIONS.md #4)."""
    incoming = dict(incoming or {})
    clear = incoming.pop("clear_attrs", None) or []
    out = dict(base or {})
    for k in clear if isinstance(clear, list) else []:
        out.pop(str(k), None)
    for k, v in incoming.items():
        if v is None or v == "":
            out.setdefault(k, v)
        else:
            out[k] = v
    return out


def _merge_sources(base, incoming):
    """Union of comma-separated source tags, order-stable."""
    seen = []
    for part in list(_split_sources(base)) + list(_split_sources(incoming)):
        if part and part not in seen:
            seen.append(part)
    return ", ".join(seen)


def _split_sources(s):
    if not s:
        return []
    return [p.strip() for p in str(s).split(",") if p.strip()]


def _match_where(node, where):
    if callable(where):
        return bool(where(node))
    for k, v in where.items():
        if k in node:
            if node.get(k) != v:
                return False
        elif node.get("attrs", {}).get(k) != v:
            return False
    return True


# ---------------------------------------------------------------------------
# CLI: render views / print stats for a graph dir (handy for debugging + poll)
# ---------------------------------------------------------------------------

def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="AI OS knowledge graph tool")
    ap.add_argument("graph_dir", help="path to the graph/ directory")
    ap.add_argument("--render", action="store_true",
                    help="regenerate views/*.md")
    ap.add_argument("--stats", action="store_true", help="print node/edge counts")
    ap.add_argument("--stale", action="store_true", help="list stale nodes")
    args = ap.parse_args(argv)

    with transaction(args.graph_dir):
        g = Graph.load(args.graph_dir)
        paths = g.render_views(args.graph_dir) if args.render else []
    if args.render:
        print("rendered %d view(s)" % len(paths))
    if args.stats or not (args.render or args.stale):
        print("nodes=%d edges=%d" % (len(g.nodes), len(g.edges)))
    if args.stale:
        for n in g.stale_nodes():
            print("STALE %s (%s)" % (n["id"], n.get("last_verified")))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
