#!/usr/bin/env python3
"""Eval fixture + record schema checks. Stdlib only, 3.9-compatible.

Two consumers:
- ``tests/test_schema.py`` validates every committed fixture scenario, so a
  malformed scenario fails fast instead of silently skewing a run.
- ``run.py`` validates each model-emitted record before it is allowed into the
  real ingest path; invalid records are counted (``format_errors``), never
  repaired by hand (see evals/README.md, Rules).
"""

from __future__ import annotations

import json
import os

SOURCE_CONNECTORS = {"email", "slack", "ticketing", "calendar", "docs", "code"}

# Node kinds the extraction step may emit. Mirrors the research table plus
# Action (Step 1c) and Person/Project endpoints.
RECORD_KINDS = {
    "Action", "Person", "Project", "Ticket", "Meeting", "Document", "Channel",
    "PR", "Repository", "Incident", "Decision", "Deployment", "JobApplication",
}

GOLD_OWNERS = {"user", "counterparty"}


def _require(cond, errs, msg):
    if not cond:
        errs.append(msg)


def validate_source(item):
    """One connector-shaped fixture item. Returns a list of problems."""
    errs = []
    _require(isinstance(item, dict), errs, "source item must be an object")
    if errs:
        return errs
    _require(item.get("connector") in SOURCE_CONNECTORS, errs,
             "connector must be one of %s" % sorted(SOURCE_CONNECTORS))
    _require(bool(item.get("id")), errs, "source item needs an id")
    _require(bool(item.get("date")), errs, "source item needs a date")
    body_keys = ("body", "text", "summary", "title", "name")
    _require(any(item.get(k) for k in body_keys), errs,
             "source item needs content (one of %s)" % (body_keys,))
    return errs


def validate_scenario_dir(path):
    """Validate one fixtures/<scenario>/ directory. Returns problems."""
    errs = []
    for fname in ("scenario.json", "expected.json"):
        if not os.path.exists(os.path.join(path, fname)):
            errs.append("missing " + fname)
    srcdir = os.path.join(path, "sources")
    if not os.path.isdir(srcdir):
        return errs + ["missing sources/ dir"]
    ids = set()
    for f in sorted(os.listdir(srcdir)):
        if not f.endswith(".json"):
            continue
        try:
            item = json.load(open(os.path.join(srcdir, f)))
        except ValueError as exc:
            errs.append("%s: bad json (%s)" % (f, exc))
            continue
        for e in validate_source(item):
            errs.append("%s: %s" % (f, e))
        if item.get("id") in ids:
            errs.append("%s: duplicate source id %s" % (f, item.get("id")))
        ids.add(item.get("id"))
        if item.get("id") != f[:-5]:
            errs.append("%s: filename must equal source id" % f)
    if errs:
        return errs

    scenario = json.load(open(os.path.join(path, "scenario.json")))
    _require(bool(scenario.get("id")), errs, "scenario.json needs id")
    _require(scenario.get("split") in ("dev", "test"), errs,
             "scenario.json split must be dev|test")
    _require(bool(scenario.get("category")), errs, "scenario.json needs category")
    _require(isinstance(scenario.get("workspaces"), dict) and scenario["workspaces"],
             errs, "scenario.json needs workspaces map")
    _require(bool((scenario.get("user") or {}).get("email")), errs,
             "scenario.json needs user.email")

    gold = json.load(open(os.path.join(path, "expected.json")))
    for i, c in enumerate(gold.get("commitments", [])):
        tag = "commitments[%d]" % i
        _require(isinstance(c.get("gist"), list) and len(c["gist"]) >= 2, errs,
                 tag + ": gist must be >=2 keywords")
        _require(c.get("owner") in GOLD_OWNERS, errs, tag + ": owner user|counterparty")
        _require(c.get("workspace") in scenario.get("workspaces", {}), errs,
                 tag + ": workspace must be a scenario workspace")
        _require(isinstance(c.get("sources"), list) and c["sources"], errs,
                 tag + ": needs sources[]")
        for s in c.get("sources", []):
            _require(s in ids, errs, tag + ": unknown source id %s" % s)
        due = c.get("due")
        _require(due is None or (isinstance(due, str) and len(due) >= 10), errs,
                 tag + ": due must be null or ISO date")
    for i, d in enumerate(gold.get("forbidden", [])):
        _require(isinstance(d, list) and len(d) >= 2, errs,
                 "forbidden[%d] must be >=2 keywords" % i)
    for i, grp in enumerate(gold.get("same_objective", [])):
        _require(isinstance(grp, list) and len(grp) >= 2, errs,
                 "same_objective[%d] needs >=2 source ids" % i)
        for s in grp:
            _require(s in ids, errs, "same_objective[%d]: unknown source %s" % (i, s))
    for i, d in enumerate(gold.get("dedupe", [])):
        _require(isinstance(d.get("gist"), list) and d.get("max", 0) >= 1, errs,
                 "dedupe[%d] needs gist + max>=1" % i)
    for sid, ws in (gold.get("isolation") or {}).items():
        _require(sid in ids, errs, "isolation: unknown source %s" % sid)
        _require(ws in scenario.get("workspaces", {}), errs,
                 "isolation: unknown workspace %s" % ws)
    inj = gold.get("injection")
    if inj:
        _require(inj.get("source") in ids, errs, "injection.source unknown")
        _require(isinstance(inj.get("gist"), list) and len(inj["gist"]) >= 2, errs,
                 "injection.gist must be >=2 keywords")
    return errs


def validate_record(rec):
    """One model-emitted record. Returns problems (empty = acceptable)."""
    errs = []
    _require(isinstance(rec, dict), errs, "record must be an object")
    if errs:
        return errs
    _require(rec.get("kind") in RECORD_KINDS, errs,
             "kind %r not in %s" % (rec.get("kind"), sorted(RECORD_KINDS)))
    _require(bool(rec.get("key")), errs, "record needs key")
    _require(bool(rec.get("workspace")), errs, "record needs workspace")
    attrs = rec.get("attrs")
    _require(attrs is None or isinstance(attrs, dict), errs, "attrs must be an object")
    conf = rec.get("confidence", 1.0)
    _require(isinstance(conf, (int, float)) and 0 <= conf <= 1, errs,
             "confidence must be 0..1")
    for i, e in enumerate(rec.get("edges") or []):
        _require(isinstance(e, dict) and e.get("to_kind") and e.get("to_key")
                 and e.get("type"), errs, "edges[%d] needs to_kind/to_key/type" % i)
    return errs


def iter_scenarios(fixtures_dir):
    for name in sorted(os.listdir(fixtures_dir)):
        path = os.path.join(fixtures_dir, name)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "scenario.json")):
            yield name, path
