#!/usr/bin/env python3
"""Held-out v2 stories, part A: P1 messy documents, P2 conflicting updates,
P3 cancellations. Labeling rules are in SPEC.md; every gold commitment
carries exact-substring support quotes."""

from world import (TODAY, USER, mail, outmail, slackmsg, tkt, calevent,
                   document, quoted, commitment, expected, frm,
                   SIG_DRITAN, FOOTER_LEGAL, HTML_REMNANT)


# ---------------------------------------------------------------------------
# P1: messy documents
# ---------------------------------------------------------------------------

def m1():
    th = "th-sla"
    first = mail("yuki", "routing SLA matrix",
                 "Riley, the carrier SLA matrix still lists the 2025 lanes. "
                 "Can you refresh it when you get a chance?" + SIG_DRITAN.replace(
                     "Dritan Pasha | Dir. Network Operations", "Yuki Onoda | NetOps"),
                 "2026-10-02T15:04:00Z", thread=th)
    mid = mail("dritan", "RE: routing SLA matrix",
               "+1 to Yuki. Also: the Meridian lane review got pulled in, so I "
               "need the revised SLA matrix by Oct 16, not end of month.\n\n"
               + quoted("On Oct 2, Yuki Onoda wrote:",
                        "Riley, the carrier SLA matrix still lists the 2025 "
                        "lanes. Can you refresh it when you get a chance?")
               + SIG_DRITAN, "2026-10-06T09:12:00Z", thread=th)
    last = mail("yuki", "RE: RE: routing SLA matrix",
                "np, i can review a draft thurs if that helps\n\n"
                + quoted("On Oct 6, Dritan Pasha wrote:",
                         "I need the revised SLA matrix by Oct 16, not end of "
                         "month.") + FOOTER_LEGAL,
                "2026-10-06T16:40:00Z", thread=th)
    exp = expected([commitment(
        ["sla", "matrix", "revised"], "user", "dritan.pasha", "2026-10-16",
        "ternlog", [mid["id"], first["id"], last["id"]],
        support=[{"source": mid["id"],
                  "quote": "I need the revised SLA matrix by Oct 16"}])],
        forbidden=[["yuki", "review", "draft"]],
        dedupe=[{"gist": ["sla", "matrix"], "max": 1}])
    return [first, mid, last], exp, "deadline set mid-thread under quoting and signatures"


def m2():
    th = "th-fwd"
    fwd = mail("celeste", "Fwd: anomaly report scope",
               "Riley, forwarding Ibrahim's note. Please treat his dates as "
               "ours.\n\n---------- Forwarded message ----------\nFrom: "
               "Ibrahim Khoury <ibrahim@quarryanalytics.example>\nDate: Oct 7, "
               "2026\nSubject: anomaly report scope\n\nWe want the first draft "
               "of the sensor anomaly report by Oct 17. Methods section can be "
               "thin; the appendix tables matter." + FOOTER_LEGAL.replace(
                   "Tern Logistics Ltd", "Quarry Analytics LLC"),
               "2026-10-07T18:22:00Z", thread=th)
    noise = mail("digest", "Ops Digest #88",
                 "Five links on cold-chain telemetry. Unsubscribe any time.",
                 "2026-10-08T07:00:00Z")
    exp = expected([commitment(
        ["anomaly", "report", "draft"], "user", "celeste", "2026-10-17",
        "quarry", [fwd["id"]],
        support=[{"source": fwd["id"],
                  "quote": "first draft of the sensor anomaly report by Oct 17"}])])
    return [fwd, noise], exp, "commitment inside a forwarded chain with legal footer"


def m3():
    doc = document(
        "Ops sync 10/08 - raw transcript",
        "[00:03] dritan: ok carrier scorecards. yuki you had the— \n"
        "[00:03] yuki: --sorry, mic. the scorecard refresh. someone needs to own\n"
        "[00:04] dritan: riley you touched it last quarter right\n"
        "[00:04] riley: yeah i can take the scorecard refresh\n"
        "[00:04] dritan: ok riley owns carrier scorecard refresh. lets say due "
        "oct 20 so it lands before the QBR\n"
        "[00:05] gus: can we talk about the dock cameras?? \n"
        "[00:05] dritan: parking lot. next item...\n"
        "[00:11] (crosstalk, inaudible)\n"
        "[00:12] dritan: fine, gus files a ticket. meeting over.",
        "2026-10-08T17:30:00Z", author=frm("dritan"))
    exp = expected([commitment(
        ["carrier", "scorecard", "refresh"], "user", "dritan.pasha",
        "2026-10-20", "ternlog", [doc["id"]],
        support=[{"source": doc["id"],
                  "quote": "riley owns carrier scorecard refresh. lets say due "
                           "oct 20"}])],
        forbidden=[["dock", "camera"]])
    return [doc], exp, "transcript with crosstalk; user claimed the item verbally"


def m4():
    msg = mail("petra", "driver rosterr for next wk" + HTML_REMNANT[:6],
               "hi riley!! quick one =20 " + HTML_REMNANT + " the saturday "
               "routes changed agian so can u send the updated driver roster "
               "by thursday? tahnks so much <br> petra",
               "2026-10-09T20:15:00Z")
    exp = expected([commitment(
        ["driver", "roster", "updated"], "user", "petra", "2026-10-15",
        "beacon", [msg["id"]],
        support=[{"source": msg["id"],
                  "quote": "send the updated driver roster by thursday"}])])
    return [msg], exp, "typos and HTML remnants; relative Thursday resolves to Oct 15"


def m5():
    th = "th-vendor"
    older = mail("gus", "pallet scanner rollout",
                 "Vendor says install window is Oct 18. Please have the bay "
                 "prep checklist done by Oct 15.",
                 "2026-10-05T11:00:00Z", thread=th)
    newer = mail("gus", "RE: pallet scanner rollout",
                 "Hold on - disregard the date below until the vendor "
                 "confirms. Install may slip. The checklist is still yours, "
                 "just no date yet.\n\n"
                 + quoted("On Oct 5, Gus Okonkwo wrote:",
                          "Please have the bay prep checklist done by Oct 15."),
                 "2026-10-08T13:45:00Z", thread=th)
    exp = expected([commitment(
        ["bay", "prep", "checklist"], "user", "gus.okonkwo", None,
        "ternlog", [newer["id"], older["id"]],
        support=[{"source": newer["id"],
                  "quote": "The checklist is still yours, just no date yet"}])],
        dedupe=[{"gist": ["prep", "checklist"], "max": 1}])
    return [older, newer], exp, "the only date lives in quoted text and is voided"


def m6():
    body = ("Team, Monday grab-bag, long one, sorry:\n"
            "1. Badge printer is fixed.\n"
            "2. Fleet fuel cards rotate next month.\n"
            "3. The Westgate dock audit passed.\n"
            "4. Parking level 2 closed Thursday.\n"
            "5. Riley - you still owe the Q4 capacity forecast, need it by "
            "Oct 21 for budget planning.\n"
            "6. New hires start the 26th.\n"
            "7. Please stop microwaving fish.\n"
            "8. Holiday schedule poll closes Friday.\n"
            "9. The espresso machine saga continues.\n"
            "10. Offsite photos are up on the drive.")
    msg = mail("gus", "ops grab-bag, wk of 10/05", body, "2026-10-05T14:00:00Z",
               to=[USER["email"], PEOPLE_LIST])
    exp = expected([commitment(
        ["capacity", "forecast", "q4"], "user", "gus.okonkwo", "2026-10-21",
        "ternlog", [msg["id"]],
        support=[{"source": msg["id"],
                  "quote": "you still owe the Q4 capacity forecast, need it by "
                           "Oct 21"}])])
    return [msg], exp, "one real item buried at position 5 of 10"


PEOPLE_LIST = "ops-all@ternlog.example"


def m7():
    msg = mail("celeste", "fianl review pass",
               "Riley - one more pass on teh calibration whitepaper plz. Due "
               "Oct 14, 5pm AoE (anywhere on earth, so dont stress the "
               "timezone). Track changes on.",
               "2026-10-09T08:30:00Z")
    exp = expected([commitment(
        ["calibration", "whitepaper", "review"], "user", "celeste",
        "2026-10-14", "quarry", [msg["id"]],
        support=[{"source": msg["id"],
                  "quote": "Due Oct 14, 5pm AoE"}])])
    return [msg], exp, "typos and a timezone suffix on the stated date"


def m8():
    th = "th-dock"
    ask = mail("dritan", "dock audit photos",
               "Insurance wants photo evidence from the Westgate dock audit. "
               "Do you have them?" + SIG_DRITAN, "2026-10-07T10:05:00Z",
               thread=th)
    reply = outmail("dritan", "RE: dock audit photos",
                    "I have them on the work phone. I'll get you the dock "
                    "audit photos before Friday.\n\n"
                    + quoted("On Oct 7, Dritan Pasha wrote:",
                             "Insurance wants photo evidence from the Westgate "
                             "dock audit. Do you have them?"),
                    "2026-10-07T12:40:00Z", thread=th)
    exp = expected([commitment(
        ["dock", "audit", "photos"], "user", "dritan.pasha", "2026-10-09",
        "ternlog", [reply["id"], ask["id"]],
        support=[{"source": reply["id"],
                  "quote": "I'll get you the dock audit photos before Friday"}])])
    return [ask, reply], exp, "the user's own sent promise, now overdue"


# ---------------------------------------------------------------------------
# P2: conflicting updates
# ---------------------------------------------------------------------------

def c1():
    peer = slackmsg("#netops", "yuki",
                    "@riley QBR deck - can you have your lanes section done "
                    "by Oct 15?", "2026-10-06T19:00:00Z")
    boss = mail("dritan", "QBR deck timing",
                "Yuki said Oct 15 for your lanes section. I need it a day "
                "earlier - Oct 14 - so I can merge the master deck."
                + SIG_DRITAN, "2026-10-08T08:20:00Z")
    exp = expected([commitment(
        ["lanes", "section", "deck"], "user", "dritan.pasha", "2026-10-14",
        "ternlog", [boss["id"], peer["id"]],
        support=[{"source": boss["id"],
                  "quote": "I need it a day earlier - Oct 14"}])],
        dedupe=[{"gist": ["lanes", "section"], "max": 1}])
    return [peer, boss], exp, "manager's date beats the peer's"


def c2():
    t = tkt("QA-114", "Ingest latency writeup", "open",
            "2026-10-03T09:00:00Z",
            comments=[{"author": USER["email"], "date": "2026-10-03T09:00:00Z",
                       "text": "Self-assigned. Targeting Oct 20."}])
    override = mail("celeste", "latency writeup - board moved",
                    "Board review moved up. We need the ingest latency "
                    "writeup by Oct 16. Sorry to squeeze you.",
                    "2026-10-09T15:10:00Z")
    exp = expected([commitment(
        ["ingest", "latency", "writeup"], "user", "celeste", "2026-10-16",
        "quarry", [override["id"], t["id"]],
        support=[{"source": override["id"],
                  "quote": "we need the ingest latency writeup by Oct 16".replace(
                      "we", "We")}])],
        dedupe=[{"gist": ["latency", "writeup"], "max": 1}])
    return [t, override], exp, "client override beats the owner's own target"


def c3():
    t = tkt("TL-310", "Dock sensor recalibration plan", "open",
            "2026-10-08T10:00:00Z",
            comments=[{"author": frm("gus"), "date": "2026-10-08T10:00:00Z",
                       "text": "Plan doc due Oct 19 per maintenance window."}])
    e = mail("yuki", "recal plan",
             "fyi the recal plan is due Oct 21 per the revised maintenance "
             "window", "2026-10-08T16:30:00Z")
    exp = expected([commitment(
        ["recalibration", "plan"], "user", "gus.okonkwo", None,
        "ternlog", [t["id"], e["id"]],
        support=[{"source": t["id"],
                  "quote": "Plan doc due Oct 19 per maintenance window."},
                 {"source": e["id"],
                  "quote": "due Oct 21 per the revised maintenance window"}])],
        dedupe=[{"gist": ["recalibration", "plan"], "max": 1}])
    return [t, e], exp, "ticket and email disagree within 24h: deadline disputed, gold due null"


def c4():
    boss = mail("dritan", "carrier insurance certificates",
                "Collect the updated insurance certificates from the top five "
                "carriers by end of month." + SIG_DRITAN,
                "2026-10-06T09:00:00Z")
    peer = slackmsg("#netops", "yuki",
                    "@riley insurance certs - pretty sure dritan actually "
                    "wants those by Oct 18, fyi", "2026-10-09T11:00:00Z")
    exp = expected([commitment(
        ["insurance", "certificates", "carriers"], "user", "dritan.pasha",
        "2026-10-31", "ternlog", [boss["id"], peer["id"]],
        support=[{"source": boss["id"],
                  "quote": "by end of month"}])],
        dedupe=[{"gist": ["insurance", "certificates"], "max": 1}])
    return [boss, peer], exp, "a peer's secondhand date does not override the manager's"


def c5():
    th = "th-heat"
    pm = mail("celeste", "heatmap draft",
              "Ibrahim needs the usage heatmap draft. Friday would be ideal.",
              "2026-10-07T10:00:00Z", thread=th)
    owner = mail("ibrahim", "RE: heatmap draft",
                 "No rush on my account - end of next week works, say Oct 23. "
                 "Quality over speed on this one.\n\n"
                 + quoted("On Oct 7, Celeste Beaumont wrote:",
                          "Ibrahim needs the usage heatmap draft. Friday would "
                          "be ideal."), "2026-10-09T09:40:00Z", thread=th)
    exp = expected([commitment(
        ["usage", "heatmap", "draft"], "user", "ibrahim", "2026-10-23",
        "quarry", [owner["id"], pm["id"]],
        support=[{"source": owner["id"],
                  "quote": "end of next week works, say Oct 23"}])],
        dedupe=[{"gist": ["heatmap", "draft"], "max": 1}])
    return [pm, owner], exp, "the person the work is for relaxes the relayed date"


def c6():
    first = mail("dritan", "integration memo",
                 "Draft the WMS integration memo this week." + SIG_DRITAN,
                 "2026-10-05T09:30:00Z")
    override = slackmsg("#netops", "dritan",
                        "@riley change of plan - do the vendor comparison "
                        "INSTEAD of the integration memo this week. Need it "
                        "by Oct 17. Memo moves to next sprint, no date.",
                        "2026-10-08T14:05:00Z")
    exp = expected([commitment(
        ["vendor", "comparison"], "user", "dritan.pasha", "2026-10-17",
        "ternlog", [override["id"]],
        support=[{"source": override["id"],
                  "quote": "do the vendor comparison INSTEAD"}])],
        forbidden=[["integration", "memo", "week"]])
    return [first, override], exp, "explicit instead-of override replaces the task"


def c7():
    invite = calevent("Quarry pipeline review",
                      "2026-10-14T17:00:00Z", "2026-09-30T12:00:00Z",
                      attendees=[USER["email"], PEOPLE_ADDR_CELESTE])
    push = mail("celeste", "pipeline review",
                "Pushing our review out a week to Oct 21, same time; the "
                "calendar invite is stale. Please have the prep deck ready "
                "before the review.", "2026-10-08T12:00:00Z")
    exp = expected([commitment(
        ["prep", "deck", "review"], "user", "celeste", "2026-10-21",
        "quarry", [push["id"]],
        support=[{"source": push["id"],
                  "quote": "Pushing our review out a week to Oct 21"}])],
        dedupe=[{"gist": ["prep", "deck"], "max": 1}])
    return [invite, push], exp, "stale calendar date loses to the organizer's email"


PEOPLE_ADDR_CELESTE = "celeste@quarryanalytics.example"


# ---------------------------------------------------------------------------
# P3: cancellations
# ---------------------------------------------------------------------------

def x1():
    th = "th-count"
    ask = mail("petra", "pantry inventory count",
               "Can you run the monthly pantry inventory count this weekend?",
               "2026-10-06T18:00:00Z", thread=th)
    cancel = mail("petra", "RE: pantry inventory count",
                  "Actually skip it this month - the county is doing their "
                  "own audit so a double count just makes noise. Nothing "
                  "needed from you.\n\n"
                  + quoted("On Oct 6, Petra Lindgren wrote:",
                           "Can you run the monthly pantry inventory count "
                           "this weekend?"), "2026-10-09T10:00:00Z", thread=th)
    exp = expected([], forbidden=[["pantry", "inventory", "count"]])
    return [ask, cancel], exp, "outright cancellation removes the obligation"


def x2():
    th = "th-two"
    ask = mail("celeste", "board pack pieces",
               "Two things for the board pack: the summary slides and the "
               "budget reconciliation sheet, both by Oct 18.",
               "2026-10-05T13:00:00Z", thread=th)
    part = mail("celeste", "RE: board pack pieces",
                "Update: finance is taking the budget reconciliation sheet "
                "in-house, so drop that one. The summary slides are still "
                "yours, still Oct 18.\n\n"
                + quoted("On Oct 5, Celeste Beaumont wrote:",
                         "the summary slides and the budget reconciliation "
                         "sheet, both by Oct 18"),
                "2026-10-08T09:30:00Z", thread=th)
    exp = expected([commitment(
        ["summary", "slides"], "user", "celeste", "2026-10-18",
        "quarry", [part["id"], ask["id"]],
        support=[{"source": part["id"],
                  "quote": "The summary slides are still yours, still Oct 18"}])],
        forbidden=[["budget", "reconciliation", "sheet"]],
        dedupe=[{"gist": ["summary", "slides"], "max": 1}])
    return [ask, part], exp, "partial cancellation keeps only the surviving half"


def x3():
    t = tkt("TL-287", "Chassis telemetry backfill", "open",
            "2026-09-28T09:00:00Z",
            comments=[
                {"author": frm("gus"), "date": "2026-09-28T09:00:00Z",
                 "text": "Backfill the September gaps. Due Oct 10."},
                {"author": frm("gus"), "date": "2026-10-03T11:00:00Z",
                 "text": "Postponed indefinitely - upstream schema is moving."},
                {"author": frm("gus"), "date": "2026-10-09T16:20:00Z",
                 "text": "Back on. Schema froze. New due date Oct 22."}])
    exp = expected([commitment(
        ["telemetry", "backfill"], "user", "gus.okonkwo", "2026-10-22",
        "ternlog", [t["id"]],
        support=[{"source": t["id"],
                  "quote": "Back on. Schema froze. New due date Oct 22."}])],
        dedupe=[{"gist": ["telemetry", "backfill"], "max": 1}])
    return [t], exp, "cancelled then reinstated with a new date"


def x4():
    th = "th-exp"
    first = mail("ibrahim", "data export",
                 "Please build the nightly CSV export for the sensor table. "
                 "Due Oct 19.", "2026-10-05T10:00:00Z", thread=th)
    swap = mail("ibrahim", "RE: data export",
                "Scratch the CSV - forget the CSV export entirely. Build the "
                "query API endpoint instead, same deadline Oct 19.\n\n"
                + quoted("On Oct 5, Ibrahim Khoury wrote:",
                         "Please build the nightly CSV export for the sensor "
                         "table. Due Oct 19."),
                "2026-10-08T11:15:00Z", thread=th)
    exp = expected([commitment(
        ["query", "api", "endpoint"], "user", "ibrahim", "2026-10-19",
        "quarry", [swap["id"]],
        support=[{"source": swap["id"],
                  "quote": "Build the query API endpoint instead, same "
                           "deadline Oct 19"}])],
        forbidden=[["csv", "export"]])
    return [first, swap], exp, "superseded by a different task, deadline carried over"


def x5():
    th = "th-nov"
    invite = mail("novara", "Novara Systems - systems design interview",
                  "Your systems design interview is scheduled for Oct 16. "
                  "Please prepare a 20 minute walkthrough of a past project.",
                  "2026-10-02T17:00:00Z", thread=th)
    cancel = mail("novara", "RE: Novara Systems - systems design interview",
                  "I am sorry to share that the position has been filled "
                  "internally and the Oct 16 interview is cancelled. We will "
                  "keep your profile on file.\n\n"
                  + quoted("Earlier:", "Your systems design interview is "
                           "scheduled for Oct 16."),
                  "2026-10-09T19:30:00Z", thread=th)
    exp = expected([], forbidden=[["walkthrough", "prepare", "interview"],
                                  ["novara", "interview", "oct"]])
    return [invite, cancel], exp, "recruiter cancellation kills the prep task"


def x6():
    th = "th-hold"
    work = mail("celeste", "dashboard milestone 2",
                "Milestone 2 (alerting rules) is due Oct 24.",
                "2026-10-01T09:00:00Z", thread=th)
    hold = mail("celeste", "RE: dashboard milestone 2",
                "Quarry is pausing the dashboard project - on hold until "
                "further notice while legal sorts the data sharing agreement. "
                "Please stop work; we will re-scope when it unfreezes.\n\n"
                + quoted("On Oct 1, Celeste Beaumont wrote:",
                         "Milestone 2 (alerting rules) is due Oct 24."),
                "2026-10-10T14:00:00Z", thread=th)
    exp = expected([], forbidden=[["milestone", "alerting", "rules"]])
    return [work, hold], exp, "project on hold: the dated obligation must not stay open"


def x7():
    th = "th-fair"
    ask = mail("petra", "volunteer fair table",
               "Could you staff our table at the volunteer fair on Oct 17? "
               "Setup is 8am.", "2026-10-03T12:00:00Z", thread=th)
    cancel = mail("petra", "RE: volunteer fair table",
                  "The fair organizers cancelled the whole event (venue "
                  "flooding). Nothing needed Oct 17 after all.\n\n"
                  + quoted("On Oct 3, Petra Lindgren wrote:",
                           "Could you staff our table at the volunteer fair "
                           "on Oct 17?"), "2026-10-08T15:00:00Z", thread=th)
    wonder = slackmsg("#beacon-volunteers", "petra",
                      "(different petra hat: does anyone know if the fair "
                      "might be rescheduled? no news yet)",
                      "2026-10-10T09:00:00Z")
    exp = expected([], forbidden=[["volunteer", "fair", "table"],
                                  ["staff", "table", "oct"]])
    return [ask, cancel, wonder], exp, "a later open question does not revive a cancellation"


STORIES_A = [
    ("p1-m1", "messy", m1), ("p1-m2", "messy", m2), ("p1-m3", "messy", m3),
    ("p1-m4", "messy", m4), ("p1-m5", "messy", m5), ("p1-m6", "messy", m6),
    ("p1-m7", "messy", m7), ("p1-m8", "messy", m8),
    ("p2-c1", "conflict", c1), ("p2-c2", "conflict", c2),
    ("p2-c3", "conflict", c3), ("p2-c4", "conflict", c4),
    ("p2-c5", "conflict", c5), ("p2-c6", "conflict", c6),
    ("p2-c7", "conflict", c7),
    ("p3-x1", "cancellation", x1), ("p3-x2", "cancellation", x2),
    ("p3-x3", "cancellation", x3), ("p3-x4", "cancellation", x4),
    ("p3-x5", "cancellation", x5), ("p3-x6", "cancellation", x6),
    ("p3-x7", "cancellation", x7),
]
