# Lessons learned

Append-only. Each entry: date, what happened, what changed as a result. Written to by
`/cos-poll`'s recurring-failure detection (see `commands/cos-poll.md`) and by hand whenever a
fix to a live deployment reflects a general lesson worth folding into this template. This file
is distinct from `PLAN.md`'s own "Lessons learned" section, which tracks lessons about
*building* this template — this file tracks lessons about *running* a deployment of it.

Format for each entry:
```
## <date>
**What happened:** ...
**Fix / workaround:** ...
**Where this is now encoded:** <file(s) updated so future deployments don't hit this cold>
```

---

## 2026-07-13 (worked example, ported from a real deployment's discovery)

**What happened:** A real send-message tool call was blocked by the messaging platform's own
org-level policy ("Your organization requires approval for this tool") — not a bug in this
system, an external permission gate.

**Fix / workaround:** Switched that connector's `action_tools` mapping (in
`dashboard/config.json`) from the real-send tool to a draft-creating variant, so "Approve"
stages a real draft for the user to send themselves instead of attempting (and failing) a real
send. `commands/cos-approve-confirmed.md`'s status handling already distinguishes `approved`
(fully completed) from `drafted` (staged, needs a human's last click) from `failed` (attempt
that didn't work), so this degrades cleanly instead of silently pretending to succeed.

**Where this is now encoded:** `agents/README.md`'s note that specialists never hold a real
send tool by default; `commands/cos-approve-confirmed.md`'s three-way status model;
`dashboard/config.example.json`'s `action_tools` comment. `/setup` should proactively ask
whether the messaging connector's send scope is already approved, or default to a draft-mode
mapping and let the recurring-failure mechanism promote it if a real send later starts working
without one.

## 2026-07-16 (V2 M1 — Python version floor discovered)

**What happened:** While building the V2 knowledge-graph library, running `python3 -m py_compile
dashboard/server.py` under macOS system Python (`/usr/bin/python3`, 3.9.6) failed with
`SyntaxError: f-string expression part cannot include a backslash` at the meeting-notes card
template. `server.py` uses an f-string whose expression embeds a `"\n\n..."` literal — legal only
on **Python 3.12+**. V1 was authored/verified on a newer Python (homebrew 3.14 here), so the
floor was real but undocumented. A deployer whose default `python3` is 3.9–3.11 would hit a
cryptic crash on `serve.sh` startup.

**Fix / workaround:** Documented the **Python 3.12+ requirement** and kept new V2 modules
(`dashboard/graph.py`) compatible with a wider range (verified passing on 3.9 and 3.14) so the
graph tooling isn't gated harder than the dashboard already is. Longer term the offending
f-string can be refactored (hoist the `"\n\nAction items:\n"` literal into a variable) to lower
the floor, but that's a separate cleanup, not required for M1.

**Where this is now encoded:** this entry; `serve.sh` should state the 3.12+ requirement (follow-up).
**Rule: run `py_compile` under the *oldest* Python a deployer might have as their default
`python3`, not just the newest one on the author's machine — a version-gated syntax error is a
silent floor that only surfaces on someone else's box.**

## 2026-07-17 (V2 review — commands existed but were never installed)

**What happened:** V2 added three commands (`cos-research`, `cos-learn`, `cos-accounts`) that
the dashboard and poll invoke as `/global:cos-*` subprocesses — but `/setup` Step 5's copy list
still named only the six V1 commands. On any fresh deployment, every V2 subprocess (chat
correction loop, accounts probe, incremental research) would have failed with "Unknown
command," silently, into log files.

**Fix / workaround:** Step 5.3 now copies all nine commands and names the failure mode.

**Where this is now encoded:** `commands/setup.md` Step 5.3. **Rule: any new `/global:`-invoked
command MUST be added to `/setup`'s copy list in the same change that introduces it — grep
`server.py` and `commands/*.md` for `/global:` and diff against the copy list before shipping.**

## 2026-09-12 (first real run — three findings in ten minutes)

**What happened:** The first real deployment (fresh machine, dashboard "Research my workspace
now") surfaced three defects no shim-gate had caught: (1) `/start-research` ran with the narrow
`poll_tools` grant (`Read,Edit,Agent`) — under `dontAsk`, `Write`/`Bash`/`Glob`/`Grep` and every
MCP read were silently denied, so research diagnosed brilliantly but couldn't persist a single
graph node; (2) the dashboard chat carried test residue — a `chat-session.json` created during a
shim-based live gate pointed at a session id the real CLI never had, so the user's first message
died with "No conversation found"; (3) that failure surfaced raw instead of self-healing.

**Fix / workaround:** New `research_tools` config key (baseline includes Write/Bash/Glob/Grep;
/setup appends discovered READ-ONLY MCP tools) used by `/start-research`; `validate_config`
enforces its baseline. Chat now detects a dead session and silently retries with a fresh
session id. Test artifacts (`chat-log.md`, `chat-session.json`) removed; live gates must point
`DASHBOARD_DIR`-writing flows at a temp dir, not the real dashboard dir.

**Where this is now encoded:** `server.py` (`RESEARCH_TOOLS`, chat self-heal),
`config.example.json`, `validate_config.py`. **Rules: (a) any subprocess grant paired with
`dontAsk` must be validated against what the command actually needs — a missing tool is a
silent no-op, not an error; (b) a stored session id is a cache, not a fact — always self-heal
on resume failure; (c) live gates that exercise the real server must never leave state files
in the repo's dashboard dir.**

## 2026-09-12 (first self-learning correction — "old stuff is showing up as current")

**Symptom:** The dashboard listed *District 9 North*, *Club Officers* and *Sai's first
project* as current projects, and stood up a whole **Volunteer** workspace around them. All of it
is dead: the two calendars are read-only subscriptions to a CNH **service club** division whose
newest event is `August DCM | Summer Send-Off`, 2019-08-02 — seven years stale. "Sai's first
project" is Asana's onboarding sample.

**Root cause (coverage_gap, at two layers):** The calendar discovery module minted `Project`
nodes out of *calendar-list entries* — container **names** — without ever reading inside them,
so it never had a shred of evidence about whether they were alive. Nothing downstream could
recover, because the graph had no concept of source activity: `is_stale()` measured
`last_verified`, i.e. *when the crawler last looked*, so tonight's poll made a 2019 relic
maximally "fresh". `sections.projects()` then returned every Project node unfiltered. Notably
the ingest had already *written down* the problem in prose — `likely_demo: true`, "historical
term calendar, still subscribed" — and nothing read it: annotation without a predicate is a
comment, not a control.

**Three traps that make a naive currency probe lie** (all three observed here, all three now
written into the module's instructions): Google Calendar's `list_events` returns only *upcoming*
events, so a calendar dead since 2019 comes back **empty** and reads as brand-new — the relics
only confessed under an explicit wide past window. A container's own `updated` field tracks the
*subscription*, not the work: both 2019 service club calendars showed `updated: 2026-07-31`. And
future instances prove nothing — the ASU 2023 term calendar projects weekly recurrences to
**2037** off events authored once in August 2023.

**Change:** `graph.py` gained the missing vocabulary — `attrs['last_activity']`,
`activity_days()`, `is_dormant()`, `DEFAULT_MAX_IDLE_DAYS=365` — deliberately split from
`is_stale()`; `_parse_iso` now always returns aware UTC (the date-only form crashed it, caught by
the gate). `sections.py` filters dormant nodes out of every "current work" section via
`_current()`, and `_live_objective()` propagates dormancy up the correlation layer so suppressing
a dead project doesn't just move the wrong answer onto its workstream card. `cos-research.md`
gained **Step 1a — Currency probe**: never mint a Project from a container's name; probe inside,
record `last_activity`, mark `dormant`.

**Proof:** 156/156 tests green (145 baseline + 11 new, incl. "freshly-crawled relic is fresh but
dormant"); `render_sections()` on the live graph no longer contains any of the six relics, and
the Volunteer workspace is gone from the page.

**Where this is now encoded:** `dashboard/graph.py`, `dashboard/sections.py`,
`commands/cos-research.md` Step 1a + Step 4. **Rules: (a) freshness is not currency — "when did
we last look" and "when did this last happen" are different questions, and only the second one
tells a live project from a relic; (b) never mint a Project or seed a Workspace from a
container's name without reading inside it, and treat an empty default listing as *no evidence*,
never as evidence of newness; (c) if a discovery module notices something is historical, it must
say so in a field a predicate can read, not in an `attrs.note`; (d) suppression needs positive
evidence of age — a node with no `last_activity` is never dormant, because hiding real work is
worse than showing a relic.**

**Left open (guardrail refusal, by design):** the correction was filed with
`connector_hint: "unknown"` even though its text says "calendar". `learning.make_correction`
only reads connector words via `classify_feedback`, and when `_MISS_RE` doesn't match the
phrasing (this text says "should not surface as current", which isn't a listed miss-phrase) it
falls back to a dict that hardcodes `"unknown"` and skips connector detection entirely. That
mis-files the ledger signature (`unknown:coverage_gap`) and would mis-route the remediation pass.
`learning.py` is a **guardrail path** — `is_change_allowed` returned `False` and the loop did not
touch it. Fixing it is a human change: run connector detection in the fallback branch too.

## 2026-09-12 (second self-learning correction — "ClientCo removed me from Life Tasks")

**Symptom:** The dashboard headlined **Workstream: life-tasks-feather** and its four ClientCo
Life Tasks documents as active work. The engagement was over: `the org's no-reply address`, 2026-08-27,
*"Conclusion of Life Tasks 2.0"* — "your contract on Life Tasks 2.0 is concluding today."
A post-exit feedback survey followed on 08-28. Neither email was in the graph.

**Root cause (filter_cutoff, over a vocabulary gap):** Every Gmail-sourced node in the graph was
dated 2026-09-11 or 09-12 — the crawl reached back **two days**. Step 1's only sizing rule was
"take the most recent / most active N per connector", and an item-count means completely
different things per connector: the same N that bought two months on Drive bought 48 hours on a
newsletter-heavy inbox. A 16-day-old `IMPORTANT` inbox thread from an org already in the graph
was simply outside the world.

Underneath that, the fix could not have landed even with the email in hand. The graph's only
currency concept was `last_activity`/`dormant` — **inference from silence**, horizon 365 days.
This engagement was *busy right up to the day it stopped*: documents modified 2026-08-04, contract
ended 08-27. It is fresh, it is active, and it is over. Dormancy could not reach it for another
year, and there was no field in which to write the ending down.

**The asymmetry that makes this its own failure mode:** staleness and dormancy are both
*waiting* predicates — they need time to pass before they say anything, and they fail safe on
relics. A termination is an *announcement*: loud, dated, immediate, and pointed at the work that
looks liveliest. Every recency signal on a just-ended engagement reads "current". So no amount of
tuning the time-based predicates can ever catch this class; it needs a different question asked
of a different kind of evidence.

**Change:** `graph.py` gained `is_concluded()` (reading `attrs['concluded']` +
`concluded_on`/`concluded_by`, or an unambiguous `attrs['status']` from a deliberately narrow
`TERMINAL_STATUSES` — `closed`/`done`/`completed` excluded as normal lifecycle) and `is_current()`
as the single predicate current-work views should ask. `sections.py` routes `_current()` and
`_live_objective()` through it — **and `_render_objectives` now filters at all**, which it never
did: the Workstreams card rendered every Objective unconditionally, so the previous correction's
dormancy fix had the same hole and only `daily_priorities` was ever honouring it.
`cos-research.md` gained a **90-day per-connector window floor** (with `attrs.window_days`
recorded so a future gap is diagnosable) and **Step 1b — Lifecycle sweep**: one pass per known
`attrs.org` searching the *ending* vocabulary rather than activity, marking the affected nodes
**and the Objective over them**.

**Proof:** 166/166 tests green (156 baseline + 10 new, incl. "concluded work is fresh and active
and still not current"); the ending event is in the graph as
`clientco:decision:life-tasks-2-0-concluded`; `render_sections()` on the live graph no longer
contains `life-tasks-feather`, while the 11 open ClientCo job applications **remain** — the
conclusion email says in as many words that it "does not affect any other active roles."

**Where this is now encoded:** `dashboard/graph.py`, `dashboard/sections.py`,
`commands/cos-research.md` Step 1 + Step 1b. **Rules: (a) a top-N is a budget, not a window —
item counts buy wildly different amounts of history per connector, so state coverage in days and
record the window actually achieved; (b) "still active" and "still current" are different claims:
an explicit ending outranks every recency signal, and the liveliest-looking work is exactly where
terminations land; (c) hunt for endings explicitly — search the termination vocabulary per known
org, because an ending is announced once and then never mentioned again, which is the opposite of
how activity accumulates; (d) any view that renders the graph directly instead of going through
the section registry must re-apply the currency filter itself — `_render_objectives` bypassed it
for a full release; (e) concluded work is suppressed from current-work views, never deleted — "what
happened with ClientCo?" must still answer.**

## 2026-09-12 (third self-learning correction — "there are no to-do lists on the dashboard")

**Symptom:** "There are no to-do lists on the dashboard. I expected actionable next steps / a
to-do list from my chief of staff, not just objective cards with document names."

**What the pipeline did vs. what was expected:** the crawl worked. 88 nodes, correctly typed,
correctly deduped, correctly correlated into 8 workstreams, freshness and dormancy and conclusion
all honoured from the two previous corrections. Every section on the page was *right*. The page
was still useless for the question actually being asked, because **every node type in the
vocabulary was a noun.** Documents, Repositories, Projects, Meetings, People, Objectives — an
inventory of things that exist. "Daily Priorities" ranked six cards all reading
`Workstream: <slug>`. Nowhere did the system hold a single record of something the user had to
*go and do*.

**Root cause — `coverage_gap`, of the schema rather than of a location.** The previous two
corrections were gaps in *where* the crawl looked (a calendar's past, an org's ending). This one
is a gap in *what the crawl is capable of representing*. `commands/cos-research.md`'s module table
told every discovery module what entities to emit and never once mentioned an obligation, so none
was ever extracted; `graph.py` had no type to put one in; `sections.py` had no view that could
render one. Three layers, all consistent with each other, all consistently missing the same thing —
which is why nothing anywhere reported an error.

**The distinction that makes this its own failure mode:** an obligation is not a property of an
entity, so no predicate over entities can derive it. `is_stale`/`is_dormant`/`is_concluded` all
ask questions *about a thing*; a document can be fresh, active and unconcluded while the user owes
nothing at all. Meanwhile the real obligations belonged to no discovered entity: the assessment due
Friday referenced no repo, board or workstream, and the suspended credential was not a document.
They arrive one message at a time, each announcing itself once, in an inbox whose bulk is
application receipts and newsletters — so recency-ranked crawling reaches them last. A top-40 sweep
of this inbox was almost entirely LinkedIn/Ashby "thanks for applying" confirmations while two hard
deadlines sat below the fold.

**Change:** `graph.py` gained the `Action` node type, `DONE_STATUSES` (deliberately separate from
`TERMINAL_STATUSES` — "done" ends an obligation but is ordinary lifecycle on a document), and
`due_days`/`is_overdue`/`is_open_action`; `is_dormant` now also reads `attrs['likely_demo']`,
because a vendor's onboarding sample ships with plausible near-term due dates and so can never be
caught by the activity clock. `sections.py` gained `next_actions()`, registered **first** in
SECTIONS. `correlate.py` admits `Action` so an obligation lands on its workstream's timeline — the
"next action" that module's docstring had always promised and never delivered.
`cos-research.md` gained **Step 1c — Obligation sweep**: the obligation vocabulary, an explicit
instruction to exclude known-noise senders in the query rather than paginating through them, the
`Action` attrs contract, and two rules — only obligations the user actually owes (a vendor
soliciting business matches every keyword and is not a to-do), and **never invent a deadline**.

**Escalation (the signature was already recurring):** `learning.recurring()` flagged
`unknown:coverage_gap` at two occurrences, so the earlier fix was too narrow — patching one
missing crawl target at a time. The systemic cause is that **an empty section and a section the
pipeline never fed render identically**: `_render_section` drops an empty section entirely, so
"nothing due" and "nothing ever looked for what's due" are both blank space, which is exactly how
this reached the user unannounced. Added `sections.coverage_report()`/`unanswered_questions()` and
a Step 5 duty to justify every zero. Run once on the live graph it immediately surfaced four more:
Personal Projects (a real bug — `personal_projects()` hardcodes workspace `personal` while the
repos live under `personal-projects`), Freelance Work, People Waiting, Blocked Work. Recorded in
`tasks/inbox.md` rather than silently fixed: each needs a convention decision, not a patch.

**Proof:** 189/189 tests green (166 baseline + 23 new). Six evidence-backed obligations ingested
and rendered by a live `server.py` on an isolated port: Vendor-A assessment *due in 6 days*
(the real deadline, `2026-09-18T23:59 PT`), 2027 coverage review *due in 19 days*, TB3 static
checks blocking PR #1, a lapsed certification renewal, a suspended payments account (account
suspended), Company-C assessment. The Asana demo tasks — "Task 1", due date next week, forever —
are now correctly absent from both the to-do list and Daily Priorities.

**Gating error caught and retracted:** the previous correction's run filed a task claiming
`server.py` was broken (`SyntaxError: f-string ... backslash`). It is not, and the dashboard was
running the whole time. That run gated with the sandbox's default `python3` = `/usr/bin/python3`
= **3.9.6**, while this deployment runs **3.14.4**; `serve.sh` already documents a >=3.12 floor and
already guards it. Retracted in `tasks/inbox.md`.

**Where this is now encoded:** `dashboard/graph.py`, `dashboard/sections.py`,
`dashboard/correlate.py`, `commands/cos-research.md` Steps 1/1a/1c/5. **Rules: (a) discovery that
only emits nouns can never answer "what should I do" — obligations are their own node type, their
own sweep, and their own clock, because they are not a property of any discovered entity; (b) the
answer goes at the top of the page and the supporting inventory underneath it, not the reverse;
(c) never invent a deadline — record only dates that were stated, since a fabricated obligation is
worse than the omission it replaces, and an undated obligation is still an obligation
(`due_days() is None` means "no deadline known", never "nothing to do"); (d) a demo is not work,
and must be suppressed by its flag rather than by its dates, which are designed to look live;
(e) an unexplained zero is a finding, not a blank — a section nothing ever fed is indistinguishable
from an empty one, so every zero must be justified at the end of a run; (f) gate with the
interpreter the deployment actually runs, not with whatever `python3` resolves to.**

## 2026-09-12 (fourth correction — "research missed my coding-assessment assessments")

**Symptom:** The user reported pending coding-assessment tests missing from the graph and the dashboard.

**What was actually true:** No coding-assessment assessment is pending. All four in the mailbox are
closed — US Tech Force *Industry Coding Assessment* completed 2026-08-04, US Tech Force *General
Coding Assessment* completed 2026-01-15, *Handshake Coding Task Team* completed 2026-02-16, and
Ramp *Frontend Challenge* **expired unattempted** 2026-07-12. The user's premise was wrong in its
specifics and right in its substance: widening around it surfaced two genuinely open assessment
obligations the graph had no trace of, both stalled and both blocked on somebody else — an
**Company-B** Early Career take-home whose CoderPad link 404s (user reported it 2026-08-25, no
reply, now 19 days overdue against a stated 7-day window) and an **Company-D** assessment-platform assessment
whose extension request went unanswered twice (2026-07-18, chased 2026-07-20, silent 54 days).
Each is one unanswered email away from resolution and neither was anywhere on the dashboard.

**Root cause (`filter_cutoff` — the *second* `email:filter_cutoff`, so the prior fix was too
narrow):** The previous correction diagnosed Gmail's top-N collapsing to a ~2-day window and
answered it by instructing the crawl to cover **at least 90 days** and to record
`attrs.window_days`. Neither held. The oldest Gmail-derived node was **one day old** — the sole
exception being the 2026-08-27 ClientCo ending, which exists only because Step 1b went hunting for
a *named target* — and `window_days` was recorded on **0 of 21** Gmail nodes. The field added
specifically so this gap would be "diagnosable rather than invisible" was never written, so the
gap stayed invisible exactly as before. The transferable half: a **breadth** instruction ("cover
90 days") loses to recency bias every time, while a **targeted** instruction ("search this org
for these words") wins — Step 1b reached back seven weeks on the same connector, in the same run,
that Step 1c reached back one day.

**The structural reason it will keep recurring for obligations specifically:** the sweep is
recency-ranked, and for obligations recency is *anti-correlated with openness*. Work that is
progressing emits reminders, receipts and confirmations; work that is **stuck** emits silence. So
an open obligation gets **older, not newer**, and sinks further beneath a recency-ranked sweep
every day it stays unresolved. The two items missed here were 3 and 8 weeks stale *because* they
were stuck. Ranking a to-do list by recency is precisely backwards.

**Change:** `research.window_audit`/`window_gaps` + `EVIDENCE_DATE_KEYS` — per-connector crawl
reach, comparing what a crawl *declared* it covered against the oldest evidence actually present,
with "declared nothing" treated as a finding rather than a pass. `server.py` renders it as an
amber banner beside the guardrail-drift check, so under-reach is seen without anyone remembering
to run a command. `commands/cos-research.md` Step 1c: read the user's **sent mail** (the
highest-precision obligation surface there is — the user stating a commitment in their own words,
with zero vendor-solicitation false positives), rank by **resolution state not recency**, resolve
each obligation series to its **terminal state** (silence = still open), and record
`attrs.blocked_on`. Step 5 reports every short source. 10 new tests; 199 pass.

**Proof:** *Follow up with Company-B — technical assessment link is broken* is now the **first item**
on the To-Do list, marked overdue by 19 days; the Company-D chase is fourth. The seven closed siblings
(all four coding-assessment items included) ingested with terminal status and correctly absent from the
list. On first render the new banner immediately flagged five more under-reaching connectors —
`github` and `local-git` at ~0.5 days, `google-drive`/`notion` at ~16, `asana` at ~58 — i.e. the
same defect, connector-wide, that nobody had noticed.

**Where this is now encoded:** `dashboard/research.py`, `dashboard/server.py`,
`commands/cos-research.md` Steps 1c/5. **Rules: (a) an open obligation gets older, not newer —
never rank a to-do sweep by recency, and treat silence on an unresolved item as "still open",
never as "presumably handled"; (b) the user's outbox is a first-class discovery surface, and an
unanswered request they sent is an obligation on them, because nobody else will move it; (c) a
coverage instruction with no reader is a comment, not a control — pair every "cover at least N"
with something that measures and reports the reach actually achieved (the same lesson
`likely_demo` and `is_dormant` taught, now applied to time); (d) when a correction's signature
recurs, the previous fix was prose — escalate to a mechanism in the same run; (e) verify a
"missing" item before agreeing it is missing: the premise here was false, and saying so while
delivering the two real misses is worth more than confirming it.**

---

## M13 — An obligation recorded as a property of a noun is a dropped obligation

**Symptom:** "Research missed a new ClientCo task assignment email — I got assigned/invited to apply
to a new ClientCo task recently and the graph only shows the old Life Tasks docs, nothing about the
new assignment."

**Root cause (`email:normalization`):** the crawl *did* read the email. Proof: it had already
minted `clientco:person:inbound-recruiter` carrying
`attrs.note = "pitched short-term ChatGPT power-user engagement for a frontier AI lab client"` and
`attrs.last_contact = 2026-09-11`. So this was neither a coverage gap nor a filter cutoff — the
message was fetched, parsed and *understood*. It was then filed as a **Person attribute** and no
`Action` was emitted, so it could never reach `sections.next_actions`, which reads `Action` nodes
and nothing else.

Two defects compounded. First, Step 1c's anti-fabrication guard — *"a vendor soliciting business …
is not a to-do"* — tests **the sender's motive** when the thing that matters is **the user's
standing**. The recruiter's mail is unsolicited, from a Growth rep, carries a Google Form, and
explicitly disclaims that it "does not guarantee selection or create an offer of work": textbook
solicitation by that test. It is also a personally-addressed, time-boxed opportunity from an org
where the user holds an account, has an application history, and has been paid three times in
four weeks. The guard is doing real work — the ClaimsHero "ClientCo Data Breach Claim" mail in the
same inbox is exactly what it should suppress — but it was binary on a spectrum, and the class it
wrongly suppressed is the one with the **worst asymmetry**: a missed opportunity expires in
silence and the user never learns it existed. This one was due the morning they complained.

Second, and more general: **entity discovery runs over the same messages as the obligation sweep
and reaches them first**, so the substance of an ask routinely gets absorbed into whatever noun
the message mentions. That miss is the hardest to notice from the inside — the crawl looks like
it worked, the entity is right there in the graph, and only the user knows the ask went nowhere.

**Change:** `commands/cos-research.md` Step 1c, two rewritten judgment rules. (a) Test **standing,
not motive** — an account held, an earning or application history, a stated deadline; the
**inbound opportunity** named explicitly as a class, emitted with `attrs.inbound_opportunity`, and
the asymmetry made a rule (genuine-but-soft → `priority: low`, never dropped). (b) **Never let an
obligation become a property of a noun** — whenever an entity's attrs describe something the user
must respond to, emit the matching `Action` as well. Prose-only change; 199/199 tests green, no
guardrail drift, snapshot `snap-20260912T111916Z` kept.

**Proof:** *Submit interest form — ClientCo short-term ChatGPT power-user project (frontier AI lab
client)* is now **#2 on the To-Do list**, due today. Widening around it recovered three more items
the same gap had swallowed: the Intelliswift AI Engineer thread (user sent a resume 2026-09-03,
silence for 9 days → open, `blocked_on` the recruiter), the individually-selected ClientCo Academy
beta invite, and 11 ClientCo/Cincinnatus applications from the 09-03 and 09-10 waves that a
recency cutoff had left out (JobApplications 10 → 21). Correlation minted a new
`clientco:objective:inbound-opportunities` workstream from them.

**Where this is now encoded:** `commands/cos-research.md` Step 1c. **Rules: (a) when suppressing a
candidate obligation, test the user's standing, never the sender's motive — the sender of a real
opportunity is always, technically, soliciting; (b) a verb stored as an adjective on a noun is a
dropped obligation — entity discovery reaching a message first must not consume the ask in it;
(c) where the costs are asymmetric, tune the filter toward the cheap error — a surplus row costs
one glance, a suppressed opportunity expires unseen; (d) "it isn't in the graph" and "it isn't
actionable" are different failures with different fixes, and a near-miss node is evidence the
crawl worked and the *mapping* failed; (e) gmail has now produced three misses under three
distinct root causes (`filter_cutoff` ×2, `normalization`) — on the densest connector, each new
guard needs its own false-negative check, because every filter added there suppresses more than
it was aimed at.**

## 2026-09-13 — external schedulers can't be trusted with user-folder deployments
- **Symptom:** polling never ran on a live deployment — poll-config.json said every 15 min, but no scheduler was registered; when a launchd agent *was* added, every tick died with `Operation not permitted` before the script's first line.
- **Root cause (two layers):** (1) setup's "register a scheduler" step is easy to skip and nothing detects the gap — a config file describing a schedule looks exactly like a working schedule. (2) macOS TCC denies launchd agents access to protected folders (Downloads/Documents/Desktop), so any deployment living there can't be ticked by launchd at all without the user hand-granting Full Disk Access.
- **Change:** the dashboard server now runs the ticker in-process (fires poll-tick.sh every 5 min while it serves; the script keeps all interval/window gating, so ticks stay idempotent and an external cron remains an optional, harmless supplement). setup.md Step 6 rewritten accordingly.
- **Proof:** first in-process tick fired within seconds of server start and recorded poll-last-run.json; a /cos-poll run was live immediately after.

## 2026-09-13 — a command whose own grant cannot run its own instructions

**What happened:** The `general` poll run fired by that first in-process tick (19:58:49Z)
completed every check `Read` can satisfy — empty approval queue, absent style-feedback queue, no
calendar events, correction queue fully resolved, graph in sync at 121 nodes — and **silently
skipped all five V2 addendum steps.** `config.json`'s `poll_tools` is `Read,Edit,Agent` plus
read-only MCP: no `Write`, no `Bash`. The addendum calls for `/cos-research --incremental` (needs
`Write`/`Bash` to persist a node) and `python3 ../dashboard/graph.py --render` (needs `Bash`).
Both launch paths pass `poll_tools` verbatim as the entire grant under `dontAsk` —
`poll-tick.sh:68,75-79` and `server.py:2331` for the "Poll now" button — so every shortfall is a
no-op, not an error. The run only noticed because it was denied live and went looking for why.

**Not a new kind of bug — the previous entry's sibling.** This is the 2026-09-12 rule (*"any
subprocess grant paired with `dontAsk` must be validated against what the command actually needs
— a missing tool is a silent no-op, not an error"*) **violated again, one command over.** That
fix was applied to `/start-research` alone: a new `RESEARCH_TOOLS` key, plus
`validate_config.validate()` enforcing its baseline, with `server.py:2446-2449` commenting the
reasoning. `/cos-poll` then gained a V2 addendum needing the same tools and kept its V1 grant.
Distinct from the entry above: that one is the *scheduler* failing to start the poll; this one is
the poll starting fine and being unable to do the work.

**The sharpest instance:** Step 3 orders every run to append to `dashboard/poll-log.md`. With
only `Edit` granted and no such file, the **first** poll run of any deployment cannot log itself
— the one artifact that would have made the other silent skips visible is the one the grant
forbids creating. This run could not, and filed to `tasks/inbox.md` instead.

**Change:** recorded only — `tasks/inbox.md` key `poll:grant-gap-v2-addendum`. The fix is a
contract decision rather than a patch: widen `poll_tools` and enforce it in `validate_config`, or
(preferable) have the poll **delegate** its graph work to a `spawn_background` subprocess carrying
`RESEARCH_TOOLS`, exactly as `/start-research` already does — which keeps an unattended `dontAsk`
job read-only instead of handing it a write grant.

**Where this is now encoded:** this entry; `dashboard/workspace/tasks/inbox.md`. **Rules: (a) a
command's instructions and its tool grant are one artifact — a step that needs a new tool is
unfinished until the grant and `validate_config` change in the same commit, and a per-command
grant fixed once does not fix its siblings; (b) never make a command's own audit log the thing
its grant cannot write — logging must be reachable with strictly fewer permissions than the work
it logs, or the first run's failures are invisible by construction; (c) `Edit` without `Write` is
not "append-only," it is "append only to files that already exist" — ship the empty file from
`/setup` or grant `Write`; (d) an unattended run cannot report what it never attempted, so every
"if the modules are present, also do X" clause needs a positive check that X was actually
possible — the unexplained-zero rule, applied to capability instead of to data.**

## 2026-09-13 — the grant gap recurred, and a missing log has no second chance

**What happened:** The next `general` run (20:14:22Z, ~16 min after the one above) hit the
identical wall: `Write` denied, `Bash` denied, V2 addendum steps 1–5 skipped again. No new task —
the dedup key `poll:grant-gap-v2-addendum` already existed — but the recurrence itself is the
finding, and it kills two hypotheses the single first observation left open. It is **not a
first-run artifact**: the missing `poll-log.md` does not get created by the second run either, so
the file's absence is self-perpetuating and every run stays unlogged forever rather than only the
first. And it is **not launch-path-specific**: this run came from a manual invocation, not from
`poll-tick.sh:75-79` or `server.py:2331`, and was denied the same way — the grant travels with the
command, so "just run it by hand" is not a workaround.

**What that changes about the fix's priority:** the previous entry's response was "recorded only,"
which the recurrence rule (2026-09-12, fourth correction, rule (d)) already forbids on a second
occurrence. Note also that the escalation was *available and declined*: `config.json` is an
existing file, so `Edit` alone is enough for the poll to widen its own `poll_tools`. It did not,
because a `dontAsk` job that can grant itself `Bash` has no meaningful grant at all — which is
itself the argument for delegation (option b) over widening (option a).

**Where this is now encoded:** this entry;
`dashboard/workspace/tasks/inbox.md` key `poll:grant-gap-v2-addendum`, occurrence 2.
**Rules: (a) a bootstrap file a command cannot create is not "missing on the first run," it is
missing permanently — absence that blocks its own repair never shows up as a growing problem, so
size it from the first sighting rather than waiting to see if it recurs; (b) a capability gap
observed once through one launch path is untested elsewhere — re-observe it through a different
entry point before concluding the launcher is at fault, because a per-command grant fails
identically from every direction; (c) a process must never hold the permission to widen its own
permissions, and finding that it does is a finding in its own right — here `Edit` over
`config.json` silently subsumed every grant the config names.**

**Addendum, occurrence 3 (same day, third `general` run):** recorded on the existing dedup key
rather than as its own section, because the pattern is unchanged — but one new fact narrows the
fix. `poll_tools` grants `Agent`, and this run used it (a subagent inventoried the workspace,
since the poll has no `Glob`/`Grep`). **The subagent was denied `Bash` too**, and finished by
`Read`-probing paths one at a time. A subagent inherits the parent session's permission mode
instead of carrying a grant of its own, so "the poll already has `Agent` — just delegate the V2
steps to a subagent" is not a fix; it relocates the silent no-op one level down. Option (b)
survives only in its literal form: a server-side `spawn_background` **subprocess** started with
`RESEARCH_TOOLS`, i.e. a fresh CLI invocation with its own grant. **Rule: "delegate it to an
agent" and "spawn it as a subprocess" are not the same escape hatch — only a new process gets a
new grant, and an in-session subagent is bounded by whatever denied its parent. Check which one a
proposed fix means before believing it routes around a permission wall.**

**Addendum, occurrence 4 (same day, 20:52Z `general` run):** the symptom held a fourth time —
`Write` denied, V2 addenda 1–5 unreachable, `poll-log.md` still absent after four runs — but the
*diagnosis in the three entries above is wrong in a way that matters.* They record "`Bash`
denied." This run ran `date`, `ls`, `cat`, `tail` and `grep` inside the dashboard directory
without any prompt. What it could not do was **invoke an interpreter** (`python3 -c "print('ok')"`
and an absolute `/opt/homebrew/bin/python3.14 graph.py --help` both refused) or **reach a path
outside the working directory**. The wall is a command-level sandbox over read-only shell, not an
absent tool. That inverts the cheapest remaining fix: option (a) — "widen `poll_tools` to
`Read,Edit,Write,Bash,Agent`" — targets a grant that was never the binding constraint, while every
addendum step still needs precisely the operation the sandbox blocks.

**Rules: (a) a capability is not one bit — "Bash" is a family of very differently-privileged
operations, and a run that probes it with `ls` and concludes "Bash works", or is refused `python3`
and concludes "Bash is denied", has measured the wrong thing; gate a capability with the *exact*
call the work requires, never with a convenient proxy for it; (b) a symptom observed identically
four times is not a diagnosis confirmed four times — three runs agreed with each other and were
all wrong about the mechanism, because each inherited the previous run's framing instead of
re-probing; when a finding recurs, re-derive the cause at least once rather than incrementing a
counter, since a confidently-worded prior observation is the thing most likely to stop the next
run from looking; (c) the permission profile of a hand-typed command is not the same artifact as
the grant its automated launchers pass — occurrence 2 asserted the two were denied identically and
occurrence 4 contradicts it, so measure both rather than generalising from whichever one you
happen to be running in.**

**Addendum, occurrence 5 (same day, fifth `general` run, hand-typed):** `poll-log.md` still
absent after five runs — `Write` denied explicitly this time, so the bootstrap gap is permanent,
not a profile accident. But the run also **falsifies occurrence 4 the way occurrence 4 falsified
occurrences 1–3.** Here `Bash` was denied *outright* at the tool level: `ls` inside the working
directory was refused, not merely `python3`. Occurrence 4 observed read-only shell working in the
cwd and concluded the wall was a command-level sandbox rather than an absent tool. Both
observations are accurate; they describe **two different walls, one run apart, same machine, same
day.** The constraint is therefore not a stable property of the command — it varies per
invocation, which no single run can detect from the inside.

What that costs: five consecutive runs have been characterising `poll_tools` by probing a
hand-typed session that **is not running under `poll_tools`**. This run held `ToolSearch` and
completed live MCP calendar reads, neither of which `poll_tools` grants, while lacking `Bash`,
which the automated path may well have. The manual session is not a subset or a superset of the
automated grant; it is a different set. So occurrence 2's "manual runs are denied identically"
and occurrence 4's "widening the grant targets a non-binding constraint" are both unsupported —
each generalised from the wrong artifact — and the wall the *scheduler* actually hits is still
unmeasured.

**Where this is now encoded:** this addendum; `dashboard/workspace/tasks/inbox.md` key
`poll:grant-gap-v2-addendum`, occurrence 5. **Rules: (a) when a symptom recurs and each run's
diagnosis contradicts the last, stop diagnosing the symptom and suspect the *measurement
environment* — three mutually inconsistent readings of one constraint mean the thing being varied
is the observer, not the wall; (b) a permission finding is only valid for the launch path that
produced it, so record the launch path beside every such observation and refuse to generalise
across paths without a second measurement — the cheap discipline that would have caught this at
occurrence 2; (c) an unattended job's grant can only be characterised from inside an unattended
run: instrument the scheduler to write down what it was actually denied, because a human
reproducing the command by hand is running a different program.**

**Addendum, occurrence 6 (same day, sixth `general` run, hand-typed):** no new class — recorded
because it **replicates** occurrence 5's claim, which occurrence 5 could only assert once. `Bash`
and `Write` denied outright at the tool level; `ToolSearch` and live MCP calendar reads worked
again. New: `Glob`/`Grep` are not *denied* in a hand-typed session, they are **absent from the
deferred-tool registry entirely** (`ToolSearch "select:Glob,Grep"` → no matching tools), so
occurrences 1–5 were wrong even to frame them as a grant shortfall here. Across the two runs that
agree, the manual session is neither subset nor superset of `poll_tools`: it holds tools the grant
never names and lacks tools the grant does name. So the correct reading of occurrences 1–4 is not
"weak evidence about the grant" but "measurements of a different artifact," and the scheduler's
actual wall remains unmeasured six runs in.

Also newly observed rather than predicted: `general` is the only scope `poll-config.json` defines,
and `general` contains no inbound-mail check, so every run reads zero new email *by construction*
while the one path that would (V2 addendum 1) is blocked. **Rule: when two open findings are
recorded as "must be fixed together," check on each recurrence whether the compound effect is now
observable — a predicted interaction that has quietly been happening for six runs is a different
size of problem from a hypothetical one, and the log of either finding alone never shows it.**
