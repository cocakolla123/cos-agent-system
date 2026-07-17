---
description: Research the user's work across all connectors and populate the knowledge graph (read-only)
argument-hint: "[--scope=<connector>] [--incremental] [--full]"
---

# /cos-research — Workspace Research Engine

Discover what the user actually works on — employers, freelance clients, personal projects, job
search, school, startups, repositories, channels, tickets, meetings, PRs, deployments, docs,
owners, incidents, decisions — **by reading connectors, not by asking**. Everything discovered is
written into the file-based knowledge graph (`dashboard/graph.py`) as nodes + edges, each with a
**source, confidence, and freshness**. This is the engine that replaces static setup questions:
`/setup` calls it, and `/cos-poll` calls it incrementally forever (see `commands/cos-poll.md`).

**Hard rules (same posture as every other cos command):**
- **Read-only against connectors.** Discovery only ever *reads/searches*. The only writes are to
  the graph store under `<workspace>/graph/` and workspace files via `cos-knowledge`. Never send,
  post, transition, merge, create, or modify anything external.
- **Never duplicate.** All graph writes go through `graph.py`'s upsert (stable id
  `<workspace>:<type>:<natural-key>`), so re-running only refreshes freshness/confidence.
- **Never re-ask what's already known.** Before asking the user anything, check the existing graph.
- **Ask only what can't be inferred** (workspace kind/label when ambiguous — see Step 4).

## Arguments
- `--full` (default) — crawl every discovered connector category.
- `--scope=<connector>` — restrict to one category (e.g. `--scope=ticketing`). Used by
  `/cos-poll` for cheap per-connector ticks.
- `--incremental` — only look at sources changed since the last run (read the newest
  `last_verified` in the graph as the watermark). Cheapest mode; the default for polling.

## Step 0 — Connector auth preflight
For each connector category you intend to crawl, make **one** cheap read-only probe (e.g. a
1-item search). Collect the outcomes as `{connector, ok, error}` and pass them through
`preflight.summarize(results)` (`dashboard/preflight.py`) to get an available/unavailable split
and a one-line report. If a category is `unavailable` (auth/permission failure or outage),
**continue with what's reachable** (`preflight.should_continue` is true as long as one connector
works) — never treat a connector outage as "no results." Report the unavailable set at the end so
the user can `/mcp` re-auth.

## Step 1 — Run the discovery modules
Dispatch the modules for the in-scope categories. Each module **reads** its connector and emits
**normalized records** (the exact dict shape `research.record(...)` builds — see
`dashboard/research.py`'s docstring): `{kind, workspace, key, name, attrs, source, confidence,
edges[]}`. Emit a provisional `workspace` and, where you can, an `attrs.org` signal (employer /
client / school domain) — Step 4 uses it to cluster.

| Module (category) | Reads | Emits (node kinds → edges) |
|---|---|---|
| **code hosting** | repos, PRs, orgs, deployments | Repository, PR, Deployment · `authored_by`, `belongs_to`, `deploys` |
| **ticketing / incidents** | tickets, boards, owners, incidents | Ticket, Incident, Person · `owned_by`, `assigned_to`, `relates_to` |
| **messaging** | channels, active threads, people | Channel, Person · `member_of`, `participates_in` |
| **calendar + meetings** | meetings, attendees, recordings | Meeting, Person · `attends`, `recorded_at` |
| **docs / wiki + enterprise search** | documents, decisions | Document, Decision · `authored_by`, `documents` |
| **local filesystem / projects** | local repos, project folders | Project, Repository · `contains` |

Keep result sets summarized/paginated — do **not** dump thousands of rows; take the most recent /
most active N per connector and record counts in `attrs` (e.g. `attrs.total=1240`).

## Step 2 — Persist to the graph
Write the records into the graph via `research.ingest(graph, records)` (see `research.py`). Because
upsert dedups by stable id, this is safe to run repeatedly. Concretely: assemble the records as
JSON and apply them with the graph library (Read/Edit/Bash on `dashboard/graph.py` + the graph
dir), or hand the batch to `cos-knowledge` to persist. Then regenerate the markdown views
(`python3 dashboard/graph.py <graph-dir> --render`).

## Step 3 — Correlate (if M5 is present)
If `dashboard/correlate.py` exists, run the correlation pass so related items collapse into
`Objective` (workstream) nodes. Otherwise skip.

## Step 4 — Infer workspaces, ask only the residual
Run `research.infer_workspaces(records)` to cluster everything into candidate workspaces. For each
proposal whose `kind` is unambiguous (single strong signal), adopt it silently. For proposals that
are ambiguous or `kind: unknown`, **ask the user one short question** ("Is *Acme* your employer,
a freelance client, or something else?") — and nothing else. Persist confirmed workspaces with
`research.workspace_records(proposals)` → `ingest`.

## Step 5 — Report
Summarize: nodes/edges added or refreshed, workspaces discovered (with kind), any connectors that
were unavailable, and any residual questions asked. Forward a one-line `Memory update:` to
`cos-knowledge`. **Nothing external was sent or modified** — say so explicitly.
