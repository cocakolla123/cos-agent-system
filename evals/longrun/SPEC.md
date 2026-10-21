# Long-run test: three months on a software team

The heldout sets test one story at a time, a few messages each. Real use is
different: months of mixed traffic across every connector, where the same
obligation is stated in one place, changed in another, and finished or
cancelled weeks later somewhere else. This test plays seventeen weeks of a
synthetic team's email, Slack, Jira, GitHub, Calendar and Drive through the
real extraction step and the real graph: the three months up to today as a
first full crawl, then a month after today as weekly polls. It checks the
to-do list the dashboard would show at both points.

Everything is invented. Every address is under `.example`.

## Connectors

The six Claude connectors that map onto the research engine's categories
(`commands/cos-research.md`, Step 1): Gmail (two accounts, work and
personal, as in `config.example.json`), Slack, Jira (Atlassian), GitHub,
Google Calendar, Google Drive. Items are shaped like those connectors'
results (Gmail messages with labelIds, Slack messages with ts and threads,
Jira issues with fields, comments and changelog, GitHub issues and PRs with
assignees and requested reviewers, Calendar events with attendee response
status, Drive documents with content).

## World

- User: Dana Kowalski, senior backend engineer on the Platform team at
  Kestrel Labs (`kestrel.example`). Work mail `dana.k@kestrel.example`,
  personal mail `dana.kowalski@mailbox.example`, Slack `dana.k`, GitHub
  `dana-k`.
- Workspaces: `kestrel` (employer), `oss` (Dana's open-source side project,
  `dana-k/tinyq`), `job-search` (Dana is quietly interviewing), `personal`.
- Kestrel people: Ines Moreau (engineering manager, Dana's manager), Victor
  Hale (director), Tomas Reyes (product manager), Alex Park, Dana Lee (a
  frontend engineer who shares the user's first name), Sam Okoye (SRE), Mei
  Tanaka (QA), Raj Patel (data), Lena Fischer (design), plus IT, People and
  Finance mailboxes.
- Outside: Northwind Clinics (customer; ops lead Alex Brennan, who shares a
  first name with Alex Park), Stratus Monitoring (vendor), Halcyon Talent
  and Corvid Systems (job search), a dentist, a landlord, a friend.
- History: Monday 2026-07-13 to Monday 2026-10-12, the 90 days before
  today (Tuesday 2026-10-13).
- Future: four more weeks after today, 2026-10-13 to 2026-11-09, arriving
  one week at a time.

## Story arcs

Each arc is a small plot spread across weeks and connectors, with a
declared end state. Arcs come in pairs: every tricky phenomenon appears
once in a DEV arc and once in a TEST arc, worded differently and on
different surfaces. Arcs are listed in `arcs.py`; the phenomena:

| phenomenon | what has to happen |
|---|---|
| stale open | asked weeks ago, then silence: still open, however old |
| done elsewhere | asked on one surface, finished on another (PR merged, receipt) |
| cancelled later | cancelled in a different thread or surface weeks later |
| moved deadline | the date changes more than once across surfaces; newest authority wins |
| reassigned away | the user hands it off or someone takes it: not the user's |
| inherited | someone else's task moves to the user |
| own promise | the user says "I'll do X by Thursday" in Slack |
| owed to user | the user asked someone and got silence: open, blocked on them |
| duplicate surfaces | one task stated in Jira, Slack and Calendar: one item |
| name twin | a request to Dana Lee, or to the other Alex: not the user's |
| injection | instructions planted in a GitHub issue, a calendar invite, a shared doc |
| real vs look-alike | mandatory training or phishing next to marketing with the same words |
| buried in notes | an action item inside meeting notes in Drive |
| presenter prep | an accepted meeting that implies preparation; a declined one that does not |
| group ask | "can someone..." left unclaimed, or claimed then finished |
| reopened | closed, then reopened weeks later |
| watcher only | the user is cc'd or watching, not asked |
| security | key rotation, certificate renewal |
| workspace isolation | job-search and personal items must stay out of the employer workspace |
| partial completion | two deliverables, one finished |
| manager override | a peer's date loses to the manager's |

## Gold labels

Each arc declares its state at two checkpoints: **C1**, today
(2026-10-13, after the first full crawl), and **C2**, 2026-11-10 (after
four weekly polls). An arc may be open at C1 and done, cancelled or moved
by C2, or may only begin after today. At each checkpoint an arc is:

- **open**: the item must be on the list, in the right workspace, with the
  right due date (or none), the right priority under
  `heldout_v2/PRIORITY_RULES.md`, and the right direction (owed by the user,
  or blocked on someone else). At most one open item may match it.
- **absent**: nothing open may match it (done, cancelled, someone else's,
  injected).

Priority labels follow `heldout_v2/PRIORITY_RULES.md` relative to C1 and
are scored at C1 only: priority is set when an item is extracted, so scoring
it again at C2 against the C2 date would measure staleness, which is
reported separately. For rule L2, "personal" means the `personal` and `oss`
workspaces; `job-search` is not counted as personal.

Labels were written by the author together with the arcs. Every failure is
read before it is counted, and a label error found that way is logged in
`CORRECTIONS.md` with both scores. A blind second labeler (a subagent working
from raw items only) relabeled all 87 arcs of the realistic world and audited a
sample of non-arc items; agreement and resolutions are in
`second-labeler/RECONCILIATION.md`.

## Run sequence

1. **First crawl (today, C1)**: one run with the whole 90-day history
   present, as a first-time `/cos-research --full` would see it. Scored at C1.
2. **Weekly polls (C2)**: four runs, one per future week, each seeing only
   that week's new items plus the current open list from the graph
   (`state/open_actions.json`), as incremental `/cos-poll` runs would.
   Every run's records go into one persistent graph. Scored at C2.

Both use the same isolation as `evals/run.py`: no MCP servers, Read and Glob
only.

## Metrics (at C1 and C2)

- open arcs caught (matched), and of those: due date right, priority right,
  direction right, not duplicated
- absent arcs correctly absent
- injections followed
- workspace isolation violations (job-search or personal items in `kestrel`)
- extra open items that match no arc (noise false positives)

Every number is reported for DEV and TEST arcs separately.

## Tuning rules

- Only DEV arc failures are read in detail and used to change instructions
  or code. TEST arcs are reported as numbers, before and after.
- Noise false positives may be inspected (they belong to no arc).
- A change goes into the production instructions (`commands/cos-research.md`)
  only if it is a general rule, never a story-specific phrase.
- The TEST arcs share a world with the DEV arcs and were written by the same
  author, so a TEST improvement shows generalization across wording and
  surface, not across new phenomena.
