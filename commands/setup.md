---
description: One-time (and re-runnable) setup for a Chief-of-Staff deployment from this template — discovers connectors, researches the user's role, generates agents + dashboard config, and registers local polling.
---

# `/setup`

Arguments: $ARGUMENTS — optional. `--dry-run` to produce a plan and show every file that would
be written/changed without writing anything. `--reconfigure` to skip connector discovery and
role research (Steps 1–2) and re-run Steps 3–7 against the existing `dashboard/config.json` —
useful after manually editing config.json, or after a connector's tool names changed, without
re-asking the user everything from scratch.

You run in the main session. Read `../PLAN.md` and `../agents/README.md` first — they contain
the design rationale and the per-role judgment this command applies; don't duplicate that
reasoning here, just execute it.

## Step 0 — collision safety check (do this before anything else)

If `dashboard/.setup-complete` already exists, this is a re-run of *this deployment's own*
prior setup, not a foreign collision — skip the rest of this step. If `--reconfigure` was
passed, skip straight to Step 3 (using the existing `dashboard/config.json` in place of
Step 1/2's discovery+answers); otherwise continue to Step 1 as normal.

Otherwise, check for signs of an existing, unrelated CoS deployment already using the global
directories this command writes to:
- Any file matching `~/.claude/agents/global/cos-*.md`
- Any file matching `~/.claude/commands/global/cos-*.md`
- An existing `~/.claude/cos/` directory

If any of these exist, **stop and tell the user explicitly**: name what you found, explain
that `/setup` writes to these same shared locations and would overwrite an existing deployment,
and ask how they want to proceed — options: (a) they confirm this IS meant to replace/refresh
that deployment, (b) they want a different, non-colliding name prefix for this deployment's
commands/agents instead of `cos-*`, or (c) they abort. Never guess and never silently
overwrite. If none of these exist, continue.

## Step 1 — discover connectors

Enumerate the MCP tools already surfaced to you at session start. Supplement with `ToolSearch`
for common categories you might not see listed by default: messaging (Slack-equivalent),
ticketing (Jira/Linear/Asana-equivalent), calendar, email, code hosting (GitHub-equivalent),
meetings/recordings (Zoom-equivalent), docs/wiki, enterprise search. Build a table: category →
concrete tool names found (or "none found"). Show this table to the user before continuing —
they may know about a connector that didn't surface automatically (e.g. it needs
authentication first).

## Step 2 — ask what can't be inferred

Connector names reveal *what tools exist*, never *what the user's actual job is*. Ask directly,
in one message, not a long form:
1. "What's your core job/domain — the thing you'd want a dedicated specialist investigating
   first, above general ticket/chat triage?" (this becomes `cos-domain` + `domain_tag`)
2. For each ambiguous connector-to-role mapping from Step 1 (e.g. two ticketing systems found,
   or a messaging tool with both a `send` and a `send_draft`-shaped tool), ask which one is the
   "real" one for this role.
3. Whether any messaging/send-capable connector is known to be blocked by an org policy on
   real sends (if the user doesn't know, default `action_tools` for that role to a draft-
   creating tool if one exists, real-send otherwise — see `lessons-learned.md`'s worked
   example).
4. Whether there are categories of action this user never wants done autonomously (common
   defaults to offer: deploy to prod, merge code, delete data, close incidents, change
   permissions, contact external users/customers, legal/financial/employment/security/policy
   decisions, impersonation without disclosure — the same list the hand-built version of this
   system used). This becomes `<workspace>/APPROVAL_POLICY.md`, which the ported orchestration
   commands already know to check (see Step 5.2) — without it, those commands fall back to
   judgment alone, which is weaker than an explicit list the user actually reviewed.

Then run a research pass modeled on general onboarding: search available docs/wiki/enterprise-
search connectors for the user's role, team, and current priorities, to fill in context the
agents will need (not to second-guess their answer to question 1).

## Step 3 — decide which agents to generate

Apply `../agents/README.md`'s judgment table: "Always generate" unconditionally; "Generate
when the matching connector exists" per Step 1's table; "Generate exactly one" for
`cos-domain`, using Step 2's answer. Show the user the resulting list (role name + one-line
why) before writing anything.

## Step 4 — generate agent files

For each agent decided in Step 3, write `~/.claude/agents/global/<name>.md` following the
frontmatter/structure convention `agents/README.md` describes (name, description, model,
tools: list; body: Mission, Operating rules, Inputs, Output format incl. `Memory update:`,
Memory scope, Approval rules, Error handling). Use the exact discovered tool names from Step 1
for the `tools:` frontmatter — never invent a tool name.

## Step 5 — generate dashboard config + copy commands

1. Write `dashboard/config.json` (in this template's own `dashboard/` dir — keep the
   deployment self-contained inside this project folder, per `PLAN.md`'s ground rule, unless
   the user explicitly asks for the workspace to live elsewhere) using the schema in
   `dashboard/config.example.json`:
   - `ticket_host`/`ticket_system_name` from Step 1's ticketing connector.
   - `action_tools` — keyed by the **canonical `action_type` strings** the dashboard already
     knows how to render: `message_send`, `ticket_update`, `calendar_change` (extend only if a
     genuinely new action shape is needed, and update `server.py`'s `ICONS`/`compute_tags` to
     match — don't invent a new key the dashboard can't render). Values from Step 2's answers.
   - `domain_tag`/`domain_keywords`/`domain_url_keywords` from Step 2's core-job answer plus a
     couple of research passes for the domain's actual terminology (queue names, product
     names, internal tool URLs — whatever's realistic to pattern-match on later).
   - `chat_tools`/`revise_tools`/`poll_tools`/`base_tools` — **each of these is used standalone
     as a subprocess's entire `--allowedTools` grant (see `server.py`), not merged with
     anything else at runtime.** Each one MUST start with the baseline that role's subprocess
     needs to function at all — `chat_tools` needs at minimum `Read,Agent` (the chat panel
     dispatches specialist agents via the Agent tool, same as `/cos`); `revise_tools`/
     `poll_tools`/`base_tools` need at minimum `Read,Edit,Agent` (they operate on local
     workspace files directly in addition to dispatching agents) — THEN append the specific
     read-only MCP tool names each role's agents need for their own research (e.g. ticket
     search/get, chat search/read-thread, calendar list/search). Forgetting the baseline
     produces a subprocess that can't even call another agent — a silent, hard-to-diagnose
     failure, not a crash.
2. Write `<workspace>/APPROVAL_POLICY.md` if Step 2's question 4 produced any never-autonomous
   categories — plain markdown list, one line per category. `/cos`, `/cos-approve`, and
   `/cos-approve-confirmed` already look for this exact filename.
3. Copy `commands/{cos,cos-approve,cos-approve-confirmed,cos-revise,cos-poll,cos-process-inbox}.md`
   into `~/.claude/commands/global/` verbatim (they're already generic — no per-deployment
   edits needed).

## Step 6 — register local polling

1. Write `dashboard/poll-config.json`: one entry per fast-check connector from Step 1 (interval
   in minutes, days, start/end time — default to weekdays 07:00–19:00 unless the user says
   otherwise) plus `"timezone"`.
2. Register `dashboard/poll-tick.sh` with a local scheduler (launchd on macOS, cron elsewhere).
   **Known lesson: a scheduler's minimal environment often lacks the `claude` binary's install
   directory on `PATH`** — explicitly set `CLAUDE_BIN` to the resolved absolute path of the
   `claude` binary (find it, e.g. `which claude`) in whatever environment block the scheduler
   config supports, rather than relying on inherited `PATH`.
3. Tell the user exactly what was registered and how to check/undo it (the literal
   launchd/cron command), and remind them `dashboard/serve.sh` is still run manually, not
   auto-started.

## Step 7 — summarize and record

Show the user: agents generated, config.json contents (redact nothing — it's their own file),
polling registered, and any connector from Step 1 that was found but not wired into any role
(so nothing silently vanishes). If anything in Steps 1–6 hit a real blocker (a connector
exists but calls fail, an ambiguous mapping had to be guessed), append it to
`../lessons-learned.md` now, even as a single occurrence — don't wait for it to recur.

Write `dashboard/.setup-complete` (just a timestamp is fine) once everything above succeeded.
This is what the Notes section below needs to tell a re-run "this is my own prior setup," not
a foreign collision — without writing it here, Step 0 would treat every re-run as colliding
with an unrelated deployment.

## Notes

- `--dry-run`: perform Steps 0–3 for real (they're read-only/advisory) but for Steps 4–6, show
  the exact file contents/commands that would be written/run instead of writing/running them.
- Re-running `/setup` later with neither flag re-runs full discovery — connectors change over
  time — and Step 0's marker-file check (above) keeps that safe on the deployment's own repeat
  runs.

## V2 addendum — research-first agent generation (see `../ROADMAP-V2.md`)

When the V2 modules are present, `/setup` runs discovery *by research*, not by questionnaire:

1. After Step 1 (connector discovery), run **`/cos-research --full`** to populate the knowledge
   graph from the connectors (read-only). This replaces most of what Step 2 used to *ask* — the
   user's projects, systems, channels, tickets, and workspaces are discovered, not typed.
2. In Step 3, decide agents with **`factory.propose_agents(graph)`** (`../dashboard/factory.py`)
   instead of the connector-only role table. Show the proposal list — each with its mission,
   evidence, and justification — and generate only what the user approves.
3. In Step 4, write each approved agent with **`factory.render_agent_md(spec)`**, substituting the
   exact fully-qualified MCP tool names for the tool categories the spec names. The Step 0
   collision check and the "no mutating tool on any specialist" rule still apply unchanged.
4. Ask the user only the **residual** questions research couldn't answer (ambiguous workspace
   kinds — see `/cos-research` Step 4 — and the never-autonomous approval categories for
   `APPROVAL_POLICY.md`).

**Fallback:** if the graph is empty (no connectors reachable, or research skipped),
`factory.propose_agents` returns the V1 connector-gated role set, so `/setup` behaves exactly as
before. This addendum is additive — a pre-V2 deployment that never runs `/cos-research` is
unaffected.
