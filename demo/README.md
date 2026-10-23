# Public demo (fictional data, read-only)

A clickable copy of the dashboard over the long-run test world: Dana Kowalski,
an engineer at Kestrel Labs, a made-up company, with three months of Slack,
mail, Jira, GitHub, calendar and Drive traffic (about 18,000 items, all
`.example` domains).

**What is real:** the task list, priorities, due dates, workspaces and waiting
items are the graph the research engine built from that world in recorded
run `evals/results/longrun/lrr-v3` (first checkpoint, 2026-10-13). They are not
hand-written.

**What is staged:** a crawl does not produce an approval queue or a history of
corrections, so `build_demo.py` adds them. Every open task carries one drafted
next step, shown on the task in the Command Center: a message waiting for
approval, or (when no connected tool can do it) a draft for Dana to finish
herself. Four are hand-written; the rest come from `draft_next_steps.py`, which
runs the poll's "a next step for every open task" rule once over the world
(each task's own sources only, $0.60) and saves `next_steps.json`. Bracketed
parts are facts the sources do not give, left for the user to fill in. The
recorded run predates `attrs.last_activity`, so the build fills it from the
world's own item dates (the newest message in each task's threads); the list
ranks on it, and long-overdue tasks nobody has mentioned in weeks sit in a
"gone quiet, still needed?" group with a check-in drafted instead of the work.
Likewise for `attrs.importance` (how much a task matters apart from its date):
`classify_importance.py` applied that rule once to each task's sources ($0.24) and
saved `importance.json`. The three corrections are the long-run test's actual dev
failures and the rule changes that fixed them. Saved chat replies that state
counts are computed from the graph at build time.

**What it cannot do:** anything. There is no model call, no connector and no
write. In demo mode the server answers every POST from `responses.json`, reads
state only from `demo/state/` (never the real dashboard folder), freezes the
clock at 2026-10-13 and does not start the poll scheduler. The static export
has no server at all.

## Build and run

```
python3 demo/build_demo.py                       # demo/state/
python3.12 dashboard/server.py --config demo/state/config.json --port 8799
python3 demo/export_static.py                    # demo/site/, plain files
```

`demo/site/` can be hosted anywhere that serves files. Open `index.html`.
`demo/artifact/` is the same pages shaped for claude.ai artifact hosting (the index
page without its own html/head/body tags); the published copy is private to its
owner until shared from its Share menu.
