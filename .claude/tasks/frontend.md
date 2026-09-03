# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

_none_

## Ready

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

## Blocked

_none_

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-001** — Minimal page shell: base layout and index template — `task/f-001-page-shell` #1,
  merged `176f7d5` (1 cycle, no rework)
