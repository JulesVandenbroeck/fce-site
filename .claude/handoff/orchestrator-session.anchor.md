# Orchestrator anchor — session 2026-09-02

**Milestone:** M1. Style ruled Bench 2026-09-01. D-009 is the open checkpoint task.

## Reconciled against git this session (list was wrong, git right)
- **D-002** — branch `task/d-002-tokens` at `9495696`, ZERO commits, no PR, no anchor. The
  2026-09-01 dispatch was lost before the coder's first write. **Re-dispatch is cycle 1.**
- **D-009** — the 2026-09-01 cycle-1 reviewer never returned a verdict and posted no comment.
  Re-dispatched 2026-09-02; that WAS cycle 1.

## Decisions this session
- D-009 cycle 1 reviewed: `2R / 2M / 3m`, scope pass, `verdict=rework`. Posted verbatim to
  PR #22 (`issuecomment-5506219239`). §5.4 diagnosis = **clause 3, a real cycle**: R1/R2 are
  against the coder's instrument (C4 was dispatched mutation-gated and the gate does not
  distinguish), not a criterion I dropped.
- **Cycle 2 dispatched** with C9 (label + Tab assertions) and C10 (zero-height precondition).
  **checks 8 -> 10.** m3 backlogged; m1/m2 folded in. M2 (`DataSource`) is overrulable — the
  coder was given the brief §4 ruling as a fact, not told how to rule.

## Held, unchanged
B-008 #19 (cycle 3 dispatch also lost, head still `fba2ad6`), B-013 #17, B-014 #18 — all
paused by the user 2026-09-01 on budget. The M1-choice reason for the hold is now spent.

## Next step
1. Collect D-009 cycle 2 -> gate -> review. It is a **checkpoint**: the user reads
   `interiors.html` and rules flyout vs inline grow. D-010 is blocked on that.
2. **D-002 re-dispatch is proposed and NOT yet approved by the user.** Do not send it
   unasked — the user is managing spend deliberately.
