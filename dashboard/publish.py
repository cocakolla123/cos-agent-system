#!/usr/bin/env python3
"""Publish the template's generic improvements to the deployment's own repo.

This is the second half of the privacy contract the system runs on:

    personal data stays local, logic + lessons flow to GitHub.

The learn loop self-commits locally after every kept improvement; this module
carries those improvements to the user's remote **through a hard privacy
gate** (``privacy.scan_tree``) that refuses the push when anything personal
is about to leave the machine. Personal/runtime files never even reach the
staging tree (EXCLUDES below mirrors .gitignore), and the scan is the
backstop for anything new the excludes don't know about.

Usage:
    python3 dashboard/publish.py "message describing the improvement"
    python3 dashboard/publish.py --dry-run "message"   # stage+scan, no push

Configured per deployment in dashboard/config.json (never committed):

    "publish": {"repo_url": "https://github.com/<you>/<your-repo>.git",
                "branch": "main",
                "author_name": "<you>", "author_email": "<you@...>",
                "enabled": true}

Unconfigured deployments are a clean no-op — publishing is opt-in.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.dirname(HERE)

sys.path.insert(0, HERE)
import privacy  # noqa: E402

STAGE_DIR = os.path.join(HERE, "publish-stage")
LOG_PATH = os.path.join(HERE, "publish.log")

# Everything personal or runtime, kept out of the staging tree entirely.
# Mirrors .gitignore; the privacy scan is the backstop for anything new.
EXCLUDES = [
    ".git", ".DS_Store", "__pycache__",
    "dashboard/workspace", "dashboard/publish-stage",
    "dashboard/config.json", "dashboard/config.json.lock",
    "dashboard/poll-config.json", "dashboard/poll-last-run.json",
    "dashboard/poll-last-completed.json", "dashboard/poll-log.md",
    "dashboard/launchd-poll.log", "dashboard/launchd-poll.err",
    "dashboard/.setup-complete", "dashboard/server.log",
    "dashboard/chat-log.md", "dashboard/chat-session.json",
    "dashboard/entry-chat-sessions.json", "dashboard/entry-chat-log.json",
    "dashboard/style-feedback-queue.md", "dashboard/account-status.json",
    "dashboard/auth-requests.json", "dashboard/accounts.log",
    "dashboard/learn.log", "dashboard/research.log", "dashboard/publish.log",
    # bring-your-own-model settings: keys and chat history never leave this machine
    "dashboard/secrets.json", "dashboard/models.json", "dashboard/api-chat-history.json",
    "dashboard/usage.jsonl", "dashboard/poll-quiet.json",
    "tasks",
]


def _log(msg):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


def _run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                          text=True, timeout=300)


def load_publish_config(config_path=None):
    path = config_path or os.path.join(HERE, "config.json")
    try:
        cfg = json.load(open(path))
    except (OSError, ValueError):
        return None, "personal"
    ws = cfg.get("workspace_dir") or os.path.join(HERE, "workspace")
    if not os.path.isabs(ws):
        ws = os.path.join(HERE, ws)
    return cfg.get("publish") or None, ws


def publish(message, config_path=None, template_root=None, dry_run=False):
    """Stage → privacy-scan → commit → push. Returns (ok, detail)."""
    root = template_root or TEMPLATE_ROOT
    pub, workspace_dir = load_publish_config(config_path)
    if not pub or not pub.get("repo_url") or not pub.get("enabled", True):
        return False, "publishing not configured (dashboard/config.json 'publish')"
    if not message or not message.strip():
        return False, "a commit message is required"
    branch = pub.get("branch", "main")

    # 1. stage clone (persistent, survives restarts)
    if not os.path.isdir(os.path.join(STAGE_DIR, ".git")):
        r = _run(["git", "clone", "--branch", branch, pub["repo_url"],
                  STAGE_DIR])
        if r.returncode != 0:
            return False, "clone failed: " + (r.stderr or "")[-300:]
    else:
        _run(["git", "fetch", "origin", branch], cwd=STAGE_DIR)
        _run(["git", "reset", "--hard", "origin/" + branch], cwd=STAGE_DIR)
        _run(["git", "clean", "-fd"], cwd=STAGE_DIR)

    # 2. mirror the template, minus personal/runtime files
    rsync = ["rsync", "-a", "--delete"]
    for e in EXCLUDES:
        rsync += ["--exclude", e]
    rsync += [root.rstrip("/") + "/", STAGE_DIR.rstrip("/") + "/"]
    r = _run(rsync)
    if r.returncode != 0:
        return False, "rsync failed: " + (r.stderr or "")[-300:]

    # 3. the gate: nothing personal leaves the machine
    tokens = privacy.load_tokens(workspace_dir)
    found = privacy.scan_tree(STAGE_DIR, tokens)
    if found:
        detail = privacy.report(found)
        _log("PUBLISH BLOCKED by privacy scan:\n" + detail)
        return False, ("privacy scan blocked the push — anonymize these and "
                       "retry (dashboard/publish.log has the full list):\n"
                       + detail)
    if not tokens:
        _log("note: %s/%s is empty — the scan ran on built-in rules only"
             % (workspace_dir, privacy.TOKENS_FILENAME))

    # 4. commit + push
    _run(["git", "add", "-A"], cwd=STAGE_DIR)
    if _run(["git", "diff", "--cached", "--quiet"],
            cwd=STAGE_DIR).returncode == 0:
        return True, "nothing to publish — remote already matches"
    if dry_run:
        stat = _run(["git", "diff", "--cached", "--stat"], cwd=STAGE_DIR)
        return True, "dry run — would publish:\n" + stat.stdout[-1500:]
    env = dict(os.environ)
    for k in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        if pub.get("author_name"):
            env[k] = pub["author_name"]
    for k in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        if pub.get("author_email"):
            env[k] = pub["author_email"]
    r = _run(["git", "commit", "-m", message.strip()], cwd=STAGE_DIR, env=env)
    if r.returncode != 0:
        return False, "commit failed: " + (r.stderr or r.stdout)[-300:]
    r = _run(["git", "push", "origin", branch], cwd=STAGE_DIR)
    if r.returncode != 0:
        return False, "push failed: " + (r.stderr or "")[-300:]
    sha = _run(["git", "rev-parse", "--short", "HEAD"],
               cwd=STAGE_DIR).stdout.strip()
    _log("published %s: %s" % (sha, message.strip().splitlines()[0]))
    try:
        import audit
        audit.record(workspace_dir, "publish:" + sha, "pushed",
                     actor="publish", detail=message.strip()[:200])
    except Exception:
        pass
    return True, "published " + sha


def main():
    args = [a for a in sys.argv[1:]]
    dry = "--dry-run" in args
    if dry:
        args.remove("--dry-run")
    if not args:
        print("usage: publish.py [--dry-run] \"commit message\"")
        raise SystemExit(2)
    ok, detail = publish(args[0], dry_run=dry)
    print(detail)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
