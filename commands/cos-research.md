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
| **calendar + meetings** | calendar list, meetings, attendees, recordings | Meeting, Person, Project · `attends`, `recorded_at` |
| **docs / wiki + enterprise search** | documents, decisions | Document, Decision · `authored_by`, `documents` |
| **local filesystem / projects** | local repos, project folders | Project, Repository · `contains` |

Every row above emits **nouns** — things that exist. None of them emits what the user has to *do*
about any of it. Step 1c closes that gap and is not optional: a graph of perfectly-discovered
nouns still leaves the user doing the chief-of-staff's job themselves.

Keep result sets summarized/paginated — do **not** dump thousands of rows; take the most recent /
most active N per connector and record counts in `attrs` (e.g. `attrs.total=1240`).

**A top-N is a budget, not a window — pair it with a time floor.** Item counts buy wildly
different amounts of *history* per connector, because item density differs by orders of
magnitude: in this deployment a top-N sweep of Gmail reached back **two days** (the inbox carries
daily newsletters) while the same N on Drive reached back two months. Anything older than the
densest connector's N simply does not exist as far as the graph is concerned. So: cover **at
least the last 90 days** of every connector, paginating past high-volume noise (newsletters,
notifications, bot traffic) rather than letting it consume the budget — and when a connector is
too dense to cover 90 days whole, spend the remaining budget on targeted queries (Step 1b, and
per-org searches for each `attrs.org` already in the graph) instead of simply stopping at the
cutoff. Record the window you actually achieved as `attrs.window_days` on the records so a later
gap is diagnosable rather than invisible.

### Step 1a — Currency probe (never mint a Project from a container's name)
A *container* — a subscribed calendar, a shared drive folder, a board, a channel, a repo — has a
name but no opinion about whether it is still alive. **Never emit a Project (or let a container
seed a Workspace) on the strength of its name alone.** Read inside it first and record what you
find:

- `attrs.last_activity` — ISO date of the newest real activity you actually observed inside it.
- `attrs.dormant: true` — when that date is over a year old, *or* when the container holds no
  activity evidence at all. `graph.is_dormant` reads both, and the dashboard's "current work"
  sections drop anything dormant (`sections._current`). A node you leave unmarked is asserted to
  be live work, so the probe is not optional.

Three traps make a naive probe lie, all of them observed in this deployment:
- **Default listings hide the past.** Google Calendar's `list_events` returns only *upcoming*
  events, so a calendar dead since 2019 comes back empty and looks like a brand-new one. Always
  probe with an explicit wide past window before concluding anything.
- **Container metadata is not activity.** A calendar's own `updated` field advances when the
  *subscription* is touched — two 2019 service club calendars both showed `updated: 2026-07-31`.
  Judge by the newest *item* `created`/`updated` inside, never by the container's.
- **Future instances are not currency.** An open-ended weekly recurrence authored in 2023
  projects instances into 2037. Rank by when events were *authored*, not by when they fall.

Non-container sources carry the same duty wherever the connector exposes it: a doc's `modified`,
a ticket's last transition, a repo's last push. And anything whose content is the vendor's own
sample data (`attrs.likely_demo`) is dormant by definition — a demo is not work. Mark the
**items** as well as their container: `graph.is_dormant` reads `likely_demo` directly, because a
demo cannot be caught by the activity clock — onboarding samples ship with plausible near-term
due dates, so an unmarked sample task reads as live work forever.

### Step 1b — Lifecycle sweep (find the event that *ended* something)
Step 1a catches work that went quiet. It cannot catch work that was **explicitly terminated**,
and the two fail in opposite directions: a concluded engagement is typically *recent* — busy right
up to the day it stopped — so every recency signal says "live" and the dormancy clock will not
trip for another year. Silence is evidence you must wait for; an ending is an announcement, and
it is already sitting in the inbox.

So make one explicit pass **per org already in the graph** (`attrs.org`) looking for endings
rather than activity. Search the ending vocabulary, not the org's name alone:

> concluded · concluding · contract ended · final day · offboard · removed from · no longer on ·
> wrapping up · transition off · access revoked · last day · terminated · project closed

Check status-bearing surfaces too, not just mail: a revoked group membership, an archived
channel, a board moved to Done, a role dropped from a profile. Widen around any hit the way Step
2 of `/cos-learn` does — same sender, same thread, same week — since an ending usually arrives
with siblings (a final-payment note, a feedback survey, an exit form).

On a hit, mark the affected nodes **and the Objective over them**:

- `attrs.concluded: true` — read by `graph.is_concluded`; `sections._current` drops it from every
  current-work view, including the Workstreams cards, no matter how fresh it looks.
- `attrs.concluded_on` — ISO date of the ending event.
- `attrs.concluded_by` — the evidence (message id / URL / subject), so the judgment is auditable
  and a later run can re-check it rather than re-deriving it.

Do **not** delete or skip the nodes: concluded work stays in the graph and stays queryable ("what
happened with ClientCo?"). It just stops claiming to be current. And mark the workstream itself —
suppressing four documents while their Objective card still headlines the page moves the wrong
answer across rather than fixing it.

### Step 1c — Obligation sweep (extract what the user must *do*)
Steps 1a/1b decide whether a discovered thing is still live. Neither of them produces a **to-do
list**, and no amount of entity discovery ever will, because an obligation is not a property of an
entity — it is a separate fact that usually arrives in its own message and names no project at
all. The assessment due Friday belongs to no repo, board or workstream; the suspended credential
is not a document. Crawl for nouns only and the dashboard answers "here is your world" to a user
who asked "what do I need to do?".

So make an explicit pass for **commitments**, and emit each one as an `Action` node. Search the
obligation vocabulary, not project names:

> action required · due · deadline · expires · complete your · submit your · verify your ·
> reminder · awaiting your · we need · schedule your · book a time · invitation to · suspended ·
> past due · unpaid · renew · confirm your · sign · approve · last chance · final notice

Check every surface that can hold one, not just mail: a ticket assigned to the user, a calendar
block that is really a task, an unsubmitted form, a review request on a PR, a failing check
blocking the user's own submission, a dated event referenced in a doc.

**Assigned tracker work is an obligation even when no message mentions it.** A ticket or issue
whose current state has the user as assignee, or a PR where the user is an individually requested
reviewer, stays open until it is done/closed/merged or another source says the work is finished;
take its due-date field. Read the newest state: a ticket reassigned away, or a review request
withdrawn, is no longer the user's. A review requested from a whole team is not an individual
obligation. **Hand-offs close items:** when the user asks someone to take a task and they accept
("on it", "I've got it"), it leaves the user's list rather than lingering as "delegated"; if they
never answered, it stays open `blocked_on` them. Personal, side-project and job-search obligations
count like work ones, each in its own workspace. **Read the newest state only:** a ticket or PR seen several
times counts by its latest snapshot. **One piece of work is one Action** however many surfaces
word it differently (say a ticket "migrate the auth service", a message "move auth over", a calendar
block "auth cutover"): merge them and cite every source. In messaging, search for the user's handle and
name across all channels (mentions in muted channels count), read every DM and group DM in
full, and read the thread around each hit for later replies that close or reassign it.

**Read the user's own sent mail — it is the highest-precision obligation signal there is.** Every
other surface makes you infer whether the user owes something; their outbox has them saying so.
"Could I please have a few more days to complete it", "I wasn't able to do the assessment on
time", "the link isn't working, can you help" — each is the user asserting an open commitment in
their own words, and unlike the inbox vocabulary it carries no vendor-solicitation false
positives at all. Search `in:sent` for the asking vocabulary — *extension · a few more days ·
wasn't able to · still interested · following up · second chance · reschedule · not working ·
haven't heard back* — and for each hit check whether a reply ever came. **A request the user sent
that was never answered is an open obligation on the user**, because nobody else is going to move
it.

**Rank obligations by resolution state, never by recency — for obligations the two are actively
opposed.** An obligation that is being handled generates fresh mail (reminders, confirmations,
receipts); one that is *stuck* generates silence. So an open obligation gets **older**, not
newer, and every day it stays unresolved it sinks further below a recency-ranked sweep. The
items most likely to be dropped are exactly the ones that most belong on a to-do list. Both
misses that forced this rule — a take-home whose link 404'd and a lapsed Company-D
assessment — were three and eight weeks stale *because* they were stuck, and each was one
unanswered email away from resolution.

Concretely, that means **resolving each obligation to its terminal state instead of sampling the
newest message**. An obligation is a *series*, not a message: invited → reminder → last chance →
deadline extended → completed / expired / silence. Take the whole series (same sender, same
thread, same subject stem), read its last message, and classify:

- a completion or submission receipt → emit it with `attrs.status` set, off the to-do list;
- an explicit expiry or withdrawal → `attrs.concluded` + `concluded_on`, off the list;
- **anything else, including silence → still open**, however old the newest message is. Never
  infer that an old obligation resolved itself; absence of a completion receipt is absence of
  evidence, and the entire failure mode above is that quiet items look finished.

**Obligation mail is the most buried class there is** — it arrives one message at a time in an
inbox whose bulk is application confirmations, newsletters and notifications, so the plain
recency sweep of Step 1 will not reach it (in this deployment the top-40 by recency were almost
entirely LinkedIn/Ashby "thanks for applying" receipts, while the two real deadlines sat below
the fold). Exclude the known-noise senders in the query itself rather than paginating through
them, and run this sweep as its own query budget, never as leftovers from Step 1's.

Emit each obligation as `kind: "Action"` with:

- `attrs.due` — ISO date or timestamp, **with the timezone offset when stated** ("due Sep 18 at
  11:59 PM PT" → `2026-09-18T23:59:00-07:00`). Omit entirely if no deadline was stated; an
  undated obligation is still an obligation and `graph.due_days` returns `None` for it.
- `attrs.status` — omit while outstanding; set it when you observe it satisfied (see
  `graph.DONE_STATUSES`: done/submitted/paid/…). `sections.next_actions` drops it then.
- `attrs.priority` — **required on every Action**: `high`, `medium` or `low`. Use all three;
  `low` is the right answer for soft items, never a reason to drop them. Apply in order,
  first match wins ("today" is the current date):
  - **high**: overdue or due within 3 days; marked "ASAP"/"urgent" by the person the work is
    for (the user's manager, or a client); asked by the manager or a client and due within
    7 days; security or access work with a date (a TLS/SSL certificate, a credential or
    password, an access log or access audit, a security incident).
  - **low**: a quick reply to a colleague's question with no deadline; volunteer or personal
    work due more than 7 days out or undated ("personal" means personal and side-project work;
    job-search work is not personal for this rule); explicitly soft wording ("no rush", "when you
    get a chance", "would be great").
  - **medium**: everything else (peer requests, dated work beyond those windows, undated
    work requests).
  Priority ranks *undated* obligations against each other. If you omit it, ingest records
  `medium`.
- `attrs.clear_attrs` — a list of attribute names to remove when re-emitting an existing Action
  (for example `["blocked_on"]` when a waiting item becomes the user's own task, or `["due"]` when a
  deadline is withdrawn). An empty value never erases an attribute; only this does.
- `attrs.blocked_on` — who the user is waiting on, when the next move is somebody else's (a
  support reply, an extension request, a re-issued link). Record it rather than dropping the
  item: an obligation waiting on a third party is still the user's to chase, and it is the state
  a stalled item sits in for weeks. Name the party and the date they were last contacted.
- `attrs.evidence` — the message id / URL / subject that stated it, so the item is auditable and
  a later run can re-check whether it is still outstanding rather than re-deriving it.
- `attrs.refs` — the workstream token when the obligation clearly belongs to one, so Step 3
  correlates it onto that Objective's timeline.
- `edges` to the org's `Person`/`Project` where one is identifiable.

Three judgment rules, all of which cost the user trust when broken:
- **An obligation must be one the user actually owes — so test the user's standing, not the
  sender's motive.** A vendor soliciting business ("complete your claim", "unlock this offer")
  matches every keyword above and is not a to-do. But the discriminator is *not* whether the
  sender wants something; it is whether the **user has standing**: a commitment they entered
  into, an account they hold, an earning or application history with that org, or a deadline
  someone is genuinely waiting on them for.

  Testing the sender instead of the user silently drops the **inbound opportunity** — a
  personally-addressed offer, role, project or invitation from an org the user already has
  standing with, usually carrying a stated deadline. It is *technically* solicitation
  (unsolicited, often a form, often explicitly disclaiming that it "does not guarantee
  selection or create an offer of work"), and it is exactly the mail a chief of staff exists to
  surface. Emit it as an `Action` with `attrs.inbound_opportunity: true`. A recruiter writing
  personally about a role, a client inviting the user onto a project, a beta or programme invite
  that names them individually — each passes the standing test when the user holds an account
  with, has earned from, or has applied to that org. A bulk marketing blast to a list, with no
  prior relationship and no named deadline, still does not.

  The cost here is asymmetric: a suppressed opportunity expires in silence and the user never
  learns it existed, while a surplus row on the to-do list costs one glance. So when standing is
  genuine but the obligation is soft, emit it at `attrs.priority: low` — never drop it.
- **Never let an obligation become a property of a noun.** Entity discovery (Step 1a) runs over
  the same messages as this sweep and reaches them first, so the *substance* of an obligation
  routinely gets absorbed into whatever noun the message mentions — a `Person` whose `attrs.note`
  records what they pitched, a `Document` whose summary records what it asks for. The fact then
  exists in the graph and is still absent from the to-do list, because `sections.next_actions`
  reads `Action` nodes and nothing else. **A verb stored as an adjective on a noun is a dropped
  obligation**, and it is the hardest miss to notice from the inside: the crawl looks like it
  worked, the entity is right there, and only the user knows the ask went nowhere. Whenever an
  entity's attrs describe something the user must respond to, emit the matching `Action` as
  well — the noun and the verb are both true, and only one of them is actionable.
- **Never invent a deadline.** Record only dates that were stated. An inferred "probably due
  soon" is a fabricated obligation, and it is worse than the omission it replaces.

Already-satisfied obligations are worth emitting *with* their status (the user asking "did I
submit that?" is a real question), but they must never appear on the to-do list.

### Step 1d: Applications, work that lives elsewhere, and content nobody committed to
Four situations a first run on a real personal inbox hits at once. Each one fails quietly if
handled with the rules above alone.

**Applications are series too.** A job, contract or platform application moves through
receipt, then screens, then interviews, then an outcome, and only some steps put the next move
on the user.
- An "application submitted" or "thanks for applying" receipt is not a task. A "profile is
  live" or talent-pool notice is not one either.
- A rejection ends the series. Re-emit it with `attrs.status: "rejected"` (or "withdrawn",
  "expired") so it leaves both the to-do list and the live applications. Do not list
  rejections one by one; a platform that sent many becomes one line in the report.
- Record each live application once, with `attrs.job_application: true` and `attrs.stage`. It
  becomes an `Action` only when a step is owed: reply with availability, book a call, take an
  assessment, send a document, prepare for an interview that has a time.
- **A time the user proposed and nobody confirmed** is an `Action` due at that time, with
  `blocked_on` the person who has to confirm. When the proposed window has passed with no
  reply, it becomes a chase. Priority comes from the date rule as usual.
- **A self-scheduling link from the counterparty** (a booking page, "pick a slot") means the
  user can unblock the item without waiting. Say so in the Action's name. Do not leave it
  only `blocked_on` the other side.
- A scheduling step that went quiet after the user's last reply (a call happened, then nothing)
  is a follow-up the user owns. Record it undated, with the date of the last contact in the
  name.

**Work that lives in a system you cannot see.** Some orgs show clear evidence that the user
does work for them, but none of the work itself reaches a connected source. The evidence looks
like: repository invitations from the org's provisioning bot, CI or review-bot notifications
on the user's own submissions, post-project surveys, payouts, an org-specific login identity,
"your profile is live". The mail is all notifications. The assignment, its deadline and its
status live in the org's own portal, chat or tracker. Two failure modes:
- *Inventing work from notifications.* A bot's "run failed" or "blocking issues" comment is not
  a deadline. Do not emit an Action for every notification thread. If a bot review gates the
  user's own open submission and the newest activity on it is recent, emit one Action for the
  submission, citing the bot review. Otherwise do not emit one.
- *Saying nothing.* The org is real, recent and probably has open work, and the dashboard shows
  none of it. That is the case Step 5 calls an unexplained zero, hidden inside one workspace.

So for each such org, record its workspace with `attrs.needs_connect: true` and add one residual
question for Step 4: offer to connect the system where the work lives (name it when the evidence
shows it: a code host org, a contractor portal, a team chat, a tracker), or ask the user what is
active there and when it is due. One question per org, not per notification. A marketplace
where the user only applies (receipts and rejections, no work evidence) does not get this
question. Its live applications are handled by the rules above.

**Template rows and machine-written pages are not commitments.** A connected tracker or notes
tool often holds seed content (rows like "Task 1" or "Write FAQ for launch" that came with a
template and were never edited). It may also hold long planning pages written by an assistant,
including an earlier run of this system. Neither is something the user or a counterparty said
the user owes. Use them as context. Do not emit an Action from them unless another source
corroborates it, and say in the report that you set them aside.

**A calendar that lacks what the mail schedules is a finding.** When mail shows interviews or
calls with times and the calendar holds none of them, the calendar is not the user's source of
truth for those. Report the mismatch in Step 5 instead of concluding "no meetings". Research is
read-only, so do not create the events.

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
proposal whose members are *all* dormant (Step 1a) is a historical workspace, not a current one:
persist it with `attrs.dormant: true` so it stays queryable without claiming to be live work — and
don't spend a Step 4 question on it. For each remaining
proposal whose `kind` is unambiguous (single strong signal), adopt it silently. For proposals that
are ambiguous or `kind: unknown`, **ask the user one short question** ("Is *Acme* your employer,
a freelance client, or something else?") — and nothing else, apart from the connect-or-tell-me
questions from Step 1d (one per org whose work lives in a system you cannot see). Persist confirmed workspaces with
`research.workspace_records(proposals)` → `ingest`.

## Step 5 — Report (and check your own coverage)
Before summarizing, call `sections.coverage_report(graph)` and **list every section with a count
of zero**. This is not cosmetic: an empty section renders as blank space, so a question the
pipeline never collected the inputs for looks precisely like a question with a genuinely empty
answer. Two separate corrections in this deployment were invisible for exactly that reason (2019
calendars surfacing as live projects; no to-do list at all), so treat each zero as a claim you
have to justify:

- *genuinely nothing* — say so ("no blocked work") and move on;
- *never looked* — that is a coverage gap you just found yourself. Go collect it now if it is in
  scope, or record it as a known gap so it is diagnosable later. **A zero you cannot explain is a
  finding, not a blank.**

Then call `research.window_audit(graph)` and report every source it marks `short`. A zero section
is at least conspicuous; a section filled from **two days of a ninety-day window** is not — it
renders as a populated, plausible, wrong answer, which is why this failure recurred twice before
anything caught it. The audit compares what each crawl *declared* it covered
(`attrs.window_days`, which is why recording it on every record is mandatory rather than nice to
have) against the oldest evidence actually present. Treat each `short` source exactly like an
unexplained zero: go widen it now if it is in scope, or say plainly that this run only saw the
last N days of it. **A window you cannot account for is a finding, not a full crawl.**

Then summarize: nodes/edges added or refreshed, workspaces discovered (with kind), any connectors
that were unavailable, unexplained zero-coverage sections, and any residual questions asked. Forward a one-line `Memory update:` to
`cos-knowledge`. **Nothing external was sent or modified** — say so explicitly.

## Multi-account note (V2.2, M10)
Connector *instances* are accounts: run `accounts.detect_instances` on the discovered tool list
and treat each instance separately — probe each via `/cos-accounts`, skip any the user has
**declined** (`accounts.is_declined`), and tag every record a module emits with the instance's
bound workspace so graph isolation holds automatically. Two Gmail instances are two different
workspaces' data, never merged.

## User-provided context (V2.3, M11) — read this FIRST
Before Step 0, check `<workspace>/context-inbox/` via `context_intake.pending_files`
(`dashboard/context_intake.py`). These are files the user pasted/uploaded through the
dashboard's startup popup (md/txt read directly; pdf/docx via the Read tool). Treat them as the
**highest-confidence source**: extract entities/facts as records with
`source="user-context"` and `confidence=0.95`, and use them to seed workspace inference
(an employer or project the user *told* you about outranks anything inferred). After ingesting
a file, `context_intake.mark_processed(ws, path)` — never delete it. User-stated facts also
resolve ambiguities that would otherwise generate a Step 4 question.

## Every node carries its link (first-run UI feedback)
Whenever the connector exposes one, record the item's canonical URL as `attrs.url` (a doc's
view link, an email thread's permalink, an event's html link, a PR/ticket URL, a repo's local
`attrs.local_path`). The dashboard renders titles as links only when `attrs.url` exists — a
card the user cannot click through to the real thing is a dead end.
