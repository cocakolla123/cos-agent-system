#!/usr/bin/env python3
"""Bug fix to pull request, behind approval (stdlib only).

The flow has three steps, and only the last touches anything outside the
user's machine:

1. ``prepare(repo, slug)``: a git worktree on a new branch ``cos/fix-<slug>``,
   cut from the repo's current HEAD. The agent (``/cos-fix``) writes a test that
   reproduces the bug and the fix there. It never pushes.
2. ``finalize(...)``: commits what the agent left, runs the repo's test command
   itself inside ``sandbox.py``'s OS sandbox (the agent's own claim that tests
   pass is not trusted, and the tests are untrusted code), saves the diff,
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
import shlex
import subprocess

import graph
import sandbox

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


# Git run against a fix worktree after untrusted code (the agent's edits, the
# repo's tests) has touched it. That code can rewrite the worktree's ``.git``
# file to point at a git dir it controls, whose config runs a command on the
# next ``git status`` (core.fsmonitor) outside the sandbox. So the git dir is
# looked up in the main repo, which neither can write, and passed explicitly,
# with fsmonitor and hooks off.
_HARDEN = ("-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null")


def _trusted_gitdir(repo, tree):
    """The worktree's real git dir, from the main repo's own records."""
    common = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    want = os.path.realpath(tree)
    wt = os.path.join(common, "worktrees")
    for name in sorted(os.listdir(wt)) if os.path.isdir(wt) else []:
        try:
            with open(os.path.join(wt, name, "gitdir")) as f:
                pointed = f.read().strip()
        except OSError:
            continue
        if os.path.realpath(os.path.dirname(pointed)) == want:
            return os.path.join(wt, name)
    raise FixError("no worktree record for %s in %s" % (tree, repo))


def _tgit(repo, tree, *args, check=True):
    gd = _trusted_gitdir(repo, tree)
    p = _run(["git", "--git-dir", gd, "--work-tree", tree, *_HARDEN, *args], tree)
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


SHELLS = {"sh", "bash", "zsh", "dash", "fish", "ksh", "csh", "tcsh", "cmd", "powershell", "pwsh"}


def test_argv(test_cmd):
    """The test command as a program and its arguments, run without a shell:
    no pipes, redirects, ';' or '&&', and no shell as the program. A suite that
    needs several steps belongs in a script in the repo, named here."""
    argv = shlex.split(test_cmd) if isinstance(test_cmd, str) else list(test_cmd)
    if not argv:
        raise FixError("empty test command")
    if os.path.basename(argv[0]).lower() in SHELLS:
        raise FixError("the test command may not be a shell; name the test runner or a script")
    return argv


# exit codes for a test run that did not complete: the card is queued as
# failed, with the reason as its summary
EXIT_NO_SANDBOX = 126
EXIT_TIMEOUT = 124


def run_tests(tree, test_cmd, timeout=900):
    """Run the repo's test command in the worktree. Returns (exit_code, tail).

    The tests are the repo's code plus the agent's patch, so they run inside
    ``sandbox.run``: no network, no reads outside the worktree and the
    toolchain (no home directory, no dashboard secrets), no writes outside the
    worktree and a temp dir, no credentials in the environment, and a hard
    timeout. Without an OS sandbox they are not run at all (EXIT_NO_SANDBOX)."""
    argv = test_argv(test_cmd)
    try:
        p = sandbox.run(argv, tree, timeout=timeout)
    except sandbox.SandboxUnavailable as exc:
        return EXIT_NO_SANDBOX, "tests not run: %s" % exc
    except sandbox.SandboxTimeout as exc:
        return EXIT_TIMEOUT, "tests %s" % exc
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
    repo = fix["repo"]
    g = lambda *a: _tgit(repo, tree, *a)  # noqa: E731
    if g("status", "--porcelain"):
        g("add", "-A")
        g("commit", "-q", "--no-verify", "-m", title)
    if not g("rev-list", "%s..HEAD" % base):
        raise FixError("no changes on %s: nothing to propose" % branch)
    diff = g("diff", "%s...HEAD" % base)
    stat = g("diff", "--stat", "%s...HEAD" % base).splitlines()
    tested = g("rev-parse", "HEAD")
    code, tail = run_tests(tree, test_cmd)
    if g("rev-parse", "HEAD") != tested or g("status", "--porcelain", "--untracked-files=no"):
        # the test run itself changed the branch or tracked files: what passed
        # is not what would be pushed
        code, tail = (code or 1), tail + "\nthe test run changed the branch or its files; not approvable"
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
        "tested_commit": tested,
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
    import approval
    path = os.path.join(ws_dir, QUEUE_FILE)
    with graph.file_lock(path):
        exists = os.path.exists(path)
        if exists:
            with open(path) as f:
                taken = approval.queue_ids(f.read())
        else:
            taken = set()
        # a re-run of the same slug must not share an id with an older card
        entry["id"] = approval.unique_id(entry["id"], taken)
        # every value on one line: a value carrying "\n- status: pending" would
        # otherwise add a field that overrides the real one
        entry = {k: _field(v) for k, v in entry.items()}
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
    gd = _trusted_gitdir(entry["repo"], tree)
    p = _run(["git", "--git-dir", gd, "--work-tree", tree, *_HARDEN,
              "merge-base", "--is-ancestor", entry["base_commit"], branch], tree)
    if p.returncode != 0:
        raise FixError("branch %s no longer descends from its base commit" % branch)
    # push exactly the commit whose tests passed, nothing added since
    tested = entry.get("tested_commit") or ""
    if not re.match(r"^[0-9a-f]{40}$", tested):
        raise FixError("no tested commit recorded; run the fix flow again")
    if _tgit(entry["repo"], tree, "rev-parse", "refs/heads/" + branch) != tested:
        raise FixError("branch %s has changed since its tests passed; run the fix flow again" % branch)
    # push from the main checkout: a remote given as a relative path is
    # relative to it, not to the worktree (the branch is shared by both)
    _git(entry["repo"], "push", "-u", remote, "%s:refs/heads/%s" % (tested, branch))
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
