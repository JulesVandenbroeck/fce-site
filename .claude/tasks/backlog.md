# Backlog

Swept 2026-09-17. Everything before the sweep, verbatim, lives in
[`archive/backlog-2026-09-17.md`](archive/backlog-2026-09-17.md) — cite items from there by
their original tag (`B-022 F14`, `D-016 F2`, …). Nothing was deleted.

The sweep split the old list three ways:

1. **Useful** — below. Real product or robustness work; each wants its own task when its
   milestone comes up. Not dispatched.
2. **Cleanup** — handed to **B-029 / F-013 / D-019** (one per role, see the role lists).
3. **Dropped** — closed by later work, superseded, or history only. Listed at the bottom with the reason.

Count: `grep -c '^- \*\*' .claude/tasks/backlog.md`. Add new findings under `## New`; the user-prioritised ones sit in `## Next up`.

---

## Next up — do these first

Raised 2026-09-22 by the **user**, from driving the running app, and moved to the head of the
backlog at their request. These are product direction on the
graph canvas, not review findings — N12-N14 change what the canvas *is*, so they want a design pass
before any of them is dispatched. N15 is a plain bug. Nothing is dispatched.

- _(CLOSED by F-015, #62, merged `dc2337f` 2026-09-23)_ **N12 The canvas should be full-bleed, not a fixed box** (design + frontend). Today the node canvas
  is a fixed-size region inset in the page. It should span the **full width of the site**. The two
  side panels then **overlay** the canvas rather than sitting beside it and stealing width — the user
  explicitly accepts the overlap, because the existing arrow buttons already collapse each panel.
  Note D-018's standing caveat: at 1024/768 `.canvas-region` h-scroll can put the leftmost node out of
  reach for coordinate clicks in e2e — full-bleed plus pan (N13) likely changes that failure mode, so
  re-check the e2e coordinate helpers rather than assuming they still hold. _(user, 2026-09-22)_
- _(CLOSED by F-016, #67, `1075a03`)_ **N13 The canvas must be an explorable map: pan and zoom** (frontend, with design). Nodes live on a
  surface larger than the viewport. **Left-click-drag on empty canvas pans**; scroll (or equivalent)
  **zooms in and out**. Open questions for the design pass, not assumptions: zoom limits, whether pan
  is bounded or infinite, what happens to a left-drag that starts *on* a node (today that is presumably
  node-move), and whether there is a reset/fit-to-content affordance. Pairs with N12 — a full-bleed
  fixed surface without pan is a smaller win than either alone. _(user, 2026-09-22)_
- _(CLOSED by F-015, #62, merged `dc2337f` 2026-09-23)_ **N14 Results belong in a bottom drawer, not below the canvas** (design + frontend). Move the
  **Run Analysis** button to the **bottom screen border**. Analysis results must **not** flow in below
  the canvas; they go in an **expandable panel that rises from the bottom**, the same interaction
  family as the two side panels, with its own **arrow button sitting above the Run Analysis button**.
  Pressing **Run Analysis auto-expands** that drawer. The collapse-chevron machinery is already in
  `shell.js`/`shell.html` (see N11) — reuse it for the third edge rather than writing a second one.
  _(user, 2026-09-22)_
- _(CLOSED by F-014, #61, merged `06e4108` 2026-09-23)_ **N15 A node that is expanded to edit does not retract to its collapsed size** (frontend, bug).
  Expand a node to edit it, then un-expand: the node keeps its **expanded footprint** instead of
  shrinking back. Almost certainly an inline/explicit height (or a stale measured height) set on
  expand and never cleared on collapse — check the collapse path clears whatever the expand path set,
  and confirm the fix on a node whose expanded content is taller than one line. Independent of
  N12-N14; can ship on its own. **Held 2026-09-22 by the user until D-020 lands**, because pan/zoom
  introduces a transform that may change how node geometry is computed. _(user, 2026-09-22)_
  **Ground truth, enumerated by `scout` 2026-09-22 — do not re-derive, and note it refutes the
  obvious hypothesis.** Nothing anywhere sets an inline `style.width/height/minWidth/minHeight` on a
  node: `graph.js` writes **only** the SVG `foreignObject` `height` attribute, at `graph.js:186`
  inside `growNode` (`:181-194`), plus the initial `width`/`height` at `:708-709`. And the collapse
  path is **not** missing a cleanup — `wireInteriorToggle` (`:237-245`) calls the *same* `growNode(id)`
  on both open and close (`:243`), so the shrink is meant to happen by re-measuring
  `div.scrollHeight`. So the defect is in the **measurement**, not in a stale value: the likeliest
  cause is that `growNode` reads `scrollHeight` in the same tick as the `toggle` event, before the
  browser has reflowed the now-closed `<details>` — and `observable.css:9-17`
  (`.node__interior[open] { flex-shrink: 0; max-height: calc(var(--space-7)*6); overflow-y: auto }`)
  is the geometry that makes the two states differ. `moveNodeTo` (`:219-230`) only *reads* size via
  `measuredSize` (`:146-152`). Existing coverage that must stay green: `test_graph.py:258, 318, 339,
  454, 480` and `test_interior_style.py:22` — note **none of them asserts that a re-collapsed node
  returns to its collapsed height**, which is exactly why this shipped. That missing assertion is the
  one runnable check the fix owes. _(scout, 2026-09-22)_

---

## Useful — raise as tasks when their milestone comes up

- **U1 Installable for a classroom** (backend; **needs user sign-off on dependencies**). A wheel
  omits `templates/`, `static/`, `content/` (B-001/F-001/B-002, confirmed three times); PyYAML is
  only transitive (M5's `missions.py` needs it); dependencies unpinned; **a fresh venv fails
  collection** because unpinned `fastapi` pulls a `starlette` whose `TestClient` wants `httpx2`
  (B-027 note, B-002). Before any teacher installs this.
- **U2 Per-job output directory** (backend, before M5 classroom use). `analytical_loop.py` writes
  `output/hist{plot_idx}_{sample}.root` keyed on `plot_idx` only, so `JobRegistry._run_lock`
  serialises every student's run. Per-job dir → drop the lock. _(B-021)_
- **U3 Vectorise `and`/`or` in `safe_eval`** (backend). `l1.pt > 20 and l2.pt > 10` — the most
  common student shape — silently falls off the vectorised path. Rewrite `BoolOp` to `&`/`|`.
  Speed only, no number changes. _(M2 planning)_
- **U4 `fit.method` surfaced** (backend + frontend, when M5 shows μ/Z). `run_fit` returns `(mu, sig)`
  from three different methods (HistFactory MLE, counting ratio, `s/√b` after a swallowed pyhf
  failure) under the same names. A `s/√b` must not be shown as a fitted signal strength.
- **U5 Module-level-state guard → default-deny** (backend). `tests/test_app.py`'s scan enumerates
  forbidden types, so a module-level `threading.Lock()` or registry object passes. Allow only
  inert types. This guards the project's founding defect. _(B-002)_
- **U6 CI** (backend, optional). pytest + flake8 on push. Needs `.venv` in `.flake8` exclude (in
  B-029). Know that `test_real_end_to_end_run_exercises_the_real_run_physics_loop` skips without
  `~/.fce/datasets`, and `_make_unwritable` skips under root. _(B-001, B-011, B-005)_
- **U7 Accessibility chrome** (frontend, M6). Skip link, `<header>/<nav>/<footer>` landmarks once
  there is chrome, `aria-live` on run progress/results if F-007 did not already add it, offline
  HTML validation in e2e. _(F-001)_
- **U8 Design ideas for M5/M6** (design). Face-down locked cards to show gating (mission unlocks
  now read *inside* a node); a per-cut "events kept: N of M" preview before running; mission 1 as a
  stepped Focus Stage, full spread from mission 2 — playtest, don't assume. _(D-001)_
- **U9 Dark "darkroom" variant** (design, post-M6). Light only for V1.
- **U10 Constraints to attach to future tasks** — not tasks themselves:
  - if M5+ wants `**` in expressions, bound the exponent; never re-admit it unbounded (B-006);
  - whoever vendors `cutflow_plotter`: `ImportError` inside it reads as "deferred", and a plot
    failure discards a finished `RunResult` (B-009 c2);
  - `--frozen-x2` 3.12:1 and `--syst-grey` 3.24:1 on `--paper` clear 3:1 by <0.25 — warming
    `--paper` breaks both (D-002);
  - at 1024/768 `.canvas-region` h-scroll can put the leftmost node out of reach for coordinate
    clicks in e2e (D-018);
  - `safe_eval` reports the canonical `__class__` escape with the `Call` message, not the
    underscore one — reorder checks if student-facing error copy is ever reworked (B-006).

## New

- _(CLOSED by D-021, #60, merged `b3f8ef2` 2026-09-22)_ **N16 The canvas-frame page opens with most of the graph under the panels** (design, D-020 F1).
  `docs/design-explorations/canvas-frame.html:409-430` (`buildGraph` node coordinates) — at load, both panels
  in their default `expanded` state, only **2 of 5** nodes are clear at 1440 (`n3` clipped at `left 980` against
  a panel edge of 1120; `n4` and `n5` entirely off-viewport); at 768 exactly **one** node is visible. The PR body
  claimed the graph "was moved into the clear band" and the reviewer could not reproduce that. Fix is either
  seeding the initial scroll/zoom so the pipeline lands between the two expanded panels, or one sentence in the
  recommendation's "What the overlay costs" saying the load state is deliberately covered and Fit is the first
  gesture. **Matters because this is the page the user rules on.** _(PR #59 F1)_
- _(CLOSED by D-021, #60, merged `b3f8ef2` 2026-09-22)_ **N17 `CANVAS_FRAME_DESIGN_WIDTHS` duplicates `SHELL_DESIGN_WIDTHS`** (design/tooling, trivial).
  `docs/design-explorations/verify.py:8931` is byte-for-byte `verify.py:6200` in the same module. Delete it and
  use the existing one, or rename that one to `DESIGN_WIDTHS` — the widths are the project's, not either page's.
  _(PR #59 F2)_
- _(CLOSED by D-021, #60, merged `b3f8ef2` 2026-09-22)_ **N18 `_canvas_frame_set_state` labels probes by requested state, not measured** (design/tooling).
  `docs/design-explorations/verify.py:8934-8940` clicks the chevron at most once and never asserts the region
  reached `want`; the per-probe label at `:8987` then reports the *requested* palette/panel state, so a toggle
  that failed to fire would silently relabel a probe as a layout it never measured. The drawer already does this
  correctly by reading `measured['drawer']` back. Same shape as this project's blind-instrument failures — the
  check currently passes its own mutation test, so this is a latent weakness, not a live false green. _(PR #59 F3)_

Raised 2026-09-22 from the truth deck (`docs/physics-truth.md`). None is dispatched; all three
belong to M5/M6 mission authoring, and B-029/F-013/D-019 are in flight.

- _(CLOSED by F-017, #66, `8f89578`)_ **N1 The `d0` label IS wrong — CONFIRMED by scout 2026-09-23: `expr.js:41` ships `label: "transverse impact parameter (d0)", unit: "mm", range: [-1, 1]` to students; no other hit. Awaiting the user's ruling on the replacement (§7: student-facing).** Was: The `d0` label is probably wrong (frontend; **before any M-4 copy is written**).
  `.d0` on a lepton is an impact-parameter *significance*, not a distance: the ROOT branch is
  `d0signif` (`engine/analytical_loop.py:159`), read as `electron_d0signif`/`muon_d0signif`
  (`engine/path_filter.py:622,630`), then **renamed to `d0`** at `:700,710` and stored by
  `_make_lepton` at `:204`. Nothing downstream records the rename. `static/js/expr.js:34-44`
  gives every property a unit and a histogram range preset — **check what it claims for `d0`**.
  If it says millimetres, that is a live mislabel in student-facing text, not future work. Also
  explains why the truth deck's M-4 axis runs 300–2000, which is absurd for a length.
  _(truth deck, slide 7)_
- **N2 Fixture has no new physics and no `X4`/`X5`** (backend; blocks running M-3 or M-4 offline).
  `tests/fixtures/datasets/IDEA/91GeV/` holds `X1`, `X2`, `X3`, `data` only. Both searches look
  for an excess **in `data`** over the stack, so authoring or reviewing either mission end to end
  needs a fixture whose `data` actually contains the signal, plus `X4`/`X5` for a faithful
  background. A task against B-018's `tests/fixtures/make_fixture.py`. _(truth deck, slides 6-7)_
- **N9 `test_observable_mode_is_config_not_identity` is flaky under the full suite** (frontend).
  `tests/e2e/test_graph.py:281`. Observed failing once in a full run and passing on rerun, standalone, and
  `tests/e2e` alone — **twice, independently: by me and by PR #56's reviewer**, on branches that touch no frontend
  file. May be N7's port contention or may be genuine; N7 is the cheaper hypothesis to rule out first. Until then it
  will keep costing false cycles. _(B-029 c2 review + orchestrator, 2026-09-22)_
- _(CLOSED by B-030, #65, `b6011c4`)_ **N10 One dead line and a false docstring clause in `test_fixture_dataset.py`** (backend, trivial).
  `:139-141` — `monkeypatch.setenv` does *not* cover `run_physics_loop`'s cache/output resolution; the `env` dict
  does (`driver.py:162` → `analytical_loop.py:266` → `paths.py:27`). Proven: forcing `setenv` to a bogus dir leaves
  the test passing. Delete the line and the `monkeypatch` parameter, cut the docstring to its first sentence.
  Rides along on any later backend touch of this file. _(PR #56 c2 F5)_
- _(CLOSED by F-018, #69, `427a0f2`)_ **N11 The expanded-state chevron is written twice and nothing checks they agree** (frontend, two lines).
  `shell.js:43-44` + `shell.html:20,88` — once as the template's `&#8249;`/`&#8250;`, once as `glyphs[0]`.
  Transposing a pair leaves all 77 e2e tests green. Fix: read the expanded glyph from the DOM at wire time
  (`const expandGlyph = glyph.textContent;`) and pass only the collapsed one. Not gating — the value is
  `aria-hidden` decoration and the screen-reader text is derived separately. _(PR #57 c2 F4)_
- _(CLOSED by D-025, #70, `585bc1e` — CSS-only branches; the e2e-guard half is N33)_ **N5 `verify.py`'s `check_git_diff` gives every design task three false reds** (design/tooling).
  `docs/design-explorations/verify.py:1936` enforces a D-002-era invariant that a branch touches nothing under
  `src/` except `tokens.css` and the fonts. Any task editing any other `src/` stylesheet trips `git-diff-clean`
  (twice) and `bench-git-diff-clean`, regardless of correctness — verified on D-019: clean `main` gives
  `['board-lane-fill']`, D-019's branch gives four. Either widen the exemption to the shipped `static/css/`
  stylesheets or retire the check. Until then **every design dispatch must state the expected red set, not
  "exactly one"** — I got that wrong on D-019's C4. _(D-019, 2026-09-22)_
- _(CLOSED by F-018, #69, `427a0f2`)_ **N6 PR #55's F8 is still open, and it is frontend's** (frontend, trivial).
  `tests/e2e/test_interior_style.py:3-11,28-32` — module docstring retells review history and calls a committed
  script "uncommitted"; function docstring repeats a mutation transcript. One line each. D-019 could not take it
  (design owns no Python) and **my dispatch wrongly said it lived in `observable.css`**. _(PR #55 F8)_
- **N7 The e2e suite is not safe to run concurrently across worktrees** (process note, no code change).
  Two full suites running at once in different worktrees contend on the live-server port: I saw
  `test_observable_mode_is_config_not_identity` fail in a full run that overlapped another worktree's suite, then
  pass 3/3 in isolation, 77/77 in e2e-only, and 728/728 on a clean re-run. **Gate one PR at a time**, or a green
  branch will look red and cost a false cycle. _(orchestrator, 2026-09-22)_
- **N8 `.venv` is an editable install rooted at the primary checkout** (process note, no code change).
  Running the suite from any other worktree silently imports `src/fce_web` from the **primary checkout** unless
  `PYTHONPATH=<worktree>/src` is set — so a worktree's own source changes are not what is being tested. PR #56's
  reviewer lost a run to exactly this, and it would silently certify the wrong tree rather than error. Every
  dispatch and every review that runs outside the primary checkout should set it. _(PR #56 review, 2026-09-22)_
- _(CLOSED by B-030, #65, `b6011c4`)_ **N4 Two backend-owned comments now say something false** (backend, trivial, fold into any
  future fixture task). `tests/fixtures/README.md:24` and `tests/fixtures/make_fixture.py:55-56`
  both say `X4`/`X5`/`X6` "are undocumented". `X4` and `X5` were identified 2026-09-22; only `X6`
  still is. The *decision* they justify — keeping them out of the fixture — is unchanged, so this
  is wording, not behaviour. Not worth its own task. _(truth deck)_
- **N3 `X6` is unidentified** (needs the user, blocks nothing). Seven sample files exist upstream,
  not six; the truth deck covers `X1`-`X5` only. `X6` is absent from the committed fixture and no
  mission needs it, but `tests/fixtures/golden/zpeak-dilepton.json` already carries its bins. Ask
  the next time a physics question goes to the user; not worth a round trip of its own.

---

## Dropped in the sweep, and why

- **All `docs/wireframes/` items** (D-001) — superseded 2026-08-16; the directory is a record.
- **All `docs/design-explorations/` items** (D-003, D-004, D-005, D-007, D-008, D-009, D-010, D-013,
  D-002 m5/m6, `check_no_fabricated_identifiers`) — exploration pages are historical; the shipped
  app is in `src/`. Their lessons are already in the manuals.
- **PR-body-only corrections** (B-007, B-012 m2, B-024 F4, D-004, D-005 m7/m8, D-009 m4, D-013 m4) —
  merged PR bodies are history.
- **`get_fce_home()` ignoring `env`** (B-011 c2, B-018, B-023 candidate) — closed by B-024.
- **B-015 m2** (observable exprs not gated) — closed by B-026, which compiles Selection/Observable
  expressions at submit.
- **F-004 F8, D-010 m3** (pagers do nothing) — closed by F-010 + D-017.
- **B-018 fixture readability** — closed by B-025. **F-007 F11** — closed by D-016.
- **B-005 monkeypatch lesson, `comm -23` instrument** — already promoted into the manuals.
- **B-003 test restructuring** (conftest helper move, stuck-navigation wiring test,
  `NavigationStuckError`), **B-002 external-host sweep** (mitigated by B-003's e2e request check),
  **B-013 m1 conftest `__debug__` guard**, **B-012 m6**, **B-007 perturbed-doc test** — churn with
  no defect behind it; ponytail says no.
- **`--node-observable` token** (D-013) — check folded into D-019; drop if it exists.

- **N19 The primary checkout's venv pins `fce_web` to the primary checkout's `src/`, so it CANNOT
  test any worktree's code** (tooling; it silently falsified an orchestrator gate). Found on F-014's
  gate, 2026-09-23. **This entry's first version blamed a playwright version skew. That was wrong,
  and it is recorded because the wrong diagnosis was plausible and cost the coder a round trip.**
  `.venv/lib/python3.12/site-packages/__editable__.fce_web-0.1.0.pth` is a plain path entry reading
  `<primary checkout>/src`. `conftest.py` inserts only the repo root, never `src/`, so nothing
  overrides it. Run pytest from a detached worktree with that venv and **pytest collects the
  worktree's test files (path-based) while the app served to the browser is the primary checkout's
  `src/` — i.e. `main`.** The branch's JS is never exercised. Confirm with
  `.venv/bin/python -c "import fce_web; print(fce_web.__file__)"` — it prints the primary path with
  cwd inside the worktree.
  **What it looked like:** F-014's gate reported 2 failed / 719 passed against the coder's 721; both
  failures were the wrong app being served. Re-run with the head checked out **detached in the primary
  checkout**, it is **721 passed, flake8 0** — the coder's numbers, exactly.
  **The version skew is real but was not the cause:** worktree venvs resolve playwright **1.63.0
  (chromium-1243)**, the primary **1.62.0 (chromium-1234)**, both builds in the shared cache. The
  coder re-ran the branch on both and got 721 on each, so the fix has no browser dependency.
  **Procedure fixed in `orchestrator/CLAUDE.md` §5.1.** A real fix is still open: pin playwright and
  make a per-worktree `pip install -e .` explicit in the dispatch template, or have `conftest.py`
  prepend the repo-local `src/`. Doing it properly needs the U1 dependency sign-off.
  _(orchestrator, 2026-09-23)_

- _(CLOSED by F-018, #69, `427a0f2`)_ **N20 `shell.js:60-62` re-reads state the setter is already idempotent about** (frontend, trivial).
  The drawer auto-expand does `getElementById("drawer")` a second time and guards on
  `dataset.state === "collapsed"` → `addEventListener("click", () => setDrawer(true));`, one line.
  _(PR #62 F1, 2026-09-23)_
- _(CLOSED by F-018, #69, `427a0f2`)_ **N21 `test_smoke.py:382`/`:397` loop the same matrix twice** (frontend, tests). C1's 12 probes are a
  strict subset of C5's 24 → fold `assert rect["width"] == width` into the C5 loop and delete the
  other loop (~16 lines). The reviewer confirmed both mutations still bite from the merged loop.
  _(PR #62 F2, 2026-09-23)_
- _(CLOSED by F-018, #69, `427a0f2`)_ **N22 Jinja header comment in `shell.html:1-27` restates task history** (frontend, trivial). ~27 lines
  repeating N12/N13/N14 ids and PR deviations → keep only the overlay/`data-state` contract and
  "pan/zoom is F-016's". _(PR #62 F5, 2026-09-23)_
- _(CLOSED by F-016, #67)_ **N23 Nested region landmarks in the results drawer** (frontend, **accessibility**).
  `shell.html:105`/`:107` — `<section id="drawer" aria-label="Results drawer">` wraps
  `<section id="results" aria-label="Run results">`, so a screen reader announces two nested regions
  where one is meant. Drop the inner `aria-label` (nothing in `src/` or `tests/` queries it, grep
  confirmed) or make `#results` a `<div>`, keeping the id `run.js` and the tests use.
  **Introduced by F-015 and carried into F-016's dispatch rather than left to rot here** — accessibility
  is on shared §6's never-simplify-away list. _(PR #62 F3, 2026-09-23)_
- _(CLOSED by F-018, #69, `427a0f2`)_ **N24** _(seen again on #67's review 2026-09-23; the reviewer suggests the focusable, scrollable `#canvas-wrap` may add timing sensitivity, so wait on `[open]` before pressing Space)_ **`test_observable_mode_is_config_not_identity` is flaky on `main`** (frontend, tests; **pre-existing**).
  `test_graph.py:328`, ~1 failure in 10 file-level runs, reproduced by the reviewer on `origin/main`
  as well as on PR #62's branch; 12/12 green in isolation. `.focus()` + Space on the `ObsGlobal` radio
  sometimes does not take, leaving `mode == "ObsVectorSum"`. Presumed fix: await the radio's checked
  state rather than firing a bare key press. **Consequence: the 726 suite floor is a true count but not
  a stable green** — do not read a single clean run as proof, and do not let a future task "fix" it by
  deleting the assertion. _(PR #62 F4, 2026-09-23)_

- _(CLOSED by D-025, #70, `585bc1e`)_ **N25** — `shell.css:117` (D-022 #63 F7): `padding-right: var(--panel-w)` does not shrink `.canvas-svg`, which keeps its own 704x512 box, so F4's defect survives symmetrically on the right — at 1024 the svg's top-right corner resolves to `.mission-panel__head`; at 768 its right edge (x=896) is 128px past the viewport. **Unlike the left edge this content IS reachable**, via `#canvas-wrap`'s horizontal scroll, which is why it did not block the merge. Either extend C11's probe to the top-right and clear it, or record right-edge coverage as accepted-because-scroll-reachable so the next reviewer does not re-derive it. Likely subsumed by **F-016**'s real pan surface.
- _(CLOSED by D-025, #70, `585bc1e`)_ **N26** — `tests/e2e/test_canvas_style.py:83` (D-022 #63 F8): the selector `'.palette, .palette__head, .mission-panel'` carries two terms that can never fire — the probe only samples the top-left, so `.mission-panel` is unreachable, and `.palette__head` is a descendant of `.palette` so `closest('.palette')` already matches it. Cut to `closest('.palette')`, or add N25's right-edge probe and earn the `.mission-panel` term. Design-owned.
- _(CLOSED by D-025, #70, `585bc1e`)_ **N27** — `shell.css:117` (D-022 #63 F9): the canvas inset is pinned to the palette's **expanded** footprint regardless of `data-state`, so collapsing the palette (256 -> 64px, measured) reclaims no canvas — a 192px dead gutter at 1440, 128px at 768. **The collapse control currently buys the student nothing.** Fix is one rule driving the custom property off state (`.frame:has(.palette[data-state="collapsed"]) { --palette-w: ... }`), or a `ponytail:` line recording the trade-off so it is not re-litigated. Design-owned.
- _(DROPPED 2026-09-23: it corrects a stale line in a merged PR body, and no code changes)_ **N28** — PR #63 body, C6 (D-022 #63 F10): the evidence line claims `grep -rn 'zoom' src/fce_web/static/css/` is empty, but cycle 2's own comment reintroduces "pan/zoom" at `shell.css:121,123`. **The criterion is met and the code is correct** — only the stated check is stale. Restate it as the check actually made: `grep -rn 'zoom-controls' ...`. Documentation-accuracy only.
- _(CLOSED by F-019, #71, `4a9a198`)_ **N32** — `tests/e2e/test_graph.py:353-360` (F-018 #69 F1): the 7-line comment above `expect(summary).to_be_focused()` repeats the neighbouring test's comment; cut it to 1 line. Frontend, trivial.
- _(CLOSED by F-018, #69, `427a0f2`)_ **N31** — `graph.js:257-265` (F-016 #67 F2): `wirePan` ignores `pointercancel`, so a cancelled pan (touch, alt-tab) leaves `is-panning` and the move listener attached. Replace the `pointerup` listener with one `lostpointercapture` (the capture is on `els.wrap`). Frontend, trivial.
- _(CLOSED by D-024, #68, `c2b7b0c`)_ **N30** — `shell.css:156` (D-023 #64 F1): `.zoom-controls { z-index: 3 }` is inert — mutated to 1/auto the guard stays green; the centred toolbar never overlaps a panel. Delete it and the "needed" clause at `:147`. Design, trivial.
- _(CLOSED by D-025, #70, `585bc1e`)_ **N29** — `shell.css:47-50` (D-022 #63 F11): `main { display:flex; flex-direction:column; height:100svh }` is **unscoped**, and `main` lives in `base.html:17` — i.e. every future page, not just the shell. No consequence today because `index.html` is the only page. **Scope it before a second template lands** (a class on the shell's own wrapper, or `main:has(.frame)`). Latent; cheap now, a confusing layout bug later. Design-owned.
- **N33** — `verify.py:1929` (D-025 #70 F3): N5 is half fixed. A design branch that also edits its own `tests/e2e/test_*_style.py` guard still gets false reds from `check_git_diff`. Widening the exemption to design-owned `*_style.py` files is a **policy question** (shared §4 gives design no `tests/e2e` ownership, yet D-022/D-023/D-025 each wrote one). Needs a ruling before any code.
- **N34** — **CLOSED by D-026 (#72, `153c1aa`).** D-025 #70 F1/F2/F4/F5, design cleanups: `verify.py:1925-1935` two prefix constants → one tuple with `startswith(tuple)`; `verify.py:1945,1978` label still says "D-002 token + font deliverables" → "design-owned static/css + fonts"; `test_canvas_style.py:66-78` rect/shift arithmetic checks the border box, not C1's claim → read padding before and after collapse and assert it shrinks (~8 lines fewer); `shell.css:90-95` and `test_canvas_style.py:108-113` 6-line rationale comments → 1 line each. Design, trivial.
- _(CLOSED by B-035, #77)_ **N35** — `store.py` (B-033 #73 F1-F3): `:175` dead `counts = None`; `:141-153` `purge_class` pre-checks `class_exists` on a second connection (check-then-act) → raise `ValueError` when `classes == 0` after the deletes; `:130` `ORDER BY completed_at` → `ORDER BY rowid`. Backend, trivial. **Folded into B-034.**
- **N36** — `tests/e2e/test_graph.py::test_keyboard_pans_the_focused_canvas_on_both_axes` fails ~1 in 3 full-suite runs (my #73 gate, #74 c2 review), 3/3 green alone on branch and on main. Order/load-dependent flake, possibly N7 port contention. Frontend; de-flake like N24, never by weakening the assertion.
- **N37** — `graph.py:94-97` (B-031 #74 F6): 4-line comment over the one-line `OBSERVABLE_MODES` alias → one line. Backend, trivial. **Folded into B-032.**
- **N38** — B-032 #75 F1-F3: `graph.py:416-419` card-gating half of C3 has no test (add `allowed_cards=("Multiplicity",)` → `GraphError` with `node_id` to the C3 test); `routes/api.py:90` dead `if mission else None`; `jobs.py:60-66` 7-line comment → 1. Backend, trivial. **Folded into B-034.**
