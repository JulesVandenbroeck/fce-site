# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

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

## Blocked

_none_

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-001** — Minimal page shell: base layout and index template — `task/f-001-page-shell` #1,
  merged `176f7d5` (1 cycle, no rework)

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
