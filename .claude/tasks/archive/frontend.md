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

