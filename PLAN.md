# CoS Template — Build Plan

Living spec for `cos-system/template/`. Treat this file as the prompt: if you (or a future
Claude session) need to build, resume, or explain this project, read this file first — it
should be enough on its own, without needing the rest of this conversation. Update it every
time a real lesson is learned, not just when a task finishes.

## What this is

A self-contained, reusable Chief-of-Staff agent system. Someone opens this `template/` folder
(or a copy of it) in Claude Code, runs `/setup`, and gets: their available MCP connectors
discovered, a profile of their role built via research, a dashboard, and a set of generated
agents matched to whatever they actually have — without hand-building any of it.

## Version 2

This file (`PLAN.md`) is the V1 spec — built and verified (see Status below). **V2 is planned in
[`ROADMAP-V2.md`](./ROADMAP-V2.md)**: automatic research replacing static setup, a file-based
knowledge graph as the single source of truth, a graph-evidence-driven agent factory, multiple
isolated workspaces, workstream correlation, an auto-populated dashboard (the existing one — not
a redesign), and continuous learning. V2 preserves every V1 invariant: file-only storage, stdlib
only, every default path inside `template/`, read/draft-only specialists, orchestrator-only
execution, and approval-gating of every external action. Work is milestoned M1–M8 there and
tracked as GitHub issues in the standalone public-of-record repo `cos-agent-system`.

## Ground rule: total self-containment

**Nothing under `template/` reads or writes anything outside `template/` by default.** No
shared file, no shared config, no default path that happens to be `~/.claude/cos` or anything
else specific to Hemanth's own already-working setup. Hemanth's live system is a separate,
unrelated deployment — this project does not touch it, depend on it, or get pointed at it as
a side effect of being built. If someone (including Hemanth, later) wants to actually run on
this template, that's a distinct, explicit choice made at that time — never automatic.

Concretely: `dashboard/server.py` defaults `--config` to `template/dashboard/config.json` and
`--workspace` to `template/dashboard/workspace/` — both resolved relative to the file's own
location (`os.path.dirname(os.path.abspath(__file__))`), never a hardcoded home-dir path.

## Directory layout

```
template/
  PLAN.md              <- this file
  README.md            <- short pointer for a human opening the folder (not written yet)
  lessons-learned.md   <- append-only log of blockers/fixes discovered while running this,
                           surfaced by /setup and /cos-poll (not written yet)
  dashboard/
    server.py           <- the dashboard; config-driven, self-contained (done, see below)
    poll-tick.sh         <- launchd-invoked poll trigger, config-aware (copied, not yet edited)
    serve.sh             <- starts server.py (not written yet)
    config.example.json  <- documents the config.json schema with placeholder values (not written yet)
    workspace/            <- default runtime data dir (daily/, approval-queue.md, etc.) — gitignored
  commands/
    setup.md              <- the /setup command (not written yet) — the real work of this project
    cos.md, cos-approve.md, cos-approve-confirmed.md, cos-revise.md, cos-poll.md,
    cos-process-inbox.md  <- ported near-verbatim from ~/.claude/commands/global/, generalizing
                              the couple of Airbnb-specific references (e.g. "PLAN.md" ->
                              "your workspace's architecture doc") (not started)
  agents/
    README.md             <- documents the agent roles and the judgment /setup applies when
                              deciding which to generate and with what tools (not written yet)
```

Generated agent `.md` files themselves are NOT stored in `template/` — `/setup` writes them to
the deployer's own `~/.claude/agents/global/` at setup time, same as any other project.

## config.json schema

```json
{
  "workspace_dir": "absolute path, default <template>/dashboard/workspace",
  "orchestrator_cwd": "cwd to run `claude -p` subprocess calls from, default <template>'s parent dir",
  "ticket_host": "e.g. https://your-org.atlassian.net, or null if no ticketing system",
  "ticket_system_name": "display name, e.g. Jira / Linear / Asana",
  "action_tools": {"message_send": "<fully-qualified MCP tool name for the one real send/draft action>", "...": "keys are canonical action_type values: message_send | ticket_update | calendar_change"},
  "base_tools": "comma-separated tool grant for /cos-approve-confirmed's minimal subprocess",
  "chat_tools": "comma-separated tool grant for the dashboard's chat assistant",
  "revise_tools": "comma-separated tool grant for /cos-revise's subprocess",
  "poll_tools": "comma-separated tool grant for /cos-poll's subprocess",
  "domain_tag": "display name for the user's core-job specialist tag, e.g. 'Genesys'",
  "domain_keywords": ["keywords that mark an entry as domain-related, for tag + linked-context display"],
  "domain_url_keywords": ["substrings that mark a URL as belonging to the domain tool, e.g. 'mypurecloud'"]
}
```

A missing config.json is a valid state (defaults apply, dashboard runs with no executable
action types and no domain tag) — this is what lets `/setup` be run incrementally.

## What `/setup` needs to do

1. **Discover connectors.** Enumerate available MCP tools already surfaced to the model, plus
   targeted `ToolSearch` for common categories (messaging, ticketing, calendar, email,
   meetings, code review). Pattern-match into roles: comms, calendar, ticket-triage,
   code-review, meeting-notes, knowledge, risk-quality, plus whatever a domain specialist
   needs.
2. **Ask only what can't be inferred.** Connector names don't reveal the user's actual
   core job/domain — ask directly. Infer everything else (which tool fills the
   `message_send`-equivalent role, the ticket host, etc.) from what's discovered, modeled on
   `/cos-onboard`'s research pass.
3. **Generate agent files** into `~/.claude/agents/global/` (the deployer's own, not this
   repo), applying the same judgment used when hand-building Hemanth's 11 agents: which tools
   a role actually needs, opus vs. sonnet, what's explicitly denied (e.g. no agent should hold
   a raw "send"/"mutate" tool unless it's the one designated draft-only action).
4. **Generate config.json** for the shared dashboard schema above, and copy the 6
   orchestration commands into the deployer's own `~/.claude/commands/global/`.
5. **Record lessons as they're found, not just once.** When a real tool call fails
   (dashboard's existing `failed` status/`execution_result` mechanism) and the same failure
   recurs, `/cos-poll` should create one deduped inbox task suggesting the likely fix (e.g.
   "request org approval for this app's send scope") — capped by a dedup key, not one task per
   failure — and append the pattern to `lessons-learned.md` so it's visible even before it
   recurs enough to trigger a task.
6. **Register local polling** (`poll-tick.sh` + the deployer's own scheduler), parameterized
   the same way.

## Relationship to Hemanth's live system

None, by design (see Ground rule above). `~/.claude/cos/`, `~/.claude/agents/global/cos-*.md`,
and `~/.claude/commands/global/cos-*.md` on this machine are Hemanth's own hand-built,
already-working deployment — untouched by this project. If a fix made to Hemanth's live
system reflects a general lesson (not Hemanth-specific content), port that lesson into this
file or into `/setup`'s instructions by hand, deliberately — don't wire the two together so it
happens automatically. That coupling was considered and rejected: the earlier plan-mode draft
("one dashboard codebase, not two," pointing Hemanth's `serve.sh` at this template) was
rejected because it makes a fresh deployment's defaults depend on a specific other person's
directory conventions, which is the opposite of "self-contained."

## Lessons learned

- **2026-07-13** — First draft of `dashboard/server.py`'s config-loading defaulted
  `DASHBOARD_DIR`/workspace path to `~/.claude/cos/dashboard` (Hemanth's live path) as a
  fallback when no config.json/`--workspace` was given. Caught before it shipped. Fixed by
  resolving all defaults relative to the file's own location
  (`os.path.dirname(os.path.abspath(__file__))`). **Rule going forward: any default path in
  this template must resolve inside `template/`'s own directory tree — never a specific
  person's home-dir convention, even as a "reasonable" fallback.**

- **2026-07-13** — While writing `commands/setup.md`, realized `/setup` unavoidably writes to
  `~/.claude/agents/global/` and `~/.claude/commands/global/` — Claude Code only loads global
  agents/commands from those exact paths, so there's no way to keep *that* part self-contained
  the way the dashboard's workspace/config paths are. This is a real collision risk on any
  machine that already runs a `cos-*`-named deployment (hand-built or template-based). Fixed
  by adding an explicit Step 0 collision check to `setup.md` (stop and ask, never silently
  overwrite) and documenting the risk in `agents/README.md`. **Rule: anywhere this template
  must write to a shared/global location it can't avoid, check for pre-existing content first
  and require explicit confirmation before overwriting — self-containment applies to defaults,
  not to pretending shared OS-level locations don't exist.**

- **2026-07-13** — A coherence read-through of the ported command files against `server.py`
  found the dashboard was only *partially* config-driven: the header constants were fixed
  (Task 55), but three deeper chunks still had the original hardcoded Airbnb/Jira/Slack/
  Genesys values and silently ignored `config.json`: (1) a leftover duplicate `CHAT_TOOLS =`
  assignment lower in the file overwrote the config-driven one from the header entirely; (2)
  the `/revise` and `/poll-now` HTTP handlers had their own hardcoded `--allowedTools` lists,
  never wired to the `revise_tools`/`poll_tools` config keys those variables existed for; (3)
  the entire domain-tag/link-detection system (`GENESYS_URL_PATTERN`, `is_genesys_related`,
  the `linked_genesys` field name, `TAG_STYLE`) was 100% hardcoded to Genesys terminology,
  completely disconnected from the `domain_tag`/`domain_keywords`/`domain_url_keywords` config
  keys the schema already promised — and it used a *different* field name (`linked_genesys`)
  than what the ported orchestration commands were instructed to write (`linked_domain`), so
  even a correctly-configured deployment's domain background info would never have displayed.
  Also found: `CONNECTORS`/`CONNECTOR_LABELS` were a fixed `["slack","email","general"]` list
  in the dashboard's own poll-schedule UI, inconsistent with `poll-tick.sh`'s already-dynamic
  connector handling. **Rule: a config-driven rename at the top of a file proves nothing about
  the rest of the file — grep the whole file for the literal brand/product strings being
  removed (`grep -n "slack_send\|genesys\|Jira\|Hemanth"` etc.) before declaring a
  generalization pass done, since a file this size will have multiple independent hardcoded
  chunks that don't reference each other.** Fixed: removed the duplicate `CHAT_TOOLS`; wired
  `REVISE_TOOLS`/`POLL_TOOLS` into their handlers; renamed `linked_genesys` → `linked_domain`
  and rebuilt domain-detection patterns from config at module load (`_alternation_pattern`,
  matching nothing when the config lists are empty); renamed the `slack_send` action_type to
  the generic `message_send`; made tag rendering return `(label, css_class)` pairs so labels
  can be runtime config values (`TICKET_SYSTEM_NAME`, `DOMAIN_TAG`) instead of fixed strings;
  made `poll_connectors()`/`connector_label()` derive the schedule-UI's connector list from
  `poll-config.json` dynamically. Verified post-fix: `py_compile` clean, a standalone import
  with zero config.json produces safe generic values (`ICONS` keyed by `message_send`,
  `compute_tags` empty for an unrecognized action_type, `is_domain_related` False), and the
  server actually binds and serves a real HTTP request on an isolated test port with no crash.

- **2026-07-13** — Coherence read-through of `commands/setup.md` itself (as opposed to the
  code, above) found three real gaps: (1) Step 5's guidance for `chat_tools`/`revise_tools`/
  `poll_tools` said only "comma-joined lists of the specific tool names each generated agent
  needs" — since `server.py` uses each of these standalone as an entire `--allowedTools` grant
  (never merged with a baseline at runtime), following that literally would produce a
  subprocess missing `Read,Agent`/`Read,Edit,Agent` and unable to even dispatch another agent
  — a silent failure, not a crash, so it likely wouldn't have been noticed until someone tried
  the chat panel on a fresh deployment and it did nothing. (2) The Notes section described a
  `.setup-complete` marker file for safe re-runs, but no step ever actually wrote it — every
  re-run would have incorrectly treated itself as colliding with a foreign deployment. (3)
  Every ported orchestration command referenced "the workspace's architecture doc" for
  approval-required/never-autonomous categories, but nothing in a fresh deployment ever
  creates such a doc — Hemanth's hand-built system has this in `PLAN.md` Part H, but the
  template's own `PLAN.md` is a different document (how the template itself was built, not a
  deployment's approval policy), so a fresh deployment had no concrete file to point at.
  Fixed: Step 5 now states the required baseline explicitly; Step 7 writes
  `.setup-complete`; Step 2 gained a 4th question capturing never-autonomous categories,
  written to `<workspace>/APPROVAL_POLICY.md`, and all 5 commands/docs that referenced the
  vague "architecture doc" now point at that concrete filename. **Rule: an instruction that
  tells the executor to "include what's needed" without stating the concrete minimum is a gap
  disguised as flexibility — state the literal floor value.**

- **2026-07-16** — Kicked off V2. A full read-through of the repo (dashboard, commands, agents,
  polling, both `PLAN.md`s, `lessons-learned.md`) confirmed V1 is complete and its strongest
  properties — approval-gating by construction, config-driven self-containment, single-writer
  memory, zero runtime deps — are exactly the ones V2 must not regress. The V2 design deliberately
  makes the **knowledge graph the foundation everything else writes to** (research fills it; the
  factory, correlation, dashboard, and poll all consume it), so it's milestone M1 and lands before
  any consumer. **Rule: V2 is additive and backward-compatible — a config that predates V2 must
  keep working unchanged, and the dashboard must still run standalone with zero config; grep for
  brand/product strings and check no default path resolves outside `template/` before calling any
  V2 generalization done.** Full plan in `ROADMAP-V2.md`.

## Honest limitation

`/setup` can't be end-to-end tested against a genuinely different machine/connector set from
inside Hemanth's own environment. Verification here is a coherence review of `setup.md`'s
instructions (would it plausibly produce a working agent set + config for, say, Linear instead
of Jira and Teams instead of Slack?) plus confirming the dashboard runs standalone with zero
config.json present. Real-world validation happens the first time someone actually runs it
somewhere else.

## Status

- [x] `dashboard/server.py` — config-driven, self-contained, workspace/config path resolution
      fixed to never default outside `template/`. Verified: imports cleanly with no
      config.json present, all paths resolve inside `template/dashboard/`, touches nothing
      under `~/.claude/cos`. A follow-up coherence pass (2026-07-13, logged above) found and
      fixed three deeper chunks that were still hardcoded to Genesys/Jira/Slack despite the
      header rename — `REVISE_TOOLS`/`POLL_TOOLS` are now actually wired into their handlers,
      `linked_domain`/`domain_tag`/`domain_keywords` are now genuinely config-driven, and the
      poll-schedule UI's connector list is dynamic. Verified again post-fix: `py_compile`
      clean, and the server actually binds and serves a real request on an isolated test port.
- [x] `dashboard/poll-tick.sh` — self-contained, config-aware, connector list read dynamically
      from `poll-config.json` instead of hardcoded.
- [x] `dashboard/serve.sh`, `config.example.json`
- [x] `commands/setup.md` and the 6 ported orchestration commands (`cos.md`, `cos-approve.md`,
      `cos-approve-confirmed.md`, `cos-revise.md`, `cos-poll.md`, `cos-process-inbox.md`)
- [x] `agents/README.md`
- [x] `lessons-learned.md` (seed file, separate from this doc's own log above)
- [x] `README.md`
- [x] Verification pass — dashboard standalone check + full generalization sweep done above;
      `setup.md` coherence review done (3 real gaps found and fixed, logged above). Still
      genuinely open, and stays open per Honest limitation: an actual dry run against a real
      foreign connector set — that can only happen the first time someone runs this somewhere
      else, not from inside this environment.
