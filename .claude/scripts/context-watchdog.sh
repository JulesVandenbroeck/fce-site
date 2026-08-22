#!/usr/bin/env bash
# Context failsafe watchdog — see .claude/shared/context-failsafe.md.
#
# Runs as a PostToolUse hook. Reads the live transcript, sums the token usage of
# the most recent assistant turn, and injects an instruction into the session
# when it crosses the anchor (50%), soft (75%) and hard (90%) thresholds of the
# context window.
#
#   50%  anchor — take a token audit, write the ≤25-line anchor file, keep working
#   75%  soft   — stop opening new work, bring the task lists current
#   90%  hard   — stop and hand off
#
# Fires for every role: the orchestrator's transcript and each sub-agent's own
# transcript are separate files, and the hook runs against whichever is active.
#
# Override the assumed window with FCE_CONTEXT_LIMIT (tokens).
set -uo pipefail

payload=$(cat)
tp=$(printf '%s' "$payload" | jq -r '.transcript_path // empty')
sid=$(printf '%s' "$payload" | jq -r '.session_id // "unknown"')
[ -n "$tp" ] && [ -f "$tp" ] || exit 0

limit=${FCE_CONTEXT_LIMIT:-200000}

# Last non-sidechain assistant turn: input + cache-creation + cache-read is the
# context actually sent on that request.
used=$(tac "$tp" 2>/dev/null | head -500 | jq -Rr '
  fromjson? // empty
  | select(.isSidechain != true)
  | .message.usage // empty
  | ((.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0))
' 2>/dev/null | head -1)

case "$used" in ''|*[!0-9]*) exit 0 ;; esac
[ "$limit" -gt 0 ] 2>/dev/null || exit 0

pct=$(( used * 100 / limit ))

if   [ "$pct" -ge 90 ]; then tier=hard
elif [ "$pct" -ge 75 ]; then tier=soft
elif [ "$pct" -ge 50 ]; then tier=anchor
else exit 0
fi

# Fire each tier once per session.
state="${TMPDIR:-/tmp}/claude-context-watchdog"
mkdir -p "$state" 2>/dev/null
stamp="$state/${sid}.${tier}"
[ -e "$stamp" ] && exit 0
: > "$stamp"

if [ "$tier" = anchor ]; then
  msg="CONTEXT WATCHDOG — ${pct}% of the context window used (${used}/${limit} tokens). This is the ANCHOR threshold from .claude/shared/context-failsafe.md §8.0. Do NOT stop working; this costs one write. (1) Token audit: are you re-reading files you already have in this transcript, re-deriving facts you already established, or reading whole files where 'grep -n' would answer it? Correct that from here on. (2) Write or refresh your anchor at .claude/handoff/<id>-<role>.anchor.md in the PRIMARY checkout — at most 25 lines: decisions made and why, dead ends already ruled out, the exact next step, criteria still open. It is what survives a compaction, and at 90% it is promoted into the handoff instead of the handoff being written from scratch. You cannot run /compact; the anchor is the substitute."
  user="Context watchdog: ${pct}% used — anchor threshold, audit and write the anchor"
elif [ "$tier" = soft ]; then
  msg="CONTEXT WATCHDOG — ${pct}% of the context window used (${used}/${limit} tokens). This is the SOFT threshold from .claude/shared/context-failsafe.md §8 / .claude/orchestrator/CLAUDE.md §10. Stop opening new work: finish the cycle in flight, do not dispatch a fresh batch or start a new milestone, prefer serial dispatch over parallel, and bring the task lists fully current NOW while you can still afford to write them properly. Do not start anything you cannot see the budget to finish. If your anchor file is stale, refresh it before anything else."
  user="Context watchdog: ${pct}% used — soft threshold, stop opening new work"
else
  msg="CONTEXT WATCHDOG — ${pct}% of the context window used (${used}/${limit} tokens). This is the HARD threshold. Trigger the handoff procedure now, in order, and do not gamble on finishing the current task first. Sub-agent: follow .claude/shared/context-failsafe.md §8.2 — stop, commit and push on your task branch, promote your §8.0 anchor into .claude/handoff/<id>-<role>-<cycle>.md in the PRIMARY checkout (not the task branch, not a worktree), report the §8.5 short form, stop. Orchestrator: follow .claude/orchestrator/CLAUDE.md §10 — stop dispatching, send 'HANDOFF NOW' to every running sub-agent via ListAgents/SendMessage, reconcile against git, update the task lists, write .claude/handoff/SESSION.md, commit .claude/ to main, then tell the user and stop."
  user="Context watchdog: ${pct}% used — HARD threshold, handoff procedure triggered"
fi

jq -n --arg m "$msg" --arg u "$user" '{
  systemMessage: $u,
  hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: $m }
}'
