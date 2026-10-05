#!/usr/bin/env python3
"""Held-out v2 world: fresh cast, orgs, domains, helpers. Nothing here is
shared with evals/gen_fixtures.py (see SPEC.md, Independence checks)."""

from __future__ import annotations

TODAY = "2026-10-12"

USER = {"name": "Riley Nakamura", "email": "riley.n@postbox.example"}

WORKSPACES = {
    "ternlog": "employer",       # Tern Logistics
    "quarry": "freelance",       # Quarry Analytics (client)
    "beacon": "volunteer",       # Beacon Food Bank
    "job-search": "job-search",
    "personal": "personal",
}

PEOPLE = {
    "dritan":  ("Dritan Pasha", "dritan.pasha@ternlog.example"),      # manager
    "yuki":    ("Yuki Onoda", "yuki.onoda@ternlog.example"),          # peer
    "chen":    ("Riley Chen", "riley.chen@ternlog.example"),          # name twin
    "celeste": ("Celeste Beaumont", "celeste@quarryanalytics.example"),  # client
    "ibrahim": ("Ibrahim Khoury", "ibrahim@quarryanalytics.example"),
    "petra":   ("Petra Lindgren", "petra@beaconfb.example"),          # volunteer lead
    "gus":     ("Gus Okonkwo", "gus.okonkwo@ternlog.example"),
    "falkner": ("Falkner Group Recruiting", "roles@falkner.example"),
    "novara":  ("Novara Systems Talent", "talent@novarasys.example"),
    "plumber": ("DrainRight Plumbing", "dispatch@drainright.example"),
    "lumen":   ("Lumen Fitness", "members@lumenfit.example"),
    "mailer":  ("SaveMore Weekly", "deals@savemoreweekly.example"),
    "digest":  ("Ops Digest", "newsletter@opsdigest.example"),
}

_seq = {"n": 0}


def sid(prefix):
    _seq["n"] += 1
    return "%s-%03d" % (prefix, _seq["n"])


def reset_ids():
    _seq["n"] = 0


def frm(who):
    name, addr = PEOPLE[who]
    return "%s <%s>" % (name, addr)


def mail(who, subject, body, date, to=None, thread=None, folder="inbox"):
    return {"connector": "email", "id": sid("em"), "thread_id": thread or sid("th"),
            "from": frm(who) if who in PEOPLE else who,
            "to": to or [USER["email"]], "date": date, "subject": subject,
            "body": body, "folder": folder}


def outmail(to_who, subject, body, date, thread=None):
    name, addr = PEOPLE[to_who]
    return {"connector": "email", "id": sid("em"), "thread_id": thread or sid("th"),
            "from": "%s <%s>" % (USER["name"], USER["email"]), "to": [addr],
            "date": date, "subject": subject, "body": body, "folder": "sent"}


def slackmsg(channel, who, text, date):
    return {"connector": "slack", "id": sid("sl"), "channel": channel,
            "user": frm(who) if who in PEOPLE else who, "text": text,
            "date": date}


def tkt(key, summary, status, date, assignee=None, comments=None):
    return {"connector": "ticketing", "id": sid("tk"), "key": key,
            "summary": summary, "status": status, "date": date,
            "assignee": assignee or USER["email"], "comments": comments or []}


def calevent(title, start, created, attendees=None, description=""):
    return {"connector": "calendar", "id": sid("cal"), "title": title,
            "start": start, "date": created, "description": description,
            "attendees": attendees or [USER["email"]]}


def document(title, body, date, author=None):
    return {"connector": "docs", "id": sid("doc"), "title": title,
            "body": body, "date": date, "author": author or USER["email"]}


# -- messiness ingredients (P1 and reused by other phenomena) ----------------

SIG_DRITAN = ("\n\n--\nDritan Pasha | Dir. Network Operations, Tern Logistics"
              "\nThis message and any attachments are confidential and may be"
              " privileged. If you are not the intended recipient please"
              " delete it and notify the sender.")

FOOTER_LEGAL = ("\n\n______________________\nTern Logistics Ltd. Registered"
                " office: 1 Harbourline Way. This email does not create any"
                " contractual obligation to deliver services by any date"
                " unless countersigned.")

HTML_REMNANT = "&nbsp;<br> =20 <div dir=3D\"ltr\">"


def quoted(author_line, text):
    return "\n".join("> " + ln for ln in (author_line + "\n" + text).splitlines())


def commitment(gist, owner, counterparty, due, workspace, sources,
               blocked_on=None, support=None):
    c = {"gist": gist, "owner": owner, "counterparty": counterparty,
         "due": due, "workspace": workspace, "sources": sources,
         "blocked_on": blocked_on}
    if support:
        c["support"] = support
    return c


def expected(commitments=None, forbidden=None, isolation=None, injection=None,
             dedupe=None, same_objective=None, external=False):
    return {"commitments": commitments or [],
            "forbidden": forbidden or [],
            "same_objective": same_objective or [],
            "dedupe": dedupe or [],
            "isolation": isolation or {},
            "injection": injection,
            "external_action_expected": external}
