# Handoff: B-020 cycle 3 — resolve F9/F10/F11 (PR #33)

- **Role:** backend-coder
- **Written:** 2026-09-08, at ~90% of the 5-hour limit
- **Cycle:** 3 — the §5.7 loop limit, there is no cycle 4
- **Continues:** nothing — first handoff on this task/cycle

## The task as I was given it

Resolve findings **F9, F10, F11** from
https://github.com/JulesVandenbroeck/fce-site/pull/33#issuecomment-5582721933
(`findings=3, scope=pass, verdict=rework`). All eight cycle-1 findings and both digest
literals from cycle 2 are confirmed correct — **the code is not in question**, only these
three:

- **F9** — false statement in the PR body (not a bug): C7 claims the fixture's digests match
  `content/analyses/zpeak-dilepton.json` bit-for-bit. They do not: `_sel_node` defaults to
  one expression, so the fixture yields `2b8e2826…`/`1d1f518b…` while the JSON holds
  `fbb913c1…`/`c9873a70…`. Fix one of two ways: correct the block to the real output, or make
  `_mission1_payload` use both expressions so the zpeak claim becomes true. Say which.
- **F10** — ladder question. The multi-path half of `graph.py` (selection grouping,
  `_selection_exprs` accumulation across chained `Selection`s, `plot_idx`, the
  branch-disagreement `GraphError` in `_shared_mult_cuts`) has no check that can fail:
  reversing `_selection_exprs`'s accumulation order leaves all 16 tests green. If kept, ship
  it with one payload — two `Selection`s, two `Histogram` branches, a pinned `h5_sel`
  covering the accumulation. If deleted (rung-1 answer, preferred), say so in one line.
- **F11** — one clause in `docs/api.md:64-69`: the edges bullet lists illegal/cyclic/
  disconnected/no-terminal as 400s but not "all branches must share the same `Multiplicity`
  chain" (`graph.py:283-288` also raises `GraphError` for this).

### File scope (verbatim)
- `src/fce_web/graph.py`
- `tests/test_graph.py`
- `docs/api.md` (`## Endpoints` only)

### Acceptance criteria (verbatim, C1–C12 from PR #33 body + new C13)
C1–C12 all still hold — verbatim in PR #33's body (do not re-paste here, read the PR). New:
- [ ] C13 Every branch of the translator that ships is covered by a check that can fail.
      Property: a code path with no failing check is either deleted or given one — no third
      option.
      Check: reverse the accumulation order in `_selection_exprs`, then run
      `pytest tests/test_graph.py -q`.
      Expect: RED if the multi-path branch is kept; **not applicable, and say so, if you
      deleted it** — a deleted branch needs no check, and that is the preferred answer.

Total checks: **13**.

## State of the branch
- Branch: `task/b-020-graph-allowlist` — pushed: yes
- HEAD: `0a6831a61af215fb232600b2c2ddb270f9c23598` — F11 only (docs/api.md edit)
- PR: #33
- Working tree at handoff: clean (docs/api.md fix committed)
- Tests at HEAD: not re-run after this commit; last known green was cycle-2's
  `pytest tests/ -q` → 621 passed (see PR #33 body "cycle 2" section)

## Acceptance criteria — where each one stands
- [x] F11 — met. `docs/api.md:64-68` now reads: "...missing a `Histogram` terminal, or
  spanning branches whose `Multiplicity` chains disagree (the digest formula has one
  `mult_cuts` for the whole run, not one per branch) are all rejected..."
- [ ] F9 — not met. Decision made but not yet applied: **use option B** — make
  `_mission1_payload` use both expressions, because the resulting digests
  (`fbb913c18c34530d355fdd949974ac58` / `c9873a70ca371612fc24cf976ff7fd5c`) then match
  `content/analyses/zpeak-dilepton.json` bit-for-bit again, keeping the PR body's existing
  JSON block and narrative true with zero edit to the PR body's pasted JSON. Concretely, in
  `tests/test_graph.py`:
  - `_mission1_payload()` line ~82: change `_sel_node()` to
    `_sel_node(exprs=["l1.pt > 20", "l2.pt > 10"])`.
  - `_MISSION1_H5` (line 196) → `"fbb913c18c34530d355fdd949974ac58"`.
  - `_MISSION1_H5_SEL` (line 197) → `"c9873a70ca371612fc24cf976ff7fd5c"`.
  - `test_mission1_graph_produces_a_run_config` line ~206: assertion
    `cfg.sel_exprs == ["l1.pt > 20"]` → `cfg.sel_exprs == ["l1.pt > 20", "l2.pt > 10"]`.
  - Update the comment block above the two constants (lines 184–195) to state
    `sel_exprs=["l1.pt > 20", "l2.pt > 10"]` instead of a single expr.
  I independently re-derived these two digests by hand from the documented formula
  (`mult_h5_base = energy+detector+str(mult_cuts)`; `h5_sel=md5(mult_h5_base+str(sel_exprs))`;
  `h5=md5(h5_sel+observable+bins+min+max+target)`) in a throwaway python one-liner (not run
  through `graph.py`) and got exactly `fbb913c18c34530d355fdd949974ac58` /
  `c9873a70ca371612fc24cf976ff7fd5c` — matching both the JSON fixture and the reviewer's own
  independent re-derivation quoted in the review comment. Safe to apply as-is.
- [ ] F10 — not met. **Decision: keep** the multi-path code (it is the documented contract
  interface — "Selection: exprs ANDed with any upstream Selection" — and F-005/F-007 already
  dispatch against it), and add the one payload the reviewer names. I worked out the exact
  fixture and independently verified its digests (see "Not done" below) but have not written
  the test yet.
- [ ] C13 — not met, blocked on F10's test being written.

## Done
- `docs/api.md:64-68` — added the Multiplicity-chain-agreement clause to the 400 list (F11).

## Not done, in the order I would do it

1. **F9**: apply the four edits to `tests/test_graph.py` listed above under F9, then run
   `pytest tests/test_graph.py -q` — expect 16 passed still (values change, not test count).

2. **F10**: add ONE new test to `tests/test_graph.py`, no `graph.py` code changes needed.
   Payload (all node helpers already exist in the file):
   ```
   nodes: _mult_node("mult1"), _sel_node("sel1", exprs=["l1.pt > 20"]),
          _sel_node("sel2", exprs=["l2.pt > 10"]),
          _obs_node("obs1", mode="ObsCustom", expr="(l1.p4 + l2.p4).mass"),
          _hist_node("hist1"),
          _obs_node("obs2", mode="ObsCustom", expr="l1.pt"),
          _hist_node("hist2")
   edges: [["mult1","sel1"], ["sel1","sel2"], ["sel2","obs1"], ["obs1","hist1"],
           ["sel1","obs2"], ["obs2","hist2"]]
   ```
   This produces two paths: a **chained** one (`mult1→sel1→sel2→obs1→hist1`, exercises
   `_selection_exprs` accumulating across two `Selection` nodes) and a **branch** one
   (`mult1→sel1→obs2→hist2`, shares the `sel1` prefix but a different group key), so it
   covers grouping, accumulation order, and `plot_idx` incrementing (0 then 1, since
   `sel1→sel2` is inserted before `sel1→obs2` in the edges list, and `_histogram_paths`
   walks children in insertion order).

   I independently derived (python one-liner, not via `graph.py`) the expected digests for
   this exact payload with `dataset=Dataset("91 GeV", "IDEA")`:
   - Chained branch (`sel_exprs=["l1.pt > 20", "l2.pt > 10"]`, `observable="(l1.p4 + l2.p4).mass"`,
     `bins/min/max/target = "50"/"60.0"/"120.0"/"None"`):
     `h5_sel = "c9873a70ca371612fc24cf976ff7fd5c"`, `h5 = "fbb913c18c34530d355fdd949974ac58"`
     (same values as the corrected mission-1 fixture above — expected, same formula inputs).
   - Branch-only path (`sel_exprs=["l1.pt > 20"]`, `observable="l1.pt"`, same
     bins/min/max/target): `h5_sel = "1d1f518b0dd7f037a7c12a160838e42d"`,
     `h5 = "2525f9e18ab8ad80c419640828167925"`.

   Write the test as (name it e.g. `test_chained_and_branching_selections_produce_two_histograms`):
   assert `len(cfg.selections) == 2`; find the selection with
   `sel_exprs == ["l1.pt > 20", "l2.pt > 10"]` and assert its `h5_sel` and its one
   histogram's `h5` equal the chained-branch pair above; find the other with
   `sel_exprs == ["l1.pt > 20"]` and assert its `h5_sel`/histogram `h5` equal the
   branch-only pair above. Also assert the two histograms' `plot_idx` are `0` and `1`
   respectively (chained path is discovered first).

3. **C13 verification** (do this after step 2, do not skip): mutate `_selection_exprs` in
   `src/fce_web/graph.py` (line ~304, `exprs.extend(branch_exprs)`) via the project's
   in-memory-module-copy mutation technique (§ backend/CLAUDE.md "Mutation-test by
   monkeypatch... never by editing a tracked file" — read the source, substitute
   `exprs.extend(branch_exprs)` → `exprs[:0] = branch_exprs` or similar reversal, `exec` into
   a fresh module object, do NOT touch the tracked file) and confirm the new test in step 2
   goes red. Report the exact failure message, then confirm `pytest tests/test_graph.py -q`
   is green again with the real (unmutated) file.

4. Run full verification:
   ```
   export PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright
   pytest tests/test_graph.py -q                                              # expect 17 passed
   FCE_PARITY_REFERENCE_ROOT=/nonexistent pytest tests/test_graph.py -q -k matches_reference   # 1 skipped
   pytest tests/test_graph.py -q -k matches_reference                          # 1 passed (reference present)
   pytest tests/ -q                                                            # floor 605; expect 621 -> 622 (one net new test)
   flake8 src/ tests/ scripts/                                                 # clean
   ```
   `main` had already been merged into this branch as of cycle 2 (see PR body "Verification
   (cycle 2, after merging main)"); check `git status`/`git log` for whether it has moved
   again before pushing — merge, never rebase, if so.

5. Update PR #33's body: append C13 (met, with the mutation evidence from step 3), update
   "Total checks: 12" → "Total checks: 13", add three lines resolving F9/F10/F11 (see
   `.claude/shared/CLAUDE.md` §7's PR template — this project's convention is a
   "Findings resolved" section per cycle, cycle 2's is already there, add a
   "Findings resolved (cycle 3)" section for F9/F10/F11). State the F9 choice (option B) and
   the F10 decision (kept, with the new test) explicitly, per the dispatch's instruction to
   "say which."

6. Commit, push (branch already pushed once at `0a6831a`, this becomes the next commit on
   the same branch), and report back per `.claude/shared/CLAUDE.md` §7 (this is a re-dispatch
   of an already-open PR, not a new one).

## Dead ends — do not repeat these
None yet — this handoff was written before F9/F10 work started, at the 90% trigger. No
approach has been tried and failed.

## Open questions for the orchestrator
None. The next steps above are fully determined; a cold successor can execute them without
further judgment calls, including the exact digests to pin (independently verified twice —
once by me, once already by the reviewer in the PR comment for the mission-1 pair).

## Environment notes
- `export PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright` before running the suite.
- Worktree: `.claude/worktrees/agent-a9c0de01733f3ab0c`, branch `task/b-020-graph-allowlist`,
  already checked out there — do not `git worktree add` again. `.venv/bin/python` exists
  there and was used for all the digest verification above (see history if re-derivation is
  wanted: `hashlib.md5(...).hexdigest()` calls only, no dependency on `graph.py` itself).
