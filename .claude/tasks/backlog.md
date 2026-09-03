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

- **`safe_eval` reports the least legible of three correct rejections.** `safe_eval.py:250` —
  the canonical escape `l1.__class__.__init__.__globals__[...]('os')` is refused with *"Only
  calling a named function or a method by name is allowed"*, because `ast.walk` is
  breadth-first and reaches the `Call` node before the `Attribute`. Correct, but the message a
  student sees on the payload that matters most pedagogically should be the underscore one.
  Checking `Attribute`/`Name` before `Call` would surface it. _(from B-006 review, cycle 1)_

- **Exponentiation is no longer available in student expressions.** B-006 dropped `ast.Pow`
  from the whitelist to close an unbounded-cost DoS (`9**9**9` was accepted and never
  returned), so `**` is refused at compile time. The reference's `eval` accepted it, since
  `**` is an operator rather than a builtin — its `_SAFE_BUILTINS` has `sqrt` and `abs` but no
  `pow`. Nothing in the reference, in any saved config, or in our corpus uses `**`, so this
  costs nothing today and B-012's parity proof is unaffected. **If M4 wants exponentiation in
  the recipe builder, bound the exponent — do not re-admit the operator unbounded.**
  _(from B-006 review cycle 1 + scout enumeration, 2026-08-21)_

- **Mutation-test by monkeypatch, never by editing a tracked file.** B-005 cycle 3's coder
  mutation-tested criterion 6 by "temporarily replacing the probe loop in
  `src/fce_web/paths.py`" and proving restoration with a follow-up `git diff`. The reviewer got
  the same two failures with a pytest plugin patching `tempfile.mkstemp`, touching nothing
  tracked. Result identical, risk not: on 2026-08-21 four agents died mid-turn, and a crash
  between mutate and restore commits the mutation. _(from B-005 review, cycle 3 — promoted to
  `.claude/backend/CLAUDE.md`)_
- **`_make_unwritable` silently disarms criterion 6 under root.** `tests/test_paths.py:110-118`
  — `chmod 0o500` does not remove write access for root, so both write-probe tests
  `pytest.skip` and the run still reports green with the criterion unverified. Correct here
  (uid 1002, neither skips), but if the suite ever moves to a root CI container it needs an
  unwritable bind mount or a fault-injected `mkstemp` instead. _(from B-005 review, cycle 3)_

## Cross-cutting

- **Dark colour variant.** V1 commits to light only — the lab-notebook aesthetic is a light
  object and a badly-done dark mode is worse than none. A "darkroom" variant is a candidate
  once the light system is settled. _(from the design direction decision, not a review)_

- **The `comm -23` / `grep -o '^def test_'` instrument is retired, everywhere.** Found by B-006's
  cycle-4 review, 2026-08-21: the command this project uses to certify "no check was retired"
  sees only **module-level** test functions and is blind to every **class-scoped** one. On PR #9
  that was 10 visible against 49 invisible — i.e. all of `TestEscapesRejected`,
  `TestCompileTimeGeneral` and `TestHepSyntax`, every escape assertion in the task. The reviewer
  re-ran the identical command against a HEAD with all class-scoped tests stripped out and got
  the same empty output. Nothing was actually lost on #9 (one documented rename), but the
  instrument cannot detect the thing it exists to detect. **Replacement: `pytest --collect-only -q`
  on both revisions, diffed.** This is the fifth instrument/count failure on this project and all
  five originated in an orchestrator criterion, which is why it is recorded here rather than only
  in the task entry.

- **Extend `check_no_fabricated_identifiers` to `tokens.css`.** D-008's final review,
  2026-08-21 (suggested-minor, approved anyway). The new lint at
  `docs/design-explorations/verify.py:1908` catches comments and docstrings citing constants that
  do not exist — the defect class that produced a `Required` on two separate D-008 cycles — but it
  scans only `verify.py` and `palette_search.py`. **The first instance of this class was in
  `tokens.css`**, which the lint does not cover. The reviewer checked `tokens.css` by hand and it
  is clean today (`_VALID_CONNECTIONS`, `NODE_LABELS`, `SELECTED_T`, `SWEEP_LADDER`,
  `RESERVED_HUE_GAP_FLOOR_DEG`, `PAINT_PROPS`, `REFERENCE_GRAPH_PY` — all real and correctly
  attributed), so nothing is wrong now. The machinery already exists: `check_no_exhaustive_prose`
  regex-scans four files including `tokens.css`. Cheap, and it closes the class rather than the
  instance.

- **Add `fit.method` to the design payload.** Raised while specifying B-004, 2026-08-21.
  `engine/fitter.py`'s `run_fit` returns `(mu, sig)` from **three statistically distinct code
  paths** — a pyhf HistFactory MLE fit; a plain counting ratio `n_tot/s_tot` when there is no
  background sample (`fitter.py:89-98`); and `s/√b` after a bare `except Exception` swallows a pyhf
  failure (`:194-203`) — under the same two field names, with nothing indicating which ran. B-004
  adds a `fit.method` field to `docs/api.md` and specifies it nullable, because
  `docs/design-explorations/payload.json` (design-owned, read-only to B-004) does not carry it.
  **The follow-up is a design task:** add `method` to `payload.json` and surface it in `plot.js`'s
  fit readout, so a `mu` from `s/√b` is not presented to a student as a fitted signal strength.
  Do this after the D-007 checkpoint, alongside whatever else `payload.json` gains.

### From B-007 cycle-2 review (PR #12), 2026-08-22 — all suggested-minor, named individually per §5.6
- **`tests/test_path_filter.py:255-275`** — `test_docstring_eval_compile_line_check_catches_a_perturbed_number` re-implements the comparison instead of exercising the real test's assertion, so it proves the *parser* is sensitive rather than that the primary test would go red. Both directions do go red (the reviewer proved it), but the in-repo mutation test does not demonstrate it. Calling the primary test under a perturbed `__doc__` would.
- **PR #12 body, "Criterion 7 mutation" block** — the transcript is a reconstruction of a failure hit while authoring, presented in `$`-prompt shape rather than as re-runnable output. Prefer a reproducible one-liner. Recorded because a hand-shaped transcript is the one thing a verification block must not be (the D-004 cycle-3 lesson).
- **`tests/test_path_filter.py:225-231`** — `_claimed_eval_compile_lines`'s regex requires the seven numbers to stay on one physical docstring line; a future reflow trips the "update this test's regex" assert rather than the real comparison. Safe (it fails loudly) but noisier than needed; `re.DOTALL` with `[0-9,\s]+` would survive a rewrap.

### From B-010 cycle-2 review (PR #11), 2026-08-22 — both suggested-minor, named individually per §5.6
- **`src/fce_web/engine/runconfig.py:311-325`** — the md5 formula now lives in three places: `compute_h5_sel`/`compute_h5` (362-375) and again inline in `_validate_nested_digests`. A change to the reference formula must be made in all three or the nested check validates against a stale rule. Divergence *would* be caught by `test_roundtrip_fixture`, so it is not major — factoring one module-level `_digest(base, ...)` helper removes the trap.
- **`src/fce_web/engine/runconfig.py:378-425`** — nothing checks the top-level flattened view *agrees with* `selections[0]`; each level is only self-consistent. Demonstrated: a top-level `sel_exprs = ["l1.pt > 999"]` with matching recomputed top-level digests loads with no error, giving top `6744140f9f50c59d5752d52036b76085` against nested `c9873a70ca371612fc24cf976ff7fd5c`. Low consequence — the engine ignores the top level when `selections` is non-empty — **but PR #11's body promises B-011/B-012 that "every digest in it has been checked", and cross-level disagreement is the one shape that promise does not cover.** Either assert `selections[0].h5_sel == h5_sel`, or qualify the docstring.

- **B-009 c1 suggested-minor — `runs.py:92`, `n_workers: int = 4` is an unexplained magic default.**
  A one-line comment on why 4, or sourcing it from the run config, saves the next reader a guess.
  Not folded into B-009 cycle 2: it is a documentation choice, and the right answer probably comes
  from B-011, which is the first code to actually pick a worker count. Raised by the PR #13 cycle-1
  review, 2026-08-22.

- **B-009 c2 suggested-minor — `analytical_loop.py:349-352`, student-facing log copy.** The line
  `"Cutflow plot skipped: fce_web.engine.cutflow_plotter is deferred to M5/M6 and is not vendored
  yet."` fires on every run, and `ctx.on_log` becomes B-011's student-facing SSE log. A dotted
  module path plus an internal milestone label is not copy a 15-year-old second-language reader can
  act on (shared §1). "Cutflow plot is not available yet." says the same thing; the detail belongs
  in the code comment where it already is. **Folded into B-011's dispatch** — recorded here so it
  is not lost if B-011 is re-scoped.
- **B-009 c2 suggested-minor — `analytical_loop.py:348`, two edges for whoever lands
  `cutflow_plotter` in M5/M6.** Narrowing to `except ImportError` was correct, but (i) an
  `ImportError` raised *inside* `generate_cutflow_plot` will still be reported as "deferred", and
  (ii) any other exception now propagates out of `run_physics_loop`, discarding a `RunResult` whose
  physics already completed because a *plot* failed. Unreachable today, zero current cost. **This
  belongs to the M5/M6 task that vendors `cutflow_plotter`** — attach it there when that task is
  written.

- **B-011 c2 — `run_physics_loop` resolves `get_fce_home()` with no `env`, so the engine's cache and
  output are NOT env-isolable.** `analytical_loop.py:241` calls `get_fce_home()` bare, so cache and
  output always resolve against the real process environment no matter what `env` a caller passes to
  `driver.run_analysis`. The driver's own `_dataset_dir` **is** correctly `env`-aware, so the two
  halves disagree. Consequence: a test can isolate dataset *discovery* from the real `~/.fce`, but
  cannot isolate the *pipeline*. Found and disclosed by the B-011 cycle-2 coder, out of its file
  scope, not fixed. Owner is `engine/analytical_loop.py` (B-009's file). **Check this before B-012
  is dispatched** — the parity proof drives both the reference and ours, and shared cache state
  between them is exactly the kind of thing that makes a parity run lie.

- **B-011 c2 suggested-minor — the integration seam silently disappears on a machine without the
  datasets.** `tests/test_driver.py:333`'s `skipif` means
  `test_real_end_to_end_run_exercises_the_real_run_physics_loop` — the **only** test in the suite
  that catches `RunConfig.to_dict()` → `run_physics_loop` dict-shape drift, proven by the cycle-2
  reviewer's `detector`→`detector_name` mutation — does not run where `~/.fce/datasets/IDEA/91GeV`
  is absent. Correct and consistent with the existing pattern, so not blocking. **Whoever sets up
  CI must know this check vanishes there**, or CI will be green on a class of drift that this
  machine catches.

- **B-012 m1** — `tests/test_engine_parity.py:341`: the 10s cache-hit bound's docstring justifies itself with "a fresh run takes ~30s"; measured 78-83s. Stale number in the one place the headroom is argued.
- **B-012 m2** — PR #15 body, C1: says "all 6 samples"; the golden covers seven (`X1`-`X6` plus `data`). PR-body-only.
- **B-012 m3** — `tests/test_engine_parity.py:304,314`: `worst` unpacked and never used in both perturbation tests. Assert on it at `:314` or discard it.
- **B-012 m4** — `tests/test_engine_parity.py:186-190`: `_compare` iterates the golden's keys only, so a spurious extra histogram key or sample in our output is invisible. Set-equality per sample closes it.

- **m5 (B-012 cycle 2)** — `tests/test_engine_parity.py:353` `_output_fingerprint` is annotated
  `Dict[str, Tuple[int, float]]` but returns `st_mtime_ns`, an `int`. The `float` reads as
  "seconds" and invites a later tolerance comparison. Cosmetic.

- **m6 (B-012 cycle 3)** — `tests/test_engine_parity.py:384-396` `_bytes_without_following_symlinks`
  double-counts each subdirectory inode (4096 B): the entry's `lstat` size is added, then again as
  the recursed path's own size. Errs upward, so C10's assertion stays sound; the printed 24.6 MB
  is a slight overstatement.

## Design explorations — D-005 (Bench)

- **`check_git_diff` diffs the local `main` ref, not `origin/main`** — `docs/design-explorations/verify.py:1868`,
  re-registered by D-005 at `:4809`. Fails in any checkout where `main` is behind `origin/main`,
  which is every fresh review worktree. Cost a full re-verification on D-005 cycle 1 and made the
  PR's headline verification non-reproducible. Fix: resolve the base as `origin/main...HEAD`.
  Inherited from D-003; two registered copies now. (D-005 c1 m1 — backlogged, not fixed.)
- **Reconcile the recorded `verify.py` floor with measurement** — `design.md` carried "31 sections /
  48 assertions" from D-008; the D-005 reviewer measured **29** registered sections on `origin/main`.
  One of the two is wrong and the floor is a `Required` gate, so it has to be settled by a command
  rather than by inheritance. (D-005 c1 m2, the half not fixed in cycle 2.)
- **Decide the canvas model at the D-007 checkpoint** — Bench clamps node position to a fixed
  980×460 viewBox; a resizable/zoomable canvas was judged out of scope for a non-shipping
  exploration. Worth an explicit decision rather than an inherited default. (D-005 coder's own
  backlog candidate.)
- **D-006 (Board) inherits the unflagged-`file://` constraint** — it must render with the page
  opened directly in a browser launched with no arguments. Not a backlog item so much as a
  criterion D-006's dispatch must carry; recorded here so it is not lost if D-006 is re-planned.
- **No harness-level guard on the launch-flag ban** — `verify.py` now launches every browser with
  no `args`, but nothing asserts it stays that way; a future edit re-adding
  `--allow-file-access-from-files` would restore D-005's R1 silently. A source-scan assertion over
  `verify.py`'s own text would make the ban self-enforcing. **D-006's dispatch must carry this as
  a criterion.** (D-005 c2 m4 — backlogged, not fixed.)
- **PR #16 body claims that do not reproduce** — "renders identically" across widths (the palette
  goes 2 rows → 1 between 768 and 1024/1440) and a `data-node-id=` count of 7 against a measured
  16. Corrected in cycle 3's body; noted here because both are the same decoration-instead-of-
  measurement habit that produced c1's 46/192. (D-005 c2 m7, m8.)

- **D-007 m1 — index card top-rules reuse node-kind tokens for the wrong axis.**
  `docs/design-explorations/index.css:76-81` colours each exploration card's top rule with a
  node-kind token (`--node-*`), so the hue encodes *which exploration* rather than *which node
  kind*. Every other surface in the project uses those tokens for node kind. Filed from PR #21
  cycle 1, suggested-minor. Sweep with the D-002 token work, which owns that palette.
- **D-007 m2 — the C2/C3 index gate exists only as PR-body output, not on disk.**
  The mutation-gated checks that prove index.html's per-style claims match the pages were run
  by hand and pasted; nothing re-runs them next time a style page changes. Filed from PR #21
  cycle 1, suggested-minor. If the design-explorations set is ever revised, put the gate in a
  small script beside `verify.py` rather than re-deriving it.
- **D-007 m3 — unnamed `<section>` landmark.** `docs/design-explorations/index.html:81` is a
  `<section>` with no accessible name, so it is an unlabelled landmark for screen-reader users.
  Filed from PR #21 cycle 1, suggested-minor.
- **D-007 m4 — a verbatim `design-brief.md` quotation sits outside its closing quote mark.**
  `docs/design-explorations/README.md:34-35` — "A student should be able to point at the graph
  and say what it does, in order." is `design-brief.md:169` verbatim but reads as the README's
  own prose. Extending the quotation by one sentence also brings it inside C8's checker instead
  of leaving it to a human. Filed from PR #21 cycle 2, suggested-minor.
- **D-007 m5 — ragged wrap and a stranded antecedent in the recommendation.**
  `docs/design-explorations/README.md:36-40` — line 38 is four words, and "but it still" points
  at the M3-inheritance fact two clauses away rather than at "choosing Board". Filed from PR #21
  cycle 2, suggested-minor.
- **D-007 m6 — C7's and C8's instruments live only in the PR body.** The cycle-2 reviewer had to
  re-implement C8 to run it, and its §-attribution rule differed from the coder's (`"_To be
  defined in M3._"` attributed to §4 rather than `section=None`); the quotation verdicts agreed,
  so it cost nothing this time. Same shape as m2: a check that cannot be re-run identically by
  the next reader is weaker than one in `verify.py`. Filed from PR #21 cycle 2, suggested-minor.

- **D-009 m3** — `docs/design-explorations/interiors.html:586-594`: the inline-grow option
  reuses `flyout__mode-label`, `flyout__checks` and `flyout__field` inside a container that is
  explicitly not the flyout. Whichever option D-010 inherits, the class names will read as the
  wrong one. Deferred until the user rules which option survives. (D-009 cycle 1, 2026-09-02)
- **D-009 m4** — PR #22 body: the cycle-2 verbatim "File scope" block lists three files while
  C7/C8 assert a four-file diff including `docs/design-explorations/README.md` (legitimately, from
  cycle 1). The two sections read as contradicting each other. Body-only; the tree is correct.
  (D-009 cycle 2, 2026-09-02)
- **`--node-observable` token missing** — the merged `Observable` node has no identity hue of its
  own. D-013's page borrows `--node-obs-global` as a stand-in, documented in `observable.css`.
  **D-002 is choosing the Observable hue from the four existing `--node-obs-*` right now**, so
  this closes itself if D-002 names the token `--node-observable`; check on merge and drop this
  item if so. (D-013 cycle 1, 2026-09-02)

- **D-013 m4** — my dispatch formatting: C9 and C10 shipped with no `Check:`/`Expect:` pair, so
  the reviewer had to map each to a `--section` or grep itself. Against the orchestrator, not the
  coder. Filed 2026-09-02.
- **D-013 m7** — `docs/design-explorations/observable_verify.py:320-337`: the footprint gate is
  one-sided. It catches the node box widening to the enclosing figure's, but a regression to a
  *smaller* wrong box (an inner panel) still satisfies `h < fig_h` and re-certifies a too-small
  number to D-010. Tighter form: assert the measured element's own selector, or the known
  ~20.5px figure-minus-node gap. Filed 2026-09-02.

- **D-002 tight non-text headroom** — `--frozen-x2` at 3.12:1 and `--syst-grey` at 3.24:1 on
  `--paper` clear WCAG SC 1.4.11's 3:1 by under 0.25. Any future warming of `--paper` breaks
  both. Raised by the coder 2026-09-02; note it whenever the ground colour is next touched.

- **D-002 m5 — the exploration `tokens.css` diverged from the shipped one.** 2026-09-03, D-002
  cycle-2 review. `docs/design-explorations/tokens.css:34,87,307` still hold the pre-SC-1.4.11
  values `--chrome-border: #d8cba8`, `--locked-border: #b3a98c`, `--frozen-x3: #b5883a`, which
  `src/fce_web/static/css/tokens.css` moved to `#847c66` / `#726c59` / `#a67d36`. The divergence
  is unrecorded anywhere. Either sync the exploration copy or write a note in it saying the
  shipped file is now authoritative. Out of D-002's file scope, which is why it is here.

- **D-002 m6 — the frozen-separation floor is a constant, not a reading of the sentence it
  certifies.** 2026-09-03, D-002 cycle-3 review. `docs/design-explorations/verify.py:7524`
  hard-codes `APP_FROZEN_SEPARATION_FLOOR = 19.0`. Rewriting `tokens.css`'s "at least 19" prose
  to "at least 25" leaves both `tokens-nontext` and `tokens-contrast` green, so m4 is closed
  against a token nudge but not against a prose nudge. Fix: a `N delta-E` literal sweep
  mirroring the existing `N.NN:1` ratio sweep, so every separation literal in the file is
  recomputed from the shipped tokens.

- **B-013 m1 — the `-O` warning belongs in a suite-wide `conftest.py` guard, not in a comment.**
  `tests/test_safe_eval.py:414-437` carries 24 lines of comment guarding
  `_ASSERT_STRIPPING_ENV_VARS`, a filter that both the coder and the cycle-1 reviewer showed has
  no observable effect on any current code path (`returncode=0 sentinel=True` in both states).
  The substance — do not trust a green suite under `PYTHONOPTIMIZE` — should be a `__debug__`
  guard in `conftest.py`, where it is enforced rather than narrated. Raised from B-013 cycle 1,
  2026-09-03.

- **D-010 m1 — `shell-verify-floors`' name implies more than it asserts.** `verify.py:6721-6728`
  only checks `board-lane-fill` is defined and registered, not that it is still red; C9's Expect
  covers redness via the external `--all` run. Say so in the docstring. Raised 2026-09-03.
- **D-010 m2 — C6's payload regex includes `open`,** which a legitimate future payload field would
  match; and `buildRunPayload` (`shell.html:129-134`) reads only `graphState`, so the check is
  near-tautological. Its real failure mode is someone putting ui state *into* `graphState`, which
  is what a later revision should gate. Raised 2026-09-03.
- **D-010 m3 — the mission pager needs disabled end states and an announcement.**
  `shell.html:69-71`: `#pager-forward` is not disabled at m3 nor `#pager-back` at m1, and
  `#mission-label` has no `aria-live`, so the change is silent to a screen reader. Out of scope
  for D-010's criteria — belongs to whoever ships the real panel markup. Raised 2026-09-03.
