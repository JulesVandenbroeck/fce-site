# Front end — completed task archive

Full entries for every merged front end task, moved out of `.claude/tasks/frontend.md` so that
`/orchestrate` no longer loads the whole project history on every session start.
Nothing here was deleted or edited — these are the entries verbatim.

**Read this file on demand only.** When a task's history is actually in question, open
it. Never at startup.

---

## Done


### F-001 — Minimal page shell: base layout and index template
- **Scope:** `src/fce_web/templates/base.html`, `src/fce_web/templates/index.html`,
  `src/fce_web/static/js/app.js`
- **Accept:** all five criteria met and independently re-verified by review
- **Contract established, and later tasks depend on it:** the templates take exactly one
  context variable, `title` (str). Static assets are referenced by literal path under
  `/static/`, not `url_for` — `url_for` would force `request` into the context and break
  the one-variable contract. B-002 must therefore mount `StaticFiles` at `/static` from
  `src/fce_web/static/` and render `index.html` with exactly `{"title": <str>}`.
- **Depends on:** nothing
- **Branch / PR:** `task/f-001-page-shell` — #1, merged as `176f7d5`
- **Status:** **done** (1 cycle, no rework)
- **Review:** 0 required, 0 suggested-major, 1 suggested-minor → backlogged (packaging:
  `templates/` and `static/` do not survive a wheel build). The review went past the
  coder's own checks: it confirmed the one-variable contract genuinely raises with no
  context rather than being satisfied by a default, and confirmed autoescaping under the
  real `Jinja2Templates` integration — `title='<img src=x onerror=...>'` escapes in both
  `<title>` and `<h1>`.
- **Declared deviation, settled:** no `<header>`/`<nav>`/`<footer>`. The coder's argument —
  empty landmarks announce content-free regions to screen readers, and the criteria asked
  only for `<main>` — was examined by the reviewer and explicitly not raised as a finding.
  Settled; do not re-litigate. Backlogged for when there is anything to put in them.
- **Why this task existed:** B-002 was originally scoped to serve HTML from a Jinja2
  template and mount `/static`, but `templates/` and `static/` belong to frontend, not
  backend (shared §4), and `StaticFiles` cannot mount a directory that does not exist. This
  pulled the first front-end task forward from M3 to M1.


---

## F-002 — Link the design tokens stylesheet into `base.html`

Merged #30 `78c0b3c`, 2026-09-07. 1 cycle + 1 re-specification, `findings=2, verdict=approve`.
checks=6 (5 live, C2 retired). Suite floor 594 → 596.

### F-002 — Link the stylesheets into `base.html`
- **Scope:** `src/fce_web/templates/base.html`
- **Accept:** `<link rel="stylesheet">` for the design role's tokens and main stylesheet,
  in cascade order; page still renders with zero console errors and zero 404s
- **Depends on:** ~~D-002~~ **merged 2026-09-03 (#24, `72d2950`) — RELEASED.**
  `src/fce_web/static/css/tokens.css` exists and is the tokens file to link. There is **no
  main stylesheet yet** — D-010 is the first task that writes one — so this task links tokens
  only, unless it is dispatched after D-010. **This entry's original premise was FALSE and is corrected here**
  (`scout`, 2026-09-07). It read: "the four self-hosted woff2 are exercised for the first time
  here ... a 404 on a font is exactly what this task's zero-404 assertion exists to catch."
  They are not exercised, and it would not catch one. `tokens.css` is 355 lines holding only
  four `@font-face` rules (`:52, :60, :68, :76`) and one `:root` block (`:84-355`); **no rule
  in it applies `font-family` to any element selector**, and a declared face is fetched only
  when some rule uses the family. So linking it fetches zero fonts and "no font 404s" is
  vacuously true. Nor could a frontend coder fix that: the fix is a `font-family` declaration
  in `static/css/`, which is the design role's file. **The fonts stay unexercised until the
  first task that applies `var(--font-body)` to a real selector — see F-003.**
- **Branch / PR:** not yet opened
- **Status:** **RELEASED — B-017 merged #28 `aef697f`, 2026-09-07.** Ready to dispatch.
  History of the block: The `scout` fact-find, 2026-09-07: `tests/e2e/conftest.py`
  collects console errors (`PageActivity.console_errors`, `:51`) and **requested URLs only**
  (`:53`, `page.on("request", ...)` at `:82`). There is **no response-status collection anywhere
  under `tests/`**, so "zero 404s" has no instrument — a font 404 is indistinguishable from a 200
  in the data that exists. `conftest.py` is backend's file, so the probe was split off as
  **B-017** and this task consumes it read-only. Do not weaken the criterion to fit the old
  instrument; that is the D-001 failure shape.
- **The contract to cite verbatim, do not re-derive:** `PageActivity.bad_responses:
  list[tuple[str, int]]` in `tests/e2e/conftest.py`, each entry `(url, status)`, collected iff
  `is_bad_response_status(status)` — **status >= 400**, so a redirect is not a failure. Fixtures
  available: `live_server`, `browser`, `page`, `index`. `tests/e2e/` holds 25 nodeids at
  `aef697f`; that floor may rise and must not fall.
- **Facts for the dispatch, enumerated 2026-09-07, do not re-derive:** `base.html` is 16 lines
  with **zero** `<link rel="stylesheet">` and its `<head>` is lines 3-10. Static is mounted at
  `/static` from `src/fce_web/static` (`app.py:94-98`). `static/css/` holds exactly one file,
  `tokens.css`. It declares **four** `@font-face` rules (`:52, :60, :68, :76`) whose `src:` URLs
  are all relative — `url("../fonts/<name>.woff2")` at `:54, :62, :70, :78` — resolving against
  `/static/css/`, so they only work if the link is served from that path.
- **The second blind spot, and the criteria must close it:** a declared `@font-face` is fetched
  only when a rule actually uses the family. `base.html` has no styled content, so "no font 404s"
  is satisfiable vacuously, by the fonts never being requested at all. The criterion has to
  assert the four woff2 are **requested and 200**, not merely that nothing failed.

### The premise that was false, caught before dispatch
This entry had said since 2026-09-03 that F-002 "is what first renders the shipped
`tokens.css`, so the four self-hosted woff2 are exercised for the first time here", and that a
font 404 "is exactly what this task's zero-404 assertion exists to catch". A `scout` fact-find
on the morning of dispatch falsified both halves: `tokens.css` is 355 lines of four
`@font-face` rules and one `:root` block, and **no rule in it applies `font-family` to any
element selector**, so no face is ever fetched and the assertion is vacuous. A frontend coder
could not have fixed it either — the fix is a declaration in `static/css/`, design's file.

This is the first time on this project that the blind-instrument shape was caught *before*
dispatch instead of by a review cycle. The cost was one `scout`. D-001 paid four cycles for
the same shape. The font check became **F-003**, blocked on the first task that applies
`var(--font-body)` to a real selector.

### C3 is why the task closed in one cycle
Instead of "no 404s", C3 asserted `getComputedStyle(document.documentElement)
.getPropertyValue('--font-body')` contains `EB Garamond` — impossible to satisfy unless the
sheet loaded *and* parsed *and* applied, and inside frontend's scope. The reviewer then built a
sharper mutation than the coder's: serving a `tokens.css` that defines
`--font-body: Comic Sans MS` turned **only** C3 red while C2 and C4 stayed green, isolating the
load-bearing check. That same mutation is what condemned C2 (F1) as fully subsumed.

### F2 — a hard boundary I contradicted
My file scope handed the frontend coder `tests/e2e/test_smoke.py`, which `frontend/CLAUDE.md`
§1 forbade. The coder followed the scope, correctly. Escalated to the user, who ruled
**`tests/e2e/` is shared**: backend owns the harness and `conftest.py`, frontend owns the
browser assertions about its own markup, and a missing fixture is reported rather than added.
Written into `shared/CLAUDE.md` §4 and `frontend/CLAUDE.md` §1 on 2026-09-07. The rejected
alternative was pairing every frontend task with a backend task, which would have made this
one-line `<link>` two branches, two reviews and two merges, serialised.


---

## F-004 — post-mortem (merged 2026-09-08, PR #32, `30cceb3`)

### The active entry as it stood at merge

### F-004 — Port the three-region shell into the app
- **Scope:** `src/fce_web/templates/` (the shell template, `base.html`),
  `src/fce_web/static/js/shell.js`, `tests/e2e/test_shell.py`
- **Accept:** C1-C7 in the plan. Three regions per the 2026-09-01 ruling (canvas always
  present, palette left/collapsible, mission panel right/expandable); collapse and expand
  keyboard-operable; `shell.html:90-310`'s inline script becomes a module file; zero inline
  `style=`; `PageActivity.console_errors == []` and `bad_responses == []`.
- **Depends on:** nothing. **Blocks F-005 and D-015.**
- **Branch / PR:** `task/f-004-shell-port` at `66bf893` — **#32, open**
- **Status:** in review (cycle 2) — `code-reviewer` re-dispatched 2026-09-08 with the cycle-1
  review URL and F1-F7. Cycle-2 head `66bf893`. §5.1 gate **PASSED** in `~/fce-gate-f004`:
  `615 passed` (605 floor + 10), flake8 0, `tests/e2e/` 37 nodeids, scope exactly four files.
  Coder reports all seven findings fixed, **none overruled**, with a mutation proof on F1
  (breaking `#palette-toggle`'s id now turns the test RED; it stayed green under exactly that
  mutation on cycle 1). ~115 lines of JS deleted — `shell.js` keeps only the two toggles.
- **Cycle-1 record:** re-dispatched 2026-09-08 with the review URL and F1-F7.
  Cycle 1 gate PASSED; review `findings=7, scope=pass, verdict=rework`
  ([comment](https://github.com/JulesVandenbroeck/fce-site/pull/32#issuecomment-5582424817)).
  **checks 7 → 8**: C8 added for uncaught page errors.
- **Review:** 7 findings, verdict=rework. F1 blocking — `test_shell_page_logs_no_console_errors`
  passes when `shell.js` throws on load, because an uncaught module exception is a Playwright
  `pageerror`, not a console error; the reviewer proved it by breaking an id and watching the
  test stay green. F5/F6/F7 accessibility (unnamed `<aside>` landmarks; a dead `tabindex="0"`
  canvas tab stop; collapsed regions left in the tab order). F2/F3/F4 deletions (~115 lines of
  dead payload builder, untested exemplar node cards, and mission text duplicated between
  template and JS).
- **§5.4 diagnosis — this is a CYCLE, clause 3, and the drafting defect is mine.** Nothing was
  dropped from a prior cycle (clause 1 does not apply), and C4 shipped *with* a command and is
  *met as written* (clause 2 does not apply). F1 is against a property no criterion gated, so it
  counts. But it is §2's *"state the property, not only the method — or the method becomes the
  ceiling"*, the B-006 cycle-2 shape exactly: I wrote the mechanism (`console_errors == []`) and
  got that mechanism and nothing else. C8 now states the property — no uncaught JS error on load
  — and names `page_errors` as one instrument, not as the definition.
- **Cycle-1 gate (still the record):** §5.1 free gate
  **PASSED** in `~/fce-gate-f004` (detached off `origin/task/f-004-shell-port`):
  `606 passed, 0 failed`, `flake8 src/ tests/ scripts/` → 0, `tests/e2e/` **27 → 37** nodeids,
  and `git diff origin/main...HEAD --name-only` returns exactly the four scoped files. Every
  number in the PR body reproduced. PR body carries scope, C1-C7 with IDs and evidence, the
  region/`data-state` table for D-015, and the transcript — §4 rule 3 satisfied.
  **The first dispatch of this task died producing nothing** (branch at `main`, clean worktree,
  no PR); confirmed against git, so **this is cycle 1, not cycle 2.**
- **Worktree:** `.claude/worktrees/agent-ac37115050f4366c3`, reused from the dead dispatch — the
  branch is checked out there, so a fresh `worktree add` would fail. The coder is told not to.
- **Note:** writes **no CSS** — the page is expected to look unstyled. D-015 styles it in wave 3.
- **Deviations accepted at the gate:** shipped as an included partial `shell.html` rather than a
  standalone `mission.html` (the plan left the choice to the coder), `base.html` untouched, and
  the ported script's `window.buildRunPayload` global dropped per shared §6's no-globals rule.
- **For D-015:** the region class names and `data-state` values are in PR #32's body under
  *Region class names and `data-state` values*. It also introduces an `sr-only` class for the
  toggles' screen-reader text, which needs a visually-hidden rule if the CSS has none.

### Cycle 1 — `findings=7, verdict=rework`

[Review](https://github.com/JulesVandenbroeck/fce-site/pull/32#issuecomment-5582424817).
F1 blocked: `test_shell_page_logs_no_console_errors` stayed GREEN when `shell.js` threw on load,
because an uncaught module exception is a Playwright `pageerror`, not a console error. The
reviewer proved it by breaking an element id. F5/F6/F7 were accessibility (two unnamed `<aside>`
landmarks; a `tabindex="0"` canvas tab stop that did nothing while narrating D-013's clamping
behaviour to a screen-reader user; collapsed regions left in the tab order, which would have
stranded focus once D-015 hid them with width or transform). F2/F3/F4 were deletions.

**The §5.4 diagnosis, and the defect is the orchestrator's.** A cycle under clause 3 — nothing was
dropped, and C4 shipped with a command and was met *as written*. But C4 said
`console_errors == []`: a **mechanism**, not the property. §2's *"state the property, not only the
method — or the method becomes the ceiling"*, which is B-006 cycle 2's shape exactly. C8 restated
it as *the page raises no uncaught JavaScript error on load*, with `page_errors` named as one
instrument rather than as the definition. **B-020 hit the identical defect in the same wave**
(C7 named `RunConfig.from_dict` acceptance rather than translation correctness), so this is not
bad luck — it is a drafting habit to watch for.

### Cycle 2 — `findings=2, scope=pass, verdict=approve`

[Review](https://github.com/JulesVandenbroeck/fce-site/pull/32#issuecomment-5582745493). All seven
fixed, none overruled. The reviewer reproduced C8's mutation proof **independently** of the
coder's method — a pytest plugin installing a `page.route` that rewrote the served `shell.js`,
rather than the coder's `sed` — and confirmed the check now goes red on a load-time `TypeError`.
It also ran a live tab sweep at three widths rather than reading attributes, confirming F7's
`hidden` actually removes the collapsed regions from the tab order.

F8 and F9 backlogged. F8 is the borderline one and the reviewer said so: the two mission-pager
buttons are keyboard-reachable and announce "Previous mission"/"Next mission" while doing nothing.
Approved because the shell ships unwired by design and F-005 owns the pager next wave — **so
F-005's dispatch must either wire them or delete them.**


### F-006 — The merged `Observable` node interior
- **Scope:** `static/js/graph.js`, `tests/e2e/test_graph.py` (`shell.html` was in scope and
  proved unnecessary)
- **Accept:** C1-C7 in the plan. **Total checks: 7.**
- **Depends on:** F-005 (merged `b7fdfdf`). Wave 3.
- **Branch / PR:** `task/f-006-observable-interior` — #38, head `8cb14ab`
- **Status:** **in review (cycle 2)**, head `892171b`. Gate reproduced in the primary checkout:
  `671 passed`, flake8 0, `tests/e2e/` **54** nodeids; scope exactly the two files. No hook refusal.
- **Review (cycle 1):** `findings=5, scope=pass, verdict=rework` — PR #38 comment `5631301455`.
  670 / flake8 0 / 16 reproduced; C1/C2/C3/C6 mutation-verified. **F1 blocks:** Enter on the
  summary drops focus to `<body>` (bring-to-front `appendChild` moves the focused element).
  F2 tautological C5 meta-test. F3 per-mode panel fields reach no `config` — delete unless a
  C1-C7 text requires them. F4 subtitle says "not configured" while config is ObsGlobal.
  **F5 against me: C4 (styled footprint) moved to D-015** — not dropped, relocated.
  checks 7 -> **10** (C8 focus kept, C9 subtitle matches config, C10 no discarded control,
  C11 meta-test deleted; C4 counted as moved).
- **Why there is no PR, and what the next session must do first:** the coder was refused by
  the `rtk`/worktree-isolation hook at `git add`/`commit`/`push` time — `checkout -b` and
  `rev-parse` succeeded, the mutating commands did not. It **stopped and reported rather than
  routing around it**, which is the 2026-09-08 ruling working as intended. I committed its
  diff verbatim to preserve it (nothing was edited by me; the commit message records this)
  and **deliberately did not open the PR**: the body must carry C1-C7 and the coder's own
  verification transcript, and §4 rule 3 forbids me writing it. **Re-dispatch F-006 to open
  the PR from the existing branch**, then review normally.
- **What it built:** native `<details>`/`<summary>` grow-in-place toggle, a native radio
  `<fieldset>` with the four modes, one mode panel each ported from `observable.html`,
  `growNode()` resizing the foreignObject to measured content height, bring-to-front on open
  by DOM reorder (SVG has no z-index), and `config: {mode}` in the exported `data-graph`.
  Six new e2e tests including the C5 meta-test that mutates away the accessible name.
- **C4 is honestly unmet and says so:** this app has no node CSS until D-015, so the measured
  footprints (`ObsGlobal` 276x160, `ObsObject` 277x160, `ObsVectorSum` 368x160, `ObsCustom`
  400x160, collapsed 107x160) are **not** comparable to D-013's styled 328x300 / 301.5 /
  290.5 / 237 / 80.5. They confirm the mechanism and the mode *ranking* only. A reviewer
  should treat the styled contract as D-015's to satisfy, not this task's.
- **Review (cycle 2):** `findings=3, verdict=approve` — PR #38 comment `5631463998`. F1-F5 fixed,
  C8/C9/C10 mutation-verified. Merged `eb4f420` 2026-09-11.


## F-010 — post-mortem (merged `57a42a5`, 2026-09-11)

Review: PR #40 comment `5633215745`, `findings=2, verdict=approve`.

### F-010 — Mission panel shows mission 3's text instead of mission 1's
- **Found by the user, 2026-09-11** (PDF of `main` at `8f094a6`): the panel reads "M-3 · The Unknown — A signal
  sample is hiding in the data. Find cuts that expose it and run a fit." — carried over from the D-010
  exploration's demo copy. Mission 3 is **blocked** (X4/X5 unidentified, shared §5: no mission-3 content), and
  M3 runs mission 1's dataset. Also claims a fit, which M3 does not build.
- **Scope:** `src/fce_web/templates/shell.html` (mission panel text only), `tests/e2e/test_shell.py`
- **Accept:** the panel shows **M-1 · First Light** with brief §3's M-1 objective in plain student English
  (`docs/design-brief.md:86-91`); no M-2/M-3 text anywhere in the rendered page; the pager does not offer
  missions that do not exist yet. Hardcoded is fine — mission loading is M5.
- **Depends on:** nothing — D-015 merged `0eded93`. Serialise with F-009.
- **Branch / PR:** `task/f-010-mission-one-text` — #40
- **Status:** in review (cycle 1) — head `cff7e54`, gate passed (679 / flake8 0). checks=5.



## F-003 — post-mortem (merged `1f9d344`, 2026-09-11)

Review: PR #41, `findings=2, verdict=approve`.

### F-003 — Prove the four woff2 are actually served
- **Depends on:** D-015 — merged `0eded93`. Full entry under `## Deferred`.
- **Status:** in progress (cycle 1), dispatched 2026-09-11, branch `task/f-003-woff2-served` — #41, scope `tests/e2e/test_fonts.py` only. checks=5. Gate running.



## Deferred

### F-003 — Prove the four woff2 are actually served
- **Why:** F-002 links `tokens.css` but cannot exercise the fonts — `tokens.css` applies
  `font-family` to nothing, so no face is ever fetched, and "no font 404s" passes vacuously.
  The four files under `src/fce_web/static/fonts/` have therefore **never been served**, and
  their `src:` URLs are all relative (`url("../fonts/<name>.woff2")` at `tokens.css:54, :62,
  :70, :78`), resolving against `/static/css/` — so they work only if the sheet is served from
  that exact path. Nothing has tested that.
- **Accept:** loading a page whose CSS actually uses `var(--font-body)` and `var(--font-mono)`
  requests all four woff2 and every one returns 200. Falsifiability shown by breaking one
  `src:` path and watching the named test go red. **The check must assert the four are
  requested, not merely that nothing failed** — the vacuity is the whole point of this task.
- **Depends on:** the first design task that applies `font-family: var(--font-body)` to a real
  selector in `src/fce_web/static/css/`. No such task exists yet; it arrives with the app's
  first main stylesheet, which is M6 work or whenever M3 needs one.
- **Branch / PR:** not yet opened


## F-009 — post-mortem (merged `ad36dd9`, 2026-09-11)

Review: PR #42, `findings=4, verdict=approve`.

### F-009 — An opened node is re-clamped onto the canvas by its measured size
- **Scope:** `src/fce_web/static/js/graph.js`, `tests/e2e/test_graph.py`
- **Accept:** after `growNode()` resizes an opened node, it is moved so its measured box lies fully inside
  the canvas (vertical and horizontal); dragging an opened node clamps by its live size, not `NODE_W`/`NODE_H`.
  Carries D-015's C12 vertical half (PR #39 cycle-2 review F6). Proven in Playwright at the bottom edge.
- **Depends on:** D-015 — merged `0eded93`. Wave 3 fix, before F-007.
- **Status:** in progress (cycle 1), dispatched 2026-09-11, branch `task/f-009-clamp-opened-node` — #42, head `6507db0`, gate passed (681 / flake8 0), in review. checks=5.



---

### F-007 — Serialise, submit, stream, show progress

## In progress

### F-007 — Serialise, submit, stream, show progress
- **Branch / PR:** `task/f-007-run-submit-stream` — #46
- **Status:** re-specification in flight (still cycle 1 — §5.4). checks 11 -> **15** (C12-C15 added).
- **Gate (§5.1) passed** at `8fa2004`: 687 / 64 e2e collected / flake8 0 / 3 files, none under `static/css/`.
- **Review cycle 1:** `findings=11, scope=pass, verdict=rework` — PR #46 comment `5694837876`.
  **Two of the gating findings are against my criteria, not the code.** C2's check — drag, resubmit,
  expect a cache hit — tests a *server* property and stayed green when the reviewer randomised `x`/`y`
  per submission; C4 shipped with no operational check at all and stayed green when **both** SSE status
  writes were deleted. §2's *instrument that structurally cannot observe the property it certifies*,
  twice in one dispatch. Re-specification, not a cycle.
  **Recorded so the next pass is not also free:** F4 (a failed run leaves the previous payload on
  `#results-chart`'s `data-result` for F-008 to render as current) and F5 (disabling the focused Run
  button drops focus to `<body>`) are against properties no criterion gated — clause 3, a cycle. If
  this needs a third pass, **it counts.**
- **C12-C15:** no `x`/`y` in the POST body, asserted on the intercepted request, not on a cache hit;
  live rendering proven by a guard that reddens when `run.js:74`/`:122` are deleted; `resetResults`
  clears `data-result` and the status; the Run button does not cost the keyboard user their place.
- F6 (`aria-live` on `<progress>` announces nothing) corrects the **published contract**, not just the
  markup. F7/F8/F9 are three deletions, about -14 lines. F11 (`#results` 26px wide, half-covering the
  Run button at 1440) is **D-016's**, backlogged.
- **F2 ruled by me:** the property stands — real datasets are slow and the brief requires a run never be
  silent. The fixture merely finishes too fast to see it. The client must be proven to render frame by
  frame; a controlled stream is a legitimate way to show that. The property is not restated to match
  what the fixture happens to show.
- **Contract shipped, verbatim in PR #46's body (C10), consumed read-only by D-016 and F-008:**
  `#run-control`/`#run-button`, and `#results` carrying `#results-status` (aria-live, phase + percent),
  `#results-progress` (native `<progress max=100>`, hidden until the first frame), `#results-note`
  (aria-live, **no `role="alert"`**, no banner class — brief §2), `#results-chart`.
  **F-008 renders into `#results-chart`**, reading its `data-result` attribute or the bubbling
  `fce:result` CustomEvent it dispatches on `done`.
- **`x`/`y` never leave the client** — `run.js` rebuilds each node as `{id, kind, config}`, so a
  drag-then-resubmit is a cache hit. That is stronger than the ride-along the dispatch allowed for.
- **Environment note:** the coder added Chromium r1243 to the shared `~/.cache/ms-playwright`
  (additive, r1234 untouched) — an unpinned `playwright` in a fresh worktree venv resolved higher.
- **Depends on:** F-005, F-006, B-020, B-021, B-022, B-023 (all merged); go-ahead given 2026-09-11. Wave 5.
- **C1/C2 deviate from the plan text by my ruling, 2026-09-16.** `docs/plan-m3-vertical-slice.md:720-727`
  asks for `{nodes, edges, ui{}}` with layout confined to `ui`. Enumerated by `scout`: nothing reads a
  `ui` key — `build_run_config` reads only `nodes`/`edges` (`graph.py:349-350`), `docs/api.md:34-50`
  documents only those, and `graph.js:93-101` already rides `x`/`y` on each node where `_parse_nodes`
  ignores them. The `ui` wrapper would need a backend change for no behavioural gain. C1/C2 state the
  same property against what shipped; C2 proves it by drag-then-resubmit landing a cache hit.
- **C10 is the contract clause:** the PR body must carry the results-region markup verbatim, the way
  F-004's PR #32 did. **D-016 and F-008 consume it read-only.**

**Outcome:** merged `1fdb8e6`, PR #46, 2 cycles + 1 re-specification + 1 pre-merge pass. checks=15.
Suite floor 683 -> 691; `tests/e2e/` 64 -> 68 nodeids.

**The task's whole lesson is about instruments, and it recurred three times at three levels.**

1. *My criteria could not observe their own properties.* C2 asked for "layout state is ignored by the
   run" and checked it by drag-then-resubmit-expect-a-cache-hit — a **server** property. The reviewer
   stamped `x: Math.random(), y: Math.random()` on every node and the check stayed green. C4 asked for
   "phase and progress render live" and shipped **no** check; the coder's `len(seen) > 1` was satisfied
   by two client-local strings, and deleting *both* SSE status writes left it green. §2's "an instrument
   that structurally cannot observe the property it certifies", twice in one dispatch. Re-specification
   under §5.4 clause 2; C12 (assert the intercepted POST body's key set) and C13 (redden when
   `run.js:74`/`:122` are deleted) replace them and were verified red under exactly those mutations.
2. *The review's own instrument was too coarse.* Cycle 1's F2 reported that the real app never renders
   live progress at all — observed sequence `Submitting… -> Run complete.` — and proposed restating C4
   to match. I ruled the property stood: real datasets are slow, the brief requires a run never be
   silent, and the fixture merely finishes too fast to watch. Cycle 2 replaced 20ms polling with a
   `MutationObserver` and recorded
   `Locating datasets... -> Reading events... -> ... 90% -> ... 100% -> Done -> Run complete.`
   **The property was always there.** Had the criterion been restated to match the instrument, the
   brief's requirement would have been quietly dropped on the strength of a measurement artefact.
3. *A green suite hid a contract hole.* F12: `buildSubmission()`'s failure path returned before
   `resetResults()`, the one route leaving a stale `data-result` on `#results-chart` for F-008 to render
   as current. Non-gating by the reviewer's judgement; closed before merge anyway, because D-004's
   post-mortem records what merging a contract task with an open finding against the shared value costs.

**Two accessibility facts that are now contract, not implementation detail.** `#run-button` is **never**
given the `disabled` attribute: disabling a focused button drops focus to `<body>` and costs a keyboard
user their place mid-run. It uses `aria-disabled` plus a re-entry guard in `run.js` (three same-tick
clicks record `['false','true','true']`). The consequence, F13, is D-016's: giving up `disabled` gives up
the free visual busy affordance the browser renders for it, so **`#run-button[aria-disabled="true"]` must
be styled busy**. `<progress>` also lost its `aria-live` — it has no text content to announce.

**Operational cost worth recording.** Twice, concurrent suites corrupted a measurement: my first §5.1
gate on B-024 read a moved `~/.fce/output` mtime because this branch's suite was running on a pre-fix
branch, and the coder lost ~8 minutes to three stale background `pytest` processes. Every dispatch and
review on this task after that carried an explicit "run nothing in the background, leave nothing running"
line. The shared `~/.fce` directory and the shared Playwright cache make suite runs non-independent.

**Findings:** F1-F11 cycle 1 (F1/F3 mine, see above; F2 overturned by a better instrument; F4 stale
`data-result`; F5 focus loss; F6 `aria-live` on `<progress>`; F7-F9 three deletions, -14 lines; F10 stale
status after an error; F11 -> D-016, backlogged). F12-F14 cycle 2 (F12 closed pre-merge, F13 into the
contract and D-016's dispatch, F14 one deletion).


---

### F-008 — The interactive SVG histogram

## In progress

### F-008 — The interactive SVG histogram
- **Branch / PR:** `task/f-008-svg-histogram` — PR not yet opened
- **Branch / PR:** `task/f-008-svg-histogram` — #47
- **Status:** in review (cycle 2). checks=11 (C1-C11).
- **Gate (§5.1) passed** at `5d7c8ad`: 698 / 75 e2e collected / flake8 0 / 4 files, none under `static/css/`.
  **C7 reproduced in my own worktree: modal bin `90.0-91.2 GeV`, centre 90.6 GeV.**
- **Review cycle 1:** `findings=8, scope=pass, verdict=rework`. A **cycle** — the gating items are the
  coder's: F1 (the published D-016 class list omits every reveal class the figure emits), F4 (both the
  PR body and a test docstring blame "the unstyled shell"), F3 (C5's stated proof is not in the code —
  the test compares the normal-motion band to itself), F7 (asserts the absence of a class `chart.js`
  never emits, so it cannot fail). F2/F5/F6/F8 ride along.
- **The renderer itself is sound:** C7 reproduces in two independent worktrees, and both load-bearing
  checks mutate red (bin edges shifted +20 GeV; the reduced-motion query broken).
- **Reference enumerated by `scout`, not remembered:** `docs/design-explorations/plot.js`, 817 lines,
  **17** top-level functions (the plan says 16). `FIG.h = 460` at `:136`, `FIG.w` 650 at `:142`.
  `drawLegend` `:548` (called from `renderHistogramFigure:473`, `renderCutflowFigure:698`);
  `renderCutflowFigure` `:568` (called from `main:782`). `chart.js` does not exist yet.
- **C2 deviates from the plan text by my ruling.** The plan has F-008 fetch
  `GET /api/run/{id}/result` itself, replacing `plot.html:167`'s embedded JSON — written before F-007
  existed. `run.js` already fetches it and publishes it on `#results-chart`. Issuing a second request
  for a payload already handed over is rung 2 of the ladder ignored. Data enters by contract.
- **C3 carries a physics constraint from B-019:** `samples[].weightsSquared` is unconditionally `null`,
  so the MC statistical input does not exist. The dispatch forbids inventing it or faking a band, and
  requires any omission to be named in the PR body with the missing field. An honest gap is not
  simplified away any more than the physics is.
- **C6:** a **static** legend is in scope — D-016 needs sample identity colour identical across graph,
  legend and plot — while legend *toggling*, PNG export, cutflow and the Z gauge stay out by the user's
  2026-09-07 ruling. `renderCutflowFigure` is left behind.
- **C7 closes M3:** the peak read off the drawn figure in the running app, not off a fixture JSON.

## Ready

**Wave 5 go-ahead given by the user, 2026-09-11.** F-007 dispatched 2026-09-16 → F-008 → D-016, serialised on the page.

**Outcome:** merged `7472675`, PR #47, 2 cycles. checks=11. Suite 691 -> 697; `tests/e2e/` 68 -> 74.
**C7 closed M3's coding work:** modal bin `90.0-91.2 GeV`, centre **90.6 GeV**, read off the drawn figure
in the running app and reproduced in three independent worktrees.

**The physics question, settled with evidence rather than argument.** C7's readout is
`6 predicted, 593 data` in the peak bin, which does not look right. The reviewer opened the fixture ROOT
files and read the per-event `weight` branches: `X1 0.008768`, `X2 0.032768`, `X3 0.004492`, `data 1.0`,
2000 entries each. Those MC weights are production normalisations (sigma*L / N_generated) over the **full**
sample; B-018's fixture keeps a 2000-event slice, so weighted MC is suppressed by the truncation while
pseudo-data at weight 1.0 is a raw count of its own slice. Totals X1 6.53 / X2 0.00 / X3 2.88 against 712
raw data, and **the shapes agree** — X1 peaks in `90.0-91.2` at 5.75, data peaks in the same bin at 593.
`chart.js` computes no counts. Not a bug. Recorded in `backend.md`'s contracts so it is not re-raised.
The consequence is against the fixture: `yMax = max(stack, data)` makes the MC stack a ~1px sliver and pegs
every populated ratio bin at the panel clip — **correct and unreadable on this fixture**. Backlogged, and
raised with the user because it is what the M3 checkpoint demo will show.

**A test was rewritten to stop tripping over a layout defect, and that needed checking.** The 650px figure
recentres the canvas row and pushes node `n1` under the palette, so F-007's cache-hit test was changed to
drag `n4`. The reviewer reproduced the shift with `elementFromPoint` (`node__title|SPAN` before,
`palette__add|BUTTON` after), confirmed `n4` is as valid a layout-only change, and confirmed the test still
asserts exactly what it did before — that test never guarded layout, so nothing was traded away. **But the
stated premise was false**: both the docstring and the PR body blamed "the unstyled shell", and the shell is
styled — `base.html:9-12` links four stylesheets and the real mechanism is `shell.css:183-204`'s
`.canvas-region { display: flex }` with `.canvas-wrap { margin: auto }` losing free space to a 650px
sibling. D-016 would have been briefed against a page state that does not exist. Fixed in every copy.

**The cycle-1 findings worth keeping.** F1: the published D-016 class list omitted every reveal class the
figure emits — a contract task shipping an incomplete contract to the task dispatched immediately after it.
F3: C5's stated proof did not exist; the test compared the normal-motion band to itself. F7: an assertion
against the absence of a class `chart.js` never emits, which cannot fail. F2/F5/F6/F8 were deletions and an
ARIA role: an undeclared 1600ms reveal budget on CSS nobody had written, a verbatim alias of `bandPath`,
`fill-opacity` hard-coded in JS, and `role="img"` on a subtree holding 50 focusable bin targets.

**Left for D-016, all in its dispatch:** `.chart-figure` needs `overflow-x: auto` or the figure shifts the
canvas; `#run-button[aria-disabled="true"]` must be styled busy because F-007 gave up the `disabled`
attribute to keep keyboard focus; `.hist-band` needs its `fill-opacity` back; `.legend-frame` paints as a
solid black block because it is a filled rect with no `fill` given; `.bin-hit` needs a visible focus ring;
the reveal must use `animation-fill-mode: forwards` because `.reveal-armed` is added once and never removed.
F9 (one garbled sentence stating that last point) was folded into D-016's dispatch rather than costing a cycle.
