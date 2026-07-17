# AI OS — Chief-of-Staff Agent System

An installable, self-contained AI operating layer for your work. Open this folder in Claude
Code, run `/setup`, and it feels like hiring a chief of staff on day one:

1. **Give it context (optional).** On first launch the dashboard asks — paste text or attach
   files (md/txt/pdf/docx: resume, project docs, notes). Skip if you'd rather it figure things
   out itself.
2. **It researches you.** `/cos-research` crawls your connected accounts **read-only** — email,
   messages, tickets, calendar, docs, repos, local projects — and builds a **knowledge graph**
   (every fact with source, confidence, freshness; deduped by construction).
3. **It discovers your workspaces.** Employer, freelance clients, personal projects, job
   search, school — each isolated; confidential info never crosses a boundary.
4. **It creates only the agents your work justifies.** A Salesforce cluster earns a Salesforce
   investigator; job-search entities earn a Job Search agent; personal repos earn a Project
   Builder — each with a full spec (mission → confidence requirements) and read/draft-only
   tools.
5. **It populates the dashboard.** Daily Priorities, People Waiting, Blocked Work,
   Investigations, Projects, Meetings, Job Applications — plus scattered Slack/ticket/meeting/
   PR activity correlated into single **workstreams**.
6. **It keeps learning forever.** Polling re-researches changed sources; tell the chat
   "you're missing the email from X" and the **self-learning loop** fetches it, reasons about
   *why* it was missed, fixes the cause (config, instructions, or its own code — test-gated
   with automatic rollback), and records the lesson.

**The line it never crosses:** agents read, research, analyze, and draft autonomously — but
every external action (send, post, ticket change, calendar change, merge, deploy) goes to an
**approval queue** for you. The only thing the system ever asks unprompted is connector
authorization, via a dashboard popup you can refuse permanently.

## Quick start

1. Open this folder in Claude Code and run `/setup` (see `commands/setup.md`).
2. `./dashboard/serve.sh` → dashboard at `http://127.0.0.1:8765` (needs Python ≥ 3.12 and the
   `claude` CLI — set `CLAUDE_BIN` if it's not on PATH).
3. On the dashboard: add context (or skip) → **Research my workspace now** → watch the
   Command Center fill in.
4. Use `/cos "<request>"` for anything ad hoc; **Poll now** for a full sweep of every
   connector; the chat bubble for questions and corrections.

Multiple accounts (two Gmails, work + personal Slack)? Add the connector again as a second
named instance in Claude's connector settings — the system detects it, probes who it's logged
in as, binds it to the right workspace, and scopes agents so a work agent physically cannot
read personal email. See the Accounts & connections panel.

## Where things live

- **[PLAN.md](./PLAN.md)** — V1 design, ground rules, config schema.
- **[ROADMAP-V2.md](./ROADMAP-V2.md)** — the V2 architecture (research engine, knowledge
  graph, agent factory, workspaces, correlation, self-learning, accounts) and build status.
- **[lessons-learned.md](./lessons-learned.md)** — append-only log of real failures and fixes.
- `dashboard/` — server + the V2 engine modules (`graph.py`, `research.py`, `workspaces.py`,
  `factory.py`, `correlate.py`, `sections.py`, `learning.py`, `accounts.py`,
  `context_intake.py`) and their tests (`dashboard/tests/`, stdlib unittest).
- `commands/` — the ten `/cos-*` orchestration commands `/setup` installs.
- `agents/README.md` — the judgment the agent factory applies.

This folder has no relationship to any other CoS deployment on this machine — see PLAN.md's
"Ground rule: total self-containment." To remove a deployment cleanly: `/cos-uninstall`.
