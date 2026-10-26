"""Arcs for the 'full' world: the rest of Dana's life.

Dana freelances on the side (Upwork, plus one direct client), is quietly job
hunting (an offer, a Handshake recruiter), and keeps personal projects in
Drive. A third Gmail account, dana.builds@mailbox.example, is the freelance
one; the old danak.dev@mailbox.example only gets spam.

Seven DEV/TEST pairs, same phenomenon on each side:
  L1 unpaid finished work      L2 already paid (trap)
  L3 deliverable with a date   L4 job offer with a deadline
  L5 extra ask withdrawn       L6 own TODO in a project file
  L7 a recruiter or client question
Priority follows the long-run rules (RULES.md, today Oct 13): freelance
clients count as clients; "personal" means the personal and oss workspaces;
job-search and freelance are not personal.
"""

from arcs import arc, open_, absent

FREELANCE = "dana.builds@mailbox.example"
OLD = "danak.dev@mailbox.example"
PERSONAL = "dana.kowalski@mailbox.example"
UPWORK = "Upwork <notifications@upwork.example>"
HANDSHAKE = "Handshake <messages@joinhandshake.example>"

LIFE_ARCS = []


def larc(aid, split, phenomenon):
    def deco(fn):
        LIFE_ARCS.append((aid, split, phenomenon, fn))
        return fn
    return deco


def up(s, date, subject, body):
    return s.email(date, UPWORK, FREELANCE, subject, body, account=FREELANCE)


# ------------------------------------------------------- L1 unpaid finished work
@larc("LD01", "dev", "unpaid finished work")
def ld01(s):
    a = up(s, "2026-08-20T18:10:00Z", "You submitted work for review: Milestone 1",
           "Contract: Shopify inventory sync (Fernhill Goods)\nMilestone 1: Sync MVP, $1,200\n"
           "You submitted work. The client will review it.")
    b = up(s, "2026-08-27T15:02:00Z", "New message from Marcus Bell (Fernhill Goods)",
           "Marcus Bell: Looks great, thanks Dana! The sync is running fine on our store.")
    c = up(s, "2026-09-24T09:00:00Z", "Milestone 1 is still waiting for the client",
           "Contract: Shopify inventory sync (Fernhill Goods)\nMilestone 1 ($1,200) has not been "
           "approved or released yet. You can message the client or request a release.")
    m = up(s, "2026-09-25T18:30:00Z", "Message sent to Marcus Bell",
           "You: Hi Marcus, glad it's working! Could you approve and release the Milestone 1 "
           "payment when you get a moment?")
    d = s.email("2026-10-22T16:40:00Z", UPWORK, FREELANCE, "Payment released: $1,200.00",
                "Fernhill Goods released $1,200.00 for Milestone 1: Sync MVP.", account=FREELANCE)
    return {"sources": [a, b, c, m, d],
            "c1": open_(["fernhill", "payment"], "freelance", None, "medium",
                        owner="counterparty", blocked_on="fernhill"),
            "c2": absent(["fernhill", "payment"])}


@larc("LT01", "test", "unpaid finished work")
def lt01(s):
    a = s.email("2026-08-30T20:15:00Z", FREELANCE, "ap@lumendental.example",
                "Invoice INV-0042: booking widget",
                "Hi Rosa, attached is invoice INV-0042 for the booking widget ($2,400), "
                "net 30, so due Sep 29. Thanks for a great project! Dana", sent=True,
                account=FREELANCE)
    b = s.email("2026-08-31T09:12:00Z", "Rosa Lin <rosa@lumendental.example>", FREELANCE,
                "RE: Invoice INV-0042: booking widget",
                "Got it, I'll pass it to accounts. The widget is live and patients love it!",
                account=FREELANCE)
    c = s.email("2026-10-06T19:30:00Z", FREELANCE, "ap@lumendental.example",
                "RE: Invoice INV-0042: booking widget",
                "Hi, just a friendly reminder that INV-0042 was due Sep 29. Could you let me "
                "know when it will be paid? Dana", sent=True, account=FREELANCE)
    d = s.email("2026-10-28T14:05:00Z", "Lumen Dental Accounts <ap@lumendental.example>",
                FREELANCE, "RE: Invoice INV-0042: booking widget",
                "Apologies for the delay, INV-0042 was paid today by bank transfer.",
                account=FREELANCE)
    e = s.email("2026-10-29T08:00:00Z", "Harborline Bank <alerts@harborline.example>", PERSONAL,
                "Incoming transfer: $2,400.00", "A transfer of $2,400.00 from LUMEN DENTAL LABS "
                "was credited to your checking account.", account="personal")
    return {"sources": [a, b, c, d, e],
            "c1": open_(["inv-0042"], "freelance", "2026-09-29", "high",
                        owner="counterparty", blocked_on="lumen"),
            "c2": absent(["inv-0042"])}


# ---------------------------------------------------------- L2 already paid
@larc("LD02", "dev", "already paid")
def ld02(s):
    a = up(s, "2026-07-29T17:00:00Z", "Payment released: $800.00",
           "Pixelmint released $800.00 for Milestone 2: Landing page build.")
    b = up(s, "2026-07-30T10:00:00Z", "Contract ended: Landing page build (Pixelmint)",
           "Pixelmint ended the contract and left you 5 stars: \"Fast and clear. Would hire again.\"")
    c = up(s, "2026-08-06T10:00:00Z", "You can still leave feedback for Pixelmint",
           "Feedback is optional and helps other freelancers. You can leave it any time.")
    return {"sources": [a, b, c], "isolation": "freelance",
            "c1": absent(["pixelmint"]), "c2": absent(["pixelmint"])}


@larc("LT02", "test", "already paid")
def lt02(s):
    a = s.email("2026-07-25T21:00:00Z", FREELANCE, "hello@harborkite.example",
                "Invoice INV-0039: brand site", "Hi Theo, here's INV-0039 ($1,650), due Aug 24. "
                "Thanks! Dana", sent=True, account=FREELANCE)
    b = s.email("2026-08-15T12:30:00Z", "Paylink <receipts@paylink.example>", FREELANCE,
                "You received $1,650.00 from Harbor Kite Studio",
                "Harbor Kite Studio paid invoice INV-0039 in full. The money is on its way to your "
                "bank.", account=FREELANCE)
    c = s.email("2026-08-15T13:00:00Z", "Theo Grant <hello@harborkite.example>", FREELANCE,
                "RE: Invoice INV-0039: brand site", "Paid! Thanks again, the site looks great.",
                account=FREELANCE)
    return {"sources": [a, b, c], "isolation": "freelance",
            "c1": absent(["inv-0039"], ["harbor kite"]), "c2": absent(["inv-0039"], ["harbor kite"])}


# ---------------------------------------------------- L3 deliverable with a date
@larc("LD03", "dev", "freelance deliverable")
def ld03(s):
    a = up(s, "2026-09-02T11:00:00Z", "Milestone 2 activated: Low-stock alerts",
           "Contract: Shopify inventory sync (Fernhill Goods)\nMilestone 2: Low-stock alerts, "
           "$900, due Oct 24.")
    b = up(s, "2026-10-02T16:20:00Z", "New message from Marcus Bell (Fernhill Goods)",
           "Marcus Bell: Hi Dana, are the low-stock alerts still on track for Oct 24?")
    c = up(s, "2026-10-02T21:00:00Z", "Message sent to Marcus Bell",
           "You: Yes, on track for the 24th.")
    d = up(s, "2026-10-23T22:10:00Z", "You submitted work for review: Milestone 2",
           "Milestone 2: Low-stock alerts, $900. You submitted work.")
    e = up(s, "2026-10-30T15:00:00Z", "Payment released: $900.00",
           "Fernhill Goods released $900.00 for Milestone 2: Low-stock alerts.")
    return {"sources": [a, b, c, d, e],
            "c1": open_(["low-stock", "alerts"], "freelance", "2026-10-24", "medium"),
            "c2": absent(["low-stock", "alerts"])}


@larc("LT03", "test", "freelance deliverable")
def lt03(s):
    a = s.email("2026-09-29T15:00:00Z", "Priya Raman <priya@orbitlabs.example>", FREELANCE,
                "SOW: API security review",
                "Hi Dana, signed SOW attached. Scope: review our public API and send the audit "
                "report by Oct 15. Fee $3,000 on delivery. Priya Raman, CTO, Orbit Labs",
                account=FREELANCE)
    b = s.email("2026-09-29T18:00:00Z", FREELANCE, "priya@orbitlabs.example",
                "RE: SOW: API security review", "Thanks Priya, countersigned. You'll have the "
                "audit report by Oct 15.", sent=True, account=FREELANCE)
    c = s.email("2026-10-15T20:30:00Z", FREELANCE, "priya@orbitlabs.example",
                "RE: SOW: API security review", "Hi Priya, the audit report is attached, plus "
                "the invoice. Happy to walk through it. Dana", sent=True, account=FREELANCE)
    d = s.email("2026-10-24T13:10:00Z", "Paylink <receipts@paylink.example>", FREELANCE,
                "You received $3,000.00 from Orbit Labs",
                "Orbit Labs paid your invoice for the API security review in full.",
                account=FREELANCE)
    return {"sources": [a, b, c, d],
            "c1": open_(["orbit", "audit"], "freelance", "2026-10-15", "high"),
            "c2": absent(["orbit", "audit"])}


# ------------------------------------------------- L4 job offer with a deadline
@larc("LD04", "dev", "offer deadline")
def ld04(s):
    a = s.email("2026-10-08T17:00:00Z", "Quillmark Talent <talent@quillmark.example>", PERSONAL,
                "Your offer from Quillmark",
                "Hi Dana, we're thrilled to offer you the Staff Engineer role. Details are in the "
                "attached letter. Please let us know your decision by Oct 24. Best, Hana, "
                "Quillmark Talent", account="personal")
    b = s.email("2026-10-21T19:00:00Z", PERSONAL, "talent@quillmark.example",
                "RE: Your offer from Quillmark", "Hi Hana, thank you so much. After a lot of "
                "thought I've decided to decline. Dana", sent=True, account="personal")
    return {"sources": [a, b],
            "c1": open_(["quillmark", "offer"], "job-search", "2026-10-24", "medium"),
            "c2": absent(["quillmark", "offer"])}


@larc("LT04", "test", "offer deadline")
def lt04(s):
    a = s.email("2026-10-09T15:00:00Z", HANDSHAKE, PERSONAL,
                "New message from Tidewater Analytics",
                "Jonah Pike (Tidewater Analytics): Congratulations Dana! Your offer for Senior "
                "Data Platform Engineer is in Handshake. Please review and sign by Oct 16.",
                account="personal")
    b = s.email("2026-10-14T18:00:00Z", HANDSHAKE, PERSONAL, "Message sent to Jonah Pike",
                "You: Thanks Jonah! Could I have until Oct 30 to decide? I'm finishing another "
                "process.", account="personal")
    c = s.email("2026-10-15T10:00:00Z", HANDSHAKE, PERSONAL,
                "New message from Tidewater Analytics",
                "Jonah Pike (Tidewater Analytics): No problem, Oct 30 works. Talk soon.",
                account="personal")
    return {"sources": [a, b, c],
            "c1": open_(["tidewater", "offer"], "job-search", "2026-10-16", "high"),
            "c2": open_(["tidewater", "offer"], "job-search", "2026-10-30", None)}


# ------------------------------------------------- L5 extra ask then withdrawn
@larc("LD05", "dev", "extra ask withdrawn")
def ld05(s):
    a = up(s, "2026-09-15T14:00:00Z", "New message from Marcus Bell (Fernhill Goods)",
           "Marcus Bell: Could you also add a Slack notification when an order fails to sync?")
    b = up(s, "2026-09-17T10:30:00Z", "New message from Marcus Bell (Fernhill Goods)",
           "Marcus Bell: Actually scratch the Slack notification, our intern will set that up.")
    return {"sources": [a, b], "isolation": "freelance",
            "c1": absent(["slack notification"]), "c2": absent(["slack notification"])}


@larc("LT05", "test", "extra ask withdrawn")
def lt05(s):
    a = s.email("2026-10-01T16:00:00Z", "Priya Raman <priya@orbitlabs.example>", FREELANCE,
                "Terraform review?", "One more thing: could you also look over our Terraform "
                "for the API stack?", account=FREELANCE)
    b = s.email("2026-10-03T09:00:00Z", "Priya Raman <priya@orbitlabs.example>", FREELANCE,
                "RE: Terraform review?", "Never mind on the Terraform, our SRE already reviewed "
                "it. Just the API audit please.", account=FREELANCE)
    return {"sources": [a, b], "isolation": "freelance",
            "c1": absent(["terraform", "orbit"]), "c2": absent(["terraform", "orbit"])}


# --------------------------------------------- L6 own TODO in a project file
@larc("LD06", "dev", "own todo in a file")
def ld06(s):
    a = s.doc("2026-09-12T21:00:00Z", "plantpal - notes", PERSONAL,
              "PlantPal (watering reminder app)\n- v0.3 shipped to TestFlight\n- ideas: "
              "humidity sensor, family sharing\nTODO (me): renew the plantpal.app domain before it "
              "expires Oct 30, auto-renew is off")
    b = s.email("2026-10-01T08:00:00Z", "Namecove <renewals@namecove.example>", PERSONAL,
                "plantpal.app expires on Oct 30", "Auto-renew is off for plantpal.app. Renew "
                "before Oct 30 to keep it.", account="personal")
    c = s.email("2026-10-25T11:00:00Z", "Namecove <renewals@namecove.example>", PERSONAL,
                "Receipt: plantpal.app renewed for 1 year", "Thanks! plantpal.app is renewed "
                "until Oct 30, 2027.", account="personal")
    return {"sources": [a, b, c],
            "c1": open_(["plantpal", "domain"], "oss", "2026-10-30", "low"),
            "c2": absent(["plantpal", "domain"])}


@larc("LT06", "test", "own todo in a file")
def lt06(s):
    a = s.doc("2026-09-20T22:00:00Z", "tinyq - docs site notes", PERSONAL,
              "tinyq docs site (open source)\n- new theme: done\n- search: done\nTODO (me): move "
              "the tinyq docs site off Hostlane before the legacy plan shuts down Nov 1")
    b = s.email("2026-09-25T09:00:00Z", "Hostlane <support@hostlane.example>", PERSONAL,
                "Your legacy plan retires on Nov 1", "Sites on the legacy plan will go offline on "
                "Nov 1. Move your site (tinyq-docs) to keep it online.", account="personal")
    c = s.email("2026-11-02T07:00:00Z", "Hostlane <support@hostlane.example>", PERSONAL,
                "Your site is offline", "tinyq-docs went offline when the legacy plan retired on "
                "Nov 1. Move it to a current plan to bring it back.", account="personal")
    return {"sources": [a, b, c],
            "c1": open_(["tinyq", "hostlane"], "oss", "2026-11-01", "low"),
            "c2": open_(["tinyq", "hostlane"], "oss", "2026-11-01", None)}


# ------------------------------------------ L7 a recruiter or client question
@larc("LD07", "dev", "recruiter or client question")
def ld07(s):
    a = s.email("2026-10-09T13:00:00Z", HANDSHAKE, PERSONAL, "New message from Brightline Health",
                "Maya Ortiz (Brightline Health): Hi Dana, could you share your availability for "
                "a 30-minute intro call next week?", account="personal")
    b = s.email("2026-10-14T09:00:00Z", HANDSHAKE, PERSONAL, "Message sent to Maya Ortiz",
                "You: Hi Maya, Tuesday or Wednesday afternoon works. Dana", account="personal")
    c = s.email("2026-10-14T15:00:00Z", HANDSHAKE, PERSONAL, "New message from Brightline Health",
                "Maya Ortiz (Brightline Health): Booked for Wednesday 2pm, invite sent.",
                account="personal")
    return {"sources": [a, b, c],
            "c1": open_(["brightline", "availability"], "job-search", None, "medium"),
            "c2": absent(["brightline", "availability"])}


@larc("LT07", "test", "recruiter or client question")
def lt07(s):
    a = up(s, "2026-10-11T12:00:00Z", "You've been invited to interview: React ops dashboard",
           "Client: Nimbus Ops. Message from the client: \"Hi Dana, loved your Fernhill work. "
           "When could you start, and what's your rate for this?\" Invitations expire in 14 days.")
    b = up(s, "2026-10-25T12:00:00Z", "Invitation expired: React ops dashboard",
           "The invitation from Nimbus Ops expired because there was no response.")
    return {"sources": [a, b],
            "c1": open_(["nimbus"], "freelance", "2026-10-25", "medium"),
            "c2": absent(["nimbus"])}
