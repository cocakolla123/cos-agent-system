# Step 1e test: the user's own projects

What it tests: `/cos-research` Step 1e, which reads inside the user's projects
instead of just listing them. The world is `evals/projects/` (fictional user,
`.example` domains): four project folders with real files, plus local git
state, GitHub repos, CI runs (with the steps that ran) and PRs, and mail.
The instructions are cut from `commands/cos-research.md` at run time, so the
test checks the shipped text. Isolation is `evals/run.py`'s: no MCP servers,
Read, Glob and Grep only.

## Result: 3 of 3 runs pass every check

Default model (`claude-sonnet-5-5`, from the envelopes), about $0.14 a run.

| trap | expected | 3 runs |
|---|---|---|
| active app mid-redesign | state summary names the redesign | 3/3 |
| collaborator's PR waiting on the user's review, due in 2 days | one Action, high | 3/3, all high |
| CI dying in 3 to 4 s with no steps, on every push | health says runner/billing, not code; one Action, not one per run | 3/3 |
| quant repo: real typecheck failure on main | health names typecheck; one Action | 3/3 |
| runbook apply steps with no record of being run | one Action | 3/3 |
| decision "pending with the user" in the ops log | one Action | 3/3 |
| healthy repo full of TODO/FIXME comments | state summary, no Actions | 3/3 |
| repo untouched for two years | not presented as live, no Action | 3/3 |
| project the user names that no source holds | one "where does it live?" question | 3/3 |
| collaborator recorded | Person for the other committer | 3/3 |

Priorities followed the rules: the dated review was high, the undated
personal-project items were low.

Not scored, worth knowing:
- One run (run2) also emitted "test Harbor Map build 0.4" as a low Action from
  the TestFlight invite. Arguable: the user called it their own project.
- Two runs asked one extra question (whether the dormant repo is retired; how
  to treat the CI failure). Harmless, but the rule asks only for residual
  questions.

## Scorer correction (made after the runs, before reading them as a result)

The first scoring said 0 of 3: glimmer "missing the review" and "one extra
CI action" in every run. The model had both. The scorer paired expected
Actions greedily in alphabetical order, so the CI check took the review
Action first (its name says "before Thursday's TestFlight **build**") and
left the real CI Action over as extra. The scorer now picks the pairing that
matches the most expected Actions (`_best_pairing`), with a regression test.
No model output or label was changed. Re-scoring the same saved outputs
gives 3 of 3.

## Round 2: a shared repo visible only through mail (2026-10-21)

A first pass on a real account missed a project the user pushes to in
someone else's repo: the code-host connector cannot see it, and only a
beta-testing invite pointed at it. Step 1e now searches code-host
notification mail for collaborator invites and the user's PRs. The world
gained the same case (collaborator invite, two merged PRs by the user, a
deploy bot blocking each PR), and the scorer requires the repo's
`owner/name`, the user's work there and the blocker.

Raw output: `raw/20261021T175904Z/`. **3 of 3 runs pass every check**
(default model, $0.14 to $0.17 a run). Every run named the repo, recorded
PRs #11 and #12 as the user's and merged, recorded the blocked deploys, and
asked for the owner to install the connector's app instead of asking where
the project lives. All round-1 traps still passed.

Not scored: runs asked more questions than the rule calls for (2, 3 and 5;
the rule wants only residual ones). Some duplicate an Action already
emitted (whether the runbook steps were run). Worth tightening if it shows
up on real data.

## Limits

- Local folders are given as connector JSON plus real files; the model does
  not run `git` itself (the harness forbids Bash). On the user's Mac the
  research agent reads git state directly.
- One small world, written by the same author as the rules. It shows the
  rule is followed on clear cases, not how it does on a real disk with
  dozens of repos.
