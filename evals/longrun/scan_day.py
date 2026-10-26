#!/usr/bin/env python3
"""One simulated day of the always-on scan, on the full benchmark world.

    python3 evals/longrun/scan_day.py --run-id scan-day-a --setup batches
    python3 evals/longrun/scan_day.py --run-id scan-day-b --setup button --button 17:00

The day is 2026-10-14, the day after the first full read (C1 is the morning of
Oct 13; the state at the start of Oct 14 is the recorded graph after the Oct 13
daily check, lrf-v3-daily/graph/d01). The day is walked in 5-minute steps
(288 scans). Each scan sees only the items whose time falls in that step and
runs dashboard/poll_direct.check(scan=True) exactly as the app does: free fetch
and sift, the waiting list, an immediate read for anything urgent, batches,
and a drafted next step for each new task. Model calls go through the app's own
route (claude -p, no tools) and are logged with their cost.

Setups:
  batches  the app default: urgent at once, batches about 8am, noon and 4pm
  button   urgent at once, no batches; the waiting list is read when the user
           presses Check now (--button HH:MM, once)

--with-meeting adds one meeting transcript at 14:30 (a Zoom call saved to a
folder), to exercise the urgent path; the benchmark world has no transcripts.
It is an addition, not part of the answer key, and its expected tasks are
listed below. Scoring the day uses the gold arcs with an event on Oct 14.
"""

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = os.path.dirname(HERE)
ROOT = os.path.dirname(EVALS)
sys.path.insert(0, os.path.join(ROOT, "dashboard"))
sys.path.insert(0, HERE)

import connections      # noqa: E402
import graph as G       # noqa: E402
import poll_direct      # noqa: E402
import transcripts      # noqa: E402

RESULTS = os.path.join(EVALS, "results", "longrun")
WORLD = os.path.join(HERE, "world_full")
START = os.path.join(RESULTS, "lrf-v3-daily", "graph", "d01")
DAY = dt.datetime(2026, 10, 14, tzinfo=dt.timezone.utc)
STEP = dt.timedelta(minutes=5)

# what the day's gold events should leave at the end of Oct 14
EXPECT = [
    {"arc": "D07", "split": "dev", "words": ["capacity", "q4"], "want": "open", "due": "2026-10-22",
     "what": "Ines's reminder moves the Q4 capacity numbers to Oct 22"},
    {"arc": "T11", "split": "test", "words": ["maintenance", "window"], "want": "open", "due": "2026-10-30",
     "what": "new: Alex asks Dana to confirm the Nov 15 maintenance window by Oct 30"},
    {"arc": "LT04", "split": "test", "words": ["tidewater", "offer"], "want": "open", "due": None,
     "what": "Dana asked Tidewater for until Oct 30 (the answer comes Oct 15): the offer task stays open"},
    {"arc": "LD07", "split": "dev", "words": ["brightline", "availability"], "want": "closed", "due": None,
     "what": "Dana sent her availability and the interview was booked: the task closes"},
]
MEETING_EXPECT = [
    {"arc": "meeting", "split": "added", "words": ["onboarding", "checklist"], "want": "open", "due": "2026-10-16"},
    {"arc": "meeting", "split": "added", "words": ["sso", "runbook"], "want": "open", "due": "2026-10-21"},
]
MEETING = [
    ("Tomas Weber", "Okay, quick one. Northwind onboarding. Their IT team starts next week."),
    ("Dana Kowalski", "Right. Do they have everything they need?"),
    ("Tomas Weber", "Not yet. Dana, can you write the onboarding checklist for them? By Friday if you can."),
    ("Dana Kowalski", "Yes, I'll have the checklist done Friday."),
    ("Priya Natarajan", "I'll set up their staging tenant tomorrow."),
    ("Tomas Weber", "Good. And the SSO setup, we need a runbook. Dana, you did the last one."),
    ("Dana Kowalski", "I can update the SSO runbook. Next Wednesday?"),
    ("Tomas Weber", "Next Wednesday is fine. That's all, thanks."),
]


def meeting_item():
    text = "\n".join("[%s] 14:%02d:%02d\n%s\n" % (sp, 2 + k // 2, (k * 23) % 60, t) for k, (sp, t) in enumerate(MEETING))
    return {"connector": "transcript", "id": "tr-added-0001", "date": "2026-10-14T14:30:00Z",
            "title": "Northwind onboarding", "speakers": transcripts.speakers(text), "origin": "file",
            "path": "~/Documents/Zoom/2026-10-14 14.00.05 Northwind onboarding/meeting_saved_closed_caption.txt",
            "text": transcripts.clean(text)}


def check_expect(g, now, exp):
    hits = []
    for n in g.query(type_="Action"):
        hay = ("%s %s" % (n.get("name") or "", n["id"])).lower()
        if all(w in hay for w in exp["words"]):
            hits.append(n)
    open_ = [n for n in hits if G.is_open_action(n, now=now)]
    # "closed": nothing about it is left open (closed today, or never opened)
    ok = bool(open_) if exp["want"] == "open" else not open_
    due = sorted({(n.get("attrs") or {}).get("due") for n in open_} - {None})
    if ok and exp.get("due"):
        ok = exp["due"] in due
    return {"ok": ok, "found": [n.get("name") for n in hits][:3], "due": due}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--setup", choices=["batches", "button"], default="batches")
    ap.add_argument("--button", default="17:00", help="button setup: when Check now is pressed")
    ap.add_argument("--with-meeting", action="store_true")
    ap.add_argument("--no-draft", action="store_true")
    args = ap.parse_args()

    items = json.load(open(os.path.join(WORLD, "items.json")))
    meta = json.load(open(os.path.join(WORLD, "meta.json")))
    day = sorted((i for i in items if i["date"][:10] == "2026-10-14"), key=lambda i: i["date"])
    if args.with_meeting:
        day.append(meeting_item())
        day.sort(key=lambda i: i["date"])
    expects = EXPECT + (MEETING_EXPECT if args.with_meeting else [])

    out = os.path.join(RESULTS, args.run_id)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    work = tempfile.mkdtemp(prefix="scan-day-")
    cfg, ws = os.path.join(work, "cfg"), os.path.join(work, "ws")
    gdir = os.path.join(ws, "graph")
    os.makedirs(cfg)
    shutil.copytree(START, gdir)
    u = meta["user"]
    connections.save_me(cfg, {"name": u["name"], "emails": [u["email"]] + list(u.get("other_emails") or []),
                              "slack": u.get("slack", ""), "github": u.get("github", "")})
    flush = ({"flush_min": 240, "flush_start": "08:00", "flush_end": "16:30"} if args.setup == "batches"
             else {"flush_min": 100000, "flush_start": "99:99", "flush_end": "99:99"})
    json.dump({"timezone": "UTC", "direct": dict({"interval_min": 5}, **flush)},
              open(os.path.join(cfg, "poll-config.json"), "w"))
    json.dump({"last_flush": "2026-10-13T23:59:00Z"}, open(os.path.join(cfg, "scan-state.json"), "w"))
    # the last 30 days as already fetched, so the sift knows the user's threads
    os.makedirs(os.path.join(cfg, "inbox"))
    by_day = {}
    for i in items:
        if "2026-09-14" <= i["date"] < "2026-10-14":
            by_day.setdefault(i["date"][:10], []).append(i)
    for d, rows in by_day.items():
        with open(os.path.join(cfg, "inbox", d + ".jsonl"), "w") as f:
            for i in rows:
                f.write(json.dumps(i, ensure_ascii=False) + "\n")

    calls = []

    def model(config_dir, prompt, job="poll_direct"):
        text, cost = poll_direct.run_model(config_dir, prompt, job=job)
        calls.append({"job": job, "cost_usd": cost or 0.0, "prompt_chars": len(prompt)})
        return text, cost

    button = None
    if args.setup == "button":
        hh, mm = args.button.split(":")
        button = DAY.replace(hour=int(hh), minute=int(mm))
    log, first_ok = [], {}
    k = 0
    t = DAY
    while t < DAY + dt.timedelta(days=1):
        nxt = t + STEP
        batch = [i for i in day[k:] if i["date"] < nxt.strftime("%Y-%m-%dT%H:%M:%SZ")]
        k += len(batch)
        if batch:
            with open(os.path.join(cfg, "inbox", "2026-10-14.jsonl"), "a") as f:
                for i in batch:
                    f.write(json.dumps(i, ensure_ascii=False) + "\n")

        def fetch(d, batch=batch):
            return {"items": batch, "per_source": {"all": {"ok": True, "count": len(batch)}}}
        press = button is not None and t <= button < nxt
        n_calls = len(calls)
        res = poll_direct.check(cfg, gdir, now=nxt, _fetch=fetch, _model=model, scan=not press,
                                draft=not args.no_draft)
        row = {"t": nxt.strftime("%H:%M"), "new": res["new"], "kept": res["kept"], "waiting": res.get("waiting", 0),
               "read": res.get("read"), "urgent": res.get("urgent"), "records": res["records"],
               "drafts": res.get("drafts", 0), "cost_usd": round(res["cost_usd"], 4),
               "calls": [c["job"] for c in calls[n_calls:]], "button": press}
        if row["calls"]:
            g = G.Graph.load(gdir)
            for e in expects:
                key = e["arc"] + ":" + "+".join(e["words"])
                if key not in first_ok and check_expect(g, nxt, e)["ok"]:
                    first_ok[key] = row["t"]
            print("%s  new %4d kept %3d read %s urgent %s -> %d records, %d drafts, $%.3f %s" % (
                row["t"], row["new"], row["kept"], row["read"], row["urgent"], row["records"],
                row["drafts"], res["cost_usd"], "(button)" if press else ""), flush=True)
        log.append(row)
        t = nxt

    end = DAY + dt.timedelta(days=1)
    g = G.Graph.load(gdir)
    before = G.Graph.load(START)
    before_open = {n["id"] for n in before.query(type_="Action") if G.is_open_action(n, now=end)}
    new_open = [n.get("name") for n in g.query(type_="Action")
                if G.is_open_action(n, now=end) and n["id"] not in before_open]
    results = []
    for e in expects:
        r = check_expect(g, end, e)
        r.update({k2: e.get(k2) for k2 in ("arc", "split", "words", "want", "what")})
        r["first_ok_at"] = first_ok.get(e["arc"] + ":" + "+".join(e["words"]))
        results.append(r)
    waiting = poll_direct._read_pending(cfg)
    summary = {
        "setup": args.setup, "button": args.button if button else None, "with_meeting": args.with_meeting,
        "scans": len(log), "items": len(day), "kept_total": sum(r["kept"] for r in log),
        "model_calls": len(calls), "calls_by_job": {j: sum(1 for c in calls if c["job"] == j) for j in {c["job"] for c in calls}},
        "cost_usd": round(sum(c["cost_usd"] for c in calls), 4),
        "cost_by_job": {j: round(sum(c["cost_usd"] for c in calls if c["job"] == j), 4) for j in {c["job"] for c in calls}},
        "still_waiting_at_midnight": len(waiting),
        "waiting_ids": [r["item"]["id"] for r in waiting][:40],
        "expectations": results, "new_open_tasks": new_open,
    }
    json.dump(log, open(os.path.join(out, "scans.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1)
    q = os.path.join(ws, "approval-queue.md")
    if os.path.exists(q):
        shutil.copy(q, os.path.join(out, "approval-queue.md"))
    G.Graph.load(gdir).save(os.path.join(out, "graph"))
    print(json.dumps({k2: v for k2, v in summary.items() if k2 not in ("waiting_ids",)}, indent=1))
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
