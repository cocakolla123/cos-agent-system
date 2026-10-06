# Priority rules for heldout_v2

Status: decided 2026-10-06 (the owner delegated the open questions; the
decisions and reasons are under "Decisions"). These rules are frozen before
any priority label is written or any model output is scored for priority.

"Today" in every story is Monday 2026-10-12.

## Rules (first rule that matches wins)

**High**

- H1. Overdue, or due within 3 days (on or before Thursday Oct 15).
- H2. Marked "ASAP" or "urgent" by your manager or a client.
- H3. Asked by your manager or a client, due within 7 days (on or before
  Monday Oct 19).
- H4. Security or access work with a stated date: the task is about a
  TLS/SSL certificate, a credential or password, an access log or access
  audit, or a security incident. (Insurance certificates, permits and
  runbooks that merely mention access do not count.)

**Low**

- L1. A quick reply to a coworker's question, with no deadline (for
  example "is it phishing?"). This is your rule from 2026-10-05.
- L2. Volunteer or personal work due more than 7 days out, or with no date.
- L3. Explicitly soft wording: "no rush", "when you get a chance", "would be
  great".

**Medium**

- M1. Everything else: dated work more than the windows above, work from
  peers, and undated work requests.

Who counts as what, from the story world: Dritan Pasha is your manager;
Celeste Beaumont and Ibrahim Khoury are clients (Quarry); Petra Lindgren
leads the volunteer work (Beacon); Yuki Onoda and Riley Chen are peers.
Gus Okonkwo is a peer (see Decisions).

## Preview: what these rules would assign

All 39 tasks in the answer key (including the corrected p6-i5 reply).
19 high, 17 medium, 3 low.

| story | task | due | asked by | priority | rule |
|---|---|---|---|---|---|
| p1-m1 (dev) | revised SLA matrix | Oct 16 | manager | high | H3 |
| p1-m2 | anomaly report draft | Oct 17 | client | high | H3 |
| p1-m3 | carrier scorecard refresh | Oct 20 | manager | medium | M1 |
| p1-m4 | driver roster | Oct 15 | volunteer lead | high | H1 |
| p1-m5 (dev) | bay prep checklist | none | Gus | medium | M1 |
| p1-m6 | Q4 capacity forecast | Oct 21 | Gus | medium | M1 |
| p1-m7 | whitepaper review | Oct 14 | client | high | H1 |
| p1-m8 | dock audit photos (your own promise) | Oct 9 | manager | high | H1 overdue |
| p2-c1 (dev) | lanes section of deck | Oct 14 | manager | high | H1 |
| p2-c2 | ingest latency writeup | Oct 16 | client | high | H3 |
| p2-c3 | recalibration plan | disputed | Gus | medium | M1 |
| p2-c4 | insurance certificates | Oct 31 | manager | medium | M1 |
| p2-c5 | usage heatmap draft | Oct 23 | client | medium | M1 |
| p2-c6 (dev) | vendor comparison | Oct 17 | manager | high | H3 |
| p2-c7 | prep deck review | Oct 21 | client | medium | M1 |
| p3-x2 (dev) | summary slides | Oct 18 | client | high | H3 |
| p3-x3 | telemetry backfill | Oct 22 | Gus | medium | M1 |
| p3-x4 | query API endpoint | Oct 19 | client | high | H3 |
| p4-o2 (dev) | forklift audit paperwork | Oct 20 | Gus | medium | M1 |
| p4-o4 | permit renewal | Oct 20 | manager | medium | M1 |
| p4-o7 | grant form | Oct 24 | volunteer lead | low | L2 |
| p5-d1 | revised retainer quote ("soon") | none | client | medium | M1 |
| p5-d2 | outage postmortem ("ASAP") | none | manager | high | H2 |
| p5-d3 (dev) | cycle count sheet | Oct 9 | Gus | high | H1 overdue |
| p5-d4 | lane cost model | Oct 23 | manager | medium | M1 |
| p5-d5 | renewal one-pager | none | client | medium | M1 |
| p5-d6 | freezer maintenance log ("would be great") | Oct 19 | volunteer lead | low | L3 |
| p5-d7 | schema diff | Oct 15 | client | high | H1 |
| p6-i1 (dev) | book fumigation vendor | Oct 16 | peer | medium | M1 |
| p6-i2 | thresholds doc | Oct 18 | Gus | medium | M1 |
| p6-i3 | lane cost one-pager | Oct 15 | peer | high | H1 |
| p6-i4 | portal access runbook | Oct 17 | Gus | medium | M1 |
| p6-i5 | badge audit log | Oct 16 | peer | high | H4 |
| p6-i5 | reply: is it phishing? | none | peer | low | L1 |
| p6-i6 | renew TLS cert | Oct 20 | peer | high | H4 |
| p6-i7 | yard lighting quotes | none | manager | medium | M1 |
| p6-i8 | confirm FreightMetrics agreement | Oct 15 | Gus | high | H1 |
| p6-i9 (dev) | September expense report | Oct 15 | manager | high | H1 |
| p6-i10 | routing memo | Oct 16 | manager | high | H3 |

## Decisions

1. **Gus Okonkwo is a peer.** In p1-m3 Dritan runs the meeting and assigns
   Gus work ("fine, gus files a ticket"), and Dritan is the only person the
   stories ever call the manager.
2. **Windows stay at 3 days (anyone) and 7 days (manager or client).**
   Three days is "this week" from a Monday; seven days is "before the next
   planning cycle". Story dates run Oct 9 to Oct 31, so both windows split
   the set meaningfully.
3. **An undated manager request is medium.** In p6-i7 Dritan says "Pick
   your own timeline, just tell me what it is", which is an explicit signal
   that it is not urgent.
4. **Security and access work with a date is high (rule H4).** An expired
   TLS certificate takes the tracking portal down, and the badge audit log
   check follows a phishing attempt. Missing either has consequences beyond
   one person, so it outranks who asked. The rule is limited to named
   security objects (TLS/SSL certificates, credentials, access logs or
   audits, incidents) so that labelers apply it the same way.
5. **Volunteer work is not automatically lower.** A near deadline still
   wins (p1-m4, the driver roster due Oct 15, stays high: drivers depend on
   it). Volunteer work only drops to low when it is more than 7 days out or
   undated (rule L2).

## How it gets tested (after approval)

1. The approved rules are frozen in this directory.
2. A separate labeler that never sees model output assigns a priority to
   each task from these rules and the sources alone. Its labels are
   compared with the preview above, and every disagreement is logged and
   resolved, the same process as `second-labeler/`.
3. The reconciled labels are frozen with their own lock file.
4. The saved model outputs are scored for priority on the tasks each model
   got right: exact-match accuracy, plus how often it was off by two levels
   (high vs low). No new model runs. It is reported as a separate post-run
   pass, because the rules were written after the runs.

One caveat to keep in the report: the models were never given these rules.
Their instructions only say "high/medium/low". So this measures how well
their sense of priority matches yours, not whether they follow a rule.
