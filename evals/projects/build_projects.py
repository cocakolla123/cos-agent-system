#!/usr/bin/env python3
"""Fixture world for /cos-research Step 1e (the user's own projects).

Writes ./world/: real project folders under projects/ (README, runbooks, logs,
code) plus connector-style JSON under sources/ (local git state, GitHub repos,
CI runs and PRs, mail). Deterministic; all names and domains are fictional.

    python3 evals/projects/build_projects.py            # (re)write evals/projects/world
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-10-21"
USER = {"name": "Riya Patel", "handle": "riyap", "email": "riya@mail.example",
        "github": "riyap"}


def commits(project, rows):
    return [{"date": d, "author": a, "subject": s} for d, a, s in rows]


GLIMMER_LOG = commits("glimmer", [
    ("2026-10-20T23:02:00-07:00", "riyap", "v3 redesign: align the post button with the tab bar"),
    ("2026-10-20T22:52:00-07:00", "riyap", "v3 redesign: home, reveal and feed screens"),
    ("2026-10-20T22:40:00-07:00", "riyap", "WIP: v3 redesign screens (in progress)"),
    ("2026-10-20T22:35:00-07:00", "riyap", "v3 redesign: foundation (palette, fonts, glass panels)"),
    ("2026-10-20T14:10:00-07:00", "devpal", "Leaderboard: weekly rank badges"),
    ("2026-10-19T18:31:00-07:00", "riyap", "Open sign-up: anyone 13+, school optional"),
    ("2026-10-19T03:59:00-07:00", "riyap", "Merge v2: review fixes, leaderboard, weekly votes"),
])
TIDEPOOL_LOG = commits("tidepool-quant", [
    ("2026-10-06T01:05:00-07:00", "riyap", "Merge branch 'fix/cash-ledger': cash ledger, repair script"),
    ("2026-10-05T12:56:00-07:00", "riyap", "feat(paper): dry-run-first repair script and release runbook"),
    ("2026-10-05T12:42:00-07:00", "riyap", "fix(paper): derive cash from a fill ledger"),
    ("2026-10-05T11:30:00-07:00", "riyap", "docs: results section with real test counts"),
])
COSHELPER_LOG = commits("cos-helper", [
    ("2026-10-18T16:20:00-07:00", "riyap", "Add calendar module tests"),
    ("2026-10-17T10:05:00-07:00", "riyap", "Refactor graph upsert"),
    ("2026-10-12T09:00:00-07:00", "riyap", "Initial dashboard"),
])
PORTFOLIO_LOG = commits("old-portfolio", [
    ("2024-09-30T10:00:00-07:00", "riyap", "Update projects page"),
])

FILES = {
    "glimmer/README.md": "# glimmer\n\nDaily photo app for college students. Post one photo a day; the top post becomes Photo of the Day.\n\n## Run it\nOpen Glimmer.xcodeproj and press Run.\n",
    "glimmer/docs/v3-design.md": "# v3 redesign\n\nGlass panels, new type, new tab bar. Screens: home, reveal, feed, profile, post.\n",
    "glimmer/App/FeedView.swift": "import SwiftUI\n// TODO: tidy spacing constants\nstruct FeedView: View { var body: some View { Text(\"Feed\") } }\n",
    "tidepool-quant/README.md": "# tidepool-quant\n\nPersonal paper-trading research platform.\n\n## Status\nPaper validation phase. Remaining before real money: accumulate clean unattended paper runs, then the human approval gate.\n",
    "tidepool-quant/docs/runbook_cash_ledger_2026-10.md": "# Runbook: cash ledger fix and release (2026-10)\n\n## Dry run (2026-10-05, read only)\nDone. Output matched expectations.\n\n## Order of operations\n1. `scripts/repair_ledger.py --step curve --apply`. Check the printed equity curve.\n2. `scripts/repair_ledger.py --step ladder --apply`.\n3. `scripts/repair_ledger.py --step ack --apply --acked-by <name>`.\n\nRecord each step in docs/ops-log.md when it is done.\n",
    "tidepool-quant/docs/ops-log.md": "# Ops log\n\n## 2026-09-23\nRestarted the scheduler; nightly ingest succeeded.\n\n**Still open:** data vendor monthly cap exhausted; the Pro plan upgrade decision is pending with Riya.\n\n## 2026-10-05\nDry run of the cash-ledger repair completed (read only). Apply steps not yet run.\n",
    "tidepool-quant/src/ledger.py": "def cash(fills):\n    # TODO: vectorize\n    return sum(f['amount'] for f in fills)\n",
    "cos-helper/README.md": "# cos-helper\n\nA small assistant that reads my calendar and mail and lists what I owe.\n",
    "cos-helper/src/graph.py": "# TODO: add edge dedup\n# TODO: support multiple accounts\n# FIXME: slow on big graphs\ndef upsert(g, n):\n    g[n['id']] = n\n",
    "cos-helper/NOTES.md": "Ideas: a mobile view someday. Maybe dark mode.\n",
    "old-portfolio/README.md": "# Portfolio site\n\nMy 2024 portfolio.\n",
}

LOCAL = []
for name, log, branch, dirty in (
        ("glimmer", GLIMMER_LOG, "main", ["App/HomeView.swift"]),
        ("tidepool-quant", TIDEPOOL_LOG, "main", []),
        ("cos-helper", COSHELPER_LOG, "main", []),
        ("old-portfolio", PORTFOLIO_LOG, "main", [])):
    LOCAL.append({"id": "lf-%s-git" % name, "connector": "local",
                  "type": "git_state", "path": "projects/%s" % name,
                  "date": log[0]["date"], "branch": branch,
                  "remote": "github.example/%s/%s" % (USER["github"], name),
                  "uncommitted_files": dirty, "recent_commits": log})


def run(rid, repo, date, sha_subject, conclusion, jobs):
    return {"id": "gh-run-%s" % rid, "connector": "github", "type": "workflow_run",
            "repo": "riyap/%s" % repo, "branch": "main", "date": date,
            "head_commit": sha_subject, "conclusion": conclusion, "jobs": jobs}


def dead_job(name, secs):
    return {"name": name, "conclusion": "failure", "duration_seconds": secs,
            "steps": []}


GH = [
    {"id": "gh-repo-glimmer", "connector": "github", "type": "repository",
     "repo": "riyap/glimmer", "owner": "riyap", "private": True,
     "date": "2026-10-21T06:02:00Z", "pushed_at": "2026-10-21T06:02:00Z",
     "collaborators": ["riyap", "devpal"]},
    {"id": "gh-repo-tidepool", "connector": "github", "type": "repository",
     "repo": "riyap/tidepool-quant", "owner": "riyap", "private": True,
     "date": "2026-10-06T08:05:00Z", "pushed_at": "2026-10-06T08:05:00Z",
     "collaborators": ["riyap"]},
    {"id": "gh-repo-coshelper", "connector": "github", "type": "repository",
     "repo": "riyap/cos-helper", "owner": "riyap", "private": True,
     "date": "2026-10-18T23:20:00Z", "pushed_at": "2026-10-18T23:20:00Z",
     "collaborators": ["riyap"]},
    {"id": "gh-repo-portfolio", "connector": "github", "type": "repository",
     "repo": "riyap/old-portfolio", "owner": "riyap", "private": False,
     "date": "2024-09-30T17:00:00Z", "pushed_at": "2024-09-30T17:00:00Z",
     "collaborators": ["riyap"]},
]
for i, (d, s) in enumerate([
        ("2026-10-21T06:02:00Z", "v3 redesign: align the post button with the tab bar"),
        ("2026-10-21T05:52:00Z", "v3 redesign: home, reveal and feed screens"),
        ("2026-10-20T21:10:00Z", "Leaderboard: weekly rank badges"),
        ("2026-10-20T01:31:00Z", "Open sign-up: anyone 13+, school optional"),
        ("2026-10-19T10:59:00Z", "Merge v2: review fixes, leaderboard, weekly votes")]):
    GH.append(run("g%d" % i, "glimmer", d, s, "failure",
                  [dead_job("ios-build-and-test", 4), dead_job("backend-tests", 3)]))
GH.append(run("g9", "glimmer", "2026-10-15T20:00:00Z", "Search tab", "success",
              [{"name": "ios-build-and-test", "conclusion": "success",
                "duration_seconds": 512, "steps": ["checkout", "build", "test"]}]))
GH.append(run("t1", "tidepool-quant", "2026-10-06T08:05:00Z",
              "Merge branch 'fix/cash-ledger': cash ledger, repair script", "failure",
              [{"name": "unit-tests", "conclusion": "success", "duration_seconds": 203,
                "steps": ["checkout", "uv sync", "pytest"]},
               {"name": "typecheck", "conclusion": "failure", "duration_seconds": 44,
                "steps": ["checkout", "uv sync", "pyright (failed: 3 errors in src/ledger.py)"]}]))
GH.append(run("t0", "tidepool-quant", "2026-10-05T18:30:00Z", "docs: results section", "success",
              [{"name": "typecheck", "conclusion": "success", "duration_seconds": 41,
                "steps": ["checkout", "uv sync", "pyright"]}]))
GH.append(run("c1", "cos-helper", "2026-10-18T23:21:00Z", "Add calendar module tests", "success",
              [{"name": "tests", "conclusion": "success", "duration_seconds": 38,
                "steps": ["checkout", "pytest"]}]))
GH.append({"id": "gh-pr-glimmer-14", "connector": "github", "type": "pull_request",
           "repo": "riyap/glimmer", "number": 14, "state": "open",
           "title": "Comments: moderation queue for flagged comments",
           "author": "devpal", "requested_reviewers": ["riyap"],
           "date": "2026-10-20T16:00:00Z",
           "body": "Riya, can you review this before Thursday's TestFlight build?"})
GH.append({"id": "gh-pr-coshelper-3", "connector": "github", "type": "pull_request",
           "repo": "riyap/cos-helper", "number": 3, "state": "merged",
           "title": "Calendar module", "author": "riyap", "requested_reviewers": [],
           "date": "2026-10-18T23:20:00Z"})

MAIL = [
    {"id": "em-01", "connector": "gmail", "date": "2026-10-07T18:00:00Z",
     "from": "TestFlight <no_reply@testflight.example>", "to": USER["email"],
     "subject": "Ana Ruiz has invited you to test Harbor Map",
     "body": "Ana Ruiz has invited you to test Harbor Map. Open the link on your iPhone to start testing build 0.4."},
    {"id": "em-02", "connector": "gmail", "date": "2026-10-19T09:00:00Z",
     "from": "DevNews <news@devnews.example>", "to": USER["email"],
     "subject": "This week in Swift", "body": "Ten new SwiftUI tricks."},
    {"id": "em-03", "connector": "gmail", "date": "2026-10-16T12:00:00Z",
     "from": "GitHub <noreply@github.example>", "to": USER["email"],
     "subject": "[riyap/glimmer] Run failed: ios - main",
     "body": "Run failed for ios on main. ios-build-and-test failed in 4s."},
]

CONTEXT = ("# About me (written by the user)\n\nI'm Riya. Right now I'm working on "
           "Harbor Map, glimmer, my quant app (tidepool-quant) and cos-helper. "
           "Those are my personal projects and they're part of my work.\n")

# What a correct pass finds. Matching is by keyword groups (any word in a
# group); "forbid" lists what must not become an Action.
GOLD = {
    "today": TODAY,
    "projects": {
        "glimmer": {"active": True,
                    "summary_any": ["redesign", "v3"],
                    "health_any": ["runner", "billing", "minutes", "no steps",
                                   "before any step", "infrastructure", "seconds",
                                   "not a code", "configuration"],
                    "actions": {"review-pr-14": [["review"], ["14", "moderation"]],
                                "ci-red": [["ci", "build", "workflow", "runner",
                                            "actions", "billing", "minutes"]]},
                    "collaborator": "devpal"},
        "tidepool-quant": {"active": True,
                           "summary_any": ["ledger", "cash", "paper"],
                           "health_any": ["typecheck", "pyright", "type"],
                           "actions": {"runbook-apply": [["runbook", "repair", "apply"]],
                                       "vendor-decision": [["vendor", "plan", "upgrade"]],
                                       "ci-red": [["typecheck", "pyright", "ci"]]}},
        "cos-helper": {"active": True, "summary_any": ["calendar", "assistant",
                                                       "graph", "test", "dashboard"],
                       "actions": {}},
        "old-portfolio": {"active": False, "actions": {}},
    },
    "question_any": ["harbor"],
}


def write(root):
    if os.path.exists(root):
        shutil.rmtree(root)
    for rel, text in FILES.items():
        p = os.path.join(root, "projects", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    src = os.path.join(root, "sources")
    os.makedirs(src)
    for name, items in (("local", LOCAL), ("github", GH), ("gmail", MAIL)):
        with open(os.path.join(src, name + ".json"), "w") as f:
            f.write("[\n" + ",\n".join(json.dumps(i, sort_keys=True) for i in items) + "\n]\n")
    with open(os.path.join(root, "context.md"), "w") as f:
        f.write(CONTEXT)
    with open(os.path.join(HERE, "gold.json"), "w") as f:
        json.dump(GOLD, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    write(os.path.join(HERE, "world"))
    print("wrote", os.path.join(HERE, "world"))
