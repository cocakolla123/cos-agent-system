# Blind second labeler, full world (2026-10-26)

The labeler got only `packet/RULES.md`, `world.json`, the 14 new arcs (LD01-LD07,
LT01-LT07) as shuffled cases, and 300 noise items sampled from items that mention Dana.
It never saw the answer key, the arc code or names. This ran before any model run on the
full world, so the fixes below are not tuning.

## Agreement before reconciliation (`compare.py`, `agreement.json`)

- State (open or gone): 14 of 14 at C1, 13 of 14 at C2.
- For arcs both called open: owner 12 of 12; due 10 of 12; priority 9 of 10;
  workspace 10 of 12.
- Noise: 2 of 300 flagged, and both were items of existing arcs (RTA-101 reopened bug,
  PLAT-420 benchmark), not noise. `make_packet.py --only` kept the other arcs' items in
  the noise pool; fixed, so an `--only` packet now excludes every arc's items. Of the 298
  true noise items, 0 were flagged.

## Disagreements and what changed

1. **LT03 at C2** (Orbit Labs audit). Gold: gone after delivery. Labeler: open, waiting on
   the $3,000 payment, since the invoice went out Oct 15 and nothing showed it was paid.
   The labeler is right that the items left it open. Fixed the world, not the label: a
   Paylink receipt on Oct 24 now shows Orbit paid, matching LD03 (paid after delivery).
2. **LT06 workspace** (move a site off Hostlane). Gold: personal; labeler: oss. "A personal
   blog" could be either. Made it unambiguous: it is now the docs site of Dana's open
   source project tinyq, so `oss` (gold changed to oss; priority L2 low either way). The
   C2 mail no longer offers a new export date, which had made the C2 task read as a
   different one.
3. **LD01 due** (Fernhill milestone payment). Gold: no date; labeler: Sep 3, from "the
   client has 14 days to review it". That is the client's review window, but the rules
   allow resolving it as a date. Removed the sentence, so the item has no date.

The labeler's other notes (Nimbus Ops is a prospective client, not yet one; the Tidewater
offer stays open with no decision at C2) agree with the gold.
