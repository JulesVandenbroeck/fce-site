# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

_none_

## Ready

_none._

## Blocked

### F-002 — Link the stylesheets into `base.html`
- **Scope:** `src/fce_web/templates/base.html`
- **Accept:** `<link rel="stylesheet">` for the design role's tokens and main stylesheet,
  in cascade order; page still renders with zero console errors and zero 404s
- **Depends on:** ~~D-002~~ **merged 2026-09-03 (#24, `72d2950`) — RELEASED.**
  `src/fce_web/static/css/tokens.css` exists and is the tokens file to link. There is **no
  main stylesheet yet** — D-010 is the first task that writes one — so this task links tokens
  only, unless it is dispatched after D-010. **F-002 is what first renders the shipped
  `tokens.css`**: nothing on the D-002 branch consumed it, by construction, so the four
  self-hosted woff2 under `src/fce_web/static/fonts/` are exercised for the first time here.
  Their `src:` URLs must resolve at the served path, not just on disk — a 404 on a font is
  exactly what this task's zero-404 assertion exists to catch.
- **Branch / PR:** not yet opened
- **Status:** **blocked on B-017.** The `scout` fact-find, 2026-09-07: `tests/e2e/conftest.py`
  collects console errors (`PageActivity.console_errors`, `:51`) and **requested URLs only**
  (`:53`, `page.on("request", ...)` at `:82`). There is **no response-status collection anywhere
  under `tests/`**, so "zero 404s" has no instrument — a font 404 is indistinguishable from a 200
  in the data that exists. `conftest.py` is backend's file, so the probe was split off as
  **B-017** and this task consumes it read-only. Do not weaken the criterion to fit the old
  instrument; that is the D-001 failure shape.
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
