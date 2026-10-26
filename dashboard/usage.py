#!/usr/bin/env python3
"""What every model call costs, and the limits that keep it small (stdlib only).

Every ``claude -p`` the app makes goes through ``run`` (the server calls it
directly; background jobs and poll-tick.sh call this file as a script). It:

1. **Sends only the tools the job may use.** ``--allowedTools`` grants
   permission but Claude Code still sends every built-in tool's definition,
   about 40k tokens per call. ``--tools`` limits what is sent; it is set to the
   built-in names already in the grant (connector tools are unaffected).
   Measured on a one-word reply: $0.057 -> $0.007.
2. **Caps each call** with ``--max-budget-usd`` (per job, in models.json), so
   one runaway job cannot burn money.
3. **Refuses new work past the daily budget** (``budget.daily_usd``). The
   user's own approve clicks are never refused.
4. **Logs cost and tokens** of each call to ``usage.jsonl`` for the Usage view.

The result text is returned exactly as ``--output-format text`` would have
printed it, so callers did not change.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import sys

USAGE_FILE = "usage.jsonl"
CONFIG_FILE = "models.json"

# Built-in tool names Claude Code knows; anything else in a grant (mcp__...)
# is a connector tool, which --tools does not touch.
_BUILTIN = {"Read", "Edit", "Write", "Glob", "Grep", "Bash", "Agent", "Task", "ToolSearch",
            "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite", "MultiEdit", "LS"}


DEFAULT_CALL_CAPS = {"research": 15.0, "learn": 3.0, "poll": 1.5, "approve": 1.0,
                     "revise": 0.75, "chat": 0.5, "task_chat": 0.5, "accounts_probe": 0.5,
                     "draft": 1.0, "poll_direct": 1.0}


def _now():
    return _dt.datetime.now(_dt.timezone.utc)


def budget(config_dir):
    """{"daily_usd": float|None, "per_call": {job: usd}} from models.json."""
    try:
        with open(os.path.join(config_dir, CONFIG_FILE)) as f:
            b = (json.load(f) or {}).get("budget") or {}
    except (OSError, ValueError):
        b = {}
    caps = dict(DEFAULT_CALL_CAPS)
    caps.update({k: float(v) for k, v in (b.get("per_call") or {}).items()
                 if isinstance(v, (int, float)) and v > 0})
    daily = b.get("daily_usd")
    return {"daily_usd": float(daily) if isinstance(daily, (int, float)) and daily > 0 else None,
            "per_call": caps}


def save_budget(config_dir, daily_usd):
    """Set (or clear, with None/0) the daily budget, keeping the rest of models.json."""
    path = os.path.join(config_dir, CONFIG_FILE)
    try:
        with open(path) as f:
            cfg = json.load(f) or {}
    except (OSError, ValueError):
        cfg = {}
    b = cfg.get("budget") or {}
    if daily_usd:
        if not 0.01 <= float(daily_usd) <= 10000:
            raise ValueError("daily budget must be between $0.01 and $10,000")
        b["daily_usd"] = round(float(daily_usd), 2)
    else:
        b.pop("daily_usd", None)
    cfg["budget"] = b
    with open(path, "w") as f:
        json.dump(cfg, f, indent=1)


def _flag_value(cmd, flag):
    for i, a in enumerate(cmd):
        if a == flag and i + 1 < len(cmd):
            return cmd[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def builtin_tools(grant, job=None):
    """The built-in tool names in an --allowedTools grant, for --tools.
    A grant that names connector tools (mcp__...) also gets ToolSearch, which
    is how Claude Code loads connector tools on demand."""
    names, connectors = [], False
    for part in re.split(r"[,\s]+", grant or ""):
        name = part.split("(", 1)[0].strip()
        if name.startswith("mcp__"):
            connectors = True
        elif name in _BUILTIN and name not in names:
            names.append(name)
    if connectors and "ToolSearch" not in names:
        names.append("ToolSearch")
    return names


def prepare(cmd, job, config_dir):
    """The command with --tools, --max-budget-usd and JSON output set."""
    cmd = list(cmd)
    if "--tools" not in cmd:
        grant = _flag_value(cmd, "--allowedTools") or _flag_value(cmd, "--allowed-tools")
        if grant is not None:
            cmd += ["--tools", ",".join(builtin_tools(grant, job))]
    if "--max-budget-usd" not in cmd:
        cap = budget(config_dir)["per_call"].get(job)
        if cap:
            cmd += ["--max-budget-usd", "%.2f" % cap]
    if "--output-format" in cmd:
        i = cmd.index("--output-format")
        cmd[i + 1] = "json"
    else:
        cmd += ["--output-format", "json"]
    return cmd


def spent_today(config_dir, now=None):
    day = (now or _now()).astimezone().date().isoformat()
    total = 0.0
    for r in _records(config_dir):
        if r.get("day") == day:
            total += r.get("cost_usd") or 0.0
    return round(total, 4)


def over_daily_budget(config_dir, now=None):
    """(over?, spent today, cap) — never over when no daily budget is set."""
    cap = budget(config_dir)["daily_usd"]
    spent = spent_today(config_dir, now)
    return (cap is not None and spent >= cap), spent, cap


def _records(config_dir):
    path = os.path.join(config_dir, USAGE_FILE)
    try:
        with open(path) as f:
            for line in f:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


def record(config_dir, job, envelope, ok=True, now=None):
    now = now or _now()
    env = envelope or {}
    u = env.get("usage") or {}
    rec = {
        "ts": now.isoformat(timespec="seconds"),
        "day": now.astimezone().date().isoformat(),
        "job": job,
        "models": sorted((env.get("modelUsage") or {}).keys()),
        "cost_usd": round(float(env.get("total_cost_usd") or 0.0), 6),
        "input_tokens": u.get("input_tokens") or 0,
        "output_tokens": u.get("output_tokens") or 0,
        "cache_read_tokens": u.get("cache_read_input_tokens") or 0,
        "cache_write_tokens": u.get("cache_creation_input_tokens") or 0,
        "duration_ms": env.get("duration_ms") or 0,
        "turns": env.get("num_turns") or 0,
        "ok": bool(ok) and not env.get("is_error"),
    }
    with open(os.path.join(config_dir, USAGE_FILE), "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


class Result:
    """Shaped like subprocess.CompletedProcess, so callers did not change."""
    def __init__(self, returncode, stdout, stderr, record=None):
        self.returncode, self.stdout, self.stderr, self.record = returncode, stdout, stderr, record


BUDGET_MESSAGE = ("Today's model budget is used up (${spent:.2f} of ${cap:.2f}), so this did "
                  "not run. Raise or clear it in Settings → Usage.")


def run(cmd, job, config_dir, cwd=None, timeout=None, env=None, enforce_budget=True, input=None):
    """Run one claude call through the limits above; returns a Result."""
    if enforce_budget and job != "approve":
        over, spent, cap = over_daily_budget(config_dir)
        if over:
            return Result(3, BUDGET_MESSAGE.format(spent=spent, cap=cap), "")
    proc = subprocess.run(prepare(cmd, job, config_dir), cwd=cwd, capture_output=True,
                          text=True, timeout=timeout, env=env,
                          input=input if input is not None else "")
    try:
        envelope = json.loads(proc.stdout)
    except ValueError:
        return Result(proc.returncode, proc.stdout, proc.stderr)
    rec = record(config_dir, job, envelope, ok=proc.returncode == 0)
    text = envelope.get("result")
    if text is None:
        text = "(stopped: %s)" % (envelope.get("subtype") or "no result")
    return Result(proc.returncode, text, proc.stderr, rec)


def summary(config_dir, days=30, now=None):
    """Totals for the Usage view: today, last 7 days, last N days, by job and model."""
    now = now or _now()
    today = now.astimezone().date()
    out = {"today": 0.0, "week": 0.0, "period": 0.0, "calls": 0, "by_job": {}, "by_model": {},
           "by_day": {}, "days": days}
    for r in _records(config_dir):
        try:
            day = _dt.date.fromisoformat(r.get("day", ""))
        except ValueError:
            continue
        age = (today - day).days
        if age < 0 or age >= days:
            continue
        c = r.get("cost_usd") or 0.0
        out["period"] += c
        out["calls"] += 1
        if age == 0:
            out["today"] += c
        if age < 7:
            out["week"] += c
        j = out["by_job"].setdefault(r.get("job", "?"), {"cost": 0.0, "calls": 0, "tokens": 0})
        j["cost"] += c
        j["calls"] += 1
        j["tokens"] += sum(r.get(k) or 0 for k in ("input_tokens", "output_tokens",
                                                     "cache_read_tokens", "cache_write_tokens"))
        for m in r.get("models") or ["?"]:
            out["by_model"][m] = out["by_model"].get(m, 0.0) + c / max(1, len(r.get("models") or [1]))
        out["by_day"][day.isoformat()] = out["by_day"].get(day.isoformat(), 0.0) + c
    return out


def main(argv):
    # usage.py run JOB CONFIG_DIR -- claude ...   (prints the result text)
    # usage.py over-budget CONFIG_DIR             (exit 0 when over today's budget)
    if len(argv) >= 2 and argv[0] == "over-budget":
        over, spent, cap = over_daily_budget(argv[1])
        if over:
            print(BUDGET_MESSAGE.format(spent=spent, cap=cap))
        return 0 if over else 1
    if len(argv) >= 4 and argv[0] == "run" and "--" in argv:
        job, config_dir = argv[1], argv[2]
        cmd = argv[argv.index("--") + 1:]
        res = run(cmd, job, config_dir)
        sys.stdout.write(res.stdout.rstrip() + "\n")
        sys.stderr.write(res.stderr)
        return res.returncode
    sys.stderr.write("usage: usage.py run JOB CONFIG_DIR -- claude ... | over-budget CONFIG_DIR\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
