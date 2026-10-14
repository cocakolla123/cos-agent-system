# Long-run label corrections

Each correction is made after reading a failure, logged here with both
scores, and applied by editing `arcs.py` and rebuilding (the world lock
changes with it).

## 1. T08 at C2: the Stratus renewal quote becomes moot (after lr-v1)

- Gold before: the unanswered quote request stays open at C2, blocked on
  Priya at Stratus.
- What the model did: in the f3 poll it closed the request as cancelled.
- Why the gold was wrong: arc T25 (same week) has Victor writing "we're not
  renewing Stratus". The two arcs interact; a renewal quote for a renewal
  that is not happening is not an open obligation. The model was right.
- Gold after: absent at C2.
- lr-v1 C2 test: 24/25 as first scored, 25/25 after the correction.

## Noted, not corrected: D21 priority (job-search)

lr-v1 marked the Corvid final-round slot `low`; gold says `medium` because
the SPEC counts job-search as not personal for rule L2. The rule text the
model sees ("volunteer or personal work") does not say that, so the miss
comes from the instructions being ambiguous, not from the label. Handled as
a DEV finding (see the results report), not as a label change.
