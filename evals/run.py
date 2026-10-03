#!/usr/bin/env python3
"""Eval runner: the real agent step, headless, against fixtures only.

    python3 evals/run.py --split dev --instructions evals/instructions/extract_v1.md
    python3 evals/run.py --score-only results/raw/<run_id>   # re-score, no model

Isolation is enforced, not requested:
- the subprocess gets ``--strict-mcp-config --mcp-config '{"mcpServers":{}}'``
  (zero MCP servers exist inside it — there is no connector to reach), and
- ``--allowedTools Read,Glob`` under ``--permission-mode dontAsk`` (every
  other tool call is denied), and
- this script REFUSES to start if its own allowlist ever names an mcp__ tool
  or any mutating tool.

Raw model envelopes are saved under results/raw/<run_id>/ so every score is
reproducible without re-running the model. Model outputs are never edited:
records that fail schema validation are counted as format errors and the
scenario is scored on whatever valid records remain (see README, Rules).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import schema  # noqa: E402
import score   # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
RESULTS = os.path.join(HERE, "results")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")

ALLOWED_TOOLS = "Read,Glob"
_FORBIDDEN_IN_ALLOWLIST = ("mcp__", "Bash", "Write", "Edit", "WebFetch",
                           "WebSearch", "Agent", "NotebookEdit")


def assert_isolated():
    """The runner's own precondition: fixtures only, ever."""
    for bad in _FORBIDDEN_IN_ALLOWLIST:
        if bad.lower() in ALLOWED_TOOLS.lower():
            raise SystemExit(
                "refusing to run: allowlist %r contains %r — the eval runner "
                "may never reach a connector or mutate anything" %
                (ALLOWED_TOOLS, bad))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load_scenarios(split, only=None):
    out = []
    for name, path in schema.iter_scenarios(FIXTURES):
        scn = json.load(open(os.path.join(path, "scenario.json")))
        if split != "all" and scn["split"] != split:
            continue
        if only and scn["id"] not in only:
            continue
        out.append((scn, path))
    return out


def build_prompt(instructions_text, scn):
    frame = {
        "user": scn["user"],
        "workspaces": scn["workspaces"],
        "today": scn["today"],
    }
    return (
        instructions_text
        + "\n\n## Scenario frame (trusted)\n```json\n"
        + json.dumps(frame, indent=1, sort_keys=True)
        + "\n```\n\nSources: the files matching `./sources/*.json`. Read all "
          "of them, then output ONLY the JSON array of records."
    )


def extract_json_array(text):
    """Pull the records array out of the model's reply. Never repairs JSON —
    a reply we can't parse is a format error, recorded as such."""
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    candidates = [m.group(1)] if m else []
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            parsed = json.loads(c)
            if isinstance(parsed, list):
                return parsed, None
        except ValueError as exc:
            err = str(exc)
    return None, err if candidates else "no JSON array in output"


def run_scenario(scn, sdir, prompt, model, timeout):
    cmd = [
        CLAUDE, "-p", prompt,
        "--output-format", "json",
        "--permission-mode", "dontAsk",
        "--allowedTools", ALLOWED_TOOLS,
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
    ]
    if model:
        cmd += ["--model", model]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    proc = subprocess.run(cmd, cwd=sdir, capture_output=True, text=True,
                          timeout=timeout)
    raw = {"scenario": scn["id"], "started": started,
           "returncode": proc.returncode, "stderr": proc.stderr[-2000:]}
    try:
        env = json.loads(proc.stdout)
    except ValueError:
        raw["envelope_error"] = "non-json stdout"
        raw["stdout"] = proc.stdout[-4000:]
        return raw
    raw["envelope"] = {k: env.get(k) for k in (
        "result", "total_cost_usd", "duration_ms", "duration_api_ms",
        "num_turns", "usage", "modelUsage", "is_error", "subtype")}
    return raw


def score_raw(raw_dir, meta):
    """Score every saved envelope in raw_dir against the fixtures."""
    rows = []
    for f in sorted(os.listdir(raw_dir)):
        if not f.endswith(".json") or f == "meta.json":
            continue
        raw = json.load(open(os.path.join(raw_dir, f)))
        sid = raw["scenario"]
        sdir = os.path.join(FIXTURES, sid)
        scn = json.load(open(os.path.join(sdir, "scenario.json")))
        gold = json.load(open(os.path.join(sdir, "expected.json")))
        env = raw.get("envelope") or {}
        text = (env.get("result") or "")
        records, parse_err = extract_json_array(text) if text else (None,
                                                                    "no result")
        valid, format_errors = [], []
        for r in records or []:
            errs = schema.validate_record(r)
            if errs:
                format_errors.append({"record": r, "errors": errs})
            else:
                valid.append(r)
        row = score.score_scenario(scn, gold, valid, today=scn.get("today"))
        row["parse_error"] = parse_err if records is None else None
        row["format_errors"] = len(format_errors)
        row["records_total"] = len(records or [])
        usage = env.get("usage") or {}
        row["trace"] = {
            "models": sorted((env.get("modelUsage") or {}).keys()),
            "num_turns": env.get("num_turns"),
            "duration_ms": env.get("duration_ms"),
            "cost_usd": env.get("total_cost_usd"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }
        rows.append(row)
    return rows


def summarize(rows, meta):
    by_split = {}
    for r in rows:
        by_split.setdefault(r["split"], []).append(r)
    out = {"meta": meta, "splits": {}}
    for split, split_rows in sorted(by_split.items()):
        agg = score.aggregate(split_rows)
        lat = [r["trace"]["duration_ms"] for r in split_rows
               if r["trace"]["duration_ms"]]
        cost = [r["trace"]["cost_usd"] for r in split_rows
                if r["trace"]["cost_usd"] is not None]
        agg["median_latency_ms"] = int(statistics.median(lat)) if lat else None
        agg["mean_cost_usd"] = round(sum(cost) / len(cost), 4) if cost else None
        agg["total_cost_usd"] = round(sum(cost), 4) if cost else None
        agg["format_errors"] = sum(r["format_errors"] for r in split_rows)
        agg["parse_failures"] = sum(1 for r in split_rows if r["parse_error"])
        out["splits"][split] = agg
    out["scenarios"] = rows
    return out


def write_report(summary, path_base):
    with open(path_base + ".json", "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    lines = ["# Eval run %s" % summary["meta"]["run_id"], ""]
    m = summary["meta"]
    lines += ["- instructions: `%s` (sha256 `%s…`)" % (
        m["instructions"], m["instructions_sha256"][:12]),
        "- model arg: %s · cli: %s" % (m["model"] or "(default)",
                                       m["cli_version"]),
        "- date: %s" % m["date"], ""]
    for split, agg in sorted(summary["splits"].items()):
        lines += ["## %s (%d scenarios)" % (split, agg["scenarios"]),
                  "",
                  "| metric | value |", "|---|---|"]
        for k in ("precision", "recall", "f1", "due_accuracy",
                  "citation_accuracy", "direction_accuracy",
                  "grouping_accuracy", "invented_items",
                  "duplicate_failures", "isolation_violations",
                  "format_errors", "parse_failures",
                  "median_latency_ms", "mean_cost_usd", "total_cost_usd"):
            lines.append("| %s | %s |" % (k, agg.get(k)))
        lines.append("| injection resisted | %s/%s |" % (
            agg["injection_resisted"], agg["injection_scenarios"]))
        lines += ["", "per category F1: " + ", ".join(
            "%s %.2f" % (c, v["f1"])
            for c, v in sorted(agg["by_category"].items())), ""]
    with open(path_base + ".md", "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=("dev", "test", "all"))
    ap.add_argument("--instructions",
                    default=os.path.join(HERE, "instructions", "extract_v1.md"))
    ap.add_argument("--model", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--scenarios", nargs="*", default=None,
                    help="restrict to these scenario ids")
    ap.add_argument("--score-only", default=None,
                    help="path to an existing results/raw/<run_id> dir")
    args = ap.parse_args()

    assert_isolated()
    os.makedirs(RESULTS, exist_ok=True)

    if args.score_only:
        raw_dir = args.score_only
        meta = json.load(open(os.path.join(raw_dir, "meta.json")))
        rows = score_raw(raw_dir, meta)
        summary = summarize(rows, meta)
        base = os.path.join(RESULTS, meta["run_id"] + "-rescored")
        write_report(summary, base)
        print("re-scored %d scenarios -> %s.md" % (len(rows), base))
        return

    instr_text = open(args.instructions).read()
    instr_sha = sha256_file(args.instructions)
    cli_version = subprocess.run([CLAUDE, "--version"], capture_output=True,
                                 text=True).stdout.strip()
    date = datetime.date.today().isoformat()
    short = instr_sha[:6]
    run_id = args.run_id or "%s-%s-%s-%s" % (
        date, os.path.basename(args.instructions).replace(".md", ""),
        args.split, short)
    raw_dir = os.path.join(RESULTS, "raw", run_id)
    os.makedirs(raw_dir, exist_ok=True)

    scenarios = load_scenarios(args.split, only=args.scenarios)
    if not scenarios:
        raise SystemExit("no scenarios for split %r" % args.split)
    meta = {"run_id": run_id, "date": date, "split": args.split,
            "instructions": os.path.relpath(args.instructions, HERE),
            "instructions_sha256": instr_sha, "model": args.model,
            "cli_version": cli_version, "allowed_tools": ALLOWED_TOOLS,
            "scenarios": len(scenarios)}
    with open(os.path.join(raw_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)

    print("run %s: %d scenarios, workers=%d" % (
        run_id, len(scenarios), args.workers))

    def _one(item):
        scn, sdir = item
        prompt = build_prompt(instr_text, scn)
        try:
            raw = run_scenario(scn, sdir, prompt, args.model, args.timeout)
        except subprocess.TimeoutExpired:
            raw = {"scenario": scn["id"], "envelope_error": "timeout"}
        with open(os.path.join(raw_dir, scn["id"] + ".json"), "w") as f:
            json.dump(raw, f, indent=1)
        ok = "envelope" in raw
        print("  %-28s %s" % (scn["id"], "ok" if ok else "ERROR"))
        return raw

    with concurrent.futures.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(_one, scenarios))

    rows = score_raw(raw_dir, meta)
    summary = summarize(rows, meta)
    base = os.path.join(RESULTS, run_id)
    write_report(summary, base)
    for split, agg in summary["splits"].items():
        print("%s: F1 %.3f  P %.3f  R %.3f  due %s  cite %s  iso %d  "
              "inj %s/%s" % (
                  split, agg["f1"], agg["precision"], agg["recall"],
                  agg["due_accuracy"], agg["citation_accuracy"],
                  agg["isolation_violations"], agg["injection_resisted"],
                  agg["injection_scenarios"]))
    print("reports: %s.{json,md}" % base)


if __name__ == "__main__":
    main()
