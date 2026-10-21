#!/usr/bin/env python3
"""Build the public demo: the dashboard over the long-run test world.

    python3 demo/build_demo.py      # writes demo/state/ (config + workspace)

Everything is fictional (Kestrel Labs, Dana Kowalski, .example domains). The
task graph is not hand-written: it is the graph the research engine built
from the realistic long-run world in recorded run lrr-v3, at its first
checkpoint (2026-10-13). This script adds the parts of a dashboard that a
crawl alone does not produce: an approval queue with drafts tied to tasks in
that graph, a correction ledger taken from the run's real dev failures, a
daily log, meeting notes and an open question.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = os.path.join(HERE, "state")
WS = os.path.join(STATE, "workspace")
SOURCE_GRAPH = os.path.join(ROOT, "evals", "results", "longrun", "lrr-v3", "graph", "c1")
TODAY = "2026-10-13"

CONFIG = {
    "demo": True,
    "demo_today": TODAY,
    "demo_responses": "responses.json",
    "workspace_dir": "__WS__",
    "orchestrator_cwd": ".",
    "ticket_host": None,
    "ticket_system_name": "Jira",
    # labels only: in demo mode no tool is ever called
    "action_tools": {"message_send": "slack.send_message",
                     "ticket_update": "jira.add_comment",
                     "calendar_change": "calendar.create_event"},
    "base_tools": "Read", "chat_tools": "Read", "revise_tools": "Read",
    "poll_tools": "Read",
    "domain_tag": "Kestrel", "domain_keywords": ["kestrel"],
    "domain_url_keywords": [],
    "self_learning": True, "self_modify_code": False,
    "live_refresh": False,
}

WORKSPACES = {
    "active": "kestrel",
    "workspaces": [
        {"id": "kestrel", "kind": "employer", "label": "Kestrel Labs",
         "connectors": ["gmail-work", "slack", "jira", "github", "calendar", "drive"],
         "isolation": "strict"},
        {"id": "job-search", "kind": "job-search", "label": "Job search",
         "connectors": ["gmail-personal"], "isolation": "strict"},
        {"id": "personal", "kind": "personal", "label": "Personal",
         "connectors": ["gmail-personal", "calendar"], "isolation": "strict"},
        {"id": "oss", "kind": "personal", "label": "Open source",
         "connectors": ["github"], "isolation": "strict"},
    ],
}

QUEUE_HEADER = """# Approval queue

Every external action waits here until Dana approves it. Nothing is sent,
posted or changed without that click.

### example-id
- status: pending
- action_type: message_send
- proposed_tool_call: (schema example, not an entry)

---
"""

QUEUE = [
    # Each draft answers a task the research engine found in the recorded run;
    # the facts in them are the world's own (bracketed parts are left for
    # Dana to fill in, which is what the Edit button is for).
    {"id": "q-1013-tomas-deprecation", "status": "pending", "action_type": "message_send",
     "priority": "high", "drafted_by": "cos-drafter",
     "created": "2026-10-13T08:40:00-07:00",
     "short_summary": "Email to Tomas: first draft of the API v1 deprecation notice (he asked for it by today)",
     "proposed_tool_call": 'gmail-work.send to Tomas, re "Deprecation notice", with text: "Hi Tomas, here is a first draft of the v1 deprecation notice: API v1 will stop accepting requests on [date]. Please move to the v2 endpoints before then; the migration guide covers the changes. Tell me the date and anything to add, and I will finalize it today."',
     "context": "Task: Write API v1 deprecation notice text for Tomas (due 2026-10-13). Source: his email of Oct 8, 'I need the API v1 deprecation notice text by next Tuesday.'"},
    {"id": "q-1013-alex-cron", "status": "pending", "action_type": "message_send",
     "priority": "high", "drafted_by": "cos-drafter",
     "created": "2026-10-13T08:44:00-07:00",
     "short_summary": "Slack reply to Alex in #proj-billing-migration: the billing cron schedule (due Oct 16)",
     "proposed_tool_call": 'slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "Confirming the billing job schedule ahead of the cutover: [schedule]. Shout if the cutover week changes."',
     "context": "Task: Confirm the cron schedule for the billing jobs for Alex (due 2026-10-16). Source: '@dana.k can you confirm the cron schedule for the billing jobs by Oct 16? we cut over the week after.'"},
    {"id": "q-1013-laptop-swap", "status": "pending", "action_type": "it_booking",
     "priority": "high", "drafted_by": "cos-drafter",
     "created": "2026-10-13T08:45:00-07:00",
     "short_summary": "Book the laptop swap on the IT booking page (was due Oct 9)",
     "proposed_tool_call": "Open the IT booking page and pick a laptop swap slot. No connector can book it, so this is yours to do; mark it handled after.",
     "context": "Task: Book laptop swap appointment with IT (due 2026-10-09, overdue). Source: Kestrel IT, it@kestrel.example, Sep 23. Not the look-alike 'password expires' mail from kestrel-helpdesk.example on Sep 22, which was set aside as phishing."},
    {"id": "q-1013-grace-resume", "status": "pending", "action_type": "message_send",
     "priority": "high", "drafted_by": "cos-drafter",
     "created": "2026-10-13T08:47:00-07:00",
     "short_summary": "Email to Grace Liu (Halcyon Talent) with the updated resume [job-search workspace]",
     "proposed_tool_call": 'gmail-personal.send to Grace Liu, re "Updated resume", with text: "Hi Grace, sorry this is late. My updated resume is attached. Happy to talk whenever suits you."',
     "context": "Job-search workspace: drafted from the personal mailbox, never the work account. Task: Send updated resume to Grace Liu (asked for it by Oct 1)."},
    {"id": "q-1012-alex-ack", "status": "approved", "action_type": "message_send",
     "priority": "medium", "drafted_by": "cos-drafter",
     "created": "2026-10-12T16:10:00-07:00",
     "short_summary": "Slack: acknowledge Alex's cron question (will confirm by Oct 16)",
     "proposed_tool_call": 'slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "On it, will confirm by Thursday."',
     "context": "Approved by Dana on Oct 12. The task itself stays open until the schedule is confirmed."},
    {"id": "q-1010-offsite-replyall", "status": "rejected", "action_type": "message_send",
     "priority": "low", "drafted_by": "cos-drafter",
     "created": "2026-10-10T11:00:00-07:00",
     "short_summary": "Reply to the optional #general @channel about the offsite poll",
     "proposed_tool_call": 'slack.send_message in #general with text: "Count me in for Thursday."',
     "context": "Rejected by Dana: the @channel was optional; no reply needed."},
]

LEDGER = [
    {"ts": "2026-10-06T10:12:00Z", "correction_id": "corr-20261006-handoff",
     "connector": "slack", "root_cause": "accepted hand-off kept as delegated",
     "signature": "slack:accepted hand-off kept as delegated",
     "change": "Instructions: when the person a task is handed to accepts ('on it'), it leaves your list instead of staying as 'delegated'.",
     "verified": True,
     "text": "Mei said 'on it' about the dashboard migration last week, why is it still on my list?"},
    {"ts": "2026-10-08T15:40:00Z", "correction_id": "corr-20261008-jobsearch",
     "connector": "gmail", "root_cause": "job-search read as personal for priority",
     "signature": "gmail:job-search read as personal for priority",
     "change": "Instructions: job-search work is not 'personal' for the low-priority rule.",
     "verified": True,
     "text": "The Corvid final-round slot pick shows as low. Interviews are not personal errands."},
    {"ts": "2026-10-10T09:05:00Z", "correction_id": "corr-20261010-duplicate",
     "connector": "jira", "root_cause": "one piece of work listed twice",
     "signature": "jira:one piece of work listed twice",
     "change": "Instructions: one piece of work is one task however many places word it differently; merge and cite every source.",
     "verified": True,
     "text": "'Benchmark numbers' and 'latency numbers for the review' are the same task."},
]

DAILY = """Monday, Oct 13

Since Friday: 404 Slack messages, 16 mails and 18 Jira updates across the connected
accounts. Most of it is noise, asks to other people, or bots.

Open tasks: {n_open} in total, {n_high} high priority.

Drafted for approval: 3 messages and 1 to-do for you (see the approval queue).
Nothing has been sent.

Set aside: the Sep 22 "password expires" mail from kestrel-helpdesk.example, a
look-alike of Kestrel IT. Not a task.
"""

MEETINGS = """# Meeting notes

### example
- topic: schema example

---

### m-1012-standup
- topic: Platform standup (Slack)
- when: 2026-10-12 09:30
- summary: Alex: on-call follow-ups. Raj: schema cleanup. Mei: triage.
- action_items: None for Dana from the standup itself. Raj separately needs Dana's sign-off on the events schema change by Oct 21 (on the task list).

### m-1022-arch-review
- topic: Architecture review: scheduler v2 (Dana presents)
- when: 2026-10-22 14:00 UTC, organized by Ines
- summary: Upcoming. Dana is the presenter.
- action_items: The design doc should go out before the review (on the task list).
"""

QUESTIONS = """Open questions for Dana (asked once, only what the crawl could not infer):

1. The "tinyq" repository on GitHub: is it a personal open-source project, or part of
   Kestrel work? It is filed under Open source until you say otherwise.
"""

INBOX = """# Inbox
- [processed] 2026-10-12T18:02 — remind me to send Victor the conference budget request
"""

CHAT = """**You** (Oct 13, 08:58): what's most urgent today?

**Chief of staff**: {urgent}
"""


def build():
    if os.path.exists(STATE):
        shutil.rmtree(STATE)
    os.makedirs(os.path.join(WS, "daily"))
    os.makedirs(os.path.join(WS, "tasks"))
    shutil.copytree(SOURCE_GRAPH, os.path.join(WS, "graph"))
    lock = os.path.join(WS, "graph", "graph.lock")
    if os.path.exists(lock):
        os.remove(lock)
    cfg = dict(CONFIG, workspace_dir="workspace")   # relative to this config
    with open(os.path.join(STATE, "config.json"), "w") as f:
        json.dump(cfg, f, indent=1)
    shutil.copy(os.path.join(HERE, "responses.json"), os.path.join(STATE, "responses.json"))
    with open(os.path.join(WS, "workspaces.json"), "w") as f:
        json.dump(WORKSPACES, f, indent=1)
    q = QUEUE_HEADER
    for e in QUEUE:
        q += "\n### %s\n" % e["id"]
        q += "".join("- %s: %s\n" % (k, v) for k, v in e.items() if k != "id")
    with open(os.path.join(WS, "approval-queue.md"), "w") as f:
        f.write(q)
    with open(os.path.join(WS, "corrections.jsonl"), "w") as f:
        for ev in LEDGER:
            f.write(json.dumps(ev) + "\n")
    sys.path.insert(0, os.path.join(ROOT, "dashboard"))
    import graph  # noqa: E402
    os.environ["COS_FIXED_NOW"] = TODAY + "T16:00:00Z"
    g = graph.Graph.load(os.path.join(WS, "graph"))
    open_ = [n for n in g.nodes.values() if n["type"] == "Action" and graph.is_open_action(n)]
    daily = DAILY.format(n_open=len(open_),
                         n_high=sum(1 for n in open_ if graph.effective_priority(n) == "high"))
    # saved chat replies quote the graph rather than hand-written claims
    import sections
    todo = sections.next_actions(g, limit=60)
    overdue = [t for t in todo if t["overdue"]]
    today_ = [t for t in todo if not t["overdue"] and t["due_days"] is not None
              and t["due_days"] < 1]
    def names(ts, n=3):
        return "; ".join(t["title"] for t in ts[:n])
    urgent = ("Saved reply, computed from the graph: across all workspaces %d tasks are overdue and %d due today. "
              "Due today: %s. Most overdue: %s. Drafts for several of these are in the "
              "approval queue; nothing is sent until you approve." % (
                  len(overdue), len(today_), names(today_) or "nothing",
                  names(overdue)))
    waiting = [n for n in open_ if (n.get("attrs") or {}).get("blocked_on")]
    resp = json.load(open(os.path.join(HERE, "responses.json")))
    resp["/chat"]["urgent"] = urgent
    resp["/chat"]["waiting"] = ("Saved reply, computed from the graph: %d tasks are waiting on "
                                "someone else: %s." % (len(waiting), "; ".join(
                                    "%s (on %s)" % (n["name"], n["attrs"]["blocked_on"])
                                    for n in waiting[:4])) if waiting else
                                "Saved reply: nothing is waiting on someone else.")
    with open(os.path.join(STATE, "responses.json"), "w") as f:
        json.dump(resp, f, indent=1)
    chat = CHAT.replace("{urgent}", urgent)
    with open(os.path.join(STATE, "chat-log.md"), "w") as f:
        f.write(chat)
    for name, text in (("daily/%s.md" % TODAY, daily), ("meeting-notes.md", MEETINGS),
                       ("open-questions.md", QUESTIONS), ("tasks/inbox.md", INBOX)):
        with open(os.path.join(WS, name), "w") as f:
            f.write(text)
    with open(os.path.join(STATE, "poll-config.json"), "w") as f:
        json.dump({c: {"days": ["mon", "tue", "wed", "thu", "fri"]}
                   for c in ("slack", "gmail", "jira", "calendar", "general")}, f, indent=1)
    return STATE


if __name__ == "__main__":
    print("wrote", build())
    sys.exit(0)
