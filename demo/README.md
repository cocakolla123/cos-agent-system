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
corrections, so `build_demo.py` adds them. The drafts answer tasks from that
graph and quote the world's own messages (bracketed parts are left for the
user to fill in). The three corrections are the long-run test's actual dev
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
