#!/usr/bin/env python3
"""Privacy gate for publishing — machine enforcement of cos-learn.md's
"shared files stay generic" hard rule. Stdlib only, 3.9-compatible.

The rule existed as prose from the first deployment and the learn loop
violated it anyway (2026-10-03: ~180KB of personal narratives appended to the
shared lessons file; two older entries leaked real org names to the public
repo, cleaned by hand). Same lesson as ``research.window_audit``: an
instruction with nothing reading it is a comment, not a control. This module
is the thing that reads it — ``publish.py`` refuses to push a tree this scan
flags.

Three signal classes:

- **Deployment tokens** (`<workspace>/privacy-tokens.txt`, gitignored, one
  case-insensitive substring per line, ``#`` comments): the user's own names,
  employers, schools, counterparties. The committed template ships only the
  mechanism — every deployment seeds its own list, so the tokens themselves
  never enter the repo.
- **Real personal emails**: an address at a consumer mail provider whose
  local part isn't an obvious documentation placeholder. Synthetic fixtures
  use ``.example`` domains and docs use ``me@…``/``you@…`` — both pass.
- **Large dollar amounts** (markdown only): a real income/balance figure in a
  lesson narrative is personal; eval costs ($0.51) and small examples pass.
"""

from __future__ import annotations

import os
import re

TOKENS_FILENAME = "privacy-tokens.txt"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# API keys: Anthropic/OpenAI/OpenRouter ("sk-..."), Google ("AIza...").
# Long enough that test fixtures like "sk-test-123" do not trip it.
API_KEY_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{32,}|AIza[0-9A-Za-z_-]{35}|xox[abposr]-[A-Za-z0-9-]{20,}|"
                        r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|ATATT[A-Za-z0-9_=-]{40,})\b")
MONEY_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\$\s?\d{5,}")

REAL_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "live.com", "aol.com", "proton.me", "protonmail.com",
    "msn.com", "me.com",
}
PLACEHOLDER_LOCALS = {
    "me", "you", "user", "someone", "name", "test", "example", "alice",
    "bob", "jane", "john", "noreply", "no-reply",
}

SCAN_EXTENSIONS = (".md", ".py", ".json", ".sh", ".yml", ".yaml", ".txt")
SKIP_DIRS = {".git", "__pycache__", "node_modules"}


def load_tokens(workspace_dir):
    path = os.path.join(workspace_dir, TOKENS_FILENAME)
    tokens = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#"):
                tokens.append(line.lower())
    return tokens


def _email_violations(text):
    out = []
    for m in EMAIL_RE.finditer(text):
        addr = m.group(0)
        local, _, domain = addr.rpartition("@")
        domain = domain.lower()
        if domain.endswith(".example") or domain.startswith("example."):
            continue
        if domain in REAL_PROVIDERS and local.lower() not in PLACEHOLDER_LOCALS:
            out.append(("email", addr))
    return out


def scan_text(text, tokens, is_markdown=False):
    """Return [(kind, excerpt), ...] for one file's content."""
    out = _email_violations(text)
    for m in API_KEY_RE.finditer(text):
        out.append(("api key", m.group(0)[:8] + "…"))
    low = text.lower()
    for tok in tokens:
        idx = low.find(tok)
        if idx != -1:
            out.append(("token:" + tok, text[max(0, idx - 20):idx + len(tok) + 20]))
    if is_markdown:
        for m in MONEY_RE.finditer(text):
            out.append(("money", m.group(0)))
    return out


# Fail closed: every file is scanned as text, whatever its name. A binary file
# is refused unless it is an image or a font; a file that cannot be read, or is
# too large to read, is refused too. (Before 2026-10-27 the scan read only seven
# extensions and silently passed everything else, .jsonl and .html included.)
SAFE_BINARY = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp",
               ".woff", ".woff2", ".ttf", ".otf", ".eot")
MAX_SCAN_BYTES = 64 * 1024 * 1024


def scan_tree(root, tokens):
    """Walk ``root`` and return {relpath: [violations]} (empty dict = clean)."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, root)
            if os.path.islink(path):
                found[rel] = [("symlink", "links are not published")]
                continue
            try:
                if os.path.getsize(path) > MAX_SCAN_BYTES:
                    found[rel] = [("too large to scan", fname)]
                    continue
                with open(path, "rb") as f:
                    raw = f.read()
            except OSError as e:
                found[rel] = [("unreadable", str(e)[:60])]
                continue
            if b"\x00" in raw[:8192]:
                if not fname.lower().endswith(SAFE_BINARY):
                    found[rel] = [("binary file not scanned", fname)]
                continue
            viols = scan_text(raw.decode("utf-8", "replace"), tokens, is_markdown=fname.endswith(".md"))
            if viols:
                found[rel] = viols
    return found


def report(found, limit=20):
    lines = []
    for path in sorted(found):
        for kind, excerpt in found[path][:3]:
            lines.append("%s: %s — %r" % (path, kind, excerpt.strip()[:60]))
            if len(lines) >= limit:
                return "\n".join(lines + ["… (truncated)"])
    return "\n".join(lines)


# ---------------------------------------------------------------- local data controls
#
# Everything below is about the data on THIS machine: which files hold account
# content, that only the owner can read them, how long they are kept, and how
# to see or delete them. PRIVACY.md describes the same inventory for people.

# (pattern relative to the dashboard dir, what it holds, kept for)
DATA_FILES = [
    ("config.json", "your identity, connected accounts, tool grants", "until you delete it"),
    ("connections.json", "direct-connection credentials (app passwords, tokens)", "until you remove the connection"),
    ("secrets.json", "API keys for optional model providers", "until you remove the key"),
    ("models.json", "model and budget settings", "until you delete it"),
    ("fetch-state.json", "per-source sync bookmarks and recently delivered item ids", "rolling"),
    ("inbox/*.jsonl", "full text of items fetched by direct connections", "INBOX_DAYS days"),
    ("pending.jsonl", "fetched items waiting for a model read", "until read"),
    ("quarantine.jsonl", "model records rejected by the schema, with source ids", "until you delete it"),
    ("runs.jsonl", "per-run trace: ids, counts, fates, costs (no message text)", "about 5 MB, oldest half dropped"),
    ("usage.jsonl", "model cost and token counts per call", "until you delete it"),
    ("scan-state.json", "batch timing and failure backoff", "rolling"),
    ("*.log", "job output, which quotes account content", "trimmed to LOG_MAX_BYTES"),
    ("*.err", "job errors", "trimmed to LOG_MAX_BYTES"),
    ("chat-log.md", "dashboard chat transcript", "until you delete it"),
    ("chat-session.json", "dashboard chat session ids", "until you delete it"),
    ("workspace/graph/*.jsonl", "the knowledge graph: people, tasks, projects", "until you delete it"),
    ("workspace/approval-queue.md", "drafted actions waiting for approval", "until approved or rejected"),
    ("workspace/privacy-tokens.txt", "your own names and employers, used to block publishing them", "until you delete it"),
    ("workspace/*.jsonl", "corrections, audit log, research batches", "until you delete it"),
]

INBOX_DAYS = 30
LOG_MAX_BYTES = 5 * 1024 * 1024


def _data_paths(dashboard_dir):
    import glob
    seen = set()
    for pattern, _what, _kept in DATA_FILES:
        for p in glob.glob(os.path.join(dashboard_dir, pattern)):
            if os.path.isfile(p) and p not in seen:
                seen.add(p)
                yield p


def audit_permissions(dashboard_dir):
    """Data files and directories readable by anyone but the owner:
    [(path, octal mode)]. Empty = private."""
    bad = []
    dirs = {dashboard_dir, os.path.join(dashboard_dir, "inbox"),
            os.path.join(dashboard_dir, "workspace"), os.path.join(dashboard_dir, "workspace", "graph")}
    for p in list(_data_paths(dashboard_dir)) + sorted(d for d in dirs if os.path.isdir(d)):
        if os.path.islink(p):
            continue        # never reach through a link to a file outside the dashboard
        try:
            mode = os.lstat(p).st_mode & 0o777
        except OSError:
            continue
        if mode & 0o077 and not (os.path.isdir(p) and p == dashboard_dir):
            bad.append((p, oct(mode)))
    return bad


def fix_permissions(dashboard_dir):
    """Make every data file 0600 and data directory 0700. Returns what changed."""
    fixed = []
    for p, mode in audit_permissions(dashboard_dir):
        try:
            os.chmod(p, 0o700 if os.path.isdir(p) else 0o600)
            fixed.append((p, mode))
        except OSError:
            continue
    return fixed


def _trim(path, max_bytes):
    """Keep the newest ``max_bytes`` of a log, cut at a line boundary."""
    size = os.path.getsize(path)
    if size <= max_bytes:
        return False
    with open(path, "rb") as f:
        f.seek(size - max_bytes)
        tail = f.read()
    nl = tail.find(b"\n")
    tail = tail[nl + 1:] if nl >= 0 else tail
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(tail)
    os.replace(tmp, path)
    return True


def enforce_retention(dashboard_dir, inbox_days=INBOX_DAYS, log_max_bytes=LOG_MAX_BYTES, today=None):
    """Delete fetched-inbox days older than ``inbox_days`` and trim oversized
    logs. Returns {"inbox_deleted": [...], "logs_trimmed": [...]}."""
    import datetime as _dt
    import glob
    today = today or _dt.date.today()
    cut = (today - _dt.timedelta(days=inbox_days)).isoformat()
    out = {"inbox_deleted": [], "logs_trimmed": []}
    for p in sorted(glob.glob(os.path.join(dashboard_dir, "inbox", "*.jsonl"))):
        if os.path.basename(p)[:10] < cut:
            try:
                os.remove(p)
                out["inbox_deleted"].append(os.path.basename(p))
            except OSError:
                pass
    for pattern in ("*.log", "*.err"):
        for p in glob.glob(os.path.join(dashboard_dir, pattern)):
            try:
                if _trim(p, log_max_bytes):
                    out["logs_trimmed"].append(os.path.basename(p))
            except OSError:
                pass
    return out


def inventory(dashboard_dir):
    """Every data file present: [{path, holds, kept, bytes, mode}]."""
    import glob
    rows = []
    for pattern, what, kept in DATA_FILES:
        for p in sorted(glob.glob(os.path.join(dashboard_dir, pattern))):
            if os.path.isfile(p):
                st = os.stat(p)
                rows.append({"path": os.path.relpath(p, dashboard_dir), "holds": what, "kept": kept,
                             "bytes": st.st_size, "mode": oct(st.st_mode & 0o777)})
    return rows


def _main(argv):
    import json
    if len(argv) < 2 or argv[0] not in ("audit", "fix", "retention", "inventory"):
        print("usage: privacy.py audit|fix|retention|inventory <dashboard_dir>")
        return 2
    cmd, d = argv[0], argv[1]
    if cmd == "audit":
        bad = audit_permissions(d)
        for p, m in bad:
            print("%s  %s  (readable by others)" % (m, p))
        print("private" if not bad else "%d too open — run: privacy.py fix %s" % (len(bad), d))
        return 1 if bad else 0
    if cmd == "fix":
        for p, m in fix_permissions(d):
            print("fixed %s (was %s)" % (p, m))
        return 0
    if cmd == "retention":
        print(json.dumps(enforce_retention(d), indent=1))
        return 0
    for r in inventory(d):
        print("%-34s %8d B  %s  %s — kept %s" % (r["path"], r["bytes"], r["mode"], r["holds"], r["kept"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
