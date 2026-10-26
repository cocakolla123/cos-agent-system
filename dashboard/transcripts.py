#!/usr/bin/env python3
"""Meeting transcripts and local files, turned into short plain text without a model.

A one-hour call saved as a caption file is mostly timestamps and cue numbers.
``clean`` keeps only who said what, joins a speaker's consecutive lines into
one turn, and drops filler, which roughly halves what a model has to read.

Formats it reads:
  WebVTT     Zoom cloud transcripts, Teams (<v Name>...</v>), Google Meet exports
  SubRip     .srt caption files
  Zoom local meeting_saved_closed_caption.txt ("[Name] 14:05:12" then the text,
             or the older "14:05:12 From Name : text")
  plain      "Name: text" or "Name  0:01" followed by the text (Otter, Fathom...)
  .docx      Teams and Word transcripts (text pulled from the zip, no library)
"""

from __future__ import annotations

import os
import re
import zipfile

TEXT_EXT = {".txt", ".md", ".vtt", ".srt", ".docx", ".csv", ".json", ".rtf"}
NAME_HINT = re.compile(r"transcript|caption|closed_caption|meeting|minutes|recording|notes", re.I)
TS = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?"
CUE = re.compile(r"^\s*(?:\d+\s*)?$|^\s*%s\s*-->\s*%s.*$" % (TS, TS))
VOICE = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>|$)", re.S)
BRACKET = re.compile(r"^\[(.+?)\]\s*%s\s*$" % TS)
OLD_ZOOM = re.compile(r"^%s\s+From\s+(.+?)\s*:\s*(.*)$" % TS)
NAME_TS = re.compile(r"^([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3})\s{1,}%s\s*$" % TS)
SAID = re.compile(r"^([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3})\s*:\s+(.+)$")
FILLER = re.compile(r"\b(?:um+|uh+|erm|hmm+)\b,?\s*", re.I)


def read_text(path, limit=2_000_000):
    """The text of a local file, or "" when it is not text we can read."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
            xml = re.sub(r"</w:p>", "\n", xml)
            return re.sub(r"<[^>]+>", "", xml)[:limit]
        with open(path, "rb") as f:
            raw = f.read(limit)
    except (OSError, KeyError, zipfile.BadZipFile):
        return ""
    if b"\x00" in raw[:4096]:
        return ""
    return raw.decode("utf-8", "replace")


def turns(text):
    """[(speaker, words)] in order; speaker is "" when the file names nobody."""
    out = []
    speaker = ""
    lines = text.replace("\r", "").split("\n")
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        lines = lines[1:]
    for line in lines:
        s = line.strip()
        if not s or CUE.match(s) or s.upper().startswith(("NOTE", "STYLE", "WEBVTT")):
            continue
        m = VOICE.search(s)
        if m:
            out.append((m.group(1).strip(), re.sub(r"<[^>]+>", "", m.group(2)).strip()))
            continue
        m = BRACKET.match(s) or NAME_TS.match(s)
        if m:
            speaker = m.group(1).strip()
            continue
        m = OLD_ZOOM.match(s)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip()))
            continue
        m = SAID.match(s)
        if m and len(m.group(1)) <= 40:
            out.append((m.group(1).strip(), m.group(2).strip()))
            continue
        out.append((speaker, re.sub(r"<[^>]+>", "", s)))
    return out


def clean(text):
    """Who said what, one turn per line ("Name: words"), filler removed."""
    merged = []
    for sp, words in turns(text):
        words = " ".join(FILLER.sub("", words).split())
        if not words:
            continue
        if merged and merged[-1][0] == sp:
            merged[-1][1].append(words)
        else:
            merged.append((sp, [words]))
    return "\n".join(("%s: %s" % (sp, " ".join(w))) if sp else " ".join(w) for sp, w in merged)


def speakers(text):
    seen = []
    for sp, _ in turns(text):
        if sp and sp not in seen:
            seen.append(sp)
    return seen


def looks_like_transcript(path, text):
    """A caption or transcript file: by its type or name, or by its shape
    (many timestamped or "Name:" speaker lines)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".vtt", ".srt"):
        return True
    head = text[:20000]
    timed = len(re.findall(r"(?m)^\s*%s\s*-->|^\[.+?\]\s*%s\s*$|^%s\s+From\s" % (TS, TS, TS), head))
    said = sum(1 for sp, _ in turns(head) if sp)
    if NAME_HINT.search(os.path.basename(path)) and (timed >= 3 or said >= 6):
        return True
    return timed >= 10 or (said >= 20 and len(speakers(head)) >= 2)
