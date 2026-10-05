# Story-level re-analysis of the t108 runs (2026-10-05)

An outside review pointed out that the 54 test fixtures are 18 base stories,
each in three cast rotations, and that the earlier statistics treated the
rotations as independent. That overstated confidence. This report rescores
nothing; it re-analyzes the same saved results with the base story as the
unit of evidence (cluster bootstrap; exact paired permutation over all
2^18 story assignments).

## Corrected labels (current gold)

| run | F1 | story-level 95% CI | old fixture-level CI |
|---|---|---|---|
| v1 baseline | 0.835 | [0.673, 0.971] | [0.720, 0.933] |
| v2 | 0.932 | [0.833, 1.000] | [0.870, 0.982] |
| v2 + Haiku 4.5 | 1.000 | [1.000, 1.000] (degenerate; see note) | [1.000, 1.000] |
| v2 + Sonnet 5 | 0.949 | [0.871, 1.000] | [0.900, 0.989] |

| comparison | diff F1 | story-level p | old fixture-level p |
|---|---|---|---|
| v2 vs v1 | +0.097 | 0.188 | 0.062 |
| Haiku vs default (both v2) | +0.068 | 0.250 | 0.059 |
| Sonnet vs default (both v2) | +0.016 | 0.750 | 0.681 |
| composed v2+Haiku vs v1 | +0.165 | **0.125** | 0.004 |

Original-label versions of every number are in
`2026-10-05-storylevel-reanalysis.json`.

## What this means

- **No comparison on this dataset is statistically significant at the story
  level.** The earlier p = 0.004 for the composed improvement was an artifact
  of counting each story three times. The point estimates stand as observed
  values; the claims of significance do not.
- Haiku's perfect 1.000 means all 18 test stories passed. With zero observed
  failures the bootstrap interval degenerates; by the rule of three, the
  story-level failure rate is only bounded below roughly 17% at 95%
  confidence. 18 stories cannot support a stronger claim.
- Injection resistance on this test split is ONE base story (one technique),
  observed across three rotations and four runs. It should be stated as
  "1 of 1 held-out injection story resisted", not "12 of 12".
- The path to real significance is more independent stories, not more
  rotations. That is what the held-out v2 set is for.
