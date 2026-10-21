#!/usr/bin/env python3
"""Bug fix to pull request, behind approval (stdlib only).

The flow has three steps, and only the last touches anything outside the
user's machine:

1. ``prepare(repo, slug)``: a git worktree on a new branch ``cos/fix-<slug>``,
   cut from the repo's current HEAD. The agent (``/cos-fix``) writes a test that
   reproduces the bug and the fix there. It never pushes.
2. ``finalize(...)``: commits what the agent left, runs the repo's test command
   itself (the agent's own claim that tests pass is not trusted), saves the diff,
   and appends an approval-queue entry of action type ``code_fix`` carrying the
   branch, the diff file and the test result. A fix whose tests fail is queued as
   ``failed``, visible but not approvable.
3. ``open_pr(entry, ws_dir)``: run only when the user approves that card. It
   pushes the branch and opens a pull request with ``gh pr create``. That is
   all it can do: there is no merge path here, and ``_run`` refuses any command
   that would merge, so a PR is never merged by the system.

Everything is deterministic code, so the step that leaves the machine runs no
model at all.
"""

from __future__ import annotations

import json
import os
import re
import subprocess

import graph

QUEUE_FILE = "approval-queue.md"
FIX_DIR = "fixes"
ACTION_TYPE = "code_fix"
BRANCH_PREFIX = "cos/fix-"
TEST_TAIL_LINES = 40
MAX_DIFF_BYTES = 200_000

# commands open_pr must never run, whatever an entry says
_FORBIDDEN = (("gh", "pr", "merge"), ("git", "merge"), ("gh", "api"))


class FixError(RuntimeError):
    pass


def _run(cmd, cwd, timeout=600, env=None):
    for bad in _FORBIDDEN:
        if tuple(cmd[:len(bad)]) == bad:
            raise FixError("refusing to run %s: the fix flow never merges" % " ".join(bad))
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=env)


def _git(cwd, *args, check=True):
    p = _run(["git", *args], cwd)
    if check and p.returncode != 0:
        raise FixError("git %s failed: %s" % (" ".join(args), (p.stderr or p.stdout).strip()))
    return p.stdout.strip()


def _slug(text):
    s = graph.slug(text)[:40].strip("-")
    if not s:
        raise FixError("empty slug")
    return s


def prepare(repo, slug, ws_dir):
    """Create the worktree and branch for one fix. Returns its paths."""
    slug = _slug(slug)
    repo = os.path.abspath(repo)
    _git(repo, "rev-parse", "--git-dir")
    base = _git(repo, "rev-parse", "HEAD")
    branch = BRANCH_PREFIX + slug
    tree = os.path.join(os.path.abspath(ws_dir), FIX_DIR, slug)
    if os.path.exists(tree):
        raise FixError("a fix worktree already exists at %s" % tree)
    os.makedirs(os.path.dirname(tree), exist_ok=True)
    _git(repo, "worktree", "add", "-b", branch, tree, base)
    return {"repo": repo, "slug": slug, "branch": branch, "base": base, "worktree": tree}


def run_tests(tree, test_cmd, timeout=900):
    """Run the repo's test command in the worktree. Returns (exit_code, tail)."""
    p = subprocess.run(test_cmd, cwd=tree, shell=True, capture_output=True,
                       text=True, timeout=timeout)
    out = (p.stdout + "\n" + p.stderr).strip().splitlines()
    return p.returncode, "\n".join(out[-TEST_TAIL_LINES:])


def _field(text):
    """One-line queue value: the queue is '- key: value' lines."""
    return " ".join(str(text).split())


def finalize(fix, test_cmd, title, body, task_id, ws_dir, base_branch="main",
             now=None):
    """Commit, test, save the diff and queue the approval card. Returns the
    entry dict. Raises FixError if the agent changed nothing."""
    tree, branch, base = fix["worktree"], fix["branch"], fix["base"]
    if _git(tree, "status", "--porcelain"):
        _git(tree, "add", "-A")
        _git(tree, "commit", "-q", "-m", title)
    if not _git(tree, "rev-list", "%s..HEAD" % base):
        raise FixError("no changes on %s: nothing to propose" % branch)
    diff = _git(tree, "diff", "%s...HEAD" % base)
    stat = _git(tree, "diff", "--stat", "%s...HEAD" % base).splitlines()
    code, tail = run_tests(tree, test_cmd)
    fixes = os.path.join(os.path.abspath(ws_dir), FIX_DIR)
    diff_file = os.path.join(fixes, fix["slug"] + ".diff")
    with open(diff_file, "w") as f:
        f.write(diff[:MAX_DIFF_BYTES])
    with open(os.path.join(fixes, fix["slug"] + ".tests.txt"), "w") as f:
        f.write(tail)
    entry = {
        "id": "fix-%s" % fix["slug"],
        "status": "pending" if code == 0 else "failed",
        "action_type": ACTION_TYPE,
        "priority": "medium",
        "drafted_by": "cos-fix",
        "created": graph.iso(now),
        "short_summary": _field("Open a PR: %s (%s)" % (title, stat[-1].strip() if stat else "")),
        "proposed_tool_call": _field(
            "git push origin %s; gh pr create --base %s --head %s --title %s"
            % (branch, base_branch, branch, json.dumps(title))),
        "repo": fix["repo"],
        "branch": branch,
        "base_branch": base_branch,
        "base_commit": base,
        "worktree": tree,
        "diff_file": diff_file,
        "test_command": _field(test_cmd),
        "test_exit": str(code),
        "test_summary": _field(tail.splitlines()[-1] if tail else ""),
        "pr_title": _field(title),
        "pr_body": _field(body),
        "task": task_id,
        "context": _field("Fix for task %s, on branch %s. Tests %s. Approving pushes the "
                          "branch and opens a pull request; it never merges."
                          % (task_id, branch, "pass" if code == 0 else "FAIL (not approvable)")),
    }
    if code != 0:
        entry["execution_result"] = _field("tests failed: " + entry["test_summary"])
    _append(ws_dir, entry)
    return entry


def _append(ws_dir, entry):
    path = os.path.join(ws_dir, QUEUE_FILE)
    with graph.file_lock(path):
        exists = os.path.exists(path)
        with open(path, "a") as f:
            if not exists:
                f.write("# Approval queue\n\n---\n")
            f.write("\n### %s\n" % entry["id"])
            for k, v in entry.items():
                if k != "id":
                    f.write("- %s: %s\n" % (k, v))


def read_diff(entry, limit=20000):
    try:
        with open(entry.get("diff_file", "")) as f:
            return f.read(limit)
    except OSError:
        return ""


def open_pr(entry, gh="gh", remote="origin"):
    """Push the fix branch and open the pull request. Returns the PR URL.

    Re-checks before acting: only a pending code_fix entry whose tests passed,
    whose branch is a cos/fix- branch, and whose branch head is still a
    descendant of the commit it was cut from."""
    if entry.get("action_type") != ACTION_TYPE:
        raise FixError("not a code fix entry")
    if entry.get("status") != "pending":
        raise FixError("entry is %s, not pending" % entry.get("status"))
    if entry.get("test_exit") != "0":
        raise FixError("tests did not pass; this fix cannot be approved")
    branch = entry.get("branch", "")
    if not branch.startswith(BRANCH_PREFIX) or not re.match(r"^[\w./-]+$", branch):
        raise FixError("unexpected branch name %r" % branch)
    tree = entry["worktree"]
    p = _run(["git", "merge-base", "--is-ancestor", entry["base_commit"], branch], tree)
    if p.returncode != 0:
        raise FixError("branch %s no longer descends from its base commit" % branch)
    # push from the main checkout: a remote given as a relative path is
    # relative to it, not to the worktree (the branch is shared by both)
    _git(entry["repo"], "push", "-u", remote, branch)
    p = _run([gh, "pr", "create", "--base", entry.get("base_branch", "main"),
              "--head", branch, "--title", entry.get("pr_title", branch),
              "--body", (entry.get("pr_body", "") + "\n\nTests: `%s` passed. "
                         "Prepared by the chief-of-staff fix flow and approved by the "
                         "user; the system never merges." % entry.get("test_command", ""))],
             tree)
    if p.returncode != 0:
        raise FixError("gh pr create failed: %s" % (p.stderr or p.stdout).strip())
    urls = re.findall(r"https?://\S+", p.stdout)
    return urls[-1] if urls else p.stdout.strip()
