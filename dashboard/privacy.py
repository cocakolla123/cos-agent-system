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
    low = text.lower()
    for tok in tokens:
        idx = low.find(tok)
        if idx != -1:
            out.append(("token:" + tok, text[max(0, idx - 20):idx + len(tok) + 20]))
    if is_markdown:
        for m in MONEY_RE.finditer(text):
            out.append(("money", m.group(0)))
    return out


def scan_tree(root, tokens):
    """Walk ``root`` and return {relpath: [violations]} (empty dict = clean)."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(SCAN_EXTENSIONS):
                continue
            path = os.path.join(dirpath, fname)
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            viols = scan_text(text, tokens, is_markdown=fname.endswith(".md"))
            if viols:
                found[os.path.relpath(path, root)] = viols
    return found


def report(found, limit=20):
    lines = []
    for path in sorted(found):
        for kind, excerpt in found[path][:3]:
            lines.append("%s: %s — %r" % (path, kind, excerpt.strip()[:60]))
            if len(lines) >= limit:
                return "\n".join(lines + ["… (truncated)"])
    return "\n".join(lines)
