# AI OS — Version 2 Roadmap

> Companion to `PLAN.md`. `PLAN.md` describes V1 (built and verified). This file is the V2
> architecture review and roadmap: what V2 adds, why, and in what order. Treat it as the prompt
> for V2 work — read it before building, and update it every time a real lesson is learned.

## Context

V1 (this `template/`) is a working, self-contained Chief-of-Staff system: a user runs `/setup`,
gets connector discovery, a dashboard, generated agents, an approval queue, and local polling.
Everything is file-based (markdown + JSON), Python stdlib only, every default path inside
`template/`.

V2's goal is to make AI OS feel like **hiring** a chief of staff rather than **configuring** one:

1. Research the user automatically (don't ask what can be discovered).
2. Turn what's discovered into a continuously-updated **knowledge graph**.
3. Create only the **agents the discovered workspace justifies**.
4. Support **multiple isolated workspaces**.
5. **Correlate** scattered Slack/Jira/docs/meetings/PRs into single workstreams.
6. **Populate the existing dashboard** — do not redesign it.
7. **Keep learning forever.**

Approval boundaries are unchanged: agents read/research/draft/recommend autonomously; every
external action still queues for human approval.

**Non-goals:** redesigning/replacing the dashboard; rewriting working systems; adding runtime
dependencies; breaking self-containment. Prefer incremental, backward-compatible additions.

---

## Part 1 — Repository Review (V1 as-is)

### Current architecture

```
/setup → generates: ~/.claude/agents/global/cos-*.md (read/draft-only specialists),
                     ~/.claude/commands/global/cos-*.md (6 orchestration commands),
                     dashboard/config.json, <workspace>/APPROVAL_POLICY.md

/cos → ORCHESTRATOR (main session): classify → route to specialists (Agent tool) →
       specialists draft only, return text + "Memory update:" → cos-knowledge is sole
       file writer → cos-risk-quality gates approval-category output → append proposed
       actions to approval-queue.md → NEVER executes.

dashboard/server.py (stdlib HTTP, 127.0.0.1:8765): renders approval-queue (pending/drafted/
       failed/archived), daily log, meetings, open questions, inbox, polling, chat. Buttons
       shell to /cos-approve-confirmed, /cos-revise, /cos-poll.

poll-tick.sh (launchd/cron, ~60s): → /cos-poll --scope=<due> re-checks pending entries,
       priority reassessment, style-feedback, meeting notes, recurring-failure detection.
```

State is all files under `dashboard/workspace/`. Zero runtime deps.

### Strengths
- Approval gating airtight by construction (no specialist holds a mutating tool; only
  `/cos-approve*` execute, verbatim; `APPROVAL_POLICY.md` hard-stops).
- Genuinely config-driven & self-contained (no brand strings; safe zero-config defaults).
- Honest multi-agent design (true subagents, orchestrator-only fan-out, single-writer memory).
- File state is git-friendly, diffable, agent-writable, crash-simple.
- Local polling is an honest persistence story that sidesteps unverified cloud-routine reach.
- Closed-loop personality learning already exists (edit diffs → style profile).

### Weaknesses
- Setup is a questionnaire, not research — infers little from real work history.
- Agents are role-templates gated by connector presence, not justified by workspace content.
- No knowledge model — state scattered, no entities/relationships/source/confidence/freshness.
- Single implicit workspace; no confidential isolation (employer vs. freelance).
- Dashboard is queue-centric, not a command center.
- No live updates — full re-parse per GET.

### Technical debt
- Regex-fragile markdown block parsing; `proposed_tool_call` stored as prose then re-parsed.
- Canonical `action_type`s hardcoded in `server.py` (`ICONS`, `compute_tags`).
- `APPROVAL_POLICY.md` is prose — matching is judgment, not schema.
- Tool-grant baselines hand-maintained (silent failure if omitted).
- `poll-last-run.json` written before subprocess (timeout looks like success).
- Approval queue/archive grow unbounded; no separate append-only audit log.
- No config validator (invalid JSON silently falls back to defaults).

### Unknown / underspecified
- `/setup` never run against a foreign connector set (Linear-not-Jira, Teams-not-Slack).
- Cloud-routine reach unverified.
- Fuzzy heuristics without spec (poll escalation, priority thresholds, failure signatures,
  domain-keyword breadth).
- Multi-ticketing / multi-messaging is single-valued in config.

### Potential improvements → V2 building blocks
Knowledge graph (source/confidence/freshness, dedup); research engine; dynamic agent factory;
multi-workspace; workstream correlation; graph-powered dashboard sections; debt fixes (config
validator, action-type registry, audit log, connector auth preflight).

---

## Part 2 — V1 vs. V2 (gap analysis)

| Vision capability | V1 today | V2 gap |
|---|---|---|
| Automatic research | `/setup` asks; infers little | New Research Engine crawling connectors |
| Knowledge graph | Scattered files | New file-based graph store + library |
| Only justified agents | Fixed roles gated by connector | Factory driven by graph evidence |
| Multiple isolated workspaces | Single implicit | Registry + tagging + isolation |
| Workstream correlation | Items shown separately | Correlation pass + Objective nodes |
| Auto-populate dashboard | Queue-centric | Graph-powered sections (preserve UI) |
| Continuous learning | Poll re-checks queue | Extend poll to research + graph |
| Approval gates | ✅ already true | Preserve; extend to agent/workspace changes |
| Rich agent spec | Partial | Extend agent template |

---

## Part 3 — V2 target architecture

```
CONNECTORS (read-only): code hosting · ticketing · messaging · calendar · email ·
                        docs/wiki · meetings · incidents · enterprise search · local FS
                                       │
                RESEARCH ENGINE (/cos-research + lib): discovery modules per connector
                        class emit entities + edges (read-only)
                                       │ upsert (dedup, confidence, freshness)
                KNOWLEDGE GRAPH (workspace/graph/): single source of truth
                        nodes: Workspace·Project·Repo·Channel·Ticket·Meeting·PR·Deploy·
                               Doc·Person·Incident·Decision·Objective(workstream)
                        every node: source·confidence·freshness   graph.py library
                          │                 │                    │
                 AGENT FACTORY       WORKSTREAM            DASHBOARD POPULATION
                 propose agents      CORRELATION           graph-powered sections
                 from graph          → Objective nodes     + existing queue/chat/poll
                          │
                 ORCHESTRATOR (/cos): routes to generated agents, still draft-only,
                          │           still queues every external action
                 APPROVAL QUEUE (unchanged)

CONTINUOUS LEARNING: /cos-poll re-runs incremental research on changed sources, refreshes
graph freshness/confidence, re-correlates, re-evaluates justified agents (proposes, never
auto-creates), refreshes dashboard sections. Never re-asks known facts.
```

**Invariants carried from V1:** file-only storage; Python stdlib only; every default path inside
`template/`; read/draft-only specialists; orchestrator-only execution; `APPROVAL_POLICY.md` hard
stops; collision-safe writes to `~/.claude/…/global/`; config-driven (no brand strings).

### Knowledge graph shape (file-based)
- `workspace/graph/nodes.jsonl` — `{id, type, workspace, name, attrs{}, source, confidence,
  first_seen, last_seen, last_verified}`.
- `workspace/graph/edges.jsonl` — `{from, to, type, source, confidence, last_seen}`.
- Stable `id` = `<workspace>:<type>:<natural-key>` → dedup by construction (upsert merges in
  place; freshness/confidence updated, never duplicated).
- `workspace/graph/views/*.md` — human-readable rendered views.
- `graph.py` — stdlib library: load / upsert_node / upsert_edge / query / neighbors / merge /
  render_view + confidence/freshness helpers. Reused by research, correlation, dashboard, poll.

### Multi-workspace
- `workspace/workspaces.json` registry: `{id, kind, label, connectors[], isolation}` where kind ∈
  employer | freelance | personal | job-search | school | startup | home | property | travel | …
- Every node/edge/agent/memory tagged with `workspace`; queries + dashboard filter by it.
- Isolation: no cross-workspace edges except an explicit, user-approved link; agents scoped to
  their workspace's nodes only. Never mix confidential info.

### Dynamic agent factory (v2)
- Input is the graph (not just connector presence): a Salesforce node cluster → Salesforce Agent;
  job-search entities → Job Search Agent; personal repos → Project Builder Agent; a domain
  incident/queue cluster → an Investigation Agent.
- Richer generated agent spec: **Mission · Responsibilities · Allowed tools · Forbidden tools ·
  Private memory · Shared memory · Approval policy · Escalation rules · Inputs · Outputs ·
  Confidence requirements.**
- Still writes to `~/.claude/agents/global/`, collision-safe, read/draft-only, proposals surfaced
  for approval before creation.

---

## Part 4 — Milestones

Ordered so each milestone is independently shippable and backward-compatible.

- **M1 — Knowledge graph foundation.** `graph.py` + schema + JSONL store + markdown views + tests.
  Additive; no behavior change.
- **M2 — Research engine.** `/cos-research` + per-connector discovery modules populating the graph
  (read-only). Incremental + full-crawl.
- **M3 — Multi-workspace model.** Registry + tagging across graph/agents/memory + isolation +
  dashboard workspace filter.
- **M4 — Dynamic agent factory v2.** Graph-evidence agent proposal + generation with the richer
  spec; `/setup` runs research first; connector-gated fallback preserved; approval-gated.
- **M5 — Workstream correlation.** Correlation pass + `Objective` nodes + dashboard timeline card.
- **M6 — Dashboard population.** Graph-powered sections (Daily Priorities, People Waiting, Blocked
  Work, Investigations, Projects, Meetings, Job Applications, Freelance, Personal Projects). Keep
  existing queue/chat/polling UI.
- **M7 — Continuous learning.** Extend `/cos-poll`: incremental research, freshness/confidence
  refresh, re-correlation, agent re-evaluation (propose only), dashboard refresh; optional live
  auto-refresh (SSE).
- **M8 — Hardening (folded in opportunistically).** Config validator, action-type registry,
  append-only audit log, connector auth preflight, graph query caching.

---

## Part 5 — Issue breakdown

Tracked as GitHub issues (labels `M1`…`M8`). Titles + acceptance criteria:

**M1 — Knowledge graph foundation**
1. graph: define node/edge schema + stable-id dedup
2. graph: implement graph.py library (stdlib)
3. graph: markdown views renderer (idempotent regen)
4. graph: freshness & confidence helpers (stale flagging)

**M2 — Research engine**
5. research: /cos-research command scaffold (full + incremental, read-only)
6. research: discovery module — code hosting (repos, PRs, orgs, deployments)
7. research: discovery module — ticketing (tickets, boards, owners, incidents)
8. research: discovery module — messaging (channels, threads, people)
9. research: discovery module — calendar + meetings
10. research: discovery module — docs/wiki + enterprise search
11. research: discovery module — local filesystem/projects
12. research: workspace inference (cluster entities; ask only what can't be inferred)

**M3 — Multi-workspace**
13. workspace: registry + workspaces.json schema
14. workspace: tag graph nodes/edges + query filtering
15. workspace: scope agents + memory per workspace; isolation rule
16. dashboard: workspace filter/switcher (additive)

**M4 — Dynamic agent factory v2**
17. factory: richer agent spec template
18. factory: graph-evidence → proposed agents mapping
19. factory: generate agents from proposals (collision-safe, draft-only, approval-gated)
20. setup: /setup runs research first, proposes agents; keep connector-gated fallback

**M5 — Workstream correlation**
21. correlate: correlation pass → Objective nodes
22. dashboard: Objective timeline card

**M6 — Dashboard population**
23. dashboard: Daily Priorities section
24. dashboard: People Waiting + Blocked Work sections
25. dashboard: Investigations + Projects sections
26. dashboard: Meetings + Job Applications + Freelance + Personal Projects sections

**M7 — Continuous learning**
27. poll: incremental research on changed sources → graph upsert
28. poll: freshness refresh + re-correlation + agent re-evaluation (propose only)
29. dashboard: optional live refresh (SSE/poll)

**M8 — Hardening**
30. debt: config validator (baseline tools, tool existence, JSON)
31. debt: action-type registry (config-driven, not hardcoded)
32. debt: append-only audit log separate from approval-queue
33. debt: connector auth preflight in /cos-research + /setup

---

## Verification (per milestone)
- Every milestone: dashboard still runs standalone with zero config (`server.py` py_compile +
  bind + serve one request); existing `/setup`, `/cos`, approval flow unchanged for a pre-V2
  config (backward-compat gate).
- M1: `graph.py` unit tests (upsert dedups by id; freshness/confidence update in place; views
  regen idempotent); zero third-party imports.
- M2: run `/cos-research`; graph nodes/edges written with real source/confidence/freshness; no
  duplicates on a second run.
- M3: two workspaces with overlapping people stay isolated; no cross-workspace edge without an
  explicit link.
- M4: on a seeded cluster the factory *proposes* an agent with full spec; nothing written to
  `~/.claude/agents/global/` without approval; collision check still fires.
- M5: a seeded thread+ticket+meeting+PR cluster collapses into one Objective card.
- M6: each section renders purely from graph queries; missing graph degrades to empty, not crash.
- M7: a changed source updates only affected nodes' freshness; new agents proposed, never
  auto-created; known facts not re-asked.
- Cross-cutting: grep the tree for brand/product strings before declaring a generalization done;
  no default path resolves outside `template/`.

## Status
- [x] **M0** — docs (this file + `PLAN.md` pointer + lessons entry) and the private repo
      `cocakolla123/cos-agent-system` created; 33 issues filed, labeled M1–M8.
- [x] **M1 — Knowledge graph foundation.** `dashboard/graph.py` (stdlib only): node/edge schema
      with stable-id dedup (`<workspace>:<type>:<natural-key>`), JSONL load/save (deterministic,
      sorted), `upsert_node`/`upsert_edge` (in-place merge; noisy-OR confidence; source union;
      freshness stamps), `query`/`neighbors`/`merge_nodes`, `is_stale`/`stale_nodes`, idempotent
      `render_views` (per-workspace + index markdown), and a small CLI (`--render/--stats/--stale`).
      Tests in `dashboard/tests/test_graph.py` (19 cases, stdlib `unittest`) — all pass on Python
      3.9 and 3.14. Additive: no existing behavior changed; dashboard still serves zero-config.
      Covers issues #1–#4. **Note:** the graph store lives under the (gitignored) workspace at
      `workspace/graph/`; it is created by the research engine in M2, not by M1.
- [ ] M2–M8 — not started

### Runtime note
`dashboard/server.py` requires **Python 3.12+** (an f-string with an embedded backslash). New V2
modules stay compatible with 3.9+ where practical. See `lessons-learned.md` (2026-07-16).
