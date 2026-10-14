"""The Kestrel Labs world: people, workspaces, connector-shaped item
constructors, and the background noise generator. Deterministic (seeded).
Every address is under .example."""

import datetime
import random

TODAY = "2026-10-13"                     # C1: first full crawl
HISTORY_START = "2026-07-13"
FUTURE_WEEKS = ["2026-10-13", "2026-10-20", "2026-10-27", "2026-11-03"]
C2 = "2026-11-10"                        # after the fourth weekly poll

USER = {
    "name": "Dana Kowalski",
    "email": "dana.k@kestrel.example",
    "other_emails": ["dana.kowalski@mailbox.example"],
    "slack": "dana.k",
    "github": "dana-k",
}

WORKSPACES = {"kestrel": "employer", "oss": "side-project",
              "job-search": "job-search", "personal": "personal"}

# handle -> (display name, email, title)
PEOPLE = {
    "dana.k":   ("Dana Kowalski", "dana.k@kestrel.example", "Senior Backend Engineer, Platform"),
    "ines":     ("Ines Moreau", "ines@kestrel.example", "Engineering Manager, Platform"),
    "victor":   ("Victor Hale", "victor@kestrel.example", "Director of Engineering"),
    "tomas":    ("Tomas Reyes", "tomas@kestrel.example", "Product Manager, Scheduling"),
    "alex.p":   ("Alex Park", "alex.park@kestrel.example", "Backend Engineer, Platform"),
    "dana.lee": ("Dana Lee", "dana.lee@kestrel.example", "Frontend Engineer"),
    "sam":      ("Sam Okoye", "sam@kestrel.example", "Site Reliability Engineer"),
    "mei":      ("Mei Tanaka", "mei@kestrel.example", "QA Engineer"),
    "raj":      ("Raj Patel", "raj@kestrel.example", "Data Engineer"),
    "lena":     ("Lena Fischer", "lena@kestrel.example", "Product Designer"),
}
GITHUB = {"dana.k": "dana-k", "ines": "ines-m", "alex.p": "alex-park",
          "dana.lee": "danalee-fe", "sam": "sam-o", "mei": "mei-t",
          "raj": "raj-p", "lena": "lena-f", "tomas": "tomas-r",
          "victor": "victor-h"}

EXTERNAL = {
    "brennan": ("Alex Brennan", "alex.brennan@northwind.example", "Operations Lead, Northwind Clinics"),
    "priya":   ("Priya Nair", "priya@stratusmon.example", "Account Executive, Stratus Monitoring"),
    "grace":   ("Grace Liu", "grace@halcyontalent.example", "Recruiter, Halcyon Talent"),
    "corvid":  ("Corvid Systems Recruiting", "recruiting@corvid.example", ""),
    "jess":    ("Jess Morales", "jess.m@mailbox.example", ""),
    "dentist": ("BrightSmile Dental", "frontdesk@brightsmile.example", ""),
    "landlord": ("Harbor Lane Properties", "leasing@harborlane.example", ""),
    "it":      ("Kestrel IT", "it@kestrel.example", ""),
    "people":  ("Kestrel People Team", "people@kestrel.example", ""),
    "finance": ("Kestrel Finance", "finance@kestrel.example", ""),
}

WORK = USER["email"]
PERSONAL = USER["other_emails"][0]


def who(handle):
    if handle in PEOPLE:
        n, e, _ = PEOPLE[handle]
    else:
        n, e, _ = EXTERNAL[handle]
    return "%s <%s>" % (n, e)


def addr(handle):
    return (PEOPLE.get(handle) or EXTERNAL[handle])[1]


class Store:
    """Collects items, assigns stable ids per connector prefix."""
    PREFIX = {"gmail": "em", "slack": "sl", "jira": "jr", "github": "gh",
              "calendar": "cal", "drive": "doc"}

    def __init__(self):
        self.items = []
        self.counters = {p: 0 for p in self.PREFIX.values()}

    def add(self, connector, item):
        p = self.PREFIX[connector]
        self.counters[p] += 1
        item = dict(item)
        item["id"] = "%s-%04d" % (p, self.counters[p])
        item["connector"] = connector
        self.items.append(item)
        return item["id"]

    # --- connector-shaped constructors -------------------------------------
    def email(self, date, frm, to, subject, body, cc=None, sent=False,
              account="work", thread=None):
        labels = ["SENT"] if sent else ["INBOX"]
        return self.add("gmail", {
            "date": date, "account": WORK if account == "work" else PERSONAL,
            "labelIds": labels, "from": frm, "to": to if isinstance(to, list) else [to],
            "cc": cc or [], "subject": subject, "body": body,
            "threadId": thread or "th-" + subject.lower().replace("re: ", "")[:24]
            .replace(" ", "-")})

    def slack(self, date, channel, user, text, thread_ts=None, reactions=None):
        return self.add("slack", {
            "date": date, "channel": channel, "user": user,
            "user_name": PEOPLE.get(user, (user,))[0], "text": text,
            "thread_ts": thread_ts, "reactions": reactions or []})

    def jira(self, date, key, summary, status, assignee, reporter, due=None,
             priority="Medium", comments=None, changelog=None, watchers=None,
             description=""):
        return self.add("jira", {
            "date": date, "key": key, "fields": {
                "summary": summary, "status": status,
                "assignee": PEOPLE[assignee][0] if assignee else None,
                "reporter": PEOPLE[reporter][0], "duedate": due,
                "priority": priority, "description": description,
                "watchers": [PEOPLE[w][0] for w in (watchers or [])],
                "updated": date},
            "comments": comments or [], "changelog": changelog or []})

    def github(self, date, repo, kind, number, title, state, author,
               body="", assignees=None, requested_reviewers=None,
               requested_teams=None, comments=None, merged=False, labels=None):
        return self.add("github", {
            "date": date, "repo": repo, "type": kind, "number": number,
            "title": title, "state": state, "user": author, "body": body,
            "assignees": assignees or [],
            "requested_reviewers": requested_reviewers or [],
            "requested_teams": requested_teams or [],
            "comments": comments or [], "merged": merged,
            "labels": labels or [], "updated_at": date})

    def event(self, date, summary, start, end, organizer, attendees,
              description="", status="confirmed", recurrence=None):
        return self.add("calendar", {
            "date": date, "summary": summary, "start": start, "end": end,
            "organizer": organizer, "attendees": attendees,
            "description": description, "status": status,
            "recurrence": recurrence})

    def doc(self, date, name, owner, content, shared_by=None):
        return self.add("drive", {
            "date": date, "name": name, "owners": [owner],
            "modifiedTime": date, "sharedBy": shared_by, "content": content})


def att(handle, status="accepted"):
    return {"email": addr(handle), "responseStatus": status}


def days(start, end):
    d = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    while d < e:
        yield d
        d += datetime.timedelta(days=1)


def ts(d, hour, minute=0):
    return "%sT%02d:%02d:00Z" % (d.isoformat() if hasattr(d, "isoformat") else d,
                                 hour, minute)


# --- background noise ----------------------------------------------------------
# Nothing here is an obligation for the user. It is the bulk of the traffic.

LUNCH = ["anyone up for tacos at 12?", "coffee run in 10, who's in",
         "the new ramen place is great btw", "pizza leftovers in the kitchen",
         "happy friday all", "who broke the espresso machine (again)"]
DEPLOYS = ["rota-api {v} deployed to production", "rota-web {v} deployed to staging",
           "scheduler-worker {v} deployed to production"]
OTHERS_TICKETS = [
    ("RTA-{n}", "Improve empty state for shift list", "lena", "dana.lee"),
    ("RTA-{n}", "Fix tooltip overflow in roster view", "dana.lee", "tomas"),
    ("PLAT-{n}", "Tune autoscaling thresholds for workers", "sam", "ines"),
    ("PLAT-{n}", "Backfill usage metrics into the warehouse", "raj", "ines"),
    ("RTA-{n}", "Regression suite for holiday calendars", "mei", "tomas"),
    ("PLAT-{n}", "Dashboards for queue latency", "alex.p", "sam"),
]
STATUSES = ["To Do", "In Progress", "In Review", "Done"]
NEWS = [
    ("Platform Weekly", "news@platformweekly.example",
     "Platform Weekly #{n}: queues, caches and the cost of retries",
     "This week: five ways to tame retry storms, a look at Postgres 18, and "
     "our reader survey. You are receiving this because you subscribed."),
    ("SaaS Insider Deals", "deals@saasinsider.example",
     "Last chance: 40% off annual plans ends {d}",
     "Complete your upgrade before the deadline to lock in pricing. Act now! "
     "Unsubscribe anytime."),
    ("DevTools Digest", "digest@devtoolsdigest.example",
     "Your weekly digest: 12 new tools",
     "Action required? Nope, just reading. Top picks this week include a new "
     "profiler and a terminal multiplexer."),
]
PERSONAL_PROMOS = [
    ("Oakline Outfitters", "orders@oakline.example", "Your order has shipped",
     "Good news! Your order #{n} is on the way. Track it anytime."),
    ("StreamBox", "hello@streambox.example", "New this week on StreamBox",
     "Three new series we think you'll love. Start watching today."),
    ("City Gym", "members@citygym.example", "Complete your profile to unlock rewards",
     "Members who complete their profile get a free smoothie. Last chance this month!"),
]


def noise(store, start, end, seed):
    rng = random.Random(seed)
    n = 0
    for d in days(start, end):
        wd = d.weekday()
        if wd >= 5:
            if rng.random() < 0.5:
                name, frm, subj, body = rng.choice(PERSONAL_PROMOS)
                n += 1
                store.email(ts(d, 9), "%s <%s>" % (name, frm), PERSONAL,
                            subj, body.format(n=rng.randint(10000, 99999)),
                            account="personal")
            continue
        # standup bot
        store.slack(ts(d, 9, 30), "#platform-standup", "standupbot",
                    "Standup: Alex: %s. Raj: %s. Mei: %s." % (
                        rng.choice(["finishing dashboards", "on-call follow-ups",
                                    "reviewing PRs"]),
                        rng.choice(["warehouse backfill", "schema cleanup",
                                    "metrics pipeline"]),
                        rng.choice(["regression runs", "release testing",
                                    "triage"])))
        if rng.random() < 0.6:
            store.slack(ts(d, 12), "#random", rng.choice(["alex.p", "raj", "lena", "mei"]),
                        rng.choice(LUNCH))
        if rng.random() < 0.5:
            v = "2.%d.%d" % (rng.randint(10, 15), rng.randint(0, 9))
            store.slack(ts(d, 15), "#deploys", "deploybot",
                        rng.choice(DEPLOYS).format(v=v))
        if rng.random() < 0.45:
            k, summ, a, r = rng.choice(OTHERS_TICKETS)
            store.jira(ts(d, 11), k.format(n=rng.randint(150, 260)), summ,
                       rng.choice(STATUSES), a, r)
        if rng.random() < 0.35:
            num = rng.randint(380, 520)
            author = rng.choice(["alex.p", "raj", "mei", "dana.lee"])
            store.github(ts(d, 16), "kestrel/rota-api", "pull_request", num,
                         rng.choice(["Refactor shift validator", "Add metrics to importer",
                                     "Tidy up config loading", "Speed up roster query"]),
                         rng.choice(["open", "closed"]), GITHUB[author],
                         requested_reviewers=[GITHUB[rng.choice(["alex.p", "raj", "mei"])]],
                         merged=rng.random() < 0.5)
        if wd == 0:
            name, frm, subj, body = NEWS[0]
            store.email(ts(d, 7), "%s <%s>" % (name, frm), WORK,
                        subj.format(n=d.isocalendar()[1]), body)
        if wd == 2 and rng.random() < 0.7:
            name, frm, subj, body = NEWS[rng.choice([1, 2])]
            store.email(ts(d, 8), "%s <%s>" % (name, frm), WORK,
                        subj.format(d=(d + datetime.timedelta(days=3)).isoformat()),
                        body)
        if wd == 4 and rng.random() < 0.5:
            store.doc(ts(d, 14), "Team lunch signup", "lena@kestrel.example",
                      "Friday lunch headcount: Alex, Raj, Lena, Mei. Add your name if you're coming.")
    return n


def recurring(store):
    store.event("2026-07-13T08:00:00Z", "Daily standup", "2026-07-13T09:30:00Z",
                "2026-07-13T09:45:00Z", addr("ines"),
                [att("dana.k"), att("alex.p"), att("raj"), att("mei"), att("sam")],
                recurrence="RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR")
    store.event("2026-07-13T08:00:00Z", "Platform sync", "2026-07-14T15:00:00Z",
                "2026-07-14T15:45:00Z", addr("ines"),
                [att("dana.k"), att("alex.p"), att("raj"), att("sam")],
                recurrence="RRULE:FREQ=WEEKLY;BYDAY=TU")
    store.event("2026-07-13T08:00:00Z", "1:1 Ines / Dana", "2026-07-14T16:00:00Z",
                "2026-07-14T16:30:00Z", addr("ines"), [att("dana.k")],
                recurrence="RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO")
