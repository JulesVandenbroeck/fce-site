#!/usr/bin/env bash
# Usage failsafe watchdog — see .claude/shared/context-failsafe.md.
#
# Runs as a PostToolUse hook. Reads the 5-hour usage figure that
# .claude/scripts/usage-probe.sh tees out of the statusLine payload, and injects
# an instruction into the session when it crosses the anchor (50%), soft (75%)
# and hard (90%) thresholds of the 5-hour limit.
#
#   50%  anchor — take a token audit, write the <=25-line anchor file, keep working
#   75%  soft   — stop opening new work, bring the task lists current
#   90%  hard   — stop and hand off
#
# The 5-hour limit is account-wide, so every role reads the same number and the
# orchestrator and its sub-agents cross each threshold together. That is
# deliberate: at 90% the whole session hands off at once.
#
# If the state file is missing or stale the watchdog stays silent — it never
# guesses. State file: ~/.claude/fce-usage.json (override with FCE_USAGE_STATE),
# staleness bound FCE_USAGE_MAX_AGE seconds.
set -uo pipefail

payload=$(cat)
sid=$(printf '%s' "$payload" | jq -r '.session_id // "unknown"')

state=${FCE_USAGE_STATE:-$HOME/.claude/fce-usage.json}
max_age=${FCE_USAGE_MAX_AGE:-900}
[ -r "$state" ] || exit 0

read -r pct resets written < <(jq -r '
  [ (.five_hour_pct // empty), (.resets_at // 0), (.written_at // 0) ] | @tsv
' "$state" 2>/dev/null | tr '\t' ' ')

case "${pct:-}" in ''|*[!0-9]*) exit 0 ;; esac
case "${written:-}" in ''|*[!0-9]*) exit 0 ;; esac
case "${resets:-}" in ''|*[!0-9]*) resets=0 ;; esac

# Stale means the status line is not feeding us — a headless or backgrounded
# session. Say nothing rather than act on a number from an hour ago.
now=$(date +%s)
[ $(( now - written )) -le "$max_age" ] || exit 0

if   [ "$pct" -ge 90 ]; then tier=hard
elif [ "$pct" -ge 75 ]; then tier=soft
elif [ "$pct" -ge 50 ]; then tier=anchor
else exit 0
fi

# Fire each tier once per session per 5-hour window: keying the stamp on
# resets_at re-arms every tier automatically when the window rolls over.
state_dir="${TMPDIR:-/tmp}/claude-usage-watchdog"
mkdir -p "$state_dir" 2>/dev/null
stamp="$state_dir/${sid}.${resets}.${tier}"
[ -e "$stamp" ] && exit 0
: > "$stamp"

if [ "$resets" -gt 0 ] 2>/dev/null; then
  when=$(date -d "@$resets" +%H:%M 2>/dev/null)
  clock="; the 5-hour window resets at ${when}"
else
  clock=""
fi

if [ "$tier" = anchor ]; then
  msg="USAGE WATCHDOG — ${pct}% of the 5-hour usage limit spent${clock}. This is the ANCHOR threshold from .claude/shared/context-failsafe.md §8.0. Do NOT stop working; this costs one write. (1) Token audit: are you re-reading files you already have in this transcript, re-deriving facts you already established, or reading whole files where 'grep -n' would answer it? Correct that from here on — every token you spend now comes out of the same shared budget the rest of this session has to finish on. (2) Write or refresh your anchor at .claude/handoff/<id>-<role>.anchor.md in the PRIMARY checkout — at most 25 lines: decisions made and why, dead ends already ruled out, the exact next step, criteria still open. It is what survives a compaction, and at 90% it is promoted into the handoff instead of the handoff being written from scratch. You cannot run /compact; the anchor is the substitute."
  user="Usage watchdog: 5h limit ${pct}% — anchor threshold, audit and write the anchor"
elif [ "$tier" = soft ]; then
  msg="USAGE WATCHDOG — ${pct}% of the 5-hour usage limit spent${clock}. This is the SOFT threshold from .claude/shared/context-failsafe.md §8 / .claude/orchestrator/CLAUDE.md §10. Stop opening new work: finish the cycle in flight, do not dispatch a fresh batch or start a new milestone, prefer serial dispatch over parallel, and bring the task lists fully current NOW while you can still afford to write them properly. Do not start anything you cannot see the budget to finish. If your anchor file is stale, refresh it before anything else."
  user="Usage watchdog: 5h limit ${pct}% — soft threshold, stop opening new work"
else
  msg="USAGE WATCHDOG — ${pct}% of the 5-hour usage limit spent${clock}. This is the HARD threshold. Trigger the handoff procedure now, in order, and do not gamble on finishing the current task first. Sub-agent: follow .claude/shared/context-failsafe.md §8.2 — stop, commit and push on your task branch, promote your §8.0 anchor into .claude/handoff/<id>-<role>-<cycle>.md in the PRIMARY checkout (not the task branch, not a worktree), report the §8.5 short form, stop. Orchestrator: follow .claude/orchestrator/CLAUDE.md §10 — stop dispatching, send 'HANDOFF NOW' to every running sub-agent via ListAgents/SendMessage, reconcile against git, update the task lists, write .claude/handoff/SESSION.md, commit .claude/ to main, then tell the user when the window resets and stop."
  user="Usage watchdog: 5h limit ${pct}% — HARD threshold, handoff procedure triggered"
fi

jq -n --arg m "$msg" --arg u "$user" '{
  systemMessage: $u,
  hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: $m }
}'
