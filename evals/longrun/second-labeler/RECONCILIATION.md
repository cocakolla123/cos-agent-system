# Blind second labeler: agreement and resolutions (realistic world)

## Method

An independent subagent labeled the realistic long-run world from raw items
only. It never saw the arcs, the phenomena, the stories or `gold.json`; its
instructions confined it to the packet directory.

- **Arcs (Task 1):** all 87 arcs, shuffled and renamed `case-01`..`case-87`
  (mapping in `mapping.json`, which the labeler never saw). Each case holds the
  arc's source items plus their context: the whole Slack thread, the whole mail
  thread, every snapshot of the same ticket or PR. The labeler decided, at C1 and
  at C2, whether Dana has an open obligation, with its due date, priority (C1),
  workspace and direction.
- **Noise (Task 2):** a second subagent read 120 items, sampled with a fixed seed,
  that are in no arc but mention or address Dana. It listed any that create an
  obligation on her. This checks for tasks the answer key is missing.

Packet: `packet/` (`make_packet.py`). Labels: `packet/labels2-cases.json` and
`packet/labels2-noise.json`. Agreement was computed by `compare.py` before any
reconciliation (`agreement.md`).

## Agreement before reconciliation

| field | C1 | C2 |
|---|---|---|
| open vs absent | 81 of 82 | 85 of 86 |
| due date (both open) | 49 of 49 | 41 of 41 |
| priority (both open) | 49 of 49 | not labeled at C2 |
| workspace (both open) | 49 of 49 | 41 of 41 |
| direction: Dana's move or waiting (both open) | 49 of 49 | 41 of 41 |

Noise: 0 of the 120 sampled items flagged as obligations. That agrees with the
answer key, which has no task outside the arcs. This second subagent finished
quickly (5 tool calls), so treat this as a light check. Its report names specific
items from across the sample and explains why each one is not an ask.

## Disagreements and resolutions

1. **D20 at C1 (rotate the leaked AWS key).** Answer key: open. Labeler: absent,
   citing Dana's "rotated and revoked the AWS key" dated 2026-10-13 09:00.
   **Answer key kept.** The C1 crawl covers items dated before 2026-10-13
   (`replay.steps`: `date < today`), so the system cannot see that message at C1.
   The labeler followed my rules sheet, which wrongly said "on or before
   2026-10-13". The fault is in the rules sheet, not in either label.
2. **T08 at C2 (Stratus renewal quote).** Answer key: absent. Labeler: open,
   waiting on Priya's quote. **Answer key kept.** The renewal is cancelled in
   another thread (logged as correction 1 in `../CORRECTIONS.md`). The labeler
   saw each case on its own and said so in its report ("I didn't carry that
   across cases").

No label changes.

## Errors in the rules sheet, found by the labeler

- It called 2026-10-13 a Monday; it is a Tuesday. The cut-off dates it gave
  (high on or before 10-16, H3 on or before 10-20) were right, and the labeler
  used the real calendar. The same slip in the demo's daily log ("Monday, Oct 13")
  is fixed.
- The "on or before the checkpoint" window, above.

## Ambiguities the labeler raised (agreed with the key, listed for the record)

The labeler raised a dozen judgment calls: "next Tuesday" sent on a Thursday,
"end of day Monday", "before Thursday's review", a recurring Friday update, a
ticket left open after the work was done, the director-vs-manager question, a
security-flavored client deliverable, and a dentist's "please call to
reschedule". On every one, its label matched the answer key's.

## Limits

One labeler, which is a model, not a person. The arc packets give each arc its
own context, so a cross-arc fact (as in T08) is invisible to it. The noise audit
samples 120 of the 2,890 items that mention Dana outside the arcs.
