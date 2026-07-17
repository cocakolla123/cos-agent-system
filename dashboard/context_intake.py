#!/usr/bin/env python3
"""AI OS startup context intake (V2.3, milestone M11). Stdlib only.

Before the system researches anything or generates agents, the dashboard offers
the user a chance to seed it with context — pasted text or files (md / txt /
pdf / docx). Everything lands in ``<workspace>/context-inbox/``; `/setup` and
`/cos-research` read that inbox first and ingest it as **user-provided facts**
(highest-confidence source) that seed workspace inference and the knowledge
graph. Entirely optional: "Skip" records the choice and the popup never
auto-opens again (a small "Add context" button stays available forever —
context can be added at any time, not just at startup).

Files:
  <workspace>/context-inbox/           incoming context files
  <workspace>/context-inbox/processed/ moved here once research ingested them
  <workspace>/context-intake.json      {choice: provided|skipped, ts}
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re

import graph

INBOX_DIR = "context-inbox"
PROCESSED_DIR = "processed"
CHOICE_FILE = "context-intake.json"

ALLOWED_EXTENSIONS = (".md", ".txt", ".pdf", ".docx")
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB — plenty for context docs

# user-provided context is the most trustworthy source in the graph
USER_CONTEXT_SOURCE = "user-context"
USER_CONTEXT_CONFIDENCE = 0.95


def inbox_dir(ws_dir):
    return os.path.join(ws_dir, INBOX_DIR)


# ---------------------------------------------------------------------------
# Saving context
# ---------------------------------------------------------------------------

def save_text(ws_dir, text, now=None):
    """Save pasted text as a markdown file in the inbox. Returns the path."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty context text")
    d = inbox_dir(ws_dir)
    os.makedirs(d, exist_ok=True)
    stamp = graph.iso(now).replace(":", "").replace("-", "")
    path = os.path.join(d, "pasted-%s.md" % stamp)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    return path


def save_file(ws_dir, filename, data_b64, now=None):
    """Save an uploaded file (sent as base64 by the dashboard JS).

    Validates extension (md/txt/pdf/docx), size, and sanitizes the filename —
    path components are stripped so an uploaded name can never escape the
    inbox. Returns the saved path.
    """
    name = sanitize_filename(filename)
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("unsupported file type '%s' — allowed: %s" %
                         (ext or filename, ", ".join(ALLOWED_EXTENSIONS)))
    try:
        blob = base64.b64decode(data_b64 or "", validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("invalid file data (expected base64)")
    if not blob:
        raise ValueError("empty file")
    if len(blob) > MAX_FILE_BYTES:
        raise ValueError("file too large (%.1f MB; max %d MB)" %
                         (len(blob) / 1048576.0, MAX_FILE_BYTES // 1048576))
    d = inbox_dir(ws_dir)
    os.makedirs(d, exist_ok=True)
    stamp = graph.iso(now).replace(":", "").replace("-", "")
    path = os.path.join(d, "%s-%s%s" % (
        os.path.splitext(name)[0][:60] or "context", stamp, ext))
    with open(path, "wb") as f:
        f.write(blob)
    return path


_FILENAME_BAD = re.compile(r"[^A-Za-z0-9._ -]")


def sanitize_filename(filename):
    """Basename only, safe characters only — uploads can't traverse paths."""
    base = os.path.basename(str(filename or "").replace("\\", "/"))
    base = _FILENAME_BAD.sub("_", base).strip(" .") or "context"
    return base


# ---------------------------------------------------------------------------
# Listing + processing
# ---------------------------------------------------------------------------

def pending_files(ws_dir):
    """Context files research hasn't ingested yet (sorted)."""
    d = inbox_dir(ws_dir)
    if not os.path.isdir(d):
        return []
    return sorted(
        os.path.join(d, n) for n in os.listdir(d)
        if os.path.isfile(os.path.join(d, n))
        and os.path.splitext(n)[1].lower() in ALLOWED_EXTENSIONS)


def mark_processed(ws_dir, path):
    """Move an ingested file into processed/ (kept, never deleted)."""
    pdir = os.path.join(inbox_dir(ws_dir), PROCESSED_DIR)
    os.makedirs(pdir, exist_ok=True)
    dest = os.path.join(pdir, os.path.basename(path))
    if os.path.exists(dest):  # same name re-uploaded — keep both
        root, ext = os.path.splitext(dest)
        i = 1
        while os.path.exists("%s.%d%s" % (root, i, ext)):
            i += 1
        dest = "%s.%d%s" % (root, i, ext)
    os.replace(path, dest)
    return dest


# ---------------------------------------------------------------------------
# The startup offer (popup gating)
# ---------------------------------------------------------------------------

def record_choice(ws_dir, choice, now=None):
    """Record the user's startup decision: provided | skipped."""
    if choice not in ("provided", "skipped"):
        raise ValueError("choice must be 'provided' or 'skipped'")
    os.makedirs(ws_dir, exist_ok=True)
    path = os.path.join(ws_dir, CHOICE_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"choice": choice, "ts": graph.iso(now)}, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def get_choice(ws_dir):
    try:
        with open(os.path.join(ws_dir, CHOICE_FILE), "r", encoding="utf-8") as f:
            return json.load(f).get("choice")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def should_offer(ws_dir, graph_empty):
    """Auto-open the startup popup? Only on a fresh deployment (empty graph)
    where the user hasn't already provided or skipped."""
    return bool(graph_empty) and get_choice(ws_dir) is None


if __name__ == "__main__":
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else "."
    print("choice:", get_choice(ws))
    for p in pending_files(ws):
        print("pending:", p)
