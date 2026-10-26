"""The 'full' world: everything else on a real person's accounts.

On top of the realistic world's traffic, this adds the volume and mess of an
actual working life, so the first crawl sees over 100,000 items:

- Slack at real volume: long channel histories, threads, CI and bot channels,
  social chatter, optional @here notices, asks addressed to other people.
- Work mail: Jira, GitHub, Docs and calendar notifications, vendor cold
  outreach, HR and IT newsletters, conference spam.
- Personal mail: spam, phishing, bank and card alerts, 2FA codes, shipping,
  receipts, autopay notices, subscriptions, family and friends chatter.
- Jira and GitHub: other teams' tickets, CI runs, dependabot PRs, reviews
  requested from other people.
- Calendar: standups, 1:1s, focus blocks, all-hands, other people's events.
- Drive: shared docs, sheets and notes that need nothing from the user.

Every item here is noise: nothing asks the user to do anything, has a
deadline for the user, or continues one of the arcs. build.py checks that no
item here matches an arc's gist (evals/score.py's matcher), and the blind
labeler sample in evals/longrun/second-labeler/full/ checks the rest.
Deterministic (seeded). Every address is under .example.
"""

import datetime
import random

from world import PEOPLE, WORK, PERSONAL, days, ts

COWORKERS = ["alex.p", "dana.lee", "sam", "mei", "raj", "lena", "tomas", "ines", "victor"]
MORE = ["jo.kim", "omar.s", "beth.w", "luis.m", "ana.r", "kai.t", "nina.p", "ravi.k", "zoe.h",
        "tom.b", "ivy.c", "max.f", "eli.n", "fay.d", "gus.o", "hana.y", "ian.v", "june.q",
        "kofi.a", "lia.m", "milo.r", "noor.s", "otto.b", "pia.l", "quinn.e", "rosa.t"]
PEOPLE_ALL = COWORKERS + MORE
FIRST = {h: h.split(".")[0].capitalize() for h in PEOPLE_ALL}

TOPICS = ["billing", "search", "mobile", "payments", "growth", "onboarding", "reports",
          "notifications", "auth", "exports", "pricing", "partners", "analytics", "caching",
          "observability", "a11y", "localization", "perf", "sso", "webhooks", "rate limits",
          "feature flags", "audit logs", "data retention", "ingest", "dashboards", "sdk",
          "cli", "push", "email templates", "dark mode", "invoices", "usage metering"]
SERVICES = ["rota-api", "rota-web", "scheduler-worker", "billing-svc", "export-svc",
            "auth-gw", "notify-svc", "search-idx", "ingest-pipe", "report-gen"]
LIFE_CHANNELS = ["#ci", "#builds", "#oncall-handoff", "#standup", "#eng-random", "#water-cooler",
                 "#wins", "#pairing", "#reading-group", "#ml-curious", "#security-news",
                 "#customer-feedback", "#sales-wins", "#support-tier2", "#product-updates",
                 "#ux-crit", "#frontend-guild", "#backend-guild", "#infra-cost",
                 "#vendor-eval", "#office-sf", "#remote", "#lunch", "#dogs", "#cats",
                 "#bikes", "#climbing", "#baking", "#chess", "#f1", "#football", "#nba",
                 "#gardening", "#diy", "#language-exchange", "#podcasts", "#tv-shows"]

# ---- Slack text -------------------------------------------------------------
TECH = ["merged the {t} cleanup, nothing user-facing", "{t} tests are green again",
        "posted the {t} numbers in the sheet", "fixed a {t} typo on the wiki",
        "{t} deploy went out fine", "rolling {t} to 10% of traffic",
        "{t} dashboard has a new panel for p99", "we're keeping {t} behind the flag for now",
        "reverted the {t} change, will retry tomorrow", "{t} on staging looks good to me",
        "TIL the {t} client backs off on 502", "the {t} RFC got approved in design review",
        "updated the {t} runbook with last week's learnings",
        "{t} latency is back to normal after the cache warmup",
        "if anyone's curious, the {t} postmortem from the frontend team is a good read",
        "bumped {t} to the new minor version", "closing the {t} spike, notes are in the doc",
        "{t} metrics are flat since Tuesday", "pairing with {p} on {t} this afternoon",
        "{t} soak test passed at 2x peak", "shipping {t} behind a kill switch",
        "the {t} migration finished overnight", "first draft of the {t} onboarding guide is up"]
ASK_OTHER = ["@{p} can you sanity check the {t} config?", "@{p} could you rebase the {t} branch?",
             "@{p} can you own the {t} follow-up?", "@{p} mind taking a look at the {t} alert?",
             "@{p} can you send the {t} export to support?", "@{p} could you demo {t} on Thursday?",
             "@{p} please add the {t} ticket to the sprint", "@{p} can you pair with {q} on {t}?",
             "@{p} when you have a sec, the {t} flag can be removed",
             "@{p} can you update the {t} status page copy?"]
REPLIES = ["on it", "done", "👍", "thanks!", "makes sense", "will do", "+1", "lgtm",
           "good catch", "ack", "sounds good", "haha", "nice", "agreed", "yep",
           "I'll take a look later", "fixed", "merged", "ty", "🙏", "ok cool", "same here",
           "can confirm", "interesting", "seen it, all fine"]
OPTIONAL = ["@here optional: lunch and learn on {t} Thursday, pizza provided",
            "@here if anyone wants to join the {t} reading group, it's open",
            "@here fyi the {t} office hours are cancelled this week",
            "@here the coffee machine on 3 is fixed",
            "@here recording of the {t} talk is in the drive for anyone who missed it",
            "@here no action needed: the {t} upgrade went fine"]
CI = ["✅ {s} main #{n} passed in {m}m", "✅ {s} PR #{n} checks passed",
      "❌ {s} PR #{n} failed: lint (author notified)", "✅ {s} nightly build passed",
      "🔁 {s} main #{n} re-run passed", "⚠️ {s} flaky test quarantined by bot: test_{t}"]
SOCIAL = ["look at this good boy 🐶", "anyone tried the new ramen place?", "5k at lunch tomorrow?",
          "sourdough attempt #4 🍞", "new album from my favorite band dropped", "board games friday?",
          "my tomatoes finally ripened", "golden hour from the roof 🌇", "who's watching the race sunday",
          "send cat pics", "this podcast episode is great", "finished that book, 10/10",
          "climbing gym was packed", "bike ride saturday if the weather holds", "chess puzzle of the day ♟️",
          "anyone want my extra concert ticket?", "the café downstairs has oat milk now",
          "rainy day playlist recommendations?", "built a bookshelf this weekend", "what a game last night"]
STANDUP = ["yesterday: {t} reviews. today: {t} tests. blockers: none",
           "y: wrapped {t}. t: starting on {u}. no blockers",
           "out this afternoon, back tomorrow", "y: {t} bugfix. t: {u} docs. b: none"]

# ---- email --------------------------------------------------------------------
SPAM = [("Crypto Daily <promo@cryptodaily.example>", "You've been selected: 3 BTC bonus inside 🚀"),
        ("Rx Discounts <deals@rx-savings.example>", "Save 80% on prescriptions today"),
        ("Prize Center <winner@prizecenter.example>", "Congratulations! You won a $500 gift card"),
        ("SEO Experts <growth@rankboost.example>", "We can get your site to #1 on Google"),
        ("Loan Desk <offers@quickloan.example>", "Pre-approved: $25,000 at 0% APR"),
        ("Hot Singles <match@lovenearby.example>", "3 people near you want to chat"),
        ("Warranty Dept <notice@autowarranty.example>", "Final notice: your vehicle warranty"),
        ("Inheritance Office <claims@estate-office.example>", "Unclaimed funds in your name"),
        ("Webinar Pro <invite@webinarpro.example>", "Masterclass: 10x your productivity"),
        ("Solar Savings <info@sunsave.example>", "Your roof qualifies for free solar")]
PHISH = [("IT Helpdesk <helpdesk@kestrel-support.example>", "Your mailbox is 98% full: verify now",
          "Click here within 24 hours to keep your mailbox active. Kestrel IT"),
         ("Payroll Team <payroll@kestrel-hr.example>", "Action required: confirm your direct deposit",
          "Your payroll details could not be verified. Log in to confirm or your salary will be delayed."),
         ("DocuSign <sign@docu-sign-secure.example>", "You have a document waiting for signature",
          "Please review and sign the attached document. This link expires in 12 hours."),
         ("Microsoft 365 <no-reply@m365-account.example>", "Unusual sign-in activity",
          "We blocked a sign-in attempt. Verify your identity to restore access."),
         ("Bank Security <alerts@secure-bank-verify.example>", "Your account has been suspended",
          "Confirm your card details to lift the suspension.")]
BANK = [("Harborline Bank <alerts@harborline.example>", "Your statement is ready",
         "Your September statement is available in online banking. No action is needed."),
        ("Harborline Bank <alerts@harborline.example>", "Card purchase: ${a} at {m}",
         "A purchase of ${a} at {m} was made with your card ending 4412. If this was you, no action is needed."),
        ("Harborline Bank <alerts@harborline.example>", "Direct deposit received",
         "A deposit of ${a} was posted to your checking account."),
        ("Meridian Card <service@meridiancard.example>", "Autopay scheduled for your balance",
         "Your autopay of ${a} is scheduled. No action is needed."),
        ("Meridian Card <service@meridiancard.example>", "Payment received, thank you",
         "We received your payment of ${a}.")]
CODES = [("Harborline Bank <alerts@harborline.example>", "Your verification code is {c}"),
         ("StreamBox <no-reply@streambox.example>", "{c} is your StreamBox sign-in code"),
         ("Ridely <no-reply@ridely.example>", "Your Ridely code: {c}"),
         ("Cloudvault <security@cloudvault.example>", "Cloudvault login code {c}")]
SHOP = [("Oakline Outfitters <orders@oakline.example>", "Your order #{o} has shipped",
         "Your package is on the way. Track it anytime from your account."),
        ("Parcelpost <tracking@parcelpost.example>", "Out for delivery today",
         "Your parcel {o} is out for delivery. No signature required."),
        ("Parcelpost <tracking@parcelpost.example>", "Delivered: parcel {o}",
         "Your parcel was left at the front door."),
        ("Grocerly <receipts@grocerly.example>", "Your Grocerly receipt (${a})",
         "Thanks for shopping. Your order of ${a} was delivered."),
        ("Ridely <receipts@ridely.example>", "Your Tuesday evening trip with Ridely",
         "Trip total ${a}. Rate your driver in the app."),
        ("Forkful <orders@forkful.example>", "Your Forkful order is on the way",
         "Estimated arrival 25 minutes. Order total ${a}."),
        ("StreamBox <billing@streambox.example>", "Your StreamBox membership renewed",
         "Your plan renewed for ${a}. Nothing else to do."),
        ("City Power <billing@citypower.example>", "Your bill is ready, autopay is on",
         "Your bill of ${a} will be paid automatically on the 15th."),
        ("Bookhaven <hello@bookhaven.example>", "Books we think you'll love",
         "New releases picked for you this week."),
        ("City Gym <members@citygym.example>", "Your class schedule for next week",
         "Classes you might like: spin, yoga, strength. Booking is optional.")]
NEWS = [("The Morning Byte <hello@morningbyte.example>", "Today's top tech stories"),
        ("Platform Weekly <news@platformweekly.example>", "Issue #{n}: scaling queues"),
        ("Rust Notes <letter@rustnotes.example>", "This week in Rust-ish things"),
        ("Product Hunt Daily <daily@phdaily.example>", "Top products today"),
        ("Neighborhood News <editor@nbhdnews.example>", "Street fair this weekend"),
        ("Hiking Club <club@trailmix.example>", "Trip report: Ridge Loop"),
        ("Recipe Box <cook@recipebox.example>", "5 dinners in 30 minutes"),
        ("Market Brief <brief@marketbrief.example>", "Markets close mixed")]
FAMILY = [("Mom <mom.kowalski@mailbox.example>", "Photos from the weekend",
           "Here are the photos from Sunday! The kids loved the lake. Love, Mom"),
          ("Mom <mom.kowalski@mailbox.example>", "Re: Thanksgiving",
           "Great, we're all set then. Your brother is bringing pie."),
          ("Pete Kowalski <pete.k@mailbox.example>", "lol look at this",
           "found this old picture of us at the fair"),
          ("Aunt Maria <maria.n@mailbox.example>", "Recipe you asked about",
           "Here's the pierogi recipe. Enjoy!"),
          ("Sofia Ruiz <sofia.r@mailbox.example>", "Re: dinner",
           "That was so fun, thanks again! Same time next month."),
          ("Ben Ortiz <ben.o@mailbox.example>", "Fantasy league recap",
           "Week {n} recap: I'm still last. Rematch next week."),
          ("Book Club <club@pageturners.example>", "Next month's pick",
           "We're reading the one about the lighthouse. See you there.")]
WORK_NOTIF = [("Google Workspace <comments-noreply@gsuite.example>", "{p} commented on '{t} notes'",
               "{p}: looks good, small nit on section 2 (for the author). You're receiving this because the doc is shared with you."),
              ("Kestrel Calendar <calendar@kestrel.example>", "Accepted: {t} sync",
               "{p} accepted the {t} sync invitation."),
              ("Kestrel Calendar <calendar@kestrel.example>", "Updated invitation: {t} weekly",
               "The {t} weekly moved 15 minutes later. You are an optional attendee."),
              ("Kestrel IT <it@kestrel.example>", "Scheduled maintenance this weekend",
               "VPN maintenance Saturday 2-4am. No action needed."),
              ("Kestrel People Team <people@kestrel.example>", "This month's People newsletter",
               "Welcome to our new hires, upcoming holidays, and the benefits FAQ."),
              ("Kestrel Facilities <facilities@kestrel.example>", "Kitchen deep clean Friday",
               "Please excuse the mess on Friday afternoon."),
              ("PagerTree <alerts@pagertree.example>", "Incident resolved: {s} latency",
               "The incident was acknowledged by {p} and resolved. You are not on call."),
              ("Vendor <sales@{v}.example>", "Quick intro: {v} for engineering teams",
               "We help teams like yours ship faster. Here's a two-minute video. Best, the {v} team"),
              ("DevConf <events@devconf.example>", "Early bird ends soon: DevConf 2027",
               "Tickets are 30% off until the end of the month."),
              ("Learning Hub <learn@kestrel.example>", "New courses in your library",
               "Optional courses on cloud cost, SQL, and writing.")]
VENDORS = ["shipfast", "logwise", "querycraft", "flagly", "tracewell", "deploydash", "testcraft"]
MERCHANTS = ["Bean There Café", "Oakline Outfitters", "Fresh Fields Market", "Cinema 9",
             "Ridely", "Corner Hardware", "Petsmartly", "Bookhaven", "Forkful"]

JIRA_PROJECTS = {"MOB": ["dana.lee", "lena"], "SUP": ["mei"], "GRW": ["tomas"], "SEC": ["sam"],
                 "INF": ["sam", "raj"], "DOCS": ["tomas", "lena"], "QA": ["mei"], "ANL": ["raj"]}
JIRA_TITLES = ["{t}: tidy up error copy", "{t}: add tracing spans", "{t}: flaky e2e on CI",
               "{t}: upgrade SDK", "{t}: support JSON export", "{t}: improve empty state",
               "{t}: backfill metrics", "{t}: remove dead flag", "{t}: a11y audit fixes",
               "{t}: paginate list endpoint", "{t}: localize profile screen", "{t}: retry on timeout"]
GH_REPOS = ["kestrel/rota-web", "kestrel/ios-client", "kestrel/design-system", "kestrel/docs-site",
            "kestrel/data-jobs", "kestrel/infra-live", "kestrel/sdk-js", "kestrel/sdk-python"]
CAL = ["Daily standup", "Platform 1:1 (Ines)", "Focus time", "Lunch", "Sprint planning",
       "Sprint retro", "Backlog grooming", "All-hands", "Design review: {t}", "Guild meeting",
       "Coffee chat", "Interview loop (shadow, optional)", "Tech talk: {t}", "Team social"]
DRIVE = ["{t} notes", "{t} metrics Q3", "{t} retro notes", "Notes: {t} sync",
         "{t} competitive scan", "{t} user interview summary", "{t} launch plan (Growth team)",
         "Copy of {t} roadmap", "{t} cost model", "Team photos {m}", "Offsite ideas",
         "Book list", "Meal plan", "Recipes to try", "Trip ideas", "Workout log",
         "Budget {m}", "Moving checklist (done)", "Gift ideas (done)"]


def _slack_day(store, d, rng, weekend):
    chans = LIFE_CHANNELS
    n = rng.randint(40, 80) if weekend else rng.randint(840, 980)
    threads = []
    for _ in range(n):
        hh, mm = (rng.randint(9, 22), rng.randint(0, 59)) if weekend else (rng.randint(7, 19), rng.randint(0, 59))
        t, u = rng.choice(TOPICS), rng.choice(TOPICS)
        p, q = rng.sample(PEOPLE_ALL, 2)
        r = rng.random()
        if threads and r < 0.28:
            parent, ch = rng.choice(threads)
            store.slack(ts(d, hh, mm), ch, rng.choice(PEOPLE_ALL), rng.choice(REPLIES), thread_ts=parent)
            continue
        if weekend or r < 0.40:
            ch = rng.choice(chans[19:] + ["#eng-random", "#water-cooler", "#wins", "#lunch"])
            text = rng.choice(SOCIAL)
        elif r < 0.52:
            ch = rng.choice(["#ci", "#builds"])
            text = rng.choice(CI).format(s=rng.choice(SERVICES), n=rng.randint(1000, 9999),
                                         m=rng.randint(3, 19), t=t.replace(" ", "_"))
            store.slack(ts(d, hh, mm), ch, "ci-bot", text)
            continue
        elif r < 0.56:
            ch = "#standup"
            text = rng.choice(STANDUP).format(t=t, u=u)
        elif r < 0.84:
            ch = rng.choice(chans[:19])
            text = rng.choice(TECH).format(t=t, p="@" + p)
        elif r < 0.97:
            ch = rng.choice(chans[:19])
            text = rng.choice(ASK_OTHER).format(p=p, q="@" + q, t=t)
        else:
            ch = rng.choice(["#office-sf", "#remote", "#eng-random", "#product-updates"])
            text = rng.choice(OPTIONAL).format(t=t)
        sid = store.slack(ts(d, hh, mm), ch, rng.choice(PEOPLE_ALL), text)
        if rng.random() < 0.15:
            threads.append((sid, ch))
    # DMs and group chats with no asks for the user
    for _ in range(rng.randint(0, 3) if weekend else rng.randint(3, 9)):
        other = rng.choice(PEOPLE_ALL)
        store.slack(ts(d, rng.randint(9, 18), rng.randint(0, 59)), "D-dana-%s" % other, other,
                    rng.choice(["haha that meeting", "thanks for the help earlier!", "see you at lunch",
                                "nice demo today", "fyi I'm out tomorrow", "saw your PR got merged, congrats",
                                "lol", "ok sounds good", "that bug was wild"]))


def _email_day(store, d, rng, weekend):
    if not weekend:
        for _ in range(rng.randint(60, 90)):
            frm, subj, body = rng.choice(WORK_NOTIF)
            fill = dict(p=FIRST[rng.choice(PEOPLE_ALL)], t=rng.choice(TOPICS),
                        s=rng.choice(SERVICES), v=rng.choice(VENDORS))
            store.email(ts(d, rng.randint(7, 20), rng.randint(0, 59)), frm.format(**fill), WORK,
                        subj.format(**fill), body.format(**fill))
        if rng.random() < 0.08:
            frm, subj, body = rng.choice(PHISH[:3])
            store.email(ts(d, rng.randint(6, 22)), frm, WORK, subj, body)
    # personal account, every day
    for _ in range(rng.randint(45, 75)):
        r = rng.random()
        when = ts(d, rng.randint(6, 23), rng.randint(0, 59))
        a = "%d.%02d" % (rng.randint(4, 240), rng.randint(0, 99))
        if r < 0.30:
            frm, subj = rng.choice(SPAM)
            body = "Limited time offer. Click to claim. Unsubscribe here."
        elif r < 0.33:
            frm, subj, body = rng.choice(PHISH)
        elif r < 0.48:
            frm, subj, body = rng.choice(BANK)
            m = rng.choice(MERCHANTS)
            subj, body = subj.format(a=a, m=m), body.format(a=a, m=m)
        elif r < 0.56:
            frm, subj = rng.choice(CODES)
            c = "%06d" % rng.randint(0, 999999)
            subj = subj.format(c=c)
            body = "Your code is %s. It expires in 10 minutes. If you didn't request it, you can ignore this." % c
        elif r < 0.80:
            frm, subj, body = rng.choice(SHOP)
            o = "%d-%04d" % (rng.randint(100, 999), rng.randint(0, 9999))
            subj, body = subj.format(a=a, o=o), body.format(a=a, o=o)
        elif r < 0.94:
            frm, subj = rng.choice(NEWS)
            subj = subj.format(n=rng.randint(100, 400))
            body = "This week's issue. Read online. Unsubscribe anytime."
        else:
            frm, subj, body = rng.choice(FAMILY)
            body = body.format(n=rng.randint(1, 17))
        store.email(when, frm, PERSONAL, subj, body, account="personal")


def _jira_github_day(store, d, rng, num, weekend):
    if weekend:
        return
    for _ in range(rng.randint(100, 140)):
        k = rng.choice(sorted(JIRA_PROJECTS))
        if rng.random() < 0.3 or not num[k]:
            num[k].append(rng.choice(JIRA_TITLES).format(t=rng.choice(TOPICS)))
        idx = rng.randrange(len(num[k]))
        status = rng.choice(["To Do", "In Progress", "In Review", "Done"])
        store.jira(ts(d, rng.randint(9, 18), rng.randint(0, 59)), "%s-%d" % (k, 100 + idx), num[k][idx],
                   status, rng.choice(JIRA_PROJECTS[k] + [None]), rng.choice(["tomas", "ines", "sam", "mei"]),
                   priority=rng.choice(["Low", "Medium", "Medium", "High"]),
                   comments=[{"author": PEOPLE[rng.choice(COWORKERS[:6])][0],
                              "body": rng.choice(["moved to next sprint", "repro'd on staging",
                                                  "PR is up", "closing as duplicate", "works for me"])}]
                   if rng.random() < 0.4 else None)
    for _ in range(rng.randint(100, 140)):
        repo = rng.choice(GH_REPOS)
        n = rng.randint(900, 4999)
        r = rng.random()
        author = rng.choice(["ana-r", "kai-t", "jo-kim", "omar-s", "beth-w", "luis-m", "dependabot[bot]", "zoe-h"])
        if r < 0.35:
            store.github(ts(d, rng.randint(8, 20), rng.randint(0, 59)), repo, "pull_request", n,
                         "Bump %s from 1.%d.0 to 1.%d.1" % (rng.choice(["axios", "urllib3", "boto3", "react", "pytest", "zod"]),
                                                            rng.randint(2, 9), rng.randint(10, 20)),
                         rng.choice(["open", "closed"]), "dependabot[bot]", body="Automated dependency update.",
                         requested_teams=["frontend-guild"] if "web" in repo or "ios" in repo else ["data-team"],
                         labels=["dependencies"])
        elif r < 0.75:
            rev = rng.choice(["ana-r", "kai-t", "jo-kim", "omar-s", "zoe-h", "danalee-fe", "lena-f"])
            store.github(ts(d, rng.randint(8, 20), rng.randint(0, 59)), repo, "pull_request", n,
                         rng.choice(JIRA_TITLES).format(t=rng.choice(TOPICS)), rng.choice(["open", "closed"]),
                         author, requested_reviewers=[rev], merged=rng.random() < 0.4,
                         comments=[{"user": rev, "body": rng.choice(["lgtm", "nit: naming", "approved", "can you add a test?"])}])
        else:
            store.github(ts(d, rng.randint(8, 20), rng.randint(0, 59)), repo, "issue", n,
                         rng.choice(JIRA_TITLES).format(t=rng.choice(TOPICS)), rng.choice(["open", "closed"]),
                         author, assignees=[rng.choice(["ana-r", "kai-t", "jo-kim", "omar-s"])])


def _calendar_day(store, d, rng, weekend):
    if weekend:
        if rng.random() < 0.4:
            store.event(ts(d, 9), rng.choice(["Farmers market", "Climbing", "Brunch with Sofia", "Hike", "Movie night"]),
                        ts(d, rng.randint(9, 19)), ts(d, 21), PERSONAL, [PERSONAL])
        return
    for _ in range(rng.randint(18, 30)):
        name = rng.choice(CAL).format(t=rng.choice(TOPICS))
        h = rng.randint(8, 17)
        org = rng.choice(PEOPLE_ALL)
        att = [WORK] + ["%s@kestrel.example" % x for x in rng.sample(PEOPLE_ALL, rng.randint(1, 8))]
        if rng.random() < 0.35:
            att = ["%s@kestrel.example" % x for x in rng.sample(PEOPLE_ALL, rng.randint(2, 8))]  # not invited
        store.event(ts(d, max(7, h - 1)), name, ts(d, h, rng.choice([0, 30])), ts(d, h + 1),
                    "%s@kestrel.example" % org, att,
                    description=rng.choice(["", "Agenda in the doc.", "Optional.", "Recurring."]))


def _drive_day(store, d, rng):
    for _ in range(rng.randint(15, 35)):
        name = rng.choice(DRIVE).format(t=rng.choice(TOPICS), m=d.strftime("%B"))
        owner = rng.choice(PEOPLE_ALL)
        body = rng.choice(["Draft. Comments welcome from the team.", "Numbers from last sprint, read-only.",
                           "Meeting notes. Decisions: keep current plan. Owners listed per item (not Dana).",
                           "Personal notes.", "Links and references.", "Summary of interviews, for the PM."])
        store.doc(ts(d, rng.randint(8, 22), rng.randint(0, 59)), name,
                  "%s@kestrel.example" % owner if "Budget" not in name and "Meal" not in name else PERSONAL,
                  body, shared_by="%s@kestrel.example" % owner if rng.random() < 0.6 else None)


def life(store, start, end, seed):
    """Add the full world's everyday traffic between start and end."""
    rng = random.Random(seed)
    num = {k: [] for k in JIRA_PROJECTS}
    for d in days(start, end):
        weekend = d.weekday() >= 5
        _slack_day(store, d, rng, weekend)
        _email_day(store, d, rng, weekend)
        _jira_github_day(store, d, rng, num, weekend)
        _calendar_day(store, d, rng, weekend)
        _drive_day(store, d, rng)
        _rest_of_life_day(store, d, rng)


# ---- the rest of Dana's life: freelance, job hunt, old accounts, side projects ----
FREELANCE = "dana.builds@mailbox.example"
OLD = "danak.dev@mailbox.example"
UP = "Upwork <notifications@upwork.example>"
SKILLS = ["Shopify", "React", "Python", "API integration", "Postgres", "Next.js", "Stripe",
          "data pipeline", "Django", "TypeScript", "AWS Lambda", "web scraping"]
UPWORK = [("New jobs matching '{k}'", "{n} new jobs match your saved search '{k}'. Budgets from $500."),
          ("Your proposal was viewed", "A client viewed your proposal for '{k} help needed'. No action needed."),
          ("Your proposal was declined", "The client hired someone else for '{k} contractor'. Keep going!"),
          ("Weekly summary", "You earned ${a} this week. Pending: $0. Available: ${a}."),
          ("Your Connects renewed", "You have 80 Connects available this month."),
          ("Profile tip", "Freelancers with a video intro get more invites. Adding one is optional."),
          ("Job closed: {k} specialist", "A job you applied to was closed by the client."),
          ("Upwork Academy", "New course: pricing your freelance work.")]
UP_PHISH = ("Upwork Payments <support@upwork-payments-verify.example>",
            "Your earnings are on hold: verify your identity",
            "We could not verify your payout method. Log in within 24 hours to release your earnings.")
HANDSHAKE = "Handshake <messages@joinhandshake.example>"
HS = [("Jobs for you this week", "{n} new roles for Westbridge alumni: platform, data, backend."),
      ("An employer viewed your profile", "A company in Healthcare viewed your profile."),
      ("Virtual career fair Oct 22", "Registration is optional. 140 employers attending."),
      ("Alumni mixer reminder", "RSVP is optional. Drinks and snacks provided."),
      ("Complete your profile", "Profiles with skills get 3x more views. This is optional.")]
LINKBOARD = "Linkboard <notify@linkboard.example>"
LB = [("You appeared in {n} searches this week", "Recruiters and others found your profile."),
      ("A recruiter shared a role", "We think you'd be a great fit for Senior Engineer at a "
       "fast-growing startup. View the role on Linkboard."),
      ("Your weekly network update", "{n} people in your network changed jobs.")]
TOOLS = [("Figma <billing@figma.example>", "Receipt for your Figma Professional plan", "Paid ${a}. Thank you."),
         ("Paylink <payouts@paylink.example>", "Payout sent to your bank", "${a} is on its way to your bank."),
         ("Toggl Track <hello@toggl.example>", "Your weekly time report", "You tracked {n} hours this week."),
         ("Notion <team@notion.example>", "Your workspace was renewed", "Your plan renewed for ${a}.")]
PROJECT_FILES = ["plantpal - ideas", "plantpal README draft", "plantpal - user feedback", "recipe app sketches",
                 "freelance rates 2026", "portfolio case studies", "taxes 2025 checklist (done)",
                 "side project ideas", "home lab notes", "reading notes", "running plan", "trip packing list (done)"]
PROJECT_BODY = ["Notes and ideas. Nothing scheduled.", "Draft text, keep iterating.",
                "Feedback from beta testers: likes the reminders, wants widgets.",
                "Sketches and links.", "Rates: $95/h for API work, $85/h for frontend.",
                "Case studies: inventory sync, brand site, booking widget."]


def _rest_of_life_day(store, d, rng):
    when = lambda: ts(d, rng.randint(6, 23), rng.randint(0, 59))
    a = lambda: "%d.%02d" % (rng.randint(9, 1900), rng.randint(0, 99))
    for _ in range(rng.randint(5, 11)):
        subj, body = rng.choice(UPWORK)
        k = rng.choice(SKILLS)
        store.email(when(), UP, FREELANCE, subj.format(k=k), body.format(k=k, n=rng.randint(3, 40), a=a()),
                    account=FREELANCE)
    if rng.random() < 0.12:
        store.email(when(), UP_PHISH[0], FREELANCE, UP_PHISH[1], UP_PHISH[2], account=FREELANCE)
    if rng.random() < 0.35:
        frm, subj, body = rng.choice(TOOLS)
        store.email(when(), frm, FREELANCE, subj, body.format(a=a(), n=rng.randint(4, 30)), account=FREELANCE)
    for _ in range(rng.randint(1, 4)):
        subj, body = rng.choice(HS)
        store.email(when(), HANDSHAKE, PERSONAL, subj, body.format(n=rng.randint(5, 60)), account="personal")
    for _ in range(rng.randint(1, 3)):
        subj, body = rng.choice(LB)
        store.email(when(), LINKBOARD, PERSONAL, subj.format(n=rng.randint(5, 90)), body.format(n=rng.randint(2, 30)),
                    account="personal")
    for _ in range(rng.randint(12, 24)):
        frm, subj = rng.choice(SPAM + NEWS)
        store.email(when(), frm, OLD, subj.format(n=rng.randint(100, 400)),
                    "Unsubscribe anytime.", account=OLD)
    if rng.random() < 0.5:
        store.doc(when(), rng.choice(PROJECT_FILES), PERSONAL, rng.choice(PROJECT_BODY))
    if rng.random() < 0.6:
        store.github(when(), "dana-k/plantpal", "pull_request" if rng.random() < 0.3 else "issue",
                     rng.randint(5, 60), rng.choice(["Bump expo from 51.0.%d to 51.0.%d" % (rng.randint(1, 9), rng.randint(10, 20)),
                                                     "Feature idea: widgets", "Crash on Android 12 (cannot repro)",
                                                     "Thanks for the app!"]),
                     rng.choice(["open", "closed"]), rng.choice(["dependabot[bot]", "plant-lover-22", "mo-dev"]),
                     labels=["dependencies"] if rng.random() < 0.3 else None)
