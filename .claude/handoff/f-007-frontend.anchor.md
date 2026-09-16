# F-007 anchor (frontend, cycle 2)

Branch task/f-007-run-submit-stream, worktree agent-a51f001c2204e4176. PR #46 open.
Cycle-1 review (F1-F11) verified as correct, all real defects/gaps, not disputing any.

Fixed in run.js: F4 (resetResults clears data-result), F5 (aria-disabled not
disabled attr, guard re-entry, setRunning()), F6 (removed aria-live from
<progress> markup), F7 (lastPhase plain let), F8 (dropped expectError param),
F9 (dropped try/catch around new EventSource), F10 (status resets to "Not run
yet." on error/cancelled).

Tests: rewrote tests/e2e/test_run.py. Dropped weak "seen>1" liveness assert
(F1) from the done-test. Added C12 (payload has no x/y, via
page.expect_request), C14 (second click clears stale data-result
synchronously), C15 (focus stays on #run-button through a run). C13 (stubbed
SSE, multi-frame liveness) is HALF-WRITTEN -- test_sse_frames_render_live_not_in_one_jump
has a placeholder assertion (`... or True`) that must be replaced with a real
capture of #results-status's text history asserting a phase string
("reading events"/"filling histogram") was actually seen.

NEXT STEP: fix that assertion properly, then run full suite + flake8, produce
the two mutation transcripts (C12: patch buildSubmission to add x/y and show
red; C13: delete the phase/progress status writes in streamRun and show red),
then fix PR body C3 quote (missing name:id) and contract's aria-live mention,
add cycle-2 section with C12-C15 + F6/F11 notes, push, report per section 7.
Not yet committed/pushed since cycle-1 push.
