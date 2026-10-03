---
description: Self-learning correction loop — remediate a reported miss, diagnose why it happened, fix the cause (config/instructions/code) autonomously, and record the lesson
argument-hint: "[--next | <what was missed/wrong>]"
---

# /cos-learn — Self-Learning Correction Loop

The user told the system it got something wrong ("you're missing the email from Acme"). Don't
just fetch the missing item — run the full correction loop: **capture → remediate → diagnose →
self-modify → learn & verify**. The deterministic half of every step lives in
`dashboard/learning.py`; you supply the judgment on top of (never instead of) its checks.

**Invocation:** with feedback text, process that correction. With `--next`, take the oldest
`pending` entry from `<workspace>/correction-queue.jsonl` (this is how the dashboard chat and
`/cos-poll` invoke you). With neither, list pending corrections and stop.

**Toggle:** read `dashboard/config.json`. If `learning.self_learning_enabled(config)` is false,
do nothing except say the feature is off. If `self_modify_code` is false, steps that would edit
`.py` files instead draft the proposed diff into `tasks/inbox.md` as a task.

## Hard rules
- **Connectors are read-only.** You fetch and search; you never send/modify anything external.
  Anything actionable still goes to the approval queue like every other flow.
- **Self-modification is local-only and guardrailed.** Before editing ANY file, call
  `learning.is_change_allowed(<template root>, path)`. A `False` is final — report the refusal;
  never work around it. (The approval-gating surface and learning.py itself are immutable.)
- **Every self-change is gated.** Snapshot → edit → gate → keep-or-revert (Step 4). A change
  that fails its gates never survives.
- **Never re-ask what's known.** Check the graph and the corrections ledger before asking the
  user anything.
- **Shared files stay generic — the user's life never enters the template.** The template
  (code, tests, command prose, `lessons-learned.md`) is shared with every deployment; the
  user's data lives ONLY under `workspace/` and `config.json`. When a self-change needs an
  example, an assertion fixture, or a lesson narrative, **anonymize it first**: no personal
  names, org/company names, email addresses or subjects, document titles, dollar amounts, or
  correction ids with personal context — write "a service-club calendar dead since 2019", not
  the club's name; "a client org's removal email", not the sender. The engineering lesson
  must survive anonymization intact; if it can't, the specifics belong in the workspace
  ledger, not the template. (This rule exists because the first live deployment's fixes
  embedded real names into tests and lessons — cleaned by hand once, never again.)

## Step 1 — Capture
If given raw text, build the record with `learning.make_correction(text)` and
`learning.enqueue(<workspace>, rec)`. Extract better keywords/scope than the cheap classifier
if the text supports it (sender names, subjects, dates) and update the record accordingly.

## Step 2 — Remediate (fix the symptom first)
Run a **targeted** research pass for the correction's connector (`/cos-research
--scope=<connector>` behavior, focused by the record's keywords): find the specific missing/
wrong item, then **widen around it** — same sender, same thread, same folder/label, same time
window — so siblings the same gap swallowed are recovered too. Upsert everything via
`research.ingest`, re-run `correlate.correlate`, regenerate views. The user should see the
missing item on the dashboard after this step, whatever the diagnosis says.

## Step 3 — Diagnose (why was it missed?)
Start from `learning.diagnose_checks(rec, graph, last_research_ts, preflight_summary)` — it
checks the machine-verifiable hypotheses (near-miss node → normalization; node without
`part_of` → correlation; connector in the last preflight's unavailable set → connector_down;
nothing recent from that source → staleness; no trace at all → coverage_gap). Then reason:
inspect what Step 2 actually found (where did the item live? was it beyond a top-N limit? did
the discovery module's instructions even mention that location?) and pick the root cause.
State your reasoning explicitly — *what you expected the pipeline to do, what it actually did,
and where they diverged*. If genuinely undeterminable, use `unknown` and record an open
question via `cos-knowledge`.

## Step 4 — Self-modify (fix the cause, no asking)
Map the root cause to a fix and apply it yourself:

| Root cause | Typical fix | How |
|---|---|---|
| staleness | shorten that connector's poll interval | edit `dashboard/poll-config.json` |
| filter_cutoff | raise the module's top-N / widen recency window | edit the module's prose in `commands/cos-research.md` |
| coverage_gap | add the missed folder/label/source to the module's search scope | edit `commands/cos-research.md` |
| connector_down | queue a re-auth task; add a retry note | `tasks/inbox.md` |
| normalization | fix the record's key/attrs mapping | edit `dashboard/research.py` |
| correlation | extend the grouping signal | edit `dashboard/correlate.py` |

For **any** file edit:
1. `token = learning.snapshot(<workspace>, [files])` — before touching anything.
2. Check `learning.is_change_allowed` for each file. Refusal → stop, report, no edit.
3. Make the smallest change that fixes the *class* of miss, not just this instance.
4. **Gate:** run `python3 -m py_compile <changed .py files>` and the full suite
   `python3 -m unittest discover -s dashboard/tests -p 'test_*.py'`; for server-affecting
   changes also confirm the dashboard still serves zero-config. If a test *should* change
   because behavior legitimately changed, update the test as part of the same change — but a
   failing suite you can't explain means the change is wrong, not the tests.
5. Green → `learning.discard(ws, token)` (snapshot retained as history), plus a git commit if
   the deployment is a git repo. Red → `learning.restore(ws, token)` and record the failed
   attempt honestly in the ledger — an auto-reverted fix is a diagnosis clue, not a failure to
   hide.
6. `audit.record(...)` every kept self-change (actor `self-learning`).
7. **Publish the kept improvement**: run `python3 dashboard/publish.py "self-learning: <one-line
   summary>"`. This is how the privacy contract actually behaves — personal data stays local,
   generic logic + lessons flow to the user's repo. The script stages only shared files and
   runs the `privacy.scan_tree` gate; **a blocked push is a hard stop you must report, never
   work around** — the fix is to anonymize the flagged lines (Hard rules above) and re-run, and
   a block means your change embedded personal data, which is itself a correction to learn
   from. An unconfigured deployment (no `publish` block in config.json) is a clean no-op.

## Step 5 — Learn & verify
1. `learning.record_outcome(ws, rec, root_cause, change_summary, verified=...)`.
2. Check `learning.recurring(ws)`: if this correction's signature is now recurring, the earlier
   fix was too narrow — escalate to a systemic change (bigger scope widening, interval change)
   in the same run, and say so.
3. Append a structured entry to `../lessons-learned.md`: symptom → root cause → change → proof.
4. `learning.resolve(ws, rec.id)`.
5. **Verify the original expectation**: is the item the user named now in the graph/dashboard?
6. Report in this exact shape — *what was missed · why it was missed (your reasoning) · what
   changed (files/None) · gates passed/reverted · proof it now works*. Forward a one-line
   `Memory update:` to `cos-knowledge`.
