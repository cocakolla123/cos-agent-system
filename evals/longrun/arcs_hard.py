"""Harder arcs for the 'hard' world: subtle wording, conditions, hand-offs,
stale tracker state, recurring asks. Same gold format as arcs.py, plus
optional "aliases" on open states: other gists that describe the same task
(used to count duplicates worded differently)."""

from world import who, addr, att, WORK, PERSONAL
from arcs import open_, absent

HARD_ARCS = []


def arc(aid, split, phenomenon):
    def deco(fn):
        HARD_ARCS.append((aid, split, phenomenon, fn))
        return fn
    return deco


def with_aliases(st, *aliases):
    st["aliases"] = [list(a) for a in aliases]
    return st


# ------------------------------------------------------------- sarcasm
@arc("HD01", "dev", "sarcasm is not a promise")
def hd01(s):
    a = s.slack("2026-09-18T16:30:00Z", "#platform", "alex.p",
                "while you're at it can you also rewrite the whole billing service by Friday 😂")
    b = s.slack("2026-09-18T16:31:00Z", "#platform", "dana.k",
                "sure, I'll get right on that 🙃", thread_ts=a)
    return {"sources": [a, b],
            "c1": absent(["billing", "service"]), "c2": absent(["billing", "service"])}


@arc("HT01", "test", "sarcasm is not a promise")
def ht01(s):
    a = s.slack("2026-10-02T17:00:00Z", "#random", "tomas",
                "Dana, want to own the entire mobile app too? lol")
    b = s.slack("2026-10-02T17:01:00Z", "#random", "dana.k",
                "absolutely, shipping it by Monday 😂", thread_ts=a)
    return {"sources": [a, b],
            "c1": absent(["mobile", "app"]), "c2": absent(["mobile", "app"])}


# --------------------------------------------------------- conditional
@arc("HD02", "dev", "conditional promise")
def hd02(s):
    a = s.slack("2026-09-28T10:00:00Z", "D-dana-raj", "dana.k",
                "if you can send me the usage export by Wednesday, I'll do the churn report "
                "by Friday")
    b = s.slack("2026-09-30T09:00:00Z", "D-dana-raj", "raj",
                "usage export is in the shared drive, all yours")
    return {"sources": [a, b],
            "c1": open_(["churn", "report"], "kestrel", "2026-10-02", "high"),
            "c2": open_(["churn", "report"], "kestrel", "2026-10-02", None)}


@arc("HT02", "test", "conditional promise")
def ht02(s):
    a = s.email("2026-09-29T10:00:00Z", WORK, "legal@kestrel.example", "DPA addendum",
                "If legal approves the approach, I'll draft the DPA addendum for Northwind "
                "by Oct 15.", sent=True)
    b = s.email("2026-10-05T11:00:00Z", "Kestrel Legal <legal@kestrel.example>", WORK,
                "RE: DPA addendum",
                "We're not going to do an addendum; the existing DPA covers it. No action "
                "needed.")
    return {"sources": [a, b],
            "c1": absent(["dpa", "addendum"]), "c2": absent(["dpa", "addendum"])}


# ---------------------------------------------------- user delegates away
@arc("HD03", "dev", "user delegates")
def hd03(s):
    a = s.slack("2026-10-06T10:00:00Z", "#qa", "dana.k",
                "@mei could you take the regression run for 2.15? I'm swamped with the "
                "cron migration")
    b = s.slack("2026-10-06T10:05:00Z", "#qa", "mei", "yep, I've got it", thread_ts=a)
    return {"sources": [a, b],
            "c1": absent(["regression", "2.15"]), "c2": absent(["regression", "2.15"])}


@arc("HT03", "test", "user delegates")
def ht03(s):
    a = s.jira("2026-09-22T10:00:00Z", "RTA-150", "Saved filters for the shift dashboard",
               "To Do", "dana.k", "tomas", due="2026-10-20")
    b = s.jira("2026-09-29T15:00:00Z", "RTA-150", "Saved filters for the shift dashboard",
               "To Do", "raj", "tomas", due="2026-10-20",
               comments=[{"author": "Dana Kowalski", "created": "2026-09-29T15:00:00Z",
                          "body": "Raj, all yours. Happy to pair if you want."}],
               changelog=[{"field": "assignee", "from": "Dana Kowalski", "to": "Raj Patel",
                           "author": "Dana Kowalski", "created": "2026-09-29T15:00:00Z"}])
    return {"sources": [a, b],
            "c1": absent(["saved", "filters"]), "c2": absent(["saved", "filters"])}


# ------------------------------------------------ stale tracker status
@arc("HD04", "dev", "stale tracker status")
def hd04(s):
    a = s.jira("2026-09-08T10:00:00Z", "PLAT-410", "Enable gzip on API responses",
               "To Do", "dana.k", "ines", due="2026-10-09")
    b = s.slack("2026-09-30T16:00:00Z", "#platform", "dana.k",
                "gzip is live in prod 🎉 (forgot to close PLAT-410, will do)")
    # tolerated after lrr-v1 (CORRECTIONS.md #2): the user said "will do" about
    # closing the ticket, so a housekeeping item is fine but not required
    return {"sources": [a, b], "tolerated": [["close", "plat-410"]],
            "c1": absent(["gzip", "api"]), "c2": absent(["gzip", "api"])}


@arc("HT04", "test", "stale tracker status")
def ht04(s):
    a = s.github("2026-09-15T10:00:00Z", "kestrel/rota-api", "issue", 490,
                 "Document webhook retries", "open", "tomas-r", assignees=["dana-k"])
    b = s.slack("2026-10-07T11:00:00Z", "#dev-portal", "dana.k",
                "webhook retry docs are published on the dev portal now")
    return {"sources": [a, b],
            "c1": absent(["webhook", "retries"]), "c2": absent(["webhook", "retries"])}


# ------------------------------------------- one task, different words
@arc("HD05", "dev", "one task, different words")
def hd05(s):
    a = s.jira("2026-10-01T10:00:00Z", "PLAT-420", "Perf benchmark for the roster API",
               "To Do", "dana.k", "ines", due="2026-10-15")
    b = s.slack("2026-10-05T10:00:00Z", "#platform", "ines",
                "@dana.k can you get me the roster latency numbers before Thursday's review?")
    c = s.event("2026-10-06T09:00:00Z", "Roster perf run", "2026-10-14T13:00:00Z",
                "2026-10-14T15:00:00Z", WORK, [att("dana.k")])
    st = with_aliases(open_(["roster", "perf"], "kestrel", "2026-10-15", "high"),
                      ["roster", "latency"], ["roster", "benchmark"])
    return {"sources": [a, b, c], "dedupe": True, "c1": st,
            "c2": with_aliases(open_(["roster", "perf"], "kestrel", "2026-10-15", None),
                               ["roster", "latency"], ["roster", "benchmark"])}


@arc("HT05", "test", "one task, different words")
def ht05(s):
    a = s.email("2026-10-05T09:00:00Z", who("ines"), WORK, "Q4 headcount",
                "Dana, can you write up the platform staffing case for Q4 headcount by "
                "Oct 19?\n\nInes Moreau\nEngineering Manager, Platform")
    b = s.doc("2026-10-06T14:00:00Z", "Q4 headcount justification", addr("ines"),
              "Sections: Platform, Product, Data.\nComment from Ines: @Dana add the "
              "platform hiring justification here.")
    c = s.slack("2026-10-08T10:00:00Z", "D-dana-ines", "ines",
                "reminder about the Q4 hiring justification for platform 🙏")
    st = with_aliases(open_(["staffing", "case"], "kestrel", "2026-10-19", "high"),
                      ["hiring", "justification"], ["headcount", "platform"])
    return {"sources": [a, b, c], "dedupe": True, "c1": st,
            "c2": with_aliases(open_(["staffing", "case"], "kestrel", "2026-10-19", None),
                               ["hiring", "justification"], ["headcount", "platform"])}


# ------------------------------------------------------ implicit ask
@arc("HD06", "dev", "question that is a task")
def hd06(s):
    a = s.email("2026-10-08T09:00:00Z", who("ines"), WORK, "Postgres 18",
                "Do we have a plan for the Postgres 18 upgrade? I'd like to see something "
                "before the Oct 20 planning meeting.\n\nInes Moreau\nEngineering Manager, Platform")
    return {"sources": [a],
            "c1": open_(["postgres", "18"], "kestrel", "2026-10-20", "high"),
            "c2": open_(["postgres", "18"], "kestrel", "2026-10-20", None)}


@arc("HT06", "test", "question that is a task")
def ht06(s):
    a = s.slack("2026-10-12T10:00:00Z", "D-dana-lena", "lena",
                "is the API going to support bulk edits? need to know to finalize the mocks "
                "by Friday (Oct 16)")
    return {"sources": [a],
            "c1": open_(["bulk", "edits"], "kestrel", "2026-10-16", "high"),
            "c2": open_(["bulk", "edits"], "kestrel", "2026-10-16", None)}


# ------------------------------------------------ quoted, already done
@arc("HD07", "dev", "quoted ask already answered")
def hd07(s):
    a = s.email("2026-08-20T10:00:00Z", who("tomas"), WORK, "SLA numbers",
                "Could you send me the SLA numbers for July?\nTomas")
    b = s.email("2026-08-20T15:00:00Z", WORK, addr("tomas"), "RE: SLA numbers",
                "Here you go: 99.94% July uptime, p95 latency 180ms.", sent=True)
    c = s.email("2026-10-07T12:00:00Z", who("tomas"), WORK, "RE: SLA numbers",
                "Thanks again for these, they made the QBR. Lunch Friday?\n\n"
                "> Here you go: 99.94% July uptime, p95 latency 180ms.\n"
                "> > Could you send me the SLA numbers for July?")
    return {"sources": [a, b, c],
            "c1": absent(["sla", "numbers"]), "c2": absent(["sla", "numbers"])}


@arc("HT07", "test", "quoted ask already answered")
def ht07(s):
    a = s.email("2026-09-24T10:00:00Z", who("brennan"), WORK, "Security documents",
                "Could you send us Kestrel's SOC 2 report?\nAlex")
    b = s.email("2026-09-25T10:00:00Z", WORK, addr("brennan"), "RE: Security documents",
                "SOC 2 report attached.", sent=True)
    c = s.email("2026-10-08T10:00:00Z", who("brennan"), WORK, "RE: Security documents",
                "Thanks for the SOC 2 report. One more: can you send the pen-test summary "
                "by Oct 22?\n\n> SOC 2 report attached.\n> > Could you send us Kestrel's "
                "SOC 2 report?")
    return {"sources": [a, b, c],
            "c1": open_(["pen-test", "summary"], "kestrel", "2026-10-22", "medium"),
            "c2": open_(["pen-test", "summary"], "kestrel", "2026-10-22", None),
            "also_absent": [["soc 2", "report"]]}


# ---------------------------------------------- one ask among many
@arc("HD08", "dev", "one ask among many")
def hd08(s):
    a = s.slack("2026-10-09T09:00:00Z", "#platform", "ines",
                "Plan for next week: Alex, finish the queue dashboards. Raj, warehouse cost "
                "report. @dana.k please review the IAM policy diff by Oct 15. Mei, release "
                "checklist for 2.15.")
    return {"sources": [a],
            "c1": open_(["iam", "policy"], "kestrel", "2026-10-15", "high"),
            "c2": open_(["iam", "policy"], "kestrel", "2026-10-15", None),
            "also_absent": [["warehouse", "cost"], ["queue", "dashboards"]]}


@arc("HT08", "test", "one ask among many")
def ht08(s):
    a = s.email("2026-10-07T09:00:00Z", who("victor"), ["eng-leads@kestrel.example", WORK],
                "Budget asks",
                "Hi all, a few asks:\n- Ines: final Q4 hiring plan\n- Tomas: roadmap "
                "one-pager\n- Dana: send me your conference budget request by Oct 30\n"
                "- Sam: on-call tooling costs\n\nVictor Hale\nDirector of Engineering")
    return {"sources": [a],
            "c1": open_(["conference", "budget"], "kestrel", "2026-10-30", "medium"),
            "c2": open_(["conference", "budget"], "kestrel", "2026-10-30", None),
            "also_absent": [["roadmap", "one-pager"], ["tooling", "costs"]]}


# --------------------------------------------- relative date over a weekend
@arc("HD09", "dev", "relative date")
def hd09(s):
    a = s.slack("2026-10-09T17:30:00Z", "#platform", "raj",
                "@dana.k can you look at the pager config by end of day Monday?")
    return {"sources": [a],
            "c1": open_(["pager", "config"], "kestrel", "2026-10-12", "high"),
            "c2": open_(["pager", "config"], "kestrel", "2026-10-12", None)}


@arc("HT09", "test", "relative date")
def ht09(s):
    a = s.email("2026-10-08T10:00:00Z", who("tomas"), WORK, "Deprecation notice",
                "Dana, I need the API v1 deprecation notice text by next Tuesday.\nTomas")
    return {"sources": [a],
            "c1": open_(["deprecation", "notice"], "kestrel", "2026-10-13", "high"),
            "c2": open_(["deprecation", "notice"], "kestrel", "2026-10-13", None)}


# --------------------------------------------- auto-resolved alerts
@arc("HD10", "dev", "auto-resolved alert")
def hd10(s):
    a = s.slack("2026-10-07T03:10:00Z", "#alerts", "alertbot",
                "CRITICAL: worker-2 CPU > 95%. On-call please acknowledge.")
    b = s.slack("2026-10-07T03:25:00Z", "#alerts", "alertbot",
                "RESOLVED: worker-2 CPU back to normal.")
    return {"sources": [a, b],
            "c1": absent(["worker-2", "cpu"]), "c2": absent(["worker-2", "cpu"])}


@arc("HT10", "test", "auto-resolved alert")
def ht10(s):
    a = s.email("2026-09-30T02:00:00Z", "Pager Alerts <alerts@pagerduty.example>", WORK,
                "Incident #8812 triggered: queue lag on scheduler",
                "Incident #8812 (queue lag) assigned to Sam Okoye. Acknowledge within 15 min.")
    b = s.email("2026-09-30T02:40:00Z", "Pager Alerts <alerts@pagerduty.example>", WORK,
                "Incident #8812 resolved", "Incident #8812 (queue lag) was resolved by Sam Okoye.")
    return {"sources": [a, b],
            "c1": absent(["queue", "lag"]), "c2": absent(["queue", "lag"])}


# ----------------------------------------------------- recurring asks
@arc("HD11", "dev", "recurring")
def hd11(s):
    a = s.email("2026-09-25T09:00:00Z", who("people"), WORK, "September timesheet",
                "Please submit your September timesheet by Oct 2.")
    b = s.email("2026-09-30T17:00:00Z", "Timely <noreply@timely.example>", WORK,
                "Timesheet submitted", "Dana Kowalski submitted the September timesheet.")
    c = s.email("2026-10-26T09:00:00Z", who("people"), WORK, "October timesheet",
                "Please submit your October timesheet by Nov 2.")
    return {"sources": [a, b, c],
            "c1": absent(["september", "timesheet"]),
            "c2": open_(["october", "timesheet"], "kestrel", "2026-11-02", None),
            "also_absent_c2": [["september", "timesheet"]]}


@arc("HT11", "test", "recurring")
def ht11(s):
    a = s.slack("2026-09-21T09:00:00Z", "D-dana-ines", "ines",
                "starting this week, could you send me a short status update every Friday?")
    src = [a]
    for d in ("2026-09-25", "2026-10-02", "2026-10-09", "2026-10-16", "2026-10-23",
              "2026-10-30", "2026-11-06"):
        src.append(s.email(d + "T16:00:00Z", WORK, addr("ines"), "Weekly status",
                           "Status: cron migration, load test, runbook. No blockers.",
                           sent=True))
    return {"sources": src,
            "c1": open_(["weekly", "status"], "kestrel", "2026-10-16", "high"),
            "c2": open_(["weekly", "status"], "kestrel", "2026-11-13", None)}


# ------------------------------------- auto-reply vs real reply
@arc("HD12", "dev", "auto-reply is not an answer")
def hd12(s):
    a = s.email("2026-09-10T10:00:00Z", WORK, addr("brennan"), "Clinic list",
                "Hi Alex, could you send the list of clinics for the pilot?", sent=True)
    b = s.email("2026-09-10T10:01:00Z", who("brennan"), WORK, "Automatic reply: Clinic list",
                "I'm out of office until Sep 28.")
    c = s.email("2026-10-01T09:00:00Z", who("brennan"), WORK, "RE: Clinic list",
                "Here's the pilot clinic list: Eastgate, Riverside, Hollow Oak.")
    return {"sources": [a, b, c],
            "c1": absent(["clinic", "list"]), "c2": absent(["clinic", "list"])}


@arc("HT12", "test", "auto-reply is not an answer")
def ht12(s):
    a = s.email("2026-09-30T10:00:00Z", WORK, "legal@kestrel.example", "Northwind MSA redlines",
                "Hi Legal, can you review the Northwind MSA redlines?", sent=True)
    b = s.email("2026-09-30T10:01:00Z", "Kestrel Legal <legal@kestrel.example>", WORK,
                "RE: Northwind MSA redlines",
                "Thanks, we've received your request and created ticket LEG-55.")
    c = s.email("2026-10-22T10:00:00Z", "Kestrel Legal <legal@kestrel.example>", WORK,
                "RE: Northwind MSA redlines", "The redlines are approved. You can send them.")
    return {"sources": [a, b, c],
            "c1": open_(["msa", "redlines"], "kestrel", None, "medium",
                        owner="counterparty", blocked_on="legal"),
            "c2": absent(["msa", "redlines"])}


# ================================================================ realistic
# Arcs that only make sense inside heavy Slack/Jira traffic.

@arc("HD13", "dev", "mention in a muted channel")
def hd13(s):
    a = s.slack("2026-10-12T15:00:00Z", "#proj-billing-migration", "alex.p",
                "@dana.k can you confirm the cron schedule for the billing jobs by Oct 16? "
                "we cut over the week after")
    return {"sources": [a],
            "c1": open_(["billing", "cron"], "kestrel", "2026-10-16", "high"),
            "c2": open_(["billing", "cron"], "kestrel", "2026-10-16", None)}


@arc("HT13", "test", "mention in a muted channel")
def ht13(s):
    a = s.slack("2026-10-09T11:00:00Z", "#data-eng", "raj",
                "@dana.k we need your sign-off on the events schema change by Oct 21")
    return {"sources": [a],
            # "sign-off" -> "sign" after lrr-v1 (CORRECTIONS.md #2): "Sign off" missed
            "c1": open_(["schema", "sign"], "kestrel", "2026-10-21", "medium"),
            "c2": open_(["schema", "sign"], "kestrel", "2026-10-21", None)}


@arc("HD14", "dev", "mandatory vs optional @channel")
def hd14(s):
    a = s.slack("2026-10-05T16:00:00Z", "#eng-announce", "victor",
                "@channel all engineers: rotate your SSH keys by Oct 23. This is required "
                "by the new security policy.")
    b = s.slack("2026-10-05T16:10:00Z", "#eng-announce", "lena",
                "@channel if you'd like, fill out the offsite activities survey. Totally optional!")
    return {"sources": [a, b],
            "c1": open_(["ssh", "keys"], "kestrel", "2026-10-23", "high"),
            "c2": open_(["ssh", "keys"], "kestrel", "2026-10-23", None),
            "also_absent": [["offsite", "survey"]]}


@arc("HT14", "test", "mandatory vs optional @channel")
def ht14(s):
    a = s.slack("2026-10-19T10:00:00Z", "#general", "people.team",
                "@here everyone must complete benefits enrollment by Nov 6. If you don't, "
                "your coverage defaults to the basic plan.")
    b = s.slack("2026-10-19T10:30:00Z", "#general", "lena", "@here cake in the kitchen 🎂")
    return {"sources": [a, b], "c1": None,
            "c2": open_(["benefits", "enrollment"], "kestrel", "2026-11-06", None),
            "also_absent_c2": [["cake", "kitchen"]]}


@arc("HD15", "dev", "shared with one other person")
def hd15(s):
    a = s.slack("2026-10-06T10:00:00Z", "mpdm-dana.k--ines--raj", "ines",
                "Dana and Raj, you two own the warehouse cutover plan. Due Oct 23.")
    b = s.slack("2026-10-06T10:05:00Z", "mpdm-dana.k--ines--raj", "raj",
                "👍 Dana, I'll take the data side if you take the infra side?")
    c = s.slack("2026-10-06T10:07:00Z", "mpdm-dana.k--ines--raj", "dana.k", "deal")
    return {"sources": [a, b, c],
            "c1": open_(["cutover", "plan"], "kestrel", "2026-10-23", "medium"),
            "c2": open_(["cutover", "plan"], "kestrel", "2026-10-23", None)}


@arc("HT15", "test", "shared with one other person")
def ht15(s):
    a = s.jira("2026-10-01T10:00:00Z", "PLAT-430", "Shard the job queue",
               "In Progress", "alex.p", "ines", due="2026-10-30",
               description="Pairing: Alex + Dana.")
    b = s.slack("2026-10-01T10:30:00Z", "D-alex-dana", "alex.p",
                "let's split the queue sharding: I'll do the producers, you take the consumers, "
                "both by Oct 30?")
    c = s.slack("2026-10-01T10:32:00Z", "D-alex-dana", "dana.k", "works for me")
    return {"sources": [a, b, c],
            "c1": open_(["consumer", "shard"], "kestrel", "2026-10-30", "medium"),
            "c2": open_(["consumer", "shard"], "kestrel", "2026-10-30", None)}


@arc("HD16", "dev", "your area, not given to you")
def hd16(s):
    a = s.jira("2026-10-02T09:00:00Z", "PLAT-440", "Scheduler: retry storm after deploys",
               "To Do", None, "sam", priority="High",
               description="Component: scheduler. Seen twice this week.")
    b = s.slack("2026-10-02T09:30:00Z", "#platform", "sam",
                "filed PLAT-440 for the retry storm, we'll pick an owner at planning")
    return {"sources": [a, b],
            "c1": absent(["retry", "storm"]), "c2": absent(["retry", "storm"])}


@arc("HT16", "test", "your area, not given to you")
def ht16(s):
    a = s.slack("2026-09-30T14:00:00Z", "#platform", "dana.k",
                "the Redis upgrade is overdue, we're two minors behind")
    b = s.slack("2026-09-30T14:20:00Z", "#platform", "ines",
                "agreed. Alex will handle the Redis upgrade next sprint.")
    return {"sources": [a, b],
            "c1": absent(["redis", "upgrade"]), "c2": absent(["redis", "upgrade"])}


@arc("HD17", "dev", "small group chat")
def hd17(s):
    a = s.slack("2026-10-08T13:00:00Z", "mpdm-dana.k--lena--mei", "lena",
                "Dana, does the roster API return each location's timezone names? need to "
                "know for the mock by Oct 14")
    return {"sources": [a],
            "c1": open_(["timezone", "names"], "kestrel", "2026-10-14", "high"),
            "c2": open_(["timezone", "names"], "kestrel", "2026-10-14", None)}


@arc("HT17", "test", "small group chat")
def ht17(s):
    a = s.slack("2026-10-07T15:00:00Z", "mpdm-dana.k--raj--tomas", "tomas",
                "Raj, can you pull the adoption numbers for the QBR? Dana, nothing needed "
                "from you this time.")
    b = s.slack("2026-10-07T15:02:00Z", "mpdm-dana.k--raj--tomas", "raj", "on it")
    return {"sources": [a, b],
            "c1": absent(["adoption", "numbers"]), "c2": absent(["adoption", "numbers"])}


@arc("HD18", "dev", "ask buried in a long thread")
def hd18(s):
    root = s.slack("2026-10-07T08:00:00Z", "#incidents", "sam",
                   "INC-240: elevated 5xx on rota-api, investigating")
    src = [root]
    chatter = ["seeing it on eu-west too", "rolled back 2.15.1?", "not yet, checking the db",
               "connection pool maxed", "bumping pool size", "errors dropping",
               "still some 502s from the LB", "LB health checks flapping", "ok stable now",
               "who's writing this up?"]
    users = ["sam", "alex.p", "raj", "ines", "mei"]
    for i in range(30):
        src.append(s.slack("2026-10-07T%02d:%02d:00Z" % (8 + i // 12, (i * 5) % 60),
                           "#incidents", users[i % 5], chatter[i % len(chatter)],
                           thread_ts=root))
    src.append(s.slack("2026-10-07T10:35:00Z", "#incidents", "ines",
                       "@dana.k can you add the timeline to the incident doc by tomorrow?",
                       thread_ts=root))
    for i in range(8):
        src.append(s.slack("2026-10-07T11:%02d:00Z" % (i * 5), "#incidents", users[i % 5],
                           chatter[(i + 3) % len(chatter)], thread_ts=root))
    return {"sources": src,
            "c1": open_(["incident", "timeline"], "kestrel", "2026-10-08", "high"),
            "c2": open_(["incident", "timeline"], "kestrel", "2026-10-08", None)}


@arc("HT18", "test", "ask buried in a long thread")
def ht18(s):
    root = s.slack("2026-10-05T09:00:00Z", "#proj-scheduler-v2", "tomas",
                   "Launch prep thread for scheduler v2 🚀")
    src = [root]
    chatter = ["docs are drafted", "QA sign-off pending", "feature flag is ready",
               "marketing wants a blog post", "support macros updated", "do we need a "
               "status page note?", "yes, Mei is on it", "rollout 10% → 50% → 100%"]
    users = ["tomas", "mei", "alex.p", "lena", "raj"]
    for i in range(25):
        src.append(s.slack("2026-10-05T%02d:%02d:00Z" % (9 + i // 12, (i * 5) % 60),
                           "#proj-scheduler-v2", users[i % 5], chatter[i % len(chatter)],
                           thread_ts=root))
    src.append(s.slack("2026-10-05T11:20:00Z", "#proj-scheduler-v2", "tomas",
                       "@dana.k please update the launch checklist with the infra steps by Oct 19",
                       thread_ts=root))
    for i in range(10):
        src.append(s.slack("2026-10-05T12:%02d:00Z" % (i * 5), "#proj-scheduler-v2",
                           users[i % 5], chatter[(i + 2) % len(chatter)], thread_ts=root))
    return {"sources": src,
            "c1": open_(["launch", "checklist"], "kestrel", "2026-10-19", "medium"),
            "c2": open_(["launch", "checklist"], "kestrel", "2026-10-19", None)}
