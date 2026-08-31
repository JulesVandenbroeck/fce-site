# Orchestrator session anchor — 2026-08-31

**Where we are:** M2 is **complete**. B-012 merged as `928c1ba` (PR #15, 3 cycles, clean gate).
Local `main` had diverged (two unpushed bookkeeping commits vs the GitHub merge); resolved with
`git merge --no-ff origin/main` → `6d39a26`. **Never rebase** — that was the correct fix.

**In flight:** D-005 cycle 2, `design-coder`, worktree isolation, branch `task/d-005-bench`, PR #16.
Cycle 1 came back `1R / 0M / 3m`, `verdict=rework`.

**The Required, in one line:** `bench.html` loads `bench.js` as an external `type="module"`;
`file://` Chromium refuses it on CORS, so the page is empty, and the coder's
`--allow-file-access-from-files` launch flag hid that from all 16 bench sections.
`bench.js` has no `import` statements, so inlining the module removes the flag entirely.

**Diagnosis: a cycle, §5.4 clause 3** — C1–C5 all shipped with commands and all were met; R1 is
against a property no criterion gated, but shared §3's no-build/offline rule did.

**Criteria: C1–C7, checks=7.** C1–C5 verbatim in PR #16's body. C6 = flag-free launch,
mutation-gated by re-introducing the external module. C7 = m3, palette list semantics.

**Floors:** `verify.py` ≥ **45** registered sections / **147** assertion lines (reviewer-measured
on the branch), of which ≥ **121** non-bench. The old "31 / 48" does not reproduce — backlogged.

**Dead ends already ruled out:**
- m1 (`check_git_diff` uses local `main`) is **backlogged, not fixed** — a falsifiable check needs
  a stale-`main` fixture that cannot be built without moving `main`.
- Do not fix R1 by keeping `type="module"` and serving over HTTP. The gate is a plain local page.

**Next step after D-005 approves:** merge #16, then D-006 (Board) — serial after D-005, never
parallel, both append to `verify.py`. Wave 6 (B-008, B-013, B-014) is released and parallelisable.

**Owed to the user:** the M2 checkpoint report (B-012 merged) — delivered in the same message as
the cycle-2 dispatch.
