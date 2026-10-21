# Long-run test: three months of a software team, then a month of polls

What it is: `evals/longrun/SPEC.md`. In short, a synthetic engineer (Dana
Kowalski at Kestrel Labs) with the six connectors that map onto the
research engine (two Gmail accounts, Slack, Jira, GitHub, Calendar, Drive).
The 90 days before today (2026-07-13 to 2026-10-12) are crawled once, as a
first `/cos-research --full` would, and scored today (**C1**, 2026-10-13).
Then four weeks of new traffic arrive one week at a time as incremental
polls on one persistent graph, scored on 2026-11-10 (**C2**). Every story
("arc") has a declared right answer at both checkpoints, and arcs come in
DEV/TEST pairs: fixes were made from DEV failures only.

Two worlds:

| world | items | Slack | arcs |
|---|---|---|---|
| easy | 423 | 218 messages | 51 |
| realistic | 18,826 (14,457 before today) | ~17,000 messages, ~140 channels (muted, member, non-member), group DMs | 87 |

The realistic world is what a working day looks like: most traffic is
noise, asks to other people, mentions of the user that are not asks, bots,
other people's Jira tickets, notification mail. Nothing can read all of it,
so the runs there get read-only Grep (standing in for connector search).

## Results (arcs fully right: caught, right due date, right priority at C1, right direction, not duplicated, and nothing that should be gone)

| run | world | instructions | model | cost | C1 dev | C1 test | C2 dev | C2 test | open tasks caught at C1 (dev+test) |
|---|---|---|---|---|---|---|---|---|---|
| lr-v1 | easy | v1 | default | $1.21 | 23/24 | 23/23 | 25/25 | 25/25 | 16/16 + 14/14 |
| lrr-v1 | realistic | v1 | default | $2.25 | 40/42 | 40/40 | 42/43 | 42/43 | 26/26 + 24/24 |
| lrr-v2 | realistic | v2 | default | $2.51 | 41/42 | 40/40 | 42/43 | 42/43 | 26/26 + 24/24 |
| **lrr-v3** | realistic | v3 | default | $2.10 | **41/42** | **40/40** | **43/43** | **43/43** | 26/26 + 24/24 |
| lr-v1-haiku | easy | v1 | Haiku 4.5 | $0.74 | 14/24 | 13/23 | 21/25 | 19/25 | 8/16 + 11/14 |
| lr-v2-haiku | easy | v2 | Haiku 4.5 | $0.69 | 13/24 | 13/23 | 16/25 | 19/25 | 10/16 + 9/14 |
| lr-v3-haiku | easy | v3 | Haiku 4.5 | $0.76 | 14/24 | 11/23 | 20/25 | 21/25 | 13/16 + 9/14 |
| lrr-v1-haiku | realistic | v1 | Haiku 4.5 | $1.03 | 16/42 | 16/40 | 27/43 | 23/43 | 4/26 + 1/24 |
| lrr-v3-haiku | realistic | v3 | Haiku 4.5 | $1.31 | 22/42 | 20/40 | 26/43 | 24/43 | 11/26 + 14/24 |

The default model was `claude-sonnet-5-5` in every run (from the envelopes).
Every row is one run; with one run per setup, a one-arc difference is within
run-to-run noise (lrr-v2 lost an arc lrr-v1 had passed). All numbers are
after the label corrections in `evals/longrun/CORRECTIONS.md`, applied to
every run alike.

No run, on either model, followed an injected instruction that closes
tasks, and none leaked a job-search or personal item into the work
workspace. Haiku followed the phishing email once (lr-v1-haiku).

## What the default model catches and misses

With v3 it got every phenomenon right at both checkpoints except one
priority: the "circulate the design doc two days before the review" task
(due exactly 7 days out, manager-organized) came out medium instead of high,
the boundary of rule H3. It caught asks in muted channels, the one ask
inside a 40-message incident thread, the mandatory @channel next to an
optional one, shared work ("you two own..."), work in its area that nobody
assigned it, sarcasm, conditional promises, stale Jira status, recurring
asks, auto-replies, and it closed or moved items correctly during the
weekly polls. Twice it was right where the answer key was wrong (a quote
for a renewal another thread cancelled; Legal's "approved, you can send
them" creating a new task), both logged as label corrections.

Its real DEV misses, and what fixed them:

| miss (run) | fix (instructions) | after |
|---|---|---|
| kept a task the user handed to Mei, who accepted, as "delegated" (lrr-v1) | v2: an accepted hand-off leaves the user's list | fixed in v2 and v3 |
| read job-search as "personal" for the low-priority rule (lr-v1, lrr-v1) | v2: spell out that job-search is not personal | fixed in v2 and v3 |
| listed one task twice under different wording, benchmark vs latency numbers (lrr-v2) | v3: one piece of work is one Action, however worded | fixed in v3 |

## What Haiku catches and misses

Haiku is not safe for a first crawl at realistic volume. With v1 it
searched Jira for the user, emitted 12 records from 14,457 items and
stopped: 4 of 26 DEV and 1 of 24 TEST open tasks caught. Its DEV failures
drove three general rules (v2/v3): assigned tracker work counts even when no
message mentions it; use only the newest snapshot of a ticket or PR; follow
an explicit search plan (mentions and the user's name across every channel,
every DM and group DM in full, assigned tickets and requested reviews, sent
mail, skip bulk senders); and during a poll check every open item against
the new traffic for completion. With v3 it catches 11/26 DEV and 14/24 TEST
at C1, still far from usable. What it still gets wrong, by phenomenon,
counting both checkpoints (lrr-v3-haiku):

- never or almost never: asks in muted channels (0/4), asks inside long
  threads (0/4), mandatory @channel (0/3), action items in meeting notes
  (0/4), manager override of a peer's date (0/4), partial completion (0/4),
  relative dates (0/4), stale tracker status (0/4), job-search items
  (0/4, missed rather than leaked)
- often: own promises (1/4), security tasks (1/4), stale open items (1/4),
  real vs look-alike mail (1/4), recurring asks (1/4)
- fine: name twins, watcher-only, sarcasm, group asks, cancellations,
  injections, work it was not given

It also does date arithmetic badly (overdue items marked medium) and rarely
re-emits items to close them in polls.

## Pipeline findings (code)

- **An attribute could never be removed.** `graph._merge_attrs` keeps the old
  value whenever a record carries an empty one, so a waiting-on that ended
  or a withdrawn deadline stayed forever. Found when the answer-key oracle
  failed on HT12. Added an explicit `attrs.clear_attrs` list (empty values
  still never erase), with a test, and documented it in
  `commands/cos-research.md`. Not yet exercised by a model run.
- **Priority goes stale.** Priority is set when an item is extracted; an item
  that was medium three weeks before its deadline is still medium the week
  it is due. Not scored at C2 for that reason. A date-derived "effective
  priority" in the dashboard (rule H1 is pure date math) would fix this and
  would also cover Haiku's date-math misses. Not built.

## Changes made

- `commands/cos-research.md` (production): assigned tracker work; accepted
  hand-offs; personal, side-project and job-search obligations; job-search is
  not "personal" for priority; newest snapshot only; one Action per piece of
  work; messaging search (mentions across all channels including muted ones,
  every DM and group DM, the thread around each hit); `clear_attrs`. All
  written as general rules, with no wording from the stories.
- `evals/instructions/longrun_v1.md` -> `v2` -> `v3`: the same rules, plus the
  fixture layout and the incremental-poll contract.
- `dashboard/graph.py`: `clear_attrs`.
- `evals/run.py`: `run_scenario` accepts an extra read-only tool (Grep);
  `assert_isolated` still forbids anything that can reach a connector or
  write.

## Caveats

- One run per setup; differences of one arc are noise.
- The answer key was written by the same author as the stories, without a
  blind second labeler. Four corrections were needed (two were the model
  being right, two were match keywords too narrow); all are logged with
  before and after scores.
- TEST arcs share the world, cast and author with DEV arcs, so TEST
  improvements show generalization across wording and surface, not to new
  kinds of situations. The TEST arcs were not read in detail until tuning
  ended; the two exceptions were found through the noise list and are logged.
- The realistic runs could search (Grep). The heldout evals and the easy-world
  runs could only Read and Glob.
- The world is synthetic and much cleaner than real life in one respect:
  every ask is written in full sentences.

## Recommendations

1. Use the default model for the first crawl and for any poll covering a
   lot of traffic. Haiku misses most obligations at realistic volume even
   with the search plan.
2. Build the date-derived effective priority in the dashboard.
3. Next test: a blind second labeler over the realistic world, then several
   runs per setup to put error bars on these numbers.

## Follow-up (2026-10-21): priority computed from the due date

The "priority goes stale" finding is fixed in the dashboard. `graph.effective_priority`
keeps the stored priority as a floor and applies rule H1 on read: overdue or due within
3 calendar days is high. A priority the user set by hand is never overridden. The
to-do ranking, the task board, Daily Priorities and the deadline labels all use it.

Scoring: C1 is scored against the hand labels as before, plus effective priority. C2
had no priority labels, so they are derived mechanically: H1 at the C2 date, otherwise
the C1 label when the due date is unchanged. Every saved run was re-scored. The old
numbers are unchanged and the rebuilt graphs are identical.

| run | C1 dev pass, stored → effective | C1 test | priority right at C1 (dev+test), stored → effective | C2 priority (effective) |
|---|---|---|---|---|
| lrr-v3 (default) | 41 → 41 /42 | 40 → 40 /40 | 49 → 49 /50 | 40/40 |
| lr-v3-haiku (easy) | 14 → 17 /24 | 11 → 15 /23 | 9 → 17 /22 | 13/13 |
| lr-v2-haiku (easy) | 13 → 15 /24 | 13 → 16 /23 | 11 → 16 /19 | 10/11 |
| lrr-v3-haiku (realistic) | 22 → 23 /42 | 20 → 21 /40 | 18 → 18 /25 | 19/20 |
| lrr-v1-haiku (realistic) | 16 → 18 /42 | 16 → 16 /40 | 0 → 2 /5 | 8/8 |

It fixes most of Haiku's date-math priority errors on the easy world (wrong
priorities fall from 13 to 5 in lr-v3-haiku, and from 8 to 3 in lr-v2-haiku). On the realistic world Haiku's problem is that it
misses tasks, not their priority, so passes barely move.

### Large-model crawl, Haiku polls (one run, `lrr-v3-mixed-haikupolls-r1`)

The first crawl reuses lrr-v3's saved C1 (default model); the four weekly polls ran on
Haiku 4.5 (`replay.py --crawl-from`).

| setup | C2 dev | C2 test | cost of the 4 polls |
|---|---|---|---|
| default model throughout (lrr-v3) | 43/43 | 43/43 | $1.25 |
| default crawl + Haiku polls | 42/43 | 38/43 | $0.99 |
| Haiku throughout (lrr-v3-haiku) | 26/43 | 24/43 | $1.04 |

Haiku polls cost about a fifth less and lose 6 arcs. What it got wrong is all poll
work: a moved deadline left at the old date (D04), two items that should have closed
left open (T04, T08), a new recurring ask and a mandatory @channel missed (HT11,
HT14), and an auto-reply taken as an answer (HT12). Its last poll returned no records
at all. On this evidence the cheap-model polls are not worth it: the saving is small
(a Haiku poll takes more turns) and it drops the updates polls exist for. One run;
the repeats in the next section put error bars on it.
