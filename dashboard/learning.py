#!/usr/bin/env python3
"""AI OS self-learning correction loop — testable core (V2.1, milestone M9).

When the user reports a miss ("you're missing the email from Acme"), the system
doesn't just fetch the missing item — it runs a correction loop: capture the
feedback, remediate the data gap, **diagnose why it was missed**, apply the fix
itself (config / instructions / code, gated by tests + guardrails), and record
the lesson so the same class of miss doesn't recur.

This module is the deterministic, unit-testable half of that loop; the judgment
half (fine-grained extraction, root-cause reasoning, writing the actual fix)
lives in ``commands/cos-learn.md``, which calls into this module.

Hard safety invariants (never relaxed, see GUARDRAIL_PATHS):
  - Self-modification touches only this deployment's own files under the
    template root. Never external state; connectors stay read-only.
  - The approval-gating surface (approve commands, APPROVAL_POLICY handling,
    the audit log, and this guardrail logic itself) can never be self-modified.
  - Every self-change must pass the full test gate or it is auto-reverted
    (snapshot-based, so it works in deployments without git).

Files (all under the workspace dir):
  correction-queue.jsonl   pending corrections (async queue, like style-feedback)
  corrections.jsonl        append-only ledger of resolved corrections + outcomes
  self-changes/<token>/    snapshots backing auto-revert
"""

from __future__ import annotations

import json
import os
import re
import shutil

import graph

QUEUE_FILE = "correction-queue.jsonl"
LEDGER_FILE = "corrections.jsonl"
SNAPSHOT_DIR = "self-changes"

# ---------------------------------------------------------------------------
# Feature toggle (the "auto self-learning mode" switch)
# ---------------------------------------------------------------------------

DEFAULTS = {"self_learning": True, "self_modify_code": True}


def self_learning_enabled(config):
    """Whole-loop switch (capture/remediate/diagnose/learn)."""
    return bool((config or {}).get("self_learning", DEFAULTS["self_learning"]))


def self_modify_enabled(config):
    """Code-change sub-switch. Off -> code fixes are drafted as tasks instead."""
    if not self_learning_enabled(config):
        return False
    return bool((config or {}).get("self_modify_code", DEFAULTS["self_modify_code"]))


# ---------------------------------------------------------------------------
# 1. Capture — classify chat text as a correction
# ---------------------------------------------------------------------------

# Phrases that signal "you got something wrong / missed something".
_MISS_RE = re.compile(
    r"\b(you('re| are)? missing|you missed|missing (from|in|the)|didn'?t (catch|see|find|pick up)|"
    r"where('s| is) (the|my)|why (isn'?t|is)n?.{0,30}(showing|there|here)|"
    r"('s|\bis|\bare|\blooks?) (wrong|incorrect|outdated|stale)|not (showing|listed|there)|"
    r"forgot (about|the)|overlooked)\b", re.IGNORECASE)

# Connector nouns -> canonical connector hint.
_CONNECTOR_WORDS = [
    (re.compile(r"\b(email|inbox|gmail|mail)\b", re.I), "email"),
    (re.compile(r"\b(slack|teams|message|dm|channel|chat thread)\b", re.I), "messaging"),
    (re.compile(r"\b(ticket|jira|linear|issue|board)\b", re.I), "ticketing"),
    (re.compile(r"\b(meeting|calendar|invite|call)\b", re.I), "calendar"),
    (re.compile(r"\b(doc|document|wiki|drive|notion)\b", re.I), "docs"),
    (re.compile(r"\b(pr|pull request|repo|repository|commit|deploy)\b", re.I), "code"),
]


def classify_feedback(text):
    """Return a correction hint dict if ``text`` reads as a correction, else None.

    Deliberately conservative and deterministic (unit-testable): the server uses
    it to decide whether to kick off the learn loop; the loop's LLM step does the
    fine-grained extraction. A normal question ("what's on my calendar?") must
    NOT classify.
    """
    if not text or not _MISS_RE.search(text):
        return None
    connector = None
    for pat, name in _CONNECTOR_WORDS:
        if pat.search(text):
            connector = name
            break
    return {
        "connector_hint": connector or "unknown",
        "expected": text.strip(),
        "keywords": _keywords(text),
    }


_STOP = {"the", "a", "an", "is", "are", "you", "your", "youre", "my", "from",
         "in", "on", "it", "its", "this", "that", "of", "to", "and", "im", "i",
         "missing", "missed", "not", "showing", "why", "isnt", "wrong", "about",
         "me", "dont", "didnt", "cant", "was", "were", "there", "here"}


def _keywords(text):
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]+", text)
    out = []
    for w in words:
        lw = w.lower().replace("'", "").strip("-")
        if lw not in _STOP and len(lw) > 2 and lw not in out:
            out.append(lw)
    return out[:8]


# ---------------------------------------------------------------------------
# Correction queue (async, like style-feedback-queue)
# ---------------------------------------------------------------------------

def make_correction(text, hint=None, workspace=None, source="chat", now=None):
    hint = hint or classify_feedback(text) or {
        "connector_hint": "unknown", "expected": text, "keywords": _keywords(text)}
    ts = graph.iso(now)
    cid = "corr-%s-%s" % (ts.replace(":", "").replace("-", "")[:15],
                          graph.slug(" ".join(hint["keywords"][:3]) or "misc")[:40])
    return {
        "id": cid,
        "status": "pending",
        "text": text.strip(),
        "connector_hint": hint["connector_hint"],
        "keywords": hint["keywords"],
        "workspace": workspace,
        "source": source,
        "created": ts,
    }


def enqueue(ws_dir, rec):
    os.makedirs(ws_dir, exist_ok=True)
    with open(os.path.join(ws_dir, QUEUE_FILE), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def pending(ws_dir):
    return [r for r in _read_jsonl(os.path.join(ws_dir, QUEUE_FILE))
            if r.get("status") == "pending"]


def resolve(ws_dir, correction_id, status="resolved"):
    """Mark a queued correction non-pending (rewrites the small queue file)."""
    path = os.path.join(ws_dir, QUEUE_FILE)
    rows = _read_jsonl(path)
    hit = False
    for r in rows:
        if r.get("id") == correction_id:
            r["status"] = status
            hit = True
    if hit:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    return hit


# ---------------------------------------------------------------------------
# 3. Diagnose — deterministic root-cause checks
# ---------------------------------------------------------------------------

FAILURE_CLASSES = [
    "staleness",        # item newer than the last research/poll pass
    "coverage_gap",     # module never searched where the item lives
    "filter_cutoff",    # dropped by a top-N/recency limit
    "connector_down",   # connector unavailable at crawl time
    "normalization",    # fetched but mis-keyed/dropped (near-miss in graph)
    "correlation",      # node exists but isn't linked to its workstream
    "unknown",
]


def diagnose_checks(rec, g, last_research_ts=None, preflight_summary=None):
    """Run the machine-checkable hypotheses. Returns ranked findings:
    ``[{"hypothesis": <class>, "evidence": str, "likely": bool}]`` — the
    cos-learn command layers LLM reasoning on top of (never instead of) these.
    """
    findings = []
    kws = [k for k in rec.get("keywords", []) if k]

    # normalization / correlation: is a near-miss node already in the graph?
    near = _near_miss_nodes(g, kws)
    if near:
        uncorrelated = [n for n in near
                        if not g.neighbors(n["id"], edge_type="part_of",
                                           direction="out")]
        if uncorrelated:
            findings.append({
                "hypothesis": "correlation",
                "evidence": "graph already has %s but it belongs to no "
                            "workstream" % ", ".join(n["id"] for n in uncorrelated[:3]),
                "likely": True})
        else:
            findings.append({
                "hypothesis": "normalization",
                "evidence": "near-miss node(s) present: %s — item may be "
                            "mis-keyed rather than missing" %
                            ", ".join(n["id"] for n in near[:3]),
                "likely": True})

    # connector down at crawl time
    if preflight_summary:
        down = {u["connector"] for u in preflight_summary.get("unavailable", [])}
        if rec.get("connector_hint") in down:
            findings.append({
                "hypothesis": "connector_down",
                "evidence": "last preflight marked '%s' unavailable" %
                            rec["connector_hint"],
                "likely": True})

    # staleness: nothing from this connector verified recently
    if last_research_ts:
        newest = _newest_from_source(g, rec.get("connector_hint"))
        if newest is None or newest < last_research_ts:
            findings.append({
                "hypothesis": "staleness",
                "evidence": "no '%s' node verified since %s — the item may "
                            "postdate the last crawl" % (
                                rec.get("connector_hint"), last_research_ts),
                "likely": not near})

    if not near and not findings:
        findings.append({
            "hypothesis": "coverage_gap",
            "evidence": "no trace of the item in the graph at all — the "
                        "discovery module likely never searched its location "
                        "(folder/label/time window) or a filter cut it",
            "likely": True})
    findings.append({"hypothesis": "unknown", "evidence": "fallback", "likely": False})
    return findings


def _near_miss_nodes(g, keywords, min_hits=1):
    if not keywords:
        return []
    out = []
    for n in g.nodes.values():
        blob = (" ".join([n.get("name", ""), n["id"],
                          json.dumps(n.get("attrs", {}))])).lower()
        hits = sum(1 for k in keywords if k.lower() in blob)
        if hits >= max(min_hits, min(2, len(keywords))):
            out.append(n)
    return sorted(out, key=lambda n: n["id"])


def _newest_from_source(g, connector_hint):
    ts = [n.get("last_verified") for n in g.nodes.values()
          if connector_hint and connector_hint in (n.get("source") or "")]
    ts = [t for t in ts if t]
    return max(ts) if ts else None


# ---------------------------------------------------------------------------
# 5. Ledger + recurrence -> generalization
# ---------------------------------------------------------------------------

def record_outcome(ws_dir, rec, root_cause, change_summary, verified=False,
                   now=None):
    """Append the resolved correction to the append-only ledger."""
    event = {
        "ts": graph.iso(now),
        "correction_id": rec.get("id"),
        "connector": rec.get("connector_hint"),
        "root_cause": root_cause,
        "signature": "%s:%s" % (rec.get("connector_hint"), root_cause),
        "change": change_summary,
        "verified": bool(verified),
        "text": rec.get("text", "")[:300],
    }
    os.makedirs(ws_dir, exist_ok=True)
    with open(os.path.join(ws_dir, LEDGER_FILE), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def recurring(ws_dir, min_count=2):
    """Signatures (``<connector>:<root_cause>``) seen >= min_count times.

    A recurring signature means the earlier fix was too narrow — the cos-learn
    command escalates it into a systemic change (and a lessons-learned entry).
    """
    counts = {}
    for ev in _read_jsonl(os.path.join(ws_dir, LEDGER_FILE)):
        sig = ev.get("signature")
        if sig:
            counts[sig] = counts.get(sig, 0) + 1
    return sorted(s for s, c in counts.items() if c >= min_count)


# ---------------------------------------------------------------------------
# 4. Guardrails + snapshot rollback for self-modification
# ---------------------------------------------------------------------------

# Relative to the template root. The approval-gating surface + this file.
GUARDRAIL_PATHS = [
    "commands/cos-approve.md",
    "commands/cos-approve-confirmed.md",
    "dashboard/audit.py",
    "dashboard/learning.py",
]
GUARDRAIL_BASENAMES = ["APPROVAL_POLICY.md"]


def is_change_allowed(template_root, path):
    """May the self-learning loop modify ``path``? False for anything outside
    the template root, any guardrail file, and any APPROVAL_POLICY.md."""
    root = os.path.realpath(template_root)
    target = os.path.realpath(path if os.path.isabs(path)
                              else os.path.join(root, path))
    if not (target == root or target.startswith(root + os.sep)):
        return False
    rel = os.path.relpath(target, root)
    if rel.replace(os.sep, "/") in GUARDRAIL_PATHS:
        return False
    if os.path.basename(target) in GUARDRAIL_BASENAMES:
        return False
    return True


def snapshot(ws_dir, paths, now=None):
    """Copy ``paths`` into a snapshot dir; returns a token for restore/discard."""
    token = "snap-" + graph.iso(now).replace(":", "").replace("-", "")
    sdir = os.path.join(ws_dir, SNAPSHOT_DIR, token)
    os.makedirs(sdir, exist_ok=True)
    manifest = []
    for i, p in enumerate(paths):
        dest = os.path.join(sdir, "%03d_%s" % (i, os.path.basename(p)))
        shutil.copy2(p, dest)
        manifest.append({"original": os.path.abspath(p), "copy": dest})
    with open(os.path.join(sdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return token


def restore(ws_dir, token):
    """Auto-revert: copy every snapshotted file back. Returns restored paths."""
    sdir = os.path.join(ws_dir, SNAPSHOT_DIR, token)
    with open(os.path.join(sdir, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    restored = []
    for item in manifest:
        shutil.copy2(item["copy"], item["original"])
        restored.append(item["original"])
    return restored


def discard(ws_dir, token):
    """Change passed its gates — drop nothing: keep the snapshot as history but
    mark it kept (snapshots are cheap and double as an audit trail)."""
    sdir = os.path.join(ws_dir, SNAPSHOT_DIR, token)
    marker = os.path.join(sdir, "KEPT")
    with open(marker, "w", encoding="utf-8") as f:
        f.write("change passed gates; snapshot retained for rollback history\n")
    return marker


# ---------------------------------------------------------------------------
# shared
# ---------------------------------------------------------------------------

def _read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


if __name__ == "__main__":
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else "."
    print("pending corrections: %d" % len(pending(ws)))
    for sig in recurring(ws):
        print("RECURRING", sig)
