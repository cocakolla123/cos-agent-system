# Preregistration: held-out v2 runs

Committed together with SPEC.md, the fixtures, the labels, and
labels.lock.json, before any model sees this set. The commit SHA of that
freeze and the SHA of the first run are both recorded in the results report
so the order can be checked.

## Dataset

46 base stories, no cast rotations: 10 dev, 36 test. The base story is the
statistical unit (it is also the fixture unit here, one fixture per story).
Phenomena: messy documents (8), conflicting updates (7), cancellations (7),
ambiguous owners (7), unsupported deadlines (7), prompt injection (10: 8
hostile with distinct carriers and techniques, 2 benign controls).

## Configs

Four runs, identical fixtures, identical scorer, one run each unless budget
allows two (variation between repeat runs is reported if run):

1. extract_v1 on the default CLI model
2. extract_v2 on the default CLI model
3. extract_v2 on claude-haiku-4-5-20251001
4. extract_v2 on claude-sonnet-5

Exact model ids are taken from the run envelopes, not assumed. The runner
uses `--strict-mcp-config '{"mcpServers":{}}'` and `--allowedTools Read,Glob`
and refuses to score if any expected.json differs from labels.lock.json.

## Primary metric and comparison

Primary metric: micro F1 over gold commitments on the TEST portion (36
stories), scored by the existing scorer (match threshold 0.6, workspace must
agree), with story-level cluster bootstrap 95% intervals.

Primary comparison, named in advance: extract_v2 on Haiku 4.5 versus
extract_v1 on the default model, story-level exact paired permutation test
on the test portion. Secondary comparisons (reported, not primary): v2 vs v1
on the default model, Haiku vs default on v2, Sonnet vs default on v2.

Also reported per config: precision, recall, due date accuracy, citation id
accuracy, supported citation rate (support.py checker v2, with its hand
audited agreement rates), isolation violations in stories, injection results
in stories broken down by technique with the benign controls reported
separately, false positives split supported versus unsupported, cost per
scenario, median latency, and the drop from the old test set's numbers.

## Decision rules

- Significance threshold 0.05, two-sided, story-level permutation only.
  Fixture-level numbers are not reported for this set (one fixture per
  story makes them identical anyway).
- No instruction may be edited against the test portion. The 10 dev stories
  are the only tuning surface. If anything is tuned after seeing test
  results, the test portion is spent and any later run on it is reported as
  non-held-out.
- Label corrections after a run: logged in CORRECTIONS.md with the reason
  and both scores; the as-registered number stays primary. The lock file is
  never rewritten after the freeze; corrected labels, if any, are scored as
  a separate clearly labeled pass.
- A scenario whose model call fails for infrastructure reasons (timeout,
  non-JSON envelope) may be re-run once; a model answer is never re-rolled.
  Unparseable model answers score as failures.
- Misses that fall under a SPEC rule the extraction contract does not
  define (marked "defined-here" in SPEC.md) are reported in their own
  column so contract gaps are distinguishable from model errors.

## Expected cost

From the old set: about $0.50 per scenario on the default model, $0.22 on
Sonnet 5, $0.08 on Haiku 4.5. These stories are longer and messier, so the
estimate is 1.5x to 2x that. For 46 stories: two default-model runs about
$35 to $90 total, one Sonnet run about $15 to $20, one Haiku run about $6
to $8. Single pass across all four configs: roughly $60 to $120. The run
does not start until the owner approves this spend.

## Independence evidence recorded at freeze time

- Second labeler: a fresh subagent labeled every story from SPEC.md and the
  sources only; pre-reconciliation agreement and every reconciled
  disagreement are in second-labeler/.
- Text overlap with the old set: 8-word shingle Jaccard, preregistered fail
  threshold 0.20, measured maximum recorded in the freeze commit.
- Stories authored or edited by the project owner, if any, are tagged
  human_authored in scenario.json and reported separately.
