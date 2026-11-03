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
umask 077   # the graph, inbox and logs it writes hold account content

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASH_DIR="${1:-$SCRIPT_DIR}"
CFG="$DASH_DIR/poll-config.json"
MAIN_CFG="$DASH_DIR/config.json"
LAST_RUN="$DASH_DIR/poll-last-run.json"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

[ -f "$CFG" ] || exit 0   # no poll config yet (e.g. /setup hasn't run) — nothing to do
[ -f "$LAST_RUN" ] || echo '{}' > "$LAST_RUN"
# Quiet streaks: a connector whose last checks found nothing new is checked
# less often (2x, then 4x its interval) until something turns up again.
QUIET="$DASH_DIR/poll-quiet.json"
[ -f "$QUIET" ] || echo '{}' > "$QUIET"

# Today's model budget (Settings → Usage) is a hard stop for scheduled work.
if python3 "$SCRIPT_DIR/usage.py" over-budget "$DASH_DIR" >> "$DASH_DIR/launchd-poll.log" 2>/dev/null; then
  exit 0
fi

TZ_NAME=$(jq -r '.timezone // "America/Los_Angeles"' "$CFG")
now_epoch=$(TZ="$TZ_NAME" date +%s)
now_day=$(TZ="$TZ_NAME" date +%a | tr '[:upper:]' '[:lower:]')   # mon/tue/.../sun
now_hm=$(TZ="$TZ_NAME" date +%H:%M)

# Connectors are whatever top-level keys /setup wrote into poll-config.json, minus "timezone" —
# not a hardcoded list, so this works for any connector set, not just slack/email/general.
# only object entries are connectors: any other top-level value would make the
# per-connector jq lookups below fail and, under set -e, end the tick silently
connectors=$(jq -r 'to_entries[] | select(.key != "timezone" and (.value | type) == "object") | .key' "$CFG")

# minutes since midnight from "H:MM" or "HH:MM" ("7:00" and "07:00" alike)
hm_min() { local h m; IFS=: read -r h m <<< "$1"; echo $(( 10#${h:-0} * 60 + 10#${m:-0} )); }
now_min=$(hm_min "$now_hm")

due=()
while IFS= read -r connector; do
  [ -z "$connector" ] && continue
  interval_min=$(jq -r --arg c "$connector" '.[$c].interval_min // 15' "$CFG")
  days=$(jq -r --arg c "$connector" '.[$c].days // ["mon","tue","wed","thu","fri","sat","sun"] | join(",")' "$CFG")
  start=$(jq -r --arg c "$connector" '.[$c].start // "07:00"' "$CFG")
  end=$(jq -r --arg c "$connector" '.[$c].end // "19:00"' "$CFG")

  if [[ ",$days," != *",$now_day,"* ]]; then continue; fi
  s_min=$(hm_min "$start"); e_min=$(hm_min "$end")
  # the end is exclusive (a 09:00-17:00 window stops at 17:00, not 17:59), and
  # a window that wraps midnight (22:00-06:00) is open on both sides of it
  if [ "$s_min" -le "$e_min" ]; then
    if [ "$now_min" -lt "$s_min" ] || [ "$now_min" -ge "$e_min" ]; then continue; fi
  else
    if [ "$now_min" -lt "$s_min" ] && [ "$now_min" -ge "$e_min" ]; then continue; fi
  fi

  last=$(jq -r --arg c "$connector" '.[$c] // 0' "$LAST_RUN")
  elapsed_min=$(( (now_epoch - last) / 60 ))
  streak=$(jq -r --arg c "$connector" '.[$c] // 0' "$QUIET")
  # "general" is the deep sweep that also re-checks open items; it keeps its pace
  if [ "$connector" != "general" ]; then
    if [ "$streak" -ge 6 ]; then interval_min=$(( interval_min * 4 ));
    elif [ "$streak" -ge 3 ]; then interval_min=$(( interval_min * 2 )); fi
  fi
  if [ "$elapsed_min" -ge "$interval_min" ]; then
    due+=("$connector")
  fi
done <<< "$connectors"

# "direct" is the check that needs no Claude Code (dashboard/poll_direct.py --scan): every few
# minutes it fetches only what is new from connections.json and sifts it without a model, which
# is free. What it keeps waits for the next batch (a few times a day) unless it is urgent, like a
# meeting transcript; only then is the model called. It never shares a run with the rest.
rest=()
for connector in ${due[@]+"${due[@]}"}; do
  if [ "$connector" = "direct" ]; then
    ws_dir=$(jq -r '.workspace_dir // empty' "$MAIN_CFG" 2>/dev/null || true)
    [ -n "$ws_dir" ] || ws_dir="$DASH_DIR/workspace"
    case "$ws_dir" in /*) ;; *) ws_dir="$DASH_DIR/$ws_dir" ;; esac
    tmp=$(mktemp)
    jq --arg now "$now_epoch" '.direct = ($now | tonumber)' "$LAST_RUN" > "$tmp" && mv "$tmp" "$LAST_RUN"
    if python3 "$SCRIPT_DIR/poll_direct.py" "$DASH_DIR" "$ws_dir/graph" --scan >> "$DASH_DIR/launchd-poll.log" 2>> "$DASH_DIR/launchd-poll.err"; then
      COMPLETED="$DASH_DIR/poll-last-completed.json"
      [ -f "$COMPLETED" ] || echo '{}' > "$COMPLETED"
      tmp=$(mktemp)
      jq --arg now "$(TZ="$TZ_NAME" date +%s)" '.direct = ($now | tonumber)' "$COMPLETED" > "$tmp" && mv "$tmp" "$COMPLETED"
    else
      echo "$(date '+%Y-%m-%dT%H:%M:%S') direct check FAILED" >> "$DASH_DIR/launchd-poll.err"
    fi
  else
    rest+=("$connector")
  fi
done
due=(${rest[@]+"${rest[@]}"})

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

# the Standard model chosen in Settings → Models (empty = the CLI default)
model_args=()
while IFS= read -r a; do [ -n "$a" ] && model_args+=("$a"); done < <(
  python3 "$SCRIPT_DIR/models.py" claude-args poll "$DASH_DIR" 2>/dev/null)

# usage.py sends only the poll's tools, caps the call and logs its cost
# run from a neutral folder: inside the repo, Claude Code loads the project's
# auto-memory into the call (see RUN_DIR in server.py); files come via --add-dir
RUN_DIR="${COS_RUN_DIR:-$HOME/.cos-agent/run}"
# the workspace the dashboard and approvals read: config's workspace_dir, as in
# the direct check above, not a hardcoded subfolder
POLL_WS=$(jq -r '.workspace_dir // empty' "$MAIN_CFG" 2>/dev/null || true)
[ -n "$POLL_WS" ] || POLL_WS="$DASH_DIR/workspace"
case "$POLL_WS" in /*) ;; *) POLL_WS="$DASH_DIR/$POLL_WS" ;; esac
mkdir -p "$RUN_DIR"
out_file=$(mktemp)
if (cd "$RUN_DIR" && python3 "$SCRIPT_DIR/usage.py" run poll "$DASH_DIR" -- \
  "$CLAUDE_BIN" -p "/global:cos-poll --scope=$scope --dashboard=$DASH_DIR --workspace=$POLL_WS" ${model_args[@]+"${model_args[@]}"} \
  --add-dir "$POLL_WS" \
  --add-dir "$DASH_DIR" \
  --disallowedTools "Edit(/$DASH_DIR/poll-last-completed.json),Edit(/$DASH_DIR/poll-last-run.json)" \
  --permission-mode dontAsk \
  --allowedTools "$poll_tools" \
  --output-format text \
  > "$out_file" 2>> "$DASH_DIR/launchd-poll.err"); then
  cat "$out_file" >> "$DASH_DIR/launchd-poll.log"
  for connector in "${due[@]}"; do
    tmp=$(mktemp)
    if grep -qiE "^[-* ]*$connector: nothing new" "$out_file"; then
      jq --arg c "$connector" '.[$c] = ((.[$c] // 0) + 1)' "$QUIET" > "$tmp"
    else
      jq --arg c "$connector" '.[$c] = 0' "$QUIET" > "$tmp"
    fi
    mv "$tmp" "$QUIET"
  done
  rm -f "$out_file"
  # the run's START, not its end: the next poll looks for mail since this
  # stamp, and mail that arrived while this run was working must not fall
  # behind it. Only this script and the dashboard write the file; a poll may
  # not (it once wrote its own guess of the time and hid 9 hours of mail).
  for connector in "${due[@]}"; do
    tmp=$(mktemp)
    jq --arg c "$connector" --arg now "$now_epoch" '.[$c] = ($now | tonumber)' "$COMPLETED" > "$tmp"
    mv "$tmp" "$COMPLETED"
  done
else
  rc=$?    # first statement: anything after this would overwrite it (it always logged 0)
  cat "$out_file" >> "$DASH_DIR/launchd-poll.log"; rm -f "$out_file"
  echo "$(date '+%Y-%m-%dT%H:%M:%S') poll FAILED (scope=$scope, exit=$rc)" >> "$DASH_DIR/launchd-poll.err"
fi
