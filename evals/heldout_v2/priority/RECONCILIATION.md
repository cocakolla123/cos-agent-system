# Priority labels: independent labeler and reconciliation

Rules: `../PRIORITY_RULES.md`, frozen in commit 557129a before any
priority label was written and before any model output was scored for
priority.

- Author labels: the preview table in PRIORITY_RULES.md (39 tasks,
  including the corrected p6-i5 reply from CORRECTIONS.md).
- Independent labeler: a fresh subagent given only the rules (without the
  preview table), the raw sources, and the task list. It never saw the
  author's labels or any model output. Its labels: `labels2_independent.json`.

## Pre-reconciliation agreement

38 of 39 tasks (97%).

## Disagreement and resolution

1. p2-c5 (usage heatmap draft, client, due Oct 23). Author: medium (M1).
   Labeler: low (L3). The client's email says "No rush on my account", and
   L3 names "no rush" explicitly. RESOLUTION: labeler adopted; the author
   missed the wording.

Final labels: `labels.json` (19 high, 16 medium, 4 low), frozen by
`priority.lock.json`. Scored by `../score_priority.py`.
