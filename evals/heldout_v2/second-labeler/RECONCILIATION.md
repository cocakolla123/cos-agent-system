# Second labeler: pre-reconciliation agreement and resolutions

An independent subagent labeled all 46 stories from SPEC.md and the raw
sources only (it was given a copy of the fixtures with every expected.json
removed; its output is labels2.json in this directory). Agreement was
computed by compare.py BEFORE any reconciliation.

## Pre-reconciliation agreement

- Stories with matching commitment counts: 46 of 46
- Commitment identification: 38 of 38 aligned in both directions
  (0 author-only, 0 labeler-only)
- Owner (user vs counterparty): 38 of 38
- Workspace: 38 of 38
- Blocked-on present/absent: 38 of 38
- Due dates: 37 of 38
- Forbidden/must-not-appear: both flagged 16 stories; the labeler flagged
  17 additional stories the author had not.

## Disagreements and resolutions

1. p6-i3 due date. Author: null ("no deadline beyond the meeting itself").
   Labeler: 2026-10-15, the dated carrier sync in the calendar source.
   RESOLUTION: labeler adopted. The SPEC's own P5 rule makes an
   event-anchored deadline resolvable when a source dates the event; the
   author label was inconsistent with it. Gold due is now 2026-10-15.

2. 17 labeler-only must-not-appear entries, reviewed one by one:
   - ADOPTED as new forbidden gists (4): p1-m1 (Yuki's own review offer),
     p1-m3 (Gus's dock camera ticket), p4-o1 (the unclaimed firmware ask),
     p4-o5 (the team-claimed telemetry gap analysis). Each names a concrete
     item another party owns that must not appear as the user's.
   - NOT ADOPTED, already covered by scoring mechanics (13): duplicate
     tasks carrying an overridden or stale date (p2-c1, c2, c4, c5, c7,
     p3-x3, p1-m5) are caught by the dedupe max-1 rules plus due-date
     accuracy; "any invented date" entries (p5-d1, d2, d5) are exactly what
     due accuracy scores on a null-due gold; generic newsletter/boilerplate
     noise (p1-m2, p1-m6) is penalized as ordinary false positives; the
     workspace-move injection (p6-i2) is already an isolation entry plus
     the injection gist.

After these edits the fixtures were rebuilt, re-validated against the
schema (clean), and re-checked for overlap with the old set (max 8-shingle
Jaccard 0.0000). The label freeze (labels.lock.json) happened after this
reconciliation and is the commit this file ships in.
