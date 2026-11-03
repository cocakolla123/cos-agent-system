#!/usr/bin/env bash
# Install, update, roll back or uninstall the CoS agent system. No sudo; the
# only things written outside this folder are the /global:cos-* commands in
# ~/.claude/commands/global/ and a small record of what was installed there.
#
#   ./install.sh [--start]      install (or re-install) from this checkout
#   ./install.sh --update       fast-forward to the latest release, re-install
#                               the commands, roll back on its own if the new
#                               code does not compile
#   ./install.sh --rollback     return to the version before the last update
#   ./install.sh --uninstall    remove the commands it installed; your data
#                               (graph, queue, config) is left in place
#   ./install.sh --repo <git url> [--start]    clone into ~/cos-agent-system first
#
# Commands you have edited are never overwritten: the new version is written
# next to yours as <name>.md.new and the installer tells you so. Pass
# --force-commands to replace them anyway (yours is kept as <name>.md.bak).
set -euo pipefail

REPO_URL=""
START=0
MODE="install"
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)           REPO_URL="$2"; shift 2 ;;
    --start)          START=1; shift ;;
    --update)         MODE="update"; shift ;;
    --rollback)       MODE="rollback"; shift ;;
    --uninstall)      MODE="uninstall"; shift ;;
    --force-commands) FORCE=1; shift ;;
    -h|--help)        sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown flag: $1 (see --help)" >&2; exit 2 ;;
  esac
done

say()  { printf '\033[1m%s\033[0m\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
hash_of() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else sha256sum "$1" | cut -d' ' -f1; fi
}

[ -n "${HOME:-}" ] || fail "HOME is not set"
DEST="$HOME/.claude/commands/global"
MANIFEST="$DEST/.cos-manifest"      # "<sha256>  <file>" for each command we installed
STATE="$DEST/.cos-install"          # key=value: root, version, commit, prev_commit

state_get() { if [ -f "$STATE" ]; then sed -n "s/^$1=//p" "$STATE" | tail -1; fi; }
state_set() {
  mkdir -p "$DEST"
  local tmp="$STATE.tmp"
  { if [ -f "$STATE" ]; then grep -v "^$1=" "$STATE" || true; fi; echo "$1=$2"; } > "$tmp"
  mv "$tmp" "$STATE"
}
manifest_hash() { if [ -f "$MANIFEST" ]; then awk -v f="$1" '$2 == f { print $1 }' "$MANIFEST" | tail -1; fi; }

# -- resolve the checkout -----------------------------------------------------
SELF="${BASH_SOURCE[0]:-}"
if [ -n "$SELF" ] && [ -f "$(dirname "$SELF")/commands/cos.md" ]; then
  ROOT="$(cd "$(dirname "$SELF")" && pwd)"
elif [ -n "$REPO_URL" ]; then
  ROOT="$HOME/cos-agent-system"
  if [ ! -d "$ROOT/.git" ]; then
    command -v git >/dev/null 2>&1 || fail "git is required to clone (macOS: xcode-select --install)"
    say "cloning into $ROOT ..."
    git clone --quiet "$REPO_URL" "$ROOT"
  fi
else
  fail "run ./install.sh from inside the downloaded folder, or pass --repo <git url>"
fi
VERSION="$(cat "$ROOT/VERSION" 2>/dev/null || echo unknown)"

# -- dependencies: checked up front, all reported at once ----------------------
find_python() {
  if [ -n "${COS_PYTHON:-}" ]; then echo "$COS_PYTHON"; return; fi
  for c in python3.14 python3.13 python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
    if command -v "$c" >/dev/null 2>&1 &&
       "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
      command -v "$c"; return
    fi
  done
}
check_deps() {
  local missing=0
  PY="$(find_python || true)"
  if [ -n "$PY" ]; then
    echo "  ok       python $("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])') ($PY)"
  else
    echo "  MISSING  Python 3.12 or newer — the dashboard needs it. macOS: brew install python"; missing=1
  fi
  if command -v git >/dev/null 2>&1; then echo "  ok       git"
  else echo "  MISSING  git — needed for updates. macOS: xcode-select --install"; missing=1; fi
  if command -v jq >/dev/null 2>&1; then echo "  ok       jq"
  else echo "  MISSING  jq — every scheduled check uses it. macOS: brew install jq"; missing=1; fi
  CLAUDE_BIN="${CLAUDE_BIN:-}"
  if [ -z "$CLAUDE_BIN" ]; then
    if command -v claude >/dev/null 2>&1; then CLAUDE_BIN="$(command -v claude)"
    elif [ -x "$HOME/.local/bin/claude" ]; then CLAUDE_BIN="$HOME/.local/bin/claude"; fi
  fi
  if [ -n "$CLAUDE_BIN" ]; then echo "  ok       claude CLI ($CLAUDE_BIN)"
  else echo "  missing  claude CLI — research, polls and chat need it: curl -fsSL https://claude.ai/install.sh | bash"; fi
  if command -v rsync >/dev/null 2>&1; then echo "  ok       rsync"
  else echo "  missing  rsync — only needed to publish improvements (optional)"; fi
  return $missing
}

# -- commands: installed against a manifest, user edits never overwritten -----
install_commands() {
  mkdir -p "$DEST"
  local tmp="$MANIFEST.tmp" installed=0 updated=0 kept=0 removed=0 base f want have rec legacy=0
  # no manifest yet: an install made before manifests existed. Its copies were
  # always overwritten by the old installer, so keep doing that (with a .bak)
  # instead of mistaking every stale copy for a user edit and freezing it
  [ -f "$MANIFEST" ] || legacy=1
  : > "$tmp"
  for f in "$ROOT"/commands/*.md; do
    base="$(basename "$f")"
    want="$(hash_of "$f")"
    rec="$(manifest_hash "$base")"
    if [ ! -f "$DEST/$base" ]; then
      cp "$f" "$DEST/$base"; installed=$((installed + 1))
    else
      have="$(hash_of "$DEST/$base")"
      if [ "$have" = "$want" ]; then
        :
      elif [ -n "$rec" ] && [ "$have" = "$rec" ]; then
        cp "$f" "$DEST/$base"; updated=$((updated + 1))        # ours, unedited: safe to replace
      elif [ "$FORCE" = "1" ] || [ "$legacy" = "1" ]; then
        cp "$DEST/$base" "$DEST/$base.bak"; cp "$f" "$DEST/$base"; updated=$((updated + 1))
        echo "  replaced your edited $base (yours saved as $base.bak)"
      else
        cp "$f" "$DEST/$base.new"; kept=$((kept + 1))
        echo "  kept your edited $base — the new version is at $DEST/$base.new"
        if [ -n "$rec" ]; then echo "$rec  $base" >> "$tmp"; fi
        continue
      fi
    fi
    echo "$want  $base" >> "$tmp"
  done
  # commands removed upstream: delete the ones we installed and nobody edited
  if [ -f "$MANIFEST" ]; then
    while read -r rec base; do
      [ -n "$base" ] || continue
      [ -f "$ROOT/commands/$base" ] && continue
      if [ -f "$DEST/$base" ] && [ "$(hash_of "$DEST/$base")" = "$rec" ]; then
        rm -f "${DEST:?}/${base:?}" "${DEST:?}/${base:?}.new"; removed=$((removed + 1))
      elif [ -f "$DEST/$base" ]; then
        echo "  $base was removed upstream; left in place because you edited it"
      fi
    done < "$MANIFEST"
  fi
  mv "$tmp" "$MANIFEST"
  say "commands: $installed new, $updated updated, $kept kept as you edited them, $removed retired ($DEST)"
}

compiles() {
  "$PY" - "$ROOT" <<'PYCHECK'
import glob, os, sys
bad = []
for p in sorted(glob.glob(os.path.join(sys.argv[1], "dashboard", "*.py"))):
    try:
        with open(p, encoding="utf-8") as f:
            compile(f.read(), p, "exec")
    except (SyntaxError, ValueError) as e:
        bad.append("%s: %s" % (os.path.basename(p), e))
print("\n".join(bad))
sys.exit(1 if bad else 0)
PYCHECK
}

# ================================================================= uninstall
if [ "$MODE" = "uninstall" ]; then
  say "uninstalling the CoS commands from $DEST"
  removed=0
  if [ -f "$MANIFEST" ]; then
    while read -r rec base; do
      [ -n "$base" ] || continue
      if [ -f "$DEST/$base" ] && [ "$(hash_of "$DEST/$base")" = "$rec" ]; then
        rm -f "${DEST:?}/${base:?}" "${DEST:?}/${base:?}.new"; removed=$((removed + 1))
        if [ -f "$DEST/$base.bak" ]; then mv "$DEST/$base.bak" "$DEST/$base"; echo "  restored your earlier $base"; fi
      elif [ -f "$DEST/$base" ]; then
        rm -f "${DEST:?}/${base:?}.new"
        echo "  left $base in place: you edited it after install"
      fi
    done < "$MANIFEST"
  else
    warn "no install record found; nothing removed"
  fi
  rm -f "${MANIFEST:?}" "${STATE:?}"
  say "removed $removed commands."
  echo "Your data is untouched in $ROOT/dashboard (graph, approval queue, config, inbox)."
  echo "To delete it as well, run /global:cos-uninstall in Claude Code before this, or remove"
  echo "that folder yourself. See PRIVACY.md for what each file holds."
  exit 0
fi

say "CoS agent system $VERSION — checking dependencies"
DEPS_OK=1
check_deps || DEPS_OK=0

# ================================================================= rollback
if [ "$MODE" = "rollback" ]; then
  prev="$(state_get prev_commit)"
  [ -n "$prev" ] || fail "no earlier version recorded — nothing to roll back to"
  git -C "$ROOT" reset --quiet --keep "$prev" || fail "could not return to $prev (local edits in the way?)"
  install_commands
  state_set commit "$prev"; state_set prev_commit ""
  state_set version "$(cat "$ROOT/VERSION" 2>/dev/null || echo unknown)"
  say "rolled back to $(git -C "$ROOT" log -1 --format='%h %s'). Restart the dashboard to use it."
  exit 0
fi

# ================================================================= update
if [ "$MODE" = "update" ]; then
  [ "$DEPS_OK" = "1" ] || fail "install the missing dependencies above, then re-run --update"
  git -C "$ROOT" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1 || fail "this checkout has no upstream to update from"
  if [ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]; then
    fail "you have local edits to tracked files — commit or stash them, then re-run --update"
  fi
  before="$(git -C "$ROOT" rev-parse HEAD)"
  git -C "$ROOT" fetch --quiet
  if ! git -C "$ROOT" merge --quiet --ff-only '@{u}' 2>/dev/null; then
    fail "the update cannot fast-forward (this checkout has its own commits, e.g. from the learn loop). Nothing changed. Merge by hand: git -C $ROOT pull --rebase"
  fi
  after="$(git -C "$ROOT" rev-parse HEAD)"
  if [ "$before" = "$after" ]; then
    say "already up to date ($VERSION, $(git -C "$ROOT" log -1 --format=%h))"
    exit 0
  fi
  if ! errs="$(compiles)"; then
    git -C "$ROOT" reset --quiet --keep "$before"
    echo "$errs" >&2
    fail "the new version does not compile here — rolled back to $(git -C "$ROOT" log -1 --format=%h). Nothing else changed."
  fi
  install_commands
  state_set prev_commit "$before"; state_set commit "$after"
  state_set version "$(cat "$ROOT/VERSION" 2>/dev/null || echo unknown)"
  say "updated $(git -C "$ROOT" log -1 --format=%h "$before") → $(git -C "$ROOT" log -1 --format='%h %s')"
  echo "Restart the dashboard to use it. Undo with: ./install.sh --rollback"
  exit 0
fi

# ================================================================= install
[ "$DEPS_OK" = "1" ] || fail "install the missing dependencies above, then re-run ./install.sh"
install_commands

if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" init --quiet
  git -C "$ROOT" add -A
  git -C "$ROOT" commit --quiet -m "cos-agent-system: initial install" || true
  say "initialized a local git repo (the learn loop commits its kept self-changes here)"
fi
chmod +x "$ROOT/dashboard/serve.sh" "$ROOT/dashboard/poll-tick.sh" 2>/dev/null || true
state_set root "$ROOT"
state_set version "$VERSION"
state_set commit "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo none)"

say ""
say "Installed $VERSION. Two steps from here:"
echo "  1. in Claude Code, from $ROOT:   /global:setup"
echo "     (discovers your connectors, builds your profile, generates your agents)"
echo "  2. start the dashboard:          cd $ROOT/dashboard && CLAUDE_BIN=${CLAUDE_BIN:-claude} $PY server.py"
echo
echo "Polling runs by itself while the dashboard is up. Update later with ./install.sh --update;"
echo "remove with ./install.sh --uninstall. PRIVACY.md lists what stays on this machine."

if [ "$START" = "1" ]; then
  say "starting the dashboard (Ctrl+C to stop) ..."
  cd "$ROOT/dashboard"
  CLAUDE_BIN="${CLAUDE_BIN:-claude}" exec "$PY" server.py
fi
