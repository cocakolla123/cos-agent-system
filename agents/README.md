# Agent roles — judgment reference for `/setup`

`/setup` generates agent definition files into the deployer's own `~/.claude/agents/global/`
(never into this repo). This doc encodes the *judgment* behind which roles to generate, what
tools each needs, model choice, and what's explicitly denied — so that judgment is legible and
maintainable here, not baked invisibly into one long `setup.md`. Every role below is
draft-only/read-only by construction: **the only mutating tool grants in this entire system
live in `/cos-approve` and `/cos-approve-confirmed`, never in a specialist agent.**

## Always generate

- **`cos-knowledge`** — maintains shared workspace context (`decisions.md`,
  `open-questions.md`, project files). The only `cos-*` agent with a `Write` tool — every other
  specialist's `Memory update:` text gets applied here, and it's the only agent that may write
  to workspace files. Tools: `Read`, `Write`, `Glob`, `Grep`, plus any enterprise-search
  connector detected (e.g. Glean) and a couple of read-only lookups useful for cross-
  referencing (ticket-get, doc-search). Sonnet — this is bookkeeping, not judgment-heavy.
  **Hardened rule (real incident, 2026-07):** an earlier version of this agent once overwrote
  an entire architecture doc with a placeholder because a `Write` call had incomplete file
  context. Every generated `cos-knowledge` must include an explicit instruction: never `Write`
  a file without having just `Read` its current full content in the same turn, and never write
  outside the workspace dir.
- **`cos-risk-quality`** — gates any output classified as approval-required or never-
  autonomous (per `<workspace>/APPROVAL_POLICY.md`, if it exists). Not every internal draft —
  only the ones that matter. Read-only, zero writes. Opus (judgment-heavy, low volume).

## Generate when the matching connector exists

- **`cos-comms`** — triages/drafts responses to chat/email. Holds **no send tool at all** —
  drafts only. Generate when a messaging connector (Slack-equivalent) and/or an email
  connector is detected. Tools: read/search on whichever of those exist, plus enterprise
  search if available. Sonnet.
- **`cos-calendar`** — meeting prep and conflict analysis. Never creates/changes/responds to
  events itself — drafts only. Generate when a calendar connector is detected. Tools:
  calendar read/list/search/suggest-time, plus ticket-get and chat-read-thread for context.
  Sonnet.
- **`cos-meeting-notes`** — summarizes a just-ended meeting (transcript/recording-service
  summary when available), cross-references real workspace/ticket context, flags action
  items. Triggered by `/cos-poll` when a meeting connector reports a recent end — never
  scheduled on its own. Generate when both a calendar connector and a meetings/recordings
  connector (Zoom-equivalent) exist. Read-only. Sonnet.
- **`cos-ticket-triage`** — single-ticket prioritization ("what should I work on next, ticket
  by ticket"). Generate when a ticketing connector (Jira/Linear/Asana-equivalent) exists.
  Read-only. Sonnet. Include a "domain-related? yes/no" output field so `/cos` knows whether
  to also call `cos-domain`.
- **`cos-delivery-lead`** — portfolio/initiative-level status across multiple tickets, distinct
  from `cos-ticket-triage`'s single-ticket focus. Generate alongside ticket-triage when the
  deployer's role research (see `/setup` Step 2) suggests they track multiple concurrent
  initiatives, not just their own individual ticket queue. Read-only. Sonnet.
- **`cos-product-manager`** — problem framing, requirements, acceptance criteria. Generate
  when a ticketing connector plus a docs/wiki connector exist and the role research suggests
  product-adjacent responsibilities.
- **`cos-tech-lead`** — technical approach, implementation plan, risk assessment for technical
  tickets. Generate when a code-hosting connector (GitHub-equivalent) plus a ticketing
  connector exist and the role research suggests an engineering role. Flags when a design
  review is warranted rather than always escalating.
- **`cos-staff-engineer`** — on-demand design-review challenge to `cos-tech-lead`'s plan.
  Invoked only when tech-lead flags genuine uncertainty, never a default chain link. Opus
  (judgment-heavy). Generate only alongside `cos-tech-lead`.
- **`cos-code-review`** — reviews a diff/PR for bugs, risk, test gaps, maintainability.
  Generate when a code-hosting connector exists. Opus, read-only, draft-only — never posts
  comments, creates reviews, or merges.

## Generate exactly one, based on the user's actual core job

- **`cos-domain`** — the user's core-job specialist. This is the one role `/setup` cannot
  infer from connector names alone (see `/setup` Step 2 — ask directly). Its tool grant is
  whatever read-only/investigation tools exist for that domain's connector(s) (support/CCaaS
  platform, data pipeline, whatever it is) — **hold no mutation tool for that domain at all**,
  even if one exists in the connector's MCP surface, unless the user explicitly confirms they
  want autonomous mutation there (rare — default to withholding it). Its output should always
  include a "Background info" block formatted as short bullet lines (`- Situation: ...`,
  `- Root cause: ...`, `- Reference: ...`, `- Recommended fix: ...`, `- Link: ...`) for
  embedding into a `linked_domain` field on a dashboard entry — bullets render as a scannable
  list on the dashboard; prose renders as one dense block. Opus — this is the highest-priority
  specialist in the system since it's the user's actual job, same reasoning as investigation-
  heavy roles elsewhere. Name it `cos-domain` (not the literal domain name) so the
  orchestration commands (`cos.md`, `cos-poll.md`) never need per-deployment rewriting — the
  agent's own `description`/`tools` frontmatter is what's domain-specific, not its name or any
  command that calls it. Populate `dashboard/config.json`'s `domain_tag` with the human-
  readable name (e.g. "Salesforce Ops," "Zendesk") for display purposes only.

## Model choice, generally

Opus for: judgment calls with real consequences and low call volume (`cos-domain`,
`cos-risk-quality`, `cos-staff-engineer`, `cos-code-review`). Sonnet for: everything else —
higher call volume, more mechanical triage/summarization work.

## What every generated agent must include, regardless of role

- A `Memory update:` section at the end of every response.
- An explicit statement of what it does NOT hold (no send/write/mutate tool, unless it's
  literally `cos-knowledge`'s workspace-write or the domain specialist's rare explicit
  exception above).
- "If a connector is unavailable, say so explicitly and continue with what's reachable" — never
  silently guess at missing data.

## Known collision risk — read before running `/setup` on a machine with an existing deployment

`/setup` writes to `~/.claude/agents/global/`, `~/.claude/commands/global/`, and (by default)
`~/.claude/cos/` — the **same** directories any other CoS deployment on this machine already
uses. If a deployment already exists there (check for any existing `cos-*.md` file in either
global dir, or an existing `~/.claude/cos/` directory, before writing anything), `/setup` must
stop and ask rather than silently overwrite — this is a real risk on a machine that already
runs a hand-built or template-based CoS system, not just a theoretical one.

---

## V2 — Dynamic agent factory (see `../ROADMAP-V2.md`, `../dashboard/factory.py`)

V1 (above) generates a fixed role set gated by **connector presence**. V2 additionally proposes
agents justified by what the **knowledge graph** actually contains, via `dashboard/factory.py`:

- **Evidence-driven, not connector-driven.** A Salesforce node cluster → a Salesforce agent; a
  distinct external system (Salesforce, Zendesk, …) with tickets/incidents/deploys → an Investigation
  agent for it; job-search entities → a Job Search agent; personal repos/projects → a Project
  Builder agent. `factory.propose_agents(graph)` returns the list; when the graph is empty it
  falls back to the V1 connector-gated roles, so a brand-new deployment is unchanged.
- **Richer spec (every generated agent).** `Mission · Responsibilities · Allowed tools ·
  Forbidden tools · Private memory · Shared memory · Approval policy · Escalation rules · Inputs ·
  Outputs · Confidence requirements` — plus the evidence and justification for why it exists.
  `factory.render_agent_md(spec)` produces the file; `/setup` substitutes the exact
  fully-qualified MCP tool names for the tool *categories* the spec names.
- **Still read/draft-only, still collision-safe, still approval-gated.** Every proposed agent's
  `forbidden_tools` include the mutating verbs (send/post/merge/deploy/delete/…); the factory
  never writes agents itself — `/setup` presents the proposal list, checks for collisions (the
  Step 0 rule above still applies), and writes to `~/.claude/agents/global/` only after the user
  approves. Each agent is tagged with its `workspace` so its memory and graph view are isolated
  (see `../dashboard/workspaces.py`).

## V2.1 — Self-learning note (M9)

The self-learning loop (`../dashboard/learning.py` + `/cos-learn`) may modify this deployment's
own config, command prose, and code — but it can **never** change any agent's tool grants, the
approve commands, `APPROVAL_POLICY.md`, the audit log, or the guardrail logic itself
(`learning.is_change_allowed` hard-blocks those paths). A generated agent's read/draft-only
posture is not self-modifiable.

## V2.2 — Per-account agents (M10)

When `connector_accounts` defines multiple instances of a connector type (e.g. `gmail-personal`
+ `gmail-work`), `factory.propose_agents(..., accounts=...)` proposes **per-workspace comms
agents** (`cos-comms-<workspace>`) whose tool grants are drawn ONLY from that workspace's
instance namespaces (`tool_prefix`). Isolation is enforced at the tool-grant level — a work
agent physically holds no personal-account tool, and vice versa.
