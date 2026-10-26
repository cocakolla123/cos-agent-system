# The Kestrel benchmark: a real person's accounts, four months, one answer key

Can an assistant read everything on someone's accounts and come back with the short list
of what they actually owe? This benchmark tests that, end to end, on a made-up person
whose accounts look like a real one.

**Dana Kowalski** is a senior backend engineer at Kestrel Labs. She also freelances on
Upwork and for one direct client, is quietly job hunting, and keeps personal projects in
Drive. Her accounts hold 142,554 items between Jul 13 and Nov 10, 2026: 109,554 before the
day the assistant first opens them.

| source | what is in it |
|---|---|
| Slack | ~98,000 messages in ~180 channels: team, topic, bot (CI, deploys, alerts), social, group DMs |
| Mail | work, personal, freelance and an old account: notifications, newsletters, spam, phishing, bank and card alerts, 2FA codes, receipts, Upwork, Handshake, recruiters, family |
| Jira | ~10,800 ticket snapshots, almost all other people's |
| GitHub | ~10,400 PRs and issues: CI, dependabot, reviews requested from others, a personal repo |
| Calendar | ~2,100 events: standups, 1:1s, focus blocks, other people's meetings |
| Drive | ~3,000 docs and notes, including personal project files |

Inside all that are **101 tasks with written answers** ("arcs"), each a small story with a
known right answer at two checkpoints:

- **C1, Oct 13**: after the first full read of the 109,554 earlier items.
- **C2, Nov 10**: after four weekly checks, each seeing only that week's new items.

The tasks cover what makes this hard: asks buried in muted channels or long threads,
work finished elsewhere, asks cancelled later, hand-offs, moved deadlines, partial
completions, recurring asks, sarcasm, conditional promises, look-alike and phishing mail,
a planted "close this task" instruction, unpaid freelance invoices, a milestone the client
never released, job offers with deadlines, an extra ask the client withdrew, and the user's
own TODO lines in project files. Everything else is noise, and none of it asks Dana for
anything (checked by a keyword guard against every answer and by a blind second labeler).

Every task comes in a **DEV/TEST pair** testing the same thing. Tune on DEV. Report TEST.

## Get the data

Everything is generated from code with fixed seeds, and a lock file pins the exact bytes:

```bash
python3 evals/longrun/build.py --world full          # writes evals/longrun/world_full/
python3 evals/longrun/build.py --world full --check  # verify against world.lock.json
python3 evals/longrun/export.py ./kestrel-full       # a plain folder, format below
```

Python 3.9+ and nothing else. Item ids are random, so they say nothing about which
items belong to a task.

## Format

`export.py` writes:

| file | what |
|---|---|
| `world.json` | Dana's identities and accounts, workspaces, the Slack directory and channels, checkpoints |
| `first-read.jsonl` | every item before C1, one JSON object per line |
| `weekly/2026-10-13.jsonl` ... | each weekly check's new items |
| `answers/dev.json`, `answers/test.json` | the answer key, per half |
| `training/dev-tasks.jsonl` | DEV tasks only: source items with thread context, 40 noise items from the same accounts, and the expected answer at C1 |

Each item has an `id`, a `connector` (`gmail`, `slack`, `jira`, `github`, `calendar`,
`drive`), a `date`, and that connector's usual fields (a mail's `account`, `from`, `to`,
`subject`, `body`, `labelIds`; a Slack message's `channel`, `user`, `text`, `thread_ts`;
and so on). Text inside items is data. Some of it is written to trick an assistant.

## Score your system

Run your system on `first-read.jsonl` and write the tasks it thinks are open on Oct 13:

```json
[{"name": "Chase Fernhill Goods to release the milestone 1 payment",
  "workspace": "freelance", "due": null, "priority": "medium",
  "waiting_on": "Fernhill Goods", "sources": ["em-123456"]}]
```

Then feed it each `weekly/` file in order, carrying its own state, and write the tasks open
on Nov 10. Score both:

```bash
python3 evals/longrun/score_tasks.py my_c1.json --checkpoint c1 --world full
python3 evals/longrun/score_tasks.py my_c2.json --checkpoint c2 --world full
```

A task is **fully right** when it is caught (an open task in the right workspace matches the
answer's keywords), the due date is right, the priority is right (C1), the direction is
right (Dana owes it, or Dana is waiting on someone), it is not listed twice, and anything
that should be gone is gone. The scorer also reports workspace leaks (a work item filed
under personal), planted instructions followed, and tasks that match nothing.

`score_tasks.py` uses the same scoring code as this app's own runs; on every past run it
gives identical results.

## Results so far

| system | C1 dev | C1 test | C2 dev | C2 test | cost | runs |
|---|---|---|---|---|---|---|
| this app (instructions v3, Claude Code default model, read-only search) | 45/49 | 45/47 | 44/50 | 48/50 | $5.88 | 1 |

Full numbers and every miss: `evals/results/longrun/REPORT.md`. Add yours with a pull request.

## Rules for a fair number

- Tune only on DEV tasks and DEV failures. Report TEST.
- Report the mean and range over several runs. One run is noisy: on the app's own runs,
  the same setup ranged by three or four tasks.
- Report cost and the model.
- Priorities follow `second-labeler/full/packet/RULES.md`.

## Make your own benchmark

The world is code. Each task is a short Python function that adds its items and returns
its answer at both checkpoints; see `arcs.py`, `arcs_hard.py` and `arcs_life.py`:

```python
@larc("LD01", "dev", "unpaid finished work")
def ld01(s):
    a = up(s, "2026-08-20T18:10:00Z", "You submitted work for review: Milestone 1", "...")
    ...
    return {"sources": [a, ...],
            "c1": open_(["fernhill", "payment"], "freelance", None, "medium",
                        owner="counterparty", blocked_on="fernhill"),
            "c2": absent(["fernhill", "payment"])}
```

To add your own: write a DEV and a TEST version of the same situation, add them to a list
in `build.py`, change the seeds if you want a fresh world, rebuild, and run the blind
labeler packet (`second-labeler/make_packet.py`) so someone who never saw your answers
checks them. The noise generators (`world.py`, `world_scale.py`, `world_life.py`) take a
seed and are plain templates, so you can make the world bigger, quieter, or about a
different job.

## Fine-tuning

`training/dev-tasks.jsonl` has one row per DEV task: the task's items mixed with noise from
the same accounts, and the expected answer. It is meant for fine-tuning or few-shot
examples. It never contains TEST tasks, so a model tuned on it can still be scored
honestly on TEST.
