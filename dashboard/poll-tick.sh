#!/bin/bash
# Fired periodically by a scheduler (launchd, cron, etc.) — pure bash/jq, effectively free —
# unless at least one connector's configured interval has elapsed AND its day/time window is
# open, in which case it shells into `claude -p /global:cos-poll --scope=<due>` for just the
# due connectors. Self-contained: every path defaults relative to this script's own directory,
# never a specific person's home-dir convention. See ../PLAN.md.
#
# Usage: poll-tick.sh [dashboard_dir]
#   dashboard_dir defaults to this script's own directory (where config.json/poll-config.json/
#   poll-last-run.json live). Override for a deployment whose data lives elsewhere.
#
# CLAUDE_BIN env var overrides the `claude` binary path (default: `claude` via PATH). Set this
# explicitly in your scheduler's environment if it runs with a minimal PATH that doesn't
# include wherever `claude` is installed — a launchd job's default environment often doesn't
# include /usr/local/bin, which breaks this silently otherwise (see PLAN.md lessons-learned).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASH_DIR="${1:-$SCRIPT_DIR}"
CFG="$DASH_DIR/poll-config.json"
MAIN_CFG="$DASH_DIR/config.json"
LAST_RUN="$DASH_DIR/poll-last-run.json"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

[ -f "$CFG" ] || exit 0   # no poll config yet (e.g. /setup hasn't run) — nothing to do
[ -f "$LAST_RUN" ] || echo '{}' > "$LAST_RUN"

TZ_NAME=$(jq -r '.timezone // "America/Los_Angeles"' "$CFG")
now_epoch=$(TZ="$TZ_NAME" date +%s)
now_day=$(TZ="$TZ_NAME" date +%a | tr '[:upper:]' '[:lower:]')   # mon/tue/.../sun
now_hm=$(TZ="$TZ_NAME" date +%H:%M)

# Connectors are whatever top-level keys /setup wrote into poll-config.json, minus "timezone" —
# not a hardcoded list, so this works for any connector set, not just slack/email/general.
connectors=$(jq -r 'keys[] | select(. != "timezone")' "$CFG")

due=()
while IFS= read -r connector; do
  [ -z "$connector" ] && continue
  interval_min=$(jq -r --arg c "$connector" '.[$c].interval_min // 15' "$CFG")
  days=$(jq -r --arg c "$connector" '.[$c].days // [] | join(",")' "$CFG")
  start=$(jq -r --arg c "$connector" '.[$c].start // "07:00"' "$CFG")
  end=$(jq -r --arg c "$connector" '.[$c].end // "19:00"' "$CFG")

  if [[ ",$days," != *",$now_day,"* ]]; then continue; fi
  if [[ "$now_hm" < "$start" || "$now_hm" > "$end" ]]; then continue; fi

  last=$(jq -r --arg c "$connector" '.[$c] // 0' "$LAST_RUN")
  elapsed_min=$(( (now_epoch - last) / 60 ))
  if [ "$elapsed_min" -ge "$interval_min" ]; then
    due+=("$connector")
  fi
done <<< "$connectors"

if [ ${#due[@]} -eq 0 ]; then
  exit 0
fi

scope=$(IFS=,; echo "${due[*]}")

# Record the attempt time before running, so a slow/failed run doesn't cause immediate re-fire.
for connector in "${due[@]}"; do
  tmp=$(mktemp)
  jq --arg c "$connector" --arg now "$now_epoch" '.[$c] = ($now | tonumber)' "$LAST_RUN" > "$tmp"
  mv "$tmp" "$LAST_RUN"
done

poll_tools=$(jq -r '.poll_tools // "Read,Edit,Agent"' "$MAIN_CFG" 2>/dev/null || echo "Read,Edit,Agent")

# M12: track attempted vs completed separately — the attempt time above stops
# immediate re-fires, but a timed-out/failed run must not look like a success.
COMPLETED="$DASH_DIR/poll-last-completed.json"
[ -f "$COMPLETED" ] || echo '{}' > "$COMPLETED"

if "$CLAUDE_BIN" -p "/global:cos-poll --scope=$scope" \
  --permission-mode dontAsk \
  --allowedTools "$poll_tools" \
  --output-format text \
  >> "$DASH_DIR/launchd-poll.log" 2>> "$DASH_DIR/launchd-poll.err"; then
  done_epoch=$(TZ="$TZ_NAME" date +%s)
  for connector in "${due[@]}"; do
    tmp=$(mktemp)
    jq --arg c "$connector" --arg now "$done_epoch" '.[$c] = ($now | tonumber)' "$COMPLETED" > "$tmp"
    mv "$tmp" "$COMPLETED"
  done
else
  echo "$(date '+%Y-%m-%dT%H:%M:%S') poll FAILED (scope=$scope, exit=$?)" >> "$DASH_DIR/launchd-poll.err"
fi
