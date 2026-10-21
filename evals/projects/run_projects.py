#!/usr/bin/env python3
"""Run and score /cos-research Step 1e against the projects fixture world.

    python3 evals/projects/run_projects.py --runs 2            # model runs + score
    python3 evals/projects/run_projects.py --score-only <raw>  # re-score saved output

The instructions are the production text: Step 1e and the priority rule are cut
from commands/cos-research.md at run time, so this tests what ships. Isolation
is the main harness's (evals/run.py run_scenario): no MCP servers, read-only
tools only.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import run as harness  # noqa: E402

ALLOWED = "Read,Glob,Grep"
DONE = {"done", "completed", "complete", "resolved", "closed", "dismissed",
        "rejected", "withdrawn", "expired"}

PREAMBLE = """You are the research engine of a chief-of-staff system, running in
fixture mode. The user's connected sources are files in this directory:

- `./context.md`: what the user wrote about themselves (trusted).
- `./projects/<name>/`: the user's local project folders. Read the files in them.
- `./sources/local.json`: what the local-filesystem connector reports for each
  folder (branch, uncommitted files, recent commits with author and date).
- `./sources/github.json`: repositories, CI workflow runs (with jobs and the
  steps that ran) and pull requests.
- `./sources/gmail.json`: mail.

Use Glob, Read and Grep. There is no other tool and no network. Today is {today}.
The user is {user}.

Follow the production instructions below, then output ONLY one JSON object:

```
{{"records": [ {{"kind": "...", "workspace": "personal", "key": "...", "name": "...",
               "attrs": {{...}}, "confidence": 0.0-1.0,
               "edges": [{{"to_kind": "...", "to_key": "...", "type": "..."}}]}} ],
 "questions": ["each residual question for the user, one string each"]}}
```

`kind` is one of Project, Repository, Action, Person. Every Action needs
`attrs.priority` and `attrs.refs` naming the project folder it belongs to.
Every Project needs `key` equal to the project's folder name.

## Production instructions (from commands/cos-research.md)

{step}

### Priority (from Step 1c)

{priority}
"""


def production_text():
    s = open(os.path.join(ROOT, "commands", "cos-research.md")).read()
    a = s.index("### Step 1e")
    b = s.index("## Step 2", a)
    p = s.index("- `attrs.priority`")
    q = s.index("- `attrs.clear_attrs`", p)
    return s[a:b].strip(), s[p:q].strip()


def build_prompt(gold, user):
    step, pri = production_text()
    return PREAMBLE.format(today=gold["today"], user=user, step=step, priority=pri)


def parse(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text or "", re.DOTALL)
    cands = [m.group(1)] if m else []
    i, j = (text or "").find("{"), (text or "").rfind("}")
    if i != -1 and j > i:
        cands.append(text[i:j + 1])
    for c in cands:
        try:
            d = json.loads(c)
            if isinstance(d, dict):
                return d
        except ValueError:
            pass
    return None


def _blob(r):
    return json.dumps(r, sort_keys=True).lower()


def _mentions(r, proj):
    stem = proj.split("-")[0]
    b = _blob(r)
    return proj in b or stem in b


def _open_action(r):
    if r.get("kind") != "Action":
        return False
    st = str((r.get("attrs") or {}).get("status") or "").lower().replace("_", " ")
    return st not in DONE


def _has_any(text, words):
    # word starts only: "ci" must not match inside "decide"
    t = (text or "").lower()
    return any(re.search(r"(?<![a-z0-9])" + re.escape(w), t) for w in words)


def _matches(r, groups):
    t = " ".join(str(x) for x in (r.get("key"), r.get("name"))).lower()
    t += " " + json.dumps(r.get("attrs") or {}).lower()
    return all(_has_any(t, g) for g in groups)


def _best_pairing(mine, expected):
    """Pair expected actions with emitted ones to match as many as possible.
    A greedy pass in key order let one expected action take an emitted one
    that only it and another could match (a review mentioning a "build"),
    leaving the other unmatched; projects have a handful of each, so try
    every assignment."""
    names = list(expected)
    best = {}

    def go(k, used, cur):
        nonlocal best
        if len(cur) + (len(names) - k) <= len(best):
            return
        if k == len(names):
            best = dict(cur)
            return
        for i, r in enumerate(mine):
            if i not in used and _matches(r, expected[names[k]]):
                cur[names[k]] = i
                go(k + 1, used | {i}, cur)
                del cur[names[k]]
        go(k + 1, used, cur)

    go(0, frozenset(), {})
    return best


def score(out, gold):
    rows, ok_all = [], True
    recs = (out or {}).get("records") or []
    questions = (out or {}).get("questions") or []
    acts = [r for r in recs if _open_action(r)]
    for proj, g in gold["projects"].items():
        mine = [r for r in acts if _mentions(r, proj)]
        projrec = [r for r in recs if r.get("kind") in ("Project", "Repository")
                   and str(r.get("key", "")).lower() == proj]
        a = (projrec[0].get("attrs") or {}) if projrec else {}
        checks = {}
        if g["active"]:
            checks["project_record"] = bool(projrec)
            checks["state_summary"] = _has_any(a.get("state_summary"), g["summary_any"])
            if g.get("health_any"):
                checks["health"] = _has_any(a.get("health"), g["health_any"])
            if g.get("collaborator"):
                checks["collaborator"] = g["collaborator"] in _blob(recs)
        else:
            checks["not_live"] = (not projrec) or bool(a.get("dormant"))
        pairing = _best_pairing(mine, g["actions"])
        used = set(pairing.values())
        for name in g["actions"]:
            checks["action:" + name] = name in pairing
        extra = [r.get("name") or r.get("key") for i, r in enumerate(mine) if i not in used]
        checks["no_extra_actions"] = not extra
        ok = all(checks.values())
        ok_all &= ok
        rows.append({"project": proj, "pass": ok, "checks": checks, "extra_actions": extra})
    q_ok = any(_has_any(q, gold["question_any"]) for q in questions) or any(
        (r.get("attrs") or {}).get("needs_connect") and _has_any(_blob(r), gold["question_any"])
        for r in recs)
    rows.append({"project": "(named but missing)", "pass": q_ok,
                 "checks": {"question": q_ok}, "extra_actions": []})
    ok_all &= q_ok
    return {"pass": ok_all, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--score-only")
    args = ap.parse_args()
    gold = json.load(open(os.path.join(HERE, "gold.json")))
    if args.score_only:
        for f in sorted(os.listdir(args.score_only)):
            raw = json.load(open(os.path.join(args.score_only, f)))
            res = score(parse((raw.get("envelope") or {}).get("result")), gold)
            print(f, json.dumps(res, indent=1))
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = os.path.join(HERE, "..", "results", "projects", "raw", stamp)
    os.makedirs(raw_dir, exist_ok=True)
    prompt = build_prompt(gold, "Riya Patel (GitHub riyap, riya@mail.example)")
    results = []
    for n in range(args.runs):
        sdir = tempfile.mkdtemp(prefix="proj-eval-")
        shutil.copytree(os.path.join(HERE, "world"), sdir, dirs_exist_ok=True)
        raw = harness.run_scenario({"id": "projects-%d" % n}, sdir, prompt,
                                   args.model, args.timeout, allowed=ALLOWED)
        shutil.rmtree(sdir, ignore_errors=True)
        json.dump(raw, open(os.path.join(raw_dir, "run%d.json" % n), "w"), indent=1)
        env = raw.get("envelope") or {}
        res = score(parse(env.get("result")), gold)
        res["cost"] = env.get("total_cost_usd")
        res["model"] = list((env.get("modelUsage") or {}).keys())
        results.append(res)
        print(json.dumps(res, indent=1))
    json.dump(results, open(os.path.join(raw_dir, "scores.json"), "w"), indent=1)
    print("saved", raw_dir)


if __name__ == "__main__":
    main()
