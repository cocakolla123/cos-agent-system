#!/bin/bash
# Starts the local CoS dashboard. Localhost only (127.0.0.1:8765). Run manually whenever you
# want to check it; not an always-on daemon — stop with Ctrl+C.
#
# Self-contained: with no arguments, reads config.json/writes workspace data inside this same
# dashboard/ directory. Pass --config/--workspace to point at a different deployment's files.
#
# Requires: Python >= 3.12 (server.py uses 3.12+ f-string syntax — see lessons-learned.md
# 2026-07-16) and the `claude` CLI (on PATH, or set CLAUDE_BIN / config `claude_bin`) for the
# subprocess-backed buttons (Approve & send, Poll now, Check now, chat).
cd "$(dirname "$0")"

# Fail fast with a clear message instead of a cryptic SyntaxError on old python3.
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  ver=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
  echo "error: this dashboard requires Python >= 3.12; your python3 is $ver." >&2
  echo "hint: install a newer python (e.g. 'brew install python') or run with an explicit" >&2
  echo "      newer interpreter: /path/to/python3.12 server.py" >&2
  exit 1
fi

if [ -z "${CLAUDE_BIN:-}" ] && ! command -v claude >/dev/null 2>&1; then
  echo "warning: 'claude' not found on PATH and CLAUDE_BIN is unset — the dashboard will" >&2
  echo "         render, but every button that shells out (Approve, Poll now, Check now," >&2
  echo "         chat, research) will fail. Set CLAUDE_BIN=/path/to/claude to fix." >&2
fi

exec python3 server.py "$@"
