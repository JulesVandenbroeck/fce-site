# Backlog

Two things land here:

1. **Suggested-minor** review findings — always, automatically. They never block a task.
   Group them by area; the orchestrator raises a single cleanup task per area once a group
   is worth sweeping.
2. **Suggested-major** findings the coder overruled on the grounds that they belong to a
   different future task. Record the coder's argument alongside, so the decision is
   auditable later.

Entries carry the task ID they came from, so context is recoverable.

**This file is not loaded by `/orchestrate`.** It is a working list, not session state — read
it when you are planning a cleanup task or filing a new finding, not at startup. For the
count alone:

```bash
grep -c '^- \*\*' .claude/tasks/backlog.md
```

| Area | Items |
|---|---:|
| Backend | 15 |
| Frontend | 4 |
| Design | 6 |
| Design explorations (`docs/design-explorations/`) | 13 |
| Design explorations — D-004 (Beamline) | 7 |
| Design explorations — D-008 | 1 |
| Cross-cutting | 1 |
| **Total** | **47** |

*Counts are a convenience, not a contract — regenerate with the command above rather than
trusting this table. (§2: never write a count you did not enumerate.)*

---

## Backend

- **`.flake8` `exclude` omits `.venv`.** `.flake8:16`. The list replaces flake8's defaults,
  so a bare `flake8 .` from the repo root reports ~40,000 errors, all from `.venv/`. The
  specified `flake8 src/ tests/` is clean so nothing is blocked today, but CI or a
  pre-commit hook running `flake8 .` would be unusable. Fix: add `.venv, venv` to the
  exclude line. _(from B-001 review)_
- **PyYAML is only a transitive dependency.** `pyproject.toml:27`. `import yaml` works
  today solely because `pyhf` pulls it in. `missions.py` will need it directly per shared
  §7 — declare it explicitly rather than inheriting it by accident. _(from B-001 review)_
- **No `README.md`.** Packaging metadata has no long description, and the repo has no entry
  point for a human arriving cold. _(from B-001)_
- **No CI workflow.** `.flake8` excludes `.github`, implying one is expected. A workflow
  running `pytest` + `flake8` on push would catch regressions the reviewer currently
  catches by hand. Depends on the `.venv` exclude fix above. _(from B-001)_
- **`templates/` and `static/` do not survive a wheel build.** `pyproject.toml:52`.
  `[tool.setuptools.packages.find]` has no `package-data` and there is no `MANIFEST.in`, so
  `pip wheel --no-deps --no-build-isolation .` produces a wheel containing only
  `fce_web/__init__.py` and `dist-info/*` — an installed `fce-web` would have no page shell
  to render. Harmless while the app runs from the source tree, but it must be fixed before
  anyone installs this for a classroom. Verified by the reviewer, not merely suspected.
  _(from F-001 review; needs a back-end task, `pyproject.toml` is back-end owned)_
  **Raised again as suggested-major on B-002 and overruled there, in writing** — the
  orchestrator accepts the argument: the fix needs `[tool.setuptools.package-data]` or a
  `MANIFEST.in`, both outside B-002's scope of "only the httpx entry"; B-002 neither
  introduced it nor can own it, since mounting a package-relative `static/` is correct and
  it is the build config that is incomplete; and the gap applies equally to `templates/`,
  `static/` and `content/missions/*.yaml`, so a proper fix wants a build-a-wheel-and-inspect
  test covering every data file type. Three independent confirmations now. Nothing is
  blocked meanwhile: source checkouts, editable or not, are unaffected.
- **`httpx` is deprecated for `starlette.testclient`.** Starlette 1.6.0 emits
  `StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated;
  install 'httpx2' instead.` One warning, no failure, so nothing is blocked. Switching the
  dev extra to `httpx2` is a dependency decision and needs user sign-off, exactly as `httpx`
  itself did. _(from B-002)_
- **The module-level-state guard is allow-by-default.** `tests/test_app.py:45-48`.
  `MUTABLE_CONTAINERS` / `PER_APP_TYPES` enumerate the types they reject, so the scan only
  catches shapes it already knows: the reviewer showed a module-level `threading.Lock()` or
  a custom registry object holding a `dict` passes clean. The reference repo's defect was a
  `dict` and would be caught, but the next one need not be. Invert it to default-deny —
  allow only inert types (`str`, `int`, `float`, `bool`, `bytes`, `tuple`, `frozenset`,
  `Path`, module, class, function) and reject the rest — matching how the same principle is
  applied in `safe_eval`. _(from B-002 review)_
- **The external-host sweep does not sweep what it promises.** `tests/test_app.py:100-118`.
  `_swept_paths()` derives routes from `app.openapi()["paths"]` plus top-level `app.routes`,
  so a route registered `include_in_schema=False` escapes entirely — the reviewer confirmed
  by adding one serving a `fonts.googleapis.com` link and watching the test pass. Worse,
  `SWEPT_STATIC_PATHS` (`tests/test_app.py:72`) is a hand-maintained tuple of one entry, so
  **the `static/css/*.css` that D-002 is about to add is not swept at all** — and
  `@import url(https://fonts.googleapis.com/…)` is the single most likely future §3 breach.
  Fix: walk `STATIC_DIR` for text-suffixed files, and either include `include_in_schema=False`
  routes or assert none exist. Failing that, soften the docstring, because its promise is
  what the next coder will trust. **Partly mitigated by B-003**, whose browser-level e2e
  assertion catches anything the page actually fetches, including `@import`. _(from B-002
  review)_
- **A leaked server thread dies quietly.** `scripts/screenshot.py:130` —
  `thread.join(timeout=SHUTDOWN_TIMEOUT)` discards its result, so a server that fails to stop
  within 10 s leaks with no signal. That undercuts the stated reason `SERVER_THREAD_NAME`
  exists ("a leaked one is identifiable"): checking `thread.is_alive()` after the join and
  raising or warning would make the leak as loud as the naming intends. _(from B-003 review)_
- **`printed_paths` splits on whitespace, not lines.** `tests/e2e/test_smoke.py:213` uses
  `self.completed.stdout.split()`, while the tool's contract is one path per line. A path
  containing a space would be silently split in two and the width assertions would fail in a
  confusing way. `splitlines()` matches the contract. _(from B-003 review)_
- **e2e helpers live in `conftest.py`.** `tests/e2e/test_smoke.py:31` imports `LoadedPage`,
  `off_origin_requests` and `REPO_ROOT` from `tests.e2e.conftest`. It works, but it is
  against pytest's own guidance; moving them to a plain `tests/e2e/harness.py` would leave
  `conftest.py` holding only fixtures. _(from B-003 review)_
- **The stuck-navigation guard is tested at the helper, not at the wiring.**
  `scripts/screenshot.py:240` — the three cycle-2 tests call `_goto_or_raise` directly, and no
  test drives `capture()` against a stuck page. The reviewer showed that reverting that one
  line to a bare `page.goto(url, wait_until="networkidle")` **leaves all 49 tests green** while
  silently restoring the raw-traceback behaviour the cycle existed to fix. The wiring is
  correct today — the reviewer drove `main()` through it — so this is coverage insurance, not
  a defect. A test invoking `capture()` against `_stuck_fetch_server` with a shortened
  `NAVIGATION_TIMEOUT_MS` would close it. _(from B-003 review, cycle 2)_
- **`RouteNotServedError` asserts the opposite of what happened.** `scripts/screenshot.py:219`
  — a stuck page raises it, but the route *was* served; it just never went idle. A sibling
  `NavigationStuckError(ScreenshotError)` would let the class name carry the meaning the
  message already carries, while `main()`'s single `except ScreenshotError` keeps working
  unchanged. _(from B-003 review, cycle 2)_
- **Vectorise `and` / `or` in `safe_eval`.** In the reference engine any expression containing
  `and` raises numpy's "truth value of an array is ambiguous" inside the vectorised path
  (`engine/path_filter.py:255`), is swallowed by the bare `except Exception: pass` at `:262`,
  and silently falls back to the per-event Python loop. So `l1.pt > 20 and l2.pt > 10` — the
  single most common shape a student will type, and the reference's own documented example
  (`fce.py:151-171`) — **never hits the fast path**, and nothing anywhere says so. Once
  `safe_eval` owns the AST it can rewrite `BoolOp` to `&`/`|` when the operands are arrays.
  Large speedup, and it changes no number a student sees. Offered to the user 2026-08-20 as a
  third option for B-006 and not chosen, to keep M2's evaluator minimal-risk. _(from M2
  planning, not a review)_
- **Dependencies unpinned, no lock file.** Fine now, but a scientific-Python stack drifts.
  Worth resolving before classroom deployment so a teacher's install matches the tested
  one. _(from B-001)_

## Frontend

- **Skip link ("skip to main content")** plus the visually-hidden class it needs, once
  navigation or site chrome exists. _(from F-001)_
- **`aria-live="polite"` containers** for run progress and results, when those views are
  built in M3. Progress that streams silently to a screen reader is progress that does not
  exist. _(from F-001)_
- **`<header>`/`<nav>`/`<footer>` landmarks** in `base.html`, once there is anything to put
  in them. F-001 deliberately shipped without them rather than emit empty landmarks.
- **Offline HTML validation.** No `tidy` or `vnu` on this machine, so template validity
  currently rests on the browser parse. A pip-installable validator in the e2e suite would
  make it checkable. _(from F-001; needs a backend task, `tests/` is backend-owned)_

## Design

> **`docs/wireframes/` was superseded 2026-08-16 by the node-graph pivot** (see `design.md`
> D-001). Every design entry below that names a file in that directory is now **closed, not
> pending** — the directory is the record of a decision that was really made, and it will not
> be reopened, so its one open `Required` finding is permanently parked. The entries stay
> because two of them describe *habits* worth carrying into `docs/design-explorations/`:
> placeholder text must meet AA, and selection state needs `aria-current`, not a class alone.

- **`docs/wireframes/brain/design-taste.md`** is the wireframe skill's colour-phase
  reference, copied unmodified and unused in phase 1. Keep it only if a phase-2 run is ever
  wanted; otherwise delete. _(from D-001)_
- **Mission-1-only layout hybrid, worth playtesting rather than assuming:** run mission 1
  as mission-screen Option 3 (Focus Stage — its stepped rail is the best teaching device of
  the five) and hand the student the full spread from mission 2 on. Not drawn, and not
  recommended without evidence. _(from D-001)_
- **Two ideas from the losing builder options**, worth carrying into whichever wins:
  Option 5's face-down locked cards as the way to show card gating, and Option 3's per-step
  "events kept: 18 420 of 240 000" preview, which turns an abstract cut into a number that
  moves before the run is even started. _(from D-001)_

- **D-001's self-describing claims are exhaustive, and therefore fragile.** `README.md:65-66`
  and `base.css:21-25` state "no third value exists anywhere in the directory" / "two stacks
  across the whole directory", but a computed `font-family` sweep finds three: `sans-serif`
  (8329 elements), `ui-monospace, "DejaVu Sans Mono", monospace` (156), and bare `monospace`
  (1) on the `<code>sans-serif</code>` element at `index.html:80`, which no author rule
  covers. **This was a `Required` finding on cycle 4, merged over on the user's explicit
  override** — see `design.md` D-001. The acceptance criterion is unharmed (`monospace` is a
  generic keyword, not a typeface), so only the sentence is false.
  Fix, if these files are ever touched again: add a `code` rule to `base.css`, **and** strip
  the exhaustiveness from every self-describing claim, since it is the "anywhere in the
  directory" phrasing that keeps manufacturing defects. Four review cycles found four of
  these; a fifth would likely find a fifth. _(from D-001 review, cycle 4)_
- **Placeholder text below AA.** `docs/wireframes/mission-screen.css:77` —
  `input::placeholder { color: #999 }` is 2.85:1 on white, the only text in the wireframes
  below AA. Acceptable in a throwaway document depicting a placeholder *state*, which is why
  it was minor — but **real placeholders must meet AA, so this pattern must not be carried
  into D-002.** `#767676` gives 4.54:1 and still reads as washed out. _(from D-001 review)_
- **Active tab state is class-only.** `docs/wireframes/mission-screen.html:20-25` and
  `recipe-builder.html` — selection lives in `class="tab-btn active"`, so keyboard operation
  and focus are fine but a screen-reader user cannot tell which option is displayed.
  `aria-current="true"` on the active button, removed alongside the class in the click
  handler, closes it. Worth carrying as a habit into real tabbed UI. _(from D-001 review)_

## Design explorations (`docs/design-explorations/`)

From the D-003 cycle-1 review. All four are suggested-minor and block nothing; the two
minors about the checker's *honesty* were fixed in cycle 2 instead of landing here.

- **Bin hit-areas are buttons that do nothing.** `plot.js:358` — the 40 bin hit-areas carry
  `role="button"` but have no click/Enter/Space handler; the only behaviour is
  announce-on-focus/hover. Confirmed in the CDP accessibility tree: 40 nodes announce as
  buttons and do nothing when activated. `role="img"` with the same `aria-label`, or no role
  at all, would describe what they actually are. Becomes a real defect the moment hover
  readout / legend toggling is built. _(from D-003 review)_
- **ARIA tablist declared, keyboard pattern not implemented.** `plot.html:19-24` —
  ArrowRight on `#tab-hist` moves neither focus nor `aria-selected`; inactive tabs keep
  `tabindex="0"`; the tabpanels have no `tabindex`. Nothing is unreachable (both tabs are Tab
  stops), so it is a pattern mismatch rather than a blocker. Worth fixing before this markup
  is copied into D-004, which will have more tabs. _(from D-003 review)_
- **The exhaustive-claim lint is a phrase denylist, not a general check.**
  `verify.py:978` — `EXHAUSTIVE_CLAIM_PATTERNS` is six phrases tuned to D-001's specific
  wording, so it supports a general criterion with a specific check. The reviewer grepped and
  confirmed the three remaining header claims in `plot.css:1`, `frame.css:8` and `plot.js:12`
  are **true**, and are claims about source text rather than about rendering, so the criterion
  holds on its wording. The honest fix is to say in the PR body what the lint actually is.
  _(from D-003 review)_
- **Interactivity the brief asks for and D-003 did not build:** hover reads out a bin, and the
  legend toggles samples (`docs/design-brief.md` §5). Deliberately out of D-003's scope, which
  was anatomy and measurement. Also unbuilt: a sub-768 legend reflow, and the reference's
  green "Discovered: …" badge (`engine/plotter.py`). _(from D-003)_
- **Parity to the reference is asserted, not checked.** ~~The D-003 reviewer declared this
  limit itself: the engine is not vendored into this repo yet, so anatomy was verified
  against the rendered DOM only, never against `engine/plotter.py`.~~ **Closed 2026-08-16 by
  the cycle-3 review**, which located `fce-project/fce/engine/plotter.py` outside the repo and
  rendered it from D-003's own `payload.json` through the reference's code path. It found four
  parity gaps nobody had seen. **The method is the lesson: "at parity" is only checkable by
  rendering the reference and diffing** — every future parity criterion must name that as its
  verification, exactly as D-001's colour criterion had to name "enumerate computed styles in
  a browser". Once M2 vendors the engine this becomes a test rather than a review technique.
  _(from D-003 reviews, cycles 1 and 3)_

From the D-003 cycle-3 review. Three suggested-minor; none blocks.

- **ARIA tablist declared, keyboard pattern still not implemented.** `plot.html:19-24` with
  `plot.js:658-674` — both tabs sit in the tab order and ArrowRight on `#tab-hist` leaves
  focus where it is. Raised in cycle 1, re-confirmed in cycle 3, still open. Either add roving
  `tabindex` + arrow handling or drop the tab roles for plain buttons. **Do not copy this
  markup into D-004**, which will have more tabs. _(from D-003 review, cycles 1 and 3)_
- **`--ink-45` is below AA and unmarked.** `tokens.css:42` — 2.60:1 composited on paper, used
  by 0 elements, so it passes only because nothing uses it. A comment marking it non-text-safe
  would stop D-002 reaching for it. This is the third time this token has been flagged; it is
  already recorded as *owed to D-002* in `design.md`. _(from D-003 review, cycle 3)_
- **OPEN `Required` FINDING, MERGED OVER ON THE USER'S OVERRIDE 2026-08-17.**
  `plot.js:106` — the main-panel y-axis majors are **step 2000** where the reference is
  **step 1000**. PR #5's criterion 1 ("y-limits *and major ticks* match the reference") is
  ticked and is half false; the limits do match, to 0.05%.
  *Reproduction:* render `engine/plotter.py` from `docs/design-explorations/payload.json` and
  read `ax.get_yticks()`, or more cheaply — this is how the orchestrator confirmed it —
  `AutoLocator` on `0..8635.47` returns `[0, 1000 … 8000]`. The DOM has `[0, 2000, 4000,
  6000, 8000]`.
  *Cause, and it is not what the code says:* `niceCeilingAndStep` computes `max = 8630.71`,
  `magnitude = 1000`, and rejects step 1000 because `8630.71 / 1000 = 8.63` fails the
  hard-coded `if (max / step <= 8)`. The comment above it calls this an inherent
  approximation of matplotlib's two-stage process. It is a tunable constant.
  *Fix:* `<= 8` → `<= 9`, which matplotlib's own `AutoLocator` effectively uses (bin budget
  9 over `steps = [1, 2, 2.5, 5, 10]`). The reviewer verified this lands bit-identically on
  the reference's ticks for this payload. Re-tick criterion 1, or un-tick it and rule the
  step a deviation.
  *Do this if `plot.js` is ever touched again* — and note it pairs with the suggested-major
  below, since the same function is the subject. _(from D-003 review, cycle 4)_
- **Three of the five tick-ladder rungs are unreachable, and a comment says otherwise.**
  `plot.js:87,103-108` — `magnitude = 10^floor(log10(max))` forces `max / magnitude ∈ [1, 10)`,
  so `s = 1` returns whenever the ratio clears the cap and `s = 2` always returns otherwise
  (ratio/2 < 5). `2.5`, `5`, `10` and the `return { max, step: 10 * magnitude }` fallback are
  dead under either cap. **Confirmed by the orchestrator.** The comment's "keeps the same
  five-multiplier ladder" therefore describes code that does not exist, and the dead rungs are
  *why* the axis can only land on 1× or 2× magnitude — so the next person tuning it will
  mis-diagnose it exactly as this cycle did. Suggested-major, unfixed at merge.
  _(from D-003 review, cycle 4)_

From the D-003 cycle-4 review. Four suggested-minor; none blocks.

- **`REFERENCE_PEAK_FRAC` is printed but never compared.** `verify.py:502,522` — the assertion
  is a hand-picked window `0.80 <= peak_frac <= 0.98` (±9 points) while real agreement is
  0.9259 vs 0.9254. A reference-derived tolerance (`abs(peak_frac - REFERENCE_PEAK_FRAC)
  <= 0.02`) would make the check actually about the reference and would still have caught the
  0.40 regression. The constant being *displayed* rather than *used* is the same shape as the
  cycle-1 finding. _(from D-003 review, cycle 4)_
- **All 40 bin rects are individual tab stops.** `plot.js:410-420` — a keyboard user traverses
  40 stops to get past the figure. The usual pattern is one stop for the plot with arrow keys
  moving between bins. Interacts with the tablist minor below; worth doing together once
  D-004 settles the surrounding layout. _(from D-003 review, cycle 4)_
- **The PR #5 body still carries counted-exception phrasing** in its retained cycle-3 history
  ("two named exceptions", "state both exceptions") — the exact wording the new lint forbids.
  Clearly framed as an unedited historical record and superseded by the cycle-4 section, but
  **the lint scans only the five directory files and the PR body is also a place deviations
  are recorded**. Worth knowing the lint's blind spot is the PR itself. _(from D-003 review,
  cycle 4)_
- **The y-scale linearity check has two samples.** `verify.py:476` — `px-per-unit` is measured
  at `[-0.0144, -0.0144]` because the axis carries only three major ticks, so it cannot
  distinguish linear from most non-linear scales. Note the coupling: if Required 1's y-scale
  fix lands, the axis gains major ticks and this check gets stronger for free. _(from D-003
  review, cycle 3)_

## Design explorations — D-004 (Beamline)

From the D-004 cycle-1 review. Three suggested-minor; none blocks. The other two minors were
folded into cycle 2 — one because it shares a CSS rule with a `Required` fix, one because it
is a false provenance claim in `tokens.css`, the file D-002 harvests.

- **The page is a classic script, so everything is global.** `beamline.html:177` —
  `<script src="beamline.js"></script>` makes `NODE_KINDS`, `VALID_CONNECTIONS`, `graphState`,
  `els` and every top-level function global bindings. Shared §6 asks for ES modules and no
  globals, and `type="module"` costs nothing on a `file://` page. **Not fixed in cycle 2
  deliberately** — the propagation is better stopped at the source, so D-005's and D-006's
  acceptance criteria name `type="module"` outright rather than letting the pattern be copied
  twice and swept later. _(from D-004 review, cycle 1)_
- **`<div>` where a semantic element exists.** `beamline.html:41` wraps a labelled region and
  `beamline.html:57` wraps a palette item; shared §6 names `<section>` and `<li>`. Also
  `aria-disabled="true"` on a non-interactive `<div>` conveys nothing to assistive tech — the
  visible "locked" text is doing the real work. _(from D-004 review, cycle 1)_
- **Locked-tile copy reads as a run-on.** `beamline.html:58` — "**LOCKED** Node kind — opens
  in a later mission" starts the sentence with the badge word. Shared §1 asks for copy simple
  enough to read as a second language; separating the badge from the label would help.
  _(from D-004 review, cycle 1)_

- **Hover previews the armed state on every port the pointer crosses.**
  `beamline.css:265-272` — `.port--armed` and `.port:hover:not(.port--absent)` both set
  `border-color: var(--graphite-blue-strong)`, so hovering an unarmed port produces the armed
  colour. Width and scale steps still separate them. Left out of cycle 3 deliberately: it is a
  judgement call best settled when the palette is re-tuned for colour-vision deficiency, since
  that work moves the same colours. _(from D-004 review, cycle 2)_

From the D-004 cycle-3 review. Three suggested-minor; none blocks. The first is folded into
**D-008** as an acceptance criterion rather than left here; the other two are PR-body accuracy
and are historical now that #6 is merged.

- **`check_beamline_pairwise_luminance` hard-codes white.** `verify.py:2617` —
  `white = (255, 255, 255)` while the docstring says `--node-label-on-fill` is "asserted rather
  than assumed". The token is never read, so if it ever moves to an off-white the check keeps
  measuring pure white and silently over-reports. **Carried into D-008 criterion 4**, since
  that task rewrites this function's docstring anyway. _(from D-004 review, cycle 3)_
- **PR #6's criterion 4 overstates hue precision.** It claims every fill kept its exact HSL hue
  "to one decimal"; the real drift is up to 0.7° (`multiplicity` +0.7, `obs-custom` −0.5,
  `selection`/`obs-global` −0.3, `obs-object` +0.2). The substance holds — all within 1°, hue
  was clearly not traded away for lightness, which was the point — but the precision claim does
  not. Same failure shape as the exhaustive-claim family: the phrasing outran the measurement.
  _(from D-004 review, cycle 3)_
- **PR #6's verification block is reformatted, not verbatim.** It prints the summary three
  sections per line where the program prints one, and says "all 25 sections" while listing 26.
  Every number in it reproduces exactly, so this is presentation only — but the verification
  block is the one part of a PR body that must be a transcript, because it is what the reviewer
  is being asked to trust. _(from D-004 review, cycle 3)_

## Design explorations — D-008

- **`check_beamline_pairwise_luminance` is misnamed.** `verify.py:2844` — after cycle 2 the
  CAM02-UCS ΔE gate is the load-bearing check and pairwise luminance is secondary, but the
  function still carries the old name. Naming only, no consequence to what it measures.
  _(from D-008 review, cycle 2)_

## Cross-cutting

- **Dark colour variant.** V1 commits to light only — the lab-notebook aesthetic is a light
  object and a badly-done dark mode is worse than none. A "darkroom" variant is a candidate
  once the light system is settled. _(from the design direction decision, not a review)_
