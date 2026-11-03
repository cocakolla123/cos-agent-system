---
description: Lightweight autonomous check-in, scoped per connector. Fired by poll-tick.sh only when a connector's own configured interval has elapsed and its window is open; also runnable on demand. Never executes anything external.
---

# `/cos-poll`

Arguments: $ARGUMENTS — `--scope=<connectors>` (comma-separated subset of whatever connectors
are defined in `dashboard/poll-config.json` — the caller, `poll-tick.sh` or the dashboard's
"Poll now," already decided which are due), `--dashboard=<absolute dashboard dir>` and
`--workspace=<absolute workspace dir>` (passed by the caller; every file this command names
resolves against them — `poll-config.json`, the logs and `poll-log.md` live in `--dashboard`,
the graph and `approval-queue.md` under `--workspace`. Use these absolute paths, never a
guessed relative one), and/or `--force` (ignore the schedule gate).

**You have no shell, and you don't need one.** Read files with `Read`, change them with
`Edit`, and check every account with its own connector tools (load them with `ToolSearch`).
Never stop or report "blocked" because Bash, Glob, Grep or `cos_tool.py` is unavailable: none
of them is part of a poll. A poll that read no account has failed, whatever else it did. If no
`--scope` is given and this is a bare manual invocation (not via `poll-tick.sh`), run a
`general` sweep (below) only.

**Dashboard "Poll now" = the quick sweep, run immediately.** The dashboard passes
`--scope=<every configured connector> --force`. Run every listed connector's anything-new scan
AND the `general` scope afterward — but each stays as lightweight as a scheduled tick: a narrow
since-last-check window per connector, no rediscovery, no re-reading of threads nothing new
arrived on. Deep rediscovery is `/cos-research`'s job (the dashboard's "Deep sweep" button),
never this command's.

You run in the main session as the orchestrator. Holds no mutating tool — same posture as
`/cos`. Each scope is intentionally narrow — re-checking known things is cheap; rediscovering
everything from scratch on every tick is not.

## Per-connector scopes

For each connector named in `--scope` that maps to a messaging/email-style connector (fast
check-in, not the full sweep): run a lightweight "anything new since last check" scan over
that connector's read/search tool, narrow time window since the last successful run for that
connector (check `dashboard/poll-log.md` for the timestamp). If nothing looks like it needs
real attention (routine chatter, already-closed threads), log `<connector>: nothing new` and
stop for that connector — don't draft anything for noise. Also print that exact line on its own
in your final reply (for example `slack: nothing new`): the scheduler reads it to check a quiet
connector less often, which is most of what polling costs. Keep these quick checks cheap: search
the narrow window first and open a message only when its preview looks like it needs the user.

**Escalation**: if something *does* look like it needs attention (a new message that's a
request, a question directed at the user, anything matching an open approval-queue item's
topic), don't just note it — also run the `general` scope's logic (below) in this same
invocation before finishing, rather than waiting for `general`'s own next scheduled tick.

## Scope: `general`

The full narrow check, in this order — the first step always runs, even when the budget
then runs out before the rest:
- **New since the last poll — first, every time.** Read `poll-last-completed.json` in
  `--dashboard` for the last successful run (if absent, look back 3 days). Then check every
  connected discovery source for what is new since then:
  - **mail:** each mailbox's search (`after:<that date>`, and `in:sent` for what the user sent);
  - **messaging:** Slack/Teams DMs, @mentions of the user, and replies in threads the user is in;
  - **tickets:** Jira, Linear, Asana, GitHub issues and PRs assigned to the user, mentioning
    them, or that they reported, changed since then (new comment, status, assignee, due date);
  - **calendar:** events created or changed since then, and anything starting in the next 48 h.
  A connector that isn't authorized is reported by name in the tick summary, never skipped
  silently. For each new message that asks the user for something, changes the state
  of something already in the graph (an offer approved, a start date set, a document now
  due), or confirms the user did something, update or create the `Action` / record with
  `attrs.thread` and `attrs.last_activity`, exactly as `cos-research` would. This is the only
  step that sees mail nobody has mentioned yet; without it a poll can only re-check what it
  already knew (observed 2026-11-03: an approved offer and a same-day onboarding deadline
  sat unseen for days while every poll re-checked old drafts).
  **Follow what a message points at.** When a new message references something in another
  connected tool — a Notion page, an Asana task, a Drive doc — open it with that connector's
  read tool before deciding what it means (the poll grant includes those read tools for
  exactly this). A message saying "updated the doc" is a pointer; the doc is the content.
- For each `pending` `approval-queue.md` entry, re-check its real source and mark it
  `superseded` (via `cos-knowledge`, with a one-line reason) if someone else already resolved
  it. Leave unchanged entries alone. **Re-checking the real source means reading the thread,
  not the graph:** for an entry whose task names a mail thread, read that thread's newest
  message and the user's own sent mail to that counterparty (last 14 days) before leaving it
  pending. A counterparty message that already answers the entry, or says they are handling,
  considering or reviewing it, supersedes the entry — name that message in the reason. The
  same check runs before minting a new entry: a chase drafted against a thread whose newest
  message makes the chase wrong is a defect, not a draft (observed twice on 2026-10-27).
- **A next step for every open task.** Every open task in the Command Center should carry
  something the user can act on. For each open `Action` in the graph (highest effective
  priority and nearest due date first, at most 10 per tick) with no `pending` entry whose
  `task` is its id, queue one entry with `task: <node id>`:
  - if the next move is a message or reply a connected tool can send, a `message_send` draft
    to the person who asked, in the thread they asked in, with an `account: <connector account
    id>` line naming the mailbox it was found in (e.g. `account: gmail-personal`) — approval
    sends only with that account's own tool and refuses an entry that names none;
  - otherwise a `self_do` entry whose `proposed_tool_call` is the drafted work itself: an
    outline with real headings for a document, the steps for a booking or a form, the text
    to paste.
  A task in the dashboard's "gone quiet" group (more than 14 days overdue, no activity for 14
  days) gets a short "is this still needed?" check-in to the person who asked instead of the
  full work, so a dropped item gets closed rather than done.
  Ground every draft in the task's own sources; never invent dates, numbers, names or
  outcomes. Leave a fact you do not have as a bracketed blank (`[date]`). A task that is
  waiting on someone else gets a short follow-up draft to that person only if the wait is
  past its due date; otherwise skip it.
- **Activity dates.** When a new message touches an open task (a reminder, a follow-up, a
  partial answer), re-emit the task with `attrs.last_activity` set to that message's date
  — and with `attrs.thread` (the Gmail thread id) / `attrs.refs` (`owner/repo#N`,
  `owner/repo@sha`) / `attrs.url` set per cos-research's source-link rule, so the card's
  clickable source link works for poll-minted and poll-refreshed tasks too. That
  is what keeps a chased task near the top and lets an abandoned one sink.
- **Priority reassessment.** For each still-`pending` entry, look at its `created` date and
  current `priority`. If it's old (roughly 30+ days with no update, and especially 6+ months)
  and still sitting at `medium`/`high` with no fresh signal, check whether it's actually tied
  to something currently active (cross-check whatever shared-context files this workspace
  keeps) — if not, demote it to `low` (via `cos-knowledge`, updating `priority` in place, not
  creating a new entry). If it *is* still tied to something active, leave/raise the priority
  and set `priority_note` explaining the connection. Don't touch entries that are recent or
  already `low`.
- **Style-feedback processing.** If `dashboard/style-feedback-queue.md` exists and has any
  entries (the dashboard's "Save edit" button appends a before/after diff here whenever the
  user manually edits a draft), fold each one's specific difference into a personality/style
  profile file if this workspace keeps one (via `cos-knowledge`) — e.g. "shortened a hedge to
  something direct," not just "they edited it." Then clear the processed entries from the
  queue file. If the queue file is empty or missing, skip this step — not an error.
- **`linked_domain` refresh.** For each still-`pending` entry that already has a
  `linked_domain` field (or whose text now looks domain-related per `dashboard/config.json`'s
  `domain_keywords` but doesn't have one yet), re-run a targeted `cos-domain` check (if that
  agent exists for this deployment) against whatever it references and refresh the field via
  `cos-knowledge` if the situation has materially changed. Don't touch it if nothing's changed
  — this is a cheap, targeted check, not a full investigation from scratch.
- If a calendar connector exists, check for meetings that ended in the last ~20 minutes with a
  recorded-meeting link; for each, invoke `cos-meeting-notes` (if generated), forward its
  output to `cos-knowledge`, and queue any approval-category follow-up exactly like any other
  flow.
- Also covers the case where a fast-check scope escalated into this scope mid-run — same
  logic, just triggered early instead of waiting for the next general tick.

## Step 3 — log and report

Append one line per scope run to `dashboard/poll-log.md`:
`<timestamp> — <scope>: <what happened, one line>`. Forward any `Memory update:` output
batched to `cos-knowledge`. Keep the report to the caller short — this runs unattended most of
the time.

## Recurring-failure task suggestion

If the same `failed` approval-queue entry's `execution_result` error (or same error class,
e.g. "org policy block" on the same action_type) has now occurred 2+ times, create **one**
deduped task in `tasks/inbox.md` suggesting the likely fix (e.g. "request org approval for
this connector's send scope") — keyed by `<action_type>:<error signature>` so repeats of the
same underlying issue don't spawn a new task each time. Also append the pattern to
`../lessons-learned.md` the first time it's noticed, even before it recurs enough to trigger a
task.

## Hard rule

Never execute anything external — no send, no ticket comment/transition, no calendar/domain
mutation. Everything actionable goes through the approval queue.

## V2 addendum — continuous learning (see `../ROADMAP-V2.md`)

When the V2 modules are present, the `general` scope also keeps the knowledge graph and the
proposed-agent set current — still **read-only against connectors**, still queue-only for
anything external:

1. **Incremental research.** Run `/cos-research --incremental` so sources changed since the last
   run are re-read and upserted into the graph. Because upsert dedups by stable id, this only
   refreshes freshness/confidence on things already known — it never re-asks the user anything
   already in the graph.
2. **Freshness refresh.** Anything not re-observed decays; `graph.stale_nodes()` flags nodes past
   the freshness horizon so the dashboard can show them as ⚠️ rather than as current fact.
3. **Re-correlate.** Re-run `correlate.correlate(graph)` so new items join (or form) the right
   `Objective` workstream. It's idempotent — existing objectives are updated in place.
4. **Re-evaluate agents (propose only).** Run `factory.propose_agents(graph)`. If the graph now
   justifies an agent that doesn't exist yet (e.g. a new external system appeared), **queue a
   proposal** — a task in `tasks/inbox.md` describing the agent and its evidence — and **never
   auto-create it**. Agent creation stays an explicit, approved `/setup` step.
5. **Regenerate views.** `python3 ../dashboard/graph.py <graph-dir> --render` so the markdown
   views stay in sync.
6. **Process corrections (V2.1, M9).** If self-learning is enabled
   (`learning.self_learning_enabled` on `dashboard/config.json`) and
   `<workspace>/correction-queue.jsonl` has `pending` entries, run `/cos-learn --next` for each,
   oldest first — this catches corrections the chat couldn't process at the time (subprocess
   failed, toggle was off, machine was busy).

All of this is additive: a deployment without the V2 modules runs the original poll scopes
above unchanged.

## Queue hygiene (M12)
In the `general` scope, if `approval-queue.md` contains entries in a terminal state
(`approved`/`rejected`/`stale`/`superseded`) older than **90 days**, move them to
`approval-queue-archive.md` exactly the way the dashboard's "Clear archive" does (append,
never delete; the audit log already holds every transition). This keeps the working file —
and every parse of it — small without waiting for the user to click the button.
