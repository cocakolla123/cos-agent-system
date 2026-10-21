"""Realistic traffic for the 'realistic' world: ~140 Slack channels (member,
muted, or not a member) carrying thousands of messages, hundreds of Jira
tickets that are mostly other people's, and notification-heavy email.

None of this is an obligation for the user. It deliberately contains:
asks addressed to other people, mentions of the user that are not asks
("thanks @dana.k", "cc @dana.k fyi"), @channel chatter, bot alerts that
resolve themselves, and tickets in the user's area assigned to others.
Deterministic (seeded)."""

import datetime
import random

from world import PEOPLE, GITHUB, WORK, PERSONAL, days, ts

OTHERS = ["alex.p", "dana.lee", "sam", "mei", "raj", "lena", "tomas", "ines", "victor"]
EXTRA_PEOPLE = ["jo.kim", "omar.s", "beth.w", "luis.m", "ana.r", "kai.t", "nina.p",
                "ravi.k", "zoe.h", "tom.b", "ivy.c", "max.f"]

TEAM_CHANNELS = ["#platform", "#frontend", "#data-eng", "#qa", "#design", "#sre",
                 "#incidents", "#deploys", "#alerts", "#releases", "#eng-announce",
                 "#general", "#random", "#it-help", "#northwind-shared", "#dev-portal",
                 "#proj-scheduler-v2", "#proj-billing-migration"]
TOPICS = ["billing", "search", "mobile", "payments", "growth", "onboarding", "reports",
          "notifications", "auth", "exports", "pricing", "partners", "analytics",
          "infra-cost", "observability", "a11y", "localization", "perf", "security",
          "compliance", "hiring", "interviews", "offsite", "docs", "support-escalations"]
SOCIAL = ["#pets", "#running", "#books", "#music", "#food", "#parents", "#gaming",
          "#plants", "#photography", "#cycling", "#coffee", "#movies", "#travel",
          "#kudos", "#til", "#memes", "#help-desk-swap", "#carpool"]

TECH = ["merged the {t} refactor, should be faster now", "anyone seen flaky {t} tests today?",
        "{t} dashboard is updated with last week's numbers", "pushed a fix for the {t} edge case",
        "the {t} migration is 60% done", "heads up, {t} config changes going out at 3pm",
        "draft doc for {t} is in the drive, comments welcome",
        "we decided to keep the old {t} endpoint for one more release",
        "rolled back the {t} change, investigating", "{t} p95 is back under 200ms"]
ASK_OTHER = ["@{p} can you review the {t} PR when you get a chance?",
             "@{p} could you update the {t} runbook by Friday?",
             "@{p} can you take the {t} ticket this sprint?",
             "@{p} please send me the {t} numbers by Thursday",
             "@{p} mind pairing on the {t} bug tomorrow?",
             "can someone look at the {t} alert?", "who owns {t} these days?",
             "@{p} please file a ticket for the {t} issue"]
MENTION_NOT_ASK = ["thanks @dana.k for the quick {t} fix!", "as @dana.k said earlier, {t} is fine",
                   "cc @dana.k fyi, no action needed on {t}", "nice work on {t} @dana.k 🙌",
                   "@dana.k's {t} notes from last week were super helpful"]
SOCIAL_MSGS = ["look at this good boy 🐶", "anyone reading something good?", "5k at lunch?",
               "recipe thread 🍝", "new album recommendations?", "who's in for board games",
               "my plant finally flowered", "golden hour shot from the roof", "coffee beans review"]
BOTS = {"#deploys": ("deploybot", ["{s} {v} deployed to production", "{s} {v} deployed to staging"]),
        "#alerts": ("alertbot", ["WARN: {s} memory at 82%", "RESOLVED: {s} memory normal",
                                 "CRITICAL: {s} error rate 3%. On-call please acknowledge.",
                                 "RESOLVED: {s} error rate normal"]),
        "#releases": ("releasebot", ["{s} {v} released"])}
SERVICES = ["rota-api", "rota-web", "scheduler-worker", "billing-svc", "export-svc"]

JIRA_PROJECTS = {"PLAT": ["sam", "alex.p", "raj"], "RTA": ["dana.lee", "mei", "lena"],
                 "DATA": ["raj"], "WEB": ["dana.lee", "lena"], "SRE": ["sam"]}
JIRA_TITLES = ["Improve {t} error messages", "Add metrics for {t}", "Refactor {t} module",
               "Fix flaky {t} test", "Document {t} API", "Upgrade {t} dependency",
               "Investigate {t} latency", "Clean up {t} feature flag",
               "Add audit log for {t}", "Support pagination in {t}"]


def channels(rng):
    """Channel directory as the Slack connector would list it for the user."""
    out = []
    for c in TEAM_CHANNELS:
        out.append({"name": c, "is_member": True,
                    "is_muted": c in ("#deploys", "#alerts", "#releases",
                                      "#proj-billing-migration", "#data-eng", "#general"),
                    "kind": "team"})
    for t in TOPICS:
        for suffix in ("", "-eng", "-alerts"):
            name = "#%s%s" % (t, suffix)
            member = rng.random() < 0.35
            out.append({"name": name, "is_member": member,
                        "is_muted": member and rng.random() < 0.6, "kind": "topic"})
    for c in SOCIAL:
        member = rng.random() < 0.4
        out.append({"name": c, "is_member": member, "is_muted": member and rng.random() < 0.5,
                    "kind": "social"})
    for i in range(30):
        out.append({"name": "#team-%s-%02d" % (rng.choice(TOPICS), i), "is_member": False,
                    "is_muted": False, "kind": "other-team"})
    return out


def slack_traffic(store, start, end, rng, chans):
    rate = {}
    for c in chans:
        if c["name"] in BOTS:
            rate[c["name"]] = 6.0
        elif c["kind"] == "team":
            rate[c["name"]] = 5.0
        elif c["kind"] == "topic":
            rate[c["name"]] = 2.0 if c["is_member"] else 0.6
        elif c["kind"] == "social":
            rate[c["name"]] = 1.2 if c["is_member"] else 0.3
        else:
            rate[c["name"]] = 0.25
    people = OTHERS + EXTRA_PEOPLE
    for d in days(start, end):
        if d.weekday() >= 5:
            continue
        for c in chans:
            name = c["name"]
            n = int(rate[name]) + (1 if rng.random() < rate[name] % 1 else 0)
            for _ in range(n):
                hh, mm = rng.randint(8, 18), rng.randint(0, 59)
                t = rng.choice(TOPICS)
                if name in BOTS:
                    bot, msgs = BOTS[name]
                    store.slack(ts(d, hh, mm), name, bot, rng.choice(msgs).format(
                        s=rng.choice(SERVICES), v="2.%d.%d" % (rng.randint(10, 16),
                                                              rng.randint(0, 9))))
                    continue
                if c["kind"] == "social":
                    store.slack(ts(d, hh, mm), name, rng.choice(people), rng.choice(SOCIAL_MSGS))
                    continue
                r = rng.random()
                if r < 0.62:
                    text = rng.choice(TECH).format(t=t)
                elif r < 0.92:
                    p = rng.choice([x for x in people if x != "dana.k"])
                    text = rng.choice(ASK_OTHER).format(p=p, t=t)
                else:
                    text = rng.choice(MENTION_NOT_ASK).format(t=t)
                store.slack(ts(d, hh, mm), name, rng.choice(people), text)
        # small group chats and DMs the user is in, without asks for the user
        if rng.random() < 0.5:
            store.slack(ts(d, 12, rng.randint(0, 59)), "mpdm-dana.k--alex.p--sam",
                        rng.choice(["alex.p", "sam"]),
                        rng.choice(["lunch?", "did the deploy go out?", "haha yes",
                                    "standup moved 10 min", "ok cool"]))
        if rng.random() < 0.3:
            store.slack(ts(d, 17, rng.randint(0, 59)), "D-dana-ines", "ines",
                        rng.choice(["thanks for today!", "nice job in planning",
                                    "fyi I'm out Friday", "saw the PR, looks good"]))


def jira_traffic(store, start, end, rng):
    tickets = []
    num = {k: 500 for k in JIRA_PROJECTS}
    for k, assignees in JIRA_PROJECTS.items():
        for _ in range(60 if k in ("PLAT", "RTA") else 30):
            num[k] += 1
            tickets.append((k, num[k], rng.choice(JIRA_TITLES).format(t=rng.choice(TOPICS)),
                            rng.choice(assignees + [None]), rng.choice(["ines", "tomas", "sam"])))
    first = datetime.date.fromisoformat(start)
    span = (datetime.date.fromisoformat(end) - first).days
    for k, n, title, assignee, reporter in tickets:
        d0 = first + datetime.timedelta(days=rng.randint(0, span - 1))
        watchers = ["dana.k"] if rng.random() < 0.12 else []
        statuses = ["To Do", "In Progress", "In Review", "Done"]
        for step in range(rng.randint(1, 4)):
            d = d0 + datetime.timedelta(days=step * rng.randint(2, 9))
            if d.isoformat() >= end:
                break
            store.jira(ts(d, rng.randint(9, 17)), "%s-%d" % (k, n), title,
                       statuses[min(step, 3)], assignee, reporter,
                       due=(d0 + datetime.timedelta(days=21)).isoformat()
                       if rng.random() < 0.4 else None, watchers=watchers)
            if watchers:
                store.email(ts(d, 17), "Jira <jira@kestrel.example>", WORK,
                            "[JIRA] (%s-%d) %s" % (k, n, title),
                            "%s updated %s-%d. Status: %s. You are watching this issue." % (
                                (PEOPLE.get(assignee) or ("Someone",))[0], k, n,
                                statuses[min(step, 3)]))


def email_traffic(store, start, end, rng):
    news = [("Platform Weekly", "news@platformweekly.example"),
            ("DevTools Digest", "digest@devtoolsdigest.example"),
            ("Cloud Cost Report", "reports@cloudcost.example"),
            ("SaaS Insider Deals", "deals@saasinsider.example"),
            ("Webinar Hub", "events@webinarhub.example")]
    for d in days(start, end):
        if d.weekday() < 5:
            for _ in range(rng.randint(3, 7)):
                name, frm = rng.choice(news)
                store.email(ts(d, rng.randint(6, 20)), "%s <%s>" % (name, frm), WORK,
                            rng.choice(["Your weekly roundup", "Last chance: register today",
                                        "Action required: confirm your subscription preferences",
                                        "New features you'll love", "Don't miss out"]),
                            "Newsletter content. Unsubscribe anytime.")
            if rng.random() < 0.6:
                num = rng.randint(380, 560)
                store.email(ts(d, rng.randint(9, 18)), "GitHub <notifications@github.example>",
                            WORK, "[kestrel/rota-api] PR #%d: %s" % (
                                num, rng.choice(["Refactor shift validator", "Add importer metrics",
                                                 "Speed up roster query", "Bump dependencies"])),
                            "%s commented. You are receiving this because you are subscribed "
                            "to this repository." % GITHUB[rng.choice(OTHERS[:6])])
            if rng.random() < 0.15:
                store.email(ts(d, 10), "Kestrel Announcements <announce@kestrel.example>", WORK,
                            rng.choice(["Office closed Monday", "New expense tool rollout",
                                        "All-hands recording", "Welcome our new hires"]),
                            "Company announcement. No action needed.")
        if rng.random() < 0.6:
            store.email(ts(d, rng.randint(8, 21)), rng.choice([
                "Oakline Outfitters <orders@oakline.example>", "StreamBox <hello@streambox.example>",
                "City Gym <members@citygym.example>", "TechJobs Weekly <jobs@techjobsweekly.example>"]),
                PERSONAL, rng.choice(["Your order has shipped", "New this week",
                                      "Complete your profile to unlock rewards",
                                      "50 new jobs matching your search"]),
                "Promotional content.", account="personal")


def scale(store, start, end, seed):
    rng = random.Random(seed)
    chans = channels(rng)
    slack_traffic(store, start, end, rng, chans)
    jira_traffic(store, start, end, rng)
    email_traffic(store, start, end, rng)
    return chans
