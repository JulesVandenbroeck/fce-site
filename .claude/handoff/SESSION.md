# Session handoff — 2026-09-02

**Why:** the user stopped both running sub-agents, then asked for the handoff. Orchestrator
context was at ~90%. Neither sub-agent wrote a handoff — both were killed, not recalled.
**Milestone:** M1 — the style choice (Bench) and the interiors ruling are both made and written
into `docs/design-brief.md` §4. Design work is now unblocked and mid-flight.

## Read first
1. This file.
2. `.claude/tasks/design.md` — current as of this commit. D-002 and D-013 entries carry the detail.
3. The per-task handoffs below — but only for tasks you are about to re-dispatch.

Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| D-002 | design | **`task/d-002-tokens-work`** (not the dispatched name) | — | 1 | 1 commit `edf82c9`, **local only, never pushed**, no PR, no gate run | none — agent killed |
| D-013 | design | `task/d-013-observable-interior` | #23 | 2 | cycle-2 delivered `c737905`, **gate passed**, reviewer killed before verdict | none — agent killed |
| B-008 | backend | `task/b-008-path-filter-safe-eval` | #19 | 3 | held by the user since 2026-09-01; cycle-3 dispatch was lost, head still `fba2ad6` | — |
| B-013 | backend | `task/b-013-safe-eval-findings` | #17 | 1 | held by the user since 2026-09-01, cycle-1 review never returned | — |
| B-014 | backend | `task/b-014-api-contract-findings` | #18 | 1 | held by the user since 2026-09-01, cycle-1 review never returned | — |

## Git as of this commit

    open PRs: #23 (D-013), #19 (B-008), #18 (B-014), #17 (B-013)
    origin/main == main (0/0)
    task/d-002-tokens        -> 9495696, ZERO commits (the dispatched branch, unused)
    task/d-002-tokens-work   -> edf82c9, LOCAL ONLY, 8 files vs main, all in scope
    task/d-013-observable-interior -> c737905 (pushed)

Re-run `git branch -a` and `gh pr list --state open` before you act. If they disagree with the
table above, **git is right.**

## First moves, in order
1. **Push `task/d-002-tokens-work` before anything else.** It is one unpushed local commit and
   the only copy of D-002's work — `tokens.css`, four self-hosted `.woff2` (EB Garamond roman +
   italic variable, Fira Mono 400/500), two OFL licence files, and `verify.py` additions. Then
   decide: open the PR from that branch, or have the coder move the commit onto
   `task/d-002-tokens`. **Do not re-dispatch D-002 from scratch** — the criteria are in
   `design.md`, checks=6, and C5 is the re-spec'd four-hue version.
2. Run the §5.1 gate on D-002 once it has a PR. Nothing has been verified: no gate, no PR body.
3. **Re-dispatch the D-013 cycle-2 reviewer** with PR #23 and the cycle-1 comment URL
   (`issuecomment-5506923899`) plus finding IDs R1/M1/M2/m1/m2/m3. It is **still cycle 2**. The
   gate already passed in `~/fce-gate-d013`: 5/5 PASS, flake8 exit 0, diff confined.
4. D-010 is dispatchable once D-013 merges. Its input is settled: node **328.0 x 300.0px**
   opened (`ObsVectorSum`, the tallest mode), 80.5px collapsed, inline-grow.

## Waiting on the user
- Whether to release **B-008 / B-013 / B-014** (#19 / #17 / #18). They were held on 2026-09-01
  pending the M1 style choice; **that choice is now made, so the stated reason for the hold is
  spent.** They remain parked on token budget, which is the user's call.

## Not carried over
- D-009 m3 and m4, and the `--node-observable` token note, are in `backlog.md` (84 items). The
  `--node-observable` item may close itself when D-002 lands — check the token name on merge.
