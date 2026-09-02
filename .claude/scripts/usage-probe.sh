#!/usr/bin/env bash
# Usage probe — the feed for the usage failsafe. See .claude/shared/context-failsafe.md.
#
# Runs as the statusLine command. The statusLine payload is the ONLY place the
# 5-hour rate-limit figures are exposed: they are not in the PostToolUse hook
# payload and not in the transcript JSONL. So this wrapper tees them to a state
# file that every role's watchdog reads, then hands the untouched payload to the
# real status line for rendering.
#
# State file: ~/.claude/fce-usage.json (override with FCE_USAGE_STATE)
#   { "five_hour_pct": 41, "resets_at": 1756842900, "written_at": 1756839300 }
#
# Rendering delegate: $FCE_STATUSLINE, else ~/.claude/statusline-spaceship.sh,
# else nothing is printed. The status line is never allowed to fail because of
# this script.
set -uo pipefail

input=$(cat)

state=${FCE_USAGE_STATE:-$HOME/.claude/fce-usage.json}

# Absent until the first rate-limit header arrives; write nothing rather than a
# zero, so a fresh session reads as "no data" instead of "plenty left".
pct=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty | floor' 2>/dev/null)
case "$pct" in
  ''|*[!0-9]*) ;;
  *)
    resets=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // 0 | floor' 2>/dev/null)
    case "$resets" in ''|*[!0-9]*) resets=0 ;; esac
    tmp="${state}.$$"
    if jq -n --argjson p "$pct" --argjson r "$resets" --argjson w "$(date +%s)" \
        '{five_hour_pct: $p, resets_at: $r, written_at: $w}' > "$tmp" 2>/dev/null; then
      mv -f "$tmp" "$state" 2>/dev/null || rm -f "$tmp" 2>/dev/null
    else
      rm -f "$tmp" 2>/dev/null
    fi
    ;;
esac

next=${FCE_STATUSLINE:-$HOME/.claude/statusline-spaceship.sh}
[ -r "$next" ] && printf '%s' "$input" | bash "$next"
exit 0
