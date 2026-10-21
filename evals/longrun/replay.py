#!/usr/bin/env python3
"""Replay the Kestrel world through the real extraction step and graph.

    python3 evals/longrun/replay.py --instructions evals/instructions/longrun_v1.md \
        --run-id lr-v1 [--model M] [--stop-after c1]
    python3 evals/longrun/replay.py --rescore lr-v1     # no model calls

Step c1: one run with the whole 90-day history (a first --full crawl),
scored at C1 (2026-10-13). Steps f1..f4: one incremental poll per future
week, each seeing only that week's items plus state/open_actions.json from
the graph. All records go into one persistent graph, scored at C2.

Isolation is the same as evals/run.py (it calls run.run_scenario): no MCP
servers, Read and Glob only. Raw envelopes are saved so scoring is
reproducible without the model.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = os.path.dirname(HERE)
sys.path.insert(0, EVALS)
sys.path.insert(0, HERE)

import run                    # noqa: E402  (also puts dashboard/ on the path)
import score                  # noqa: E402
import research               # noqa: E402
import correlate              # noqa: E402
import graph as graphlib      # noqa: E402
import score_longrun          # noqa: E402

import build                  # noqa: E402

RESULTS = os.path.join(EVALS, "results", "longrun")


def load_world(kind):
    if not os.path.exists(os.path.join(build.DIRS[kind], "items.json")):
        # large worlds are regenerated, not committed; the lock still binds them
        subprocess.run([sys.executable, os.path.join(HERE, "build.py"), "--world", kind,
                        "--from-lock"], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(HERE, "build.py"), "--world", kind,
                    "--check"], check=True, capture_output=True)
    d = build.DIRS[kind]
    items = json.load(open(os.path.join(d, "items.json")))
    meta = json.load(open(os.path.join(d, "meta.json")))
    return items, meta


def write_items(path, rows):
    """One item per line: valid JSON, and a search hit returns a whole item."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
                + "\n]\n")


def fname(channel):
    return channel.lstrip("#").replace("/", "_") + ".json"


def week_start(date_str):
    d = datetime.date.fromisoformat(date_str[:10])
    return (d - datetime.timedelta(days=d.weekday())).isoformat()


def steps(meta):
    weeks = meta["future_weeks"] + [meta["c2"]]
    out = [{"name": "c1", "lo": "0000", "hi": meta["today"], "today": meta["today"],
            "incremental": False}]
    for i in range(len(meta["future_weeks"])):
        out.append({"name": "f%d" % (i + 1), "lo": weeks[i], "hi": weeks[i + 1],
                    "today": weeks[i + 1], "incremental": True})
    return out


def open_state(g, now):
    rows = []
    for n in score.open_actions(g):
        if not graphlib.is_open_action(n, now=now):
            continue
        a = n.get("attrs") or {}
        rows.append({"workspace": n["workspace"],
                     "key": n["id"].split(":action:", 1)[-1], "name": n.get("name"),
                     "attrs": {k: a[k] for k in ("due", "priority", "blocked_on",
                                                 "status", "evidence", "refs")
                               if k in a}})
    return sorted(rows, key=lambda r: (r["workspace"], r["key"]))


def materialize(d, items, step, meta, g):
    src = os.path.join(d, "sources")
    sel = [i for i in items if step["lo"] <= i["date"] < step["hi"]]
    by = {}
    for i in sel:
        if i["connector"] == "slack":
            path = os.path.join(src, "slack", "channels", fname(i["channel"]))
        elif step["incremental"]:
            path = os.path.join(src, i["connector"] + ".json")
        else:
            path = os.path.join(src, i["connector"], week_start(i["date"]) + ".json")
        by.setdefault(path, []).append(i)
    for path, rows in by.items():
        write_items(path, rows)
    if step["incremental"]:
        os.makedirs(os.path.join(d, "state"))
        json.dump(open_state(g, graphlib._parse_iso(step["today"])),
                  open(os.path.join(d, "state", "open_actions.json"), "w"), indent=1)
    write_items(os.path.join(src, "slack", "users.json"), meta["slack_users"])
    if meta.get("slack_channels"):
        write_items(os.path.join(src, "slack", "channels.json"), meta["slack_channels"])
    return len(sel)


def prompt(instructions, meta, step):
    frame = {"user": meta["user"], "workspaces": meta["workspaces"],
             "today": step["today"]}
    tail = ("Sources: every file under `./sources/` (use Glob `./sources/**/*.json`)."
            + (" This is an incremental poll: also read `./state/open_actions.json`."
               if step["incremental"] else "")
            + " Then output ONLY the JSON array of records.")
    return (instructions + "\n\n## Scenario frame (trusted)\n```json\n"
            + json.dumps(frame, indent=1, sort_keys=True) + "\n```\n\n" + tail)


def ingest(g, raw, today):
    env = raw.get("envelope") or {}
    recs, err = run.extract_json_array(env.get("result") or "") \
        if env.get("result") else (None, "no result")
    valid = [r for r in recs or [] if not run.schema.validate_record(r)]
    now = graphlib._parse_iso(today)
    research.ingest(g, valid, now=now)
    correlate.correlate(g, now=now)
    return {"records": len(recs or []), "valid": len(valid), "parse_error": err
            if recs is None else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instructions")
    ap.add_argument("--run-id", required=False)
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--stop-after", default=None)
    ap.add_argument("--rescore", default=None, help="run id: rebuild graph from raw")
    ap.add_argument("--world", default="easy", choices=sorted(build.DIRS))
    ap.add_argument("--crawl-from", default=None,
                    help="run id whose saved first crawl (c1) to reuse; the polls "
                         "then run on --model. Tests a large-model crawl with "
                         "cheap-model polls without paying for the crawl twice.")
    ap.add_argument("--tools", default=None,
                    help="read-only allowlist (default Read,Glob; realistic adds Grep)")
    args = ap.parse_args()
    tools = args.tools or ("Read,Glob,Grep" if args.world == "realistic" else "Read,Glob")
    run.assert_isolated(tools)
    items, meta = load_world(args.world)
    wdir = build.DIRS[args.world]
    rid = args.rescore or args.run_id
    out = os.path.join(RESULTS, rid)
    raw_dir = os.path.join(out, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    if not args.rescore:
        instr = open(args.instructions).read()
        info = {"run_id": rid, "instructions": os.path.relpath(args.instructions, EVALS),
                "instructions_sha256": run.sha256_file(args.instructions),
                "model": args.model, "date": datetime.date.today().isoformat(),
                "cli_version": subprocess.run([run.CLAUDE, "--version"],
                                              capture_output=True, text=True).stdout.strip(),
                "world": args.world, "tools": tools, "crawl_from": args.crawl_from,
                "world_lock": json.load(open(os.path.join(wdir, "world.lock.json")))}
        json.dump(info, open(os.path.join(out, "meta.json"), "w"), indent=1)
    g = graphlib.Graph()
    log = []
    for st in steps(meta):
        raw_path = os.path.join(raw_dir, st["name"] + ".json")
        if not args.rescore and args.crawl_from and st["name"] == "c1":
            src = os.path.join(RESULTS, args.crawl_from, "raw", "c1.json")
            raw = json.load(open(src))
            raw["reused_from"] = args.crawl_from
            json.dump(raw, open(raw_path, "w"), indent=1)
        elif not args.rescore:
            for attempt in (1, 2):      # one re-run for infrastructure failure only
                with tempfile.TemporaryDirectory() as d:
                    n = materialize(d, items, st, meta, g)
                    try:
                        raw = run.run_scenario({"id": st["name"]}, d,
                                               prompt(instr, meta, st), args.model,
                                               args.timeout, allowed=tools)
                    except subprocess.TimeoutExpired:
                        raw = {"scenario": st["name"], "envelope_error": "timeout"}
                raw["items_in_window"] = n
                raw["attempt"] = attempt
                if "envelope" in raw:
                    break
                print("  %s infrastructure failure (%s), attempt %d" % (
                    st["name"], raw.get("envelope_error"), attempt))
            json.dump(raw, open(raw_path, "w"), indent=1)
        raw = json.load(open(raw_path))
        res = ingest(g, raw, st["today"])
        env = raw.get("envelope") or {}
        res.update({"step": st["name"], "today": st["today"],
                    "items": raw.get("items_in_window"),
                    "cost_usd": env.get("total_cost_usd"),
                    "duration_ms": env.get("duration_ms"),
                    "models": sorted((env.get("modelUsage") or {}).keys())})
        log.append(res)
        print("%s: %s items, %s records (%s valid), $%s, %ss" % (
            st["name"], res["items"], res["records"], res["valid"],
            res["cost_usd"], (res["duration_ms"] or 0) // 1000))
        g.save(os.path.join(out, "graph", st["name"]))
        if st["name"] == "c1":
            score_longrun.write(out, "c1", g, meta["today"], wdir)
        if args.stop_after == st["name"]:
            break
    else:
        score_longrun.write(out, "c2", g, meta["c2"], wdir)
    json.dump(log, open(os.path.join(out, "steps.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
