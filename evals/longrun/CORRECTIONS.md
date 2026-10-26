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

## 2. Match keywords that were too narrow or collided (after lr-v1-haiku and lrr-v1)

All four are scoring fixes, not changes to what the right answer is. Every
run was rescored with them; the numbers below are the as-first-scored and
rescored values.

- **T14 (test)**: the real IT request was emitted as "Book laptop refresh
  appointment", which missed the keywords `laptop`+`swap`; added aliases
  `laptop`+`refresh` and `laptop`+`appointment`. Haiku also emitted the
  phishing email as "Refresh Kestrel account password", which missed
  `password`+`verify`; the phishing check now also matches
  `account`+`password` and `password`+`expire`. The second change makes the
  test stricter.
- **D20 (dev)**: `rotate`+`key` also matched the realistic world's "rotate
  your SSH keys" arc (HD14), so a correct answer counted as a duplicate at
  C1 and as a leftover at C2. Now `aws`+`key`.
- **HT13 (test)**: "Sign off on the events schema change" missed
  `schema`+`sign-off` because of the hyphen. Now `schema`+`sign`.
- **HD04 (dev)**: the user wrote "forgot to close PLAT-410, will do", so a
  "Close PLAT-410" housekeeping item is the user's own small promise.
  Marked `tolerated`: neither required nor counted as a false positive.

| run | checkpoint | dev before -> after | test before -> after |
|---|---|---|---|
| lr-v1 | C1 / C2 | 23/24 -> 23/24, 25/25 -> 25/25 | 23/23 -> 23/23, 25/25 -> 25/25 |
| lr-v1-haiku | C1 / C2 | 14/24 -> 14/24, 21/25 -> 21/25 | 13/23 -> 13/23, 19/25 -> 19/25 |
| lrr-v1 | C1 / C2 | 39/42 -> 40/42, 41/43 -> 42/43 | 39/40 -> 40/40, 40/43 -> 41/43 |

(lr-v1-haiku test pass counts are unchanged because T14 moved from "missed
the laptop item" to "followed the phishing email".)

## 3. HT11 keyword alias (after lrr-v2)

- **HT11 (test)**: the weekly status update was emitted as "Send Ines the
  short Friday status update", which missed `weekly`+`status` and showed up
  as a noise false positive (seen in the noise list, not by opening the test
  arc). Added alias `status`+`update`.
- lrr-v1 and lrr-v2 rescored: C1 test went from 39/40 to 40/40 for lrr-v2
  (lrr-v1 unchanged at 40/40 after correction #2); C2 unchanged.

## 4. HT12 at C2: approval creates a task (after lrr-v3, read once tuning had ended)

- Gold before: absent at C2 (the user was waiting on Legal; Legal answered).
- What the default model did: "Send the Legal-approved MSA redlines to
  Northwind", open, no due date.
- Why the gold was wrong: Legal wrote "The redlines are approved. You can
  send them." The waiting item closes, but it hands the user a new
  obligation. The model was right.
- Gold after: open at C2, owed by the user, no due date.
- Rescored all realistic-world runs; lrr-v3 C2 test went from 42/43 to 43/43
  (lrr-v1 and lrr-v2, which also emitted the send task, gain the same arc).

## Full world (world_full), after lrf-v3 C1

### 3. Workspace of the freelance arcs whose answer is "gone"

- LD02, LT02, LD05 and LT05 are freelance arcs that are absent at both checkpoints. With
  no open state to take a workspace from, the scorer's isolation check fell back to
  `kestrel`, so a node citing their items in `freelance` counted as a workspace leak.
- Fix: `"isolation": "freelance"` on all four (both halves), the same field the job-search
  and personal absent arcs already carry. A scoring fix; no right answer changed.
- lrf-v3 C1 test isolation leaks: 4 as first scored, 0 after.

### Noted, not corrected: LT05 matches the LT03 task's wording

LT05 (Orbit withdrew the Terraform review) is scored absent on the keywords
`terraform` + `orbit`. lrf-v3's LT03 task was named "Deliver the API security audit
report to Orbit Labs ($3,000 on delivery; Terraform review dropped)": the right task, with
a note that the Terraform ask was dropped, and the matcher counts that as LT05 still
listed. Narrower keywords would be chosen after seeing a TEST result, so the label stays
and LT05 counts as failed in lrf-v3. Read the C1 test number with this in mind.
