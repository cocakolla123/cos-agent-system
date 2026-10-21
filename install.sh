#!/usr/bin/env bash
# One-command install for the CoS agent system. No sudo, no system changes
# beyond ~/.claude/commands/global/ and (optionally) a git init in this folder.
#
#   In a checkout:    ./install.sh [--start]
#   From nothing:     curl -fsSL https://raw.githubusercontent.com/YOU/YOUR-REPO/main/install.sh \
#                       | bash -s -- --repo https://github.com/YOU/YOUR-REPO.git [--start]
#
# What it does: finds a Python >= 3.12, checks for the claude CLI, installs
# the /cos-* commands + /setup into ~/.claude/commands/global/ (backing up
# anything it would overwrite), makes this folder a git repo (the learn loop
# self-commits its kept improvements), and tells you the two commands that
# start everything. --start also launches the dashboard right away.
set -euo pipefail

REPO_URL=""
START=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)  REPO_URL="$2"; shift 2 ;;
    --start) START=1; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

say()  { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

# -- 1. resolve a checkout ---------------------------------------------------
SELF="${BASH_SOURCE[0]:-}"
if [ -n "$SELF" ] && [ -f "$(dirname "$SELF")/commands/cos.md" ]; then
  ROOT="$(cd "$(dirname "$SELF")" && pwd)"
elif [ -n "$REPO_URL" ]; then
  ROOT="$HOME/cos-agent-system"
  if [ ! -d "$ROOT/.git" ]; then
    command -v git >/dev/null 2>&1 || fail "git is required to clone (xcode-select --install)"
    say "cloning into $ROOT ..."
    git clone --quiet "$REPO_URL" "$ROOT"
  fi
else
  fail "run this from a checkout of the repo, or pass --repo <your fork's git url>"
fi
say "installing from: $ROOT"

# -- 2. python >= 3.12 (server.py's floor; everything else runs on 3.9+) -----
PY=""
for c in python3.14 python3.13 python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1 &&
     "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
[ -n "$PY" ] || fail "no Python >= 3.12 found — install one (e.g. 'brew install python') and re-run"
say "python: $PY ($("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])'))"

# -- 3. claude CLI ------------------------------------------------------------
CLAUDE_BIN="${CLAUDE_BIN:-}"
if [ -z "$CLAUDE_BIN" ]; then
  if command -v claude >/dev/null 2>&1; then CLAUDE_BIN="$(command -v claude)";
  elif [ -x "$HOME/.local/bin/claude" ]; then CLAUDE_BIN="$HOME/.local/bin/claude"; fi
fi
if [ -n "$CLAUDE_BIN" ]; then
  say "claude CLI: $CLAUDE_BIN ($("$CLAUDE_BIN" --version 2>/dev/null | head -1))"
else
  echo "warning: the 'claude' CLI was not found. Install it first:" >&2
  echo "    curl -fsSL https://claude.ai/install.sh | bash" >&2
  echo "then re-run this installer. Continuing — the dashboard will render," >&2
  echo "but research/chat/poll buttons need the CLI." >&2
fi

# -- 4. install the commands --------------------------------------------------
DEST="$HOME/.claude/commands/global"
mkdir -p "$DEST"
INSTALLED=0
for f in "$ROOT"/commands/*.md; do
  base="$(basename "$f")"
  if [ -f "$DEST/$base" ] && ! cmp -s "$f" "$DEST/$base"; then
    cp "$DEST/$base" "$DEST/$base.bak"   # never clobber silently
    echo "  (existing $base differed — backed up to $base.bak)"
  fi
  cp "$f" "$DEST/$base"
  INSTALLED=$((INSTALLED + 1))
done
say "installed $INSTALLED commands to $DEST (use as /global:<name>)"

# -- 5. git repo for the self-learning loop's local commits -------------------
if command -v git >/dev/null 2>&1 && ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" init --quiet
  git -C "$ROOT" add -A
  git -C "$ROOT" commit --quiet -m "cos-agent-system: initial install" || true
  say "initialized a local git repo (the learn loop commits its kept self-changes here)"
fi

chmod +x "$ROOT/dashboard/serve.sh" "$ROOT/dashboard/poll-tick.sh" 2>/dev/null || true

# -- 6. done -------------------------------------------------------------------
say ""
say "Install complete. Two steps from here:"
echo "  1. in Claude Code, from $ROOT:   /global:setup"
echo "     (discovers your connectors, builds your profile, generates your agents)"
echo "  2. start the dashboard:          cd $ROOT/dashboard && CLAUDE_BIN=${CLAUDE_BIN:-claude} $PY server.py"
echo
echo "Polling runs by itself while the dashboard is up (in-process ticker)."
echo "Optional: point the self-learning loop's publisher at YOUR OWN fork —"
echo "see the 'publish' block in dashboard/config.example.json."

if [ "$START" = "1" ]; then
  say "starting the dashboard (Ctrl+C to stop) ..."
  cd "$ROOT/dashboard"
  CLAUDE_BIN="${CLAUDE_BIN:-claude}" exec "$PY" server.py
fi
