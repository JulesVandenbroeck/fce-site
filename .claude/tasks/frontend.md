# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

_none_

## Ready

_none_

## Blocked

### F-002 — Link the stylesheets into `base.html`
- **Scope:** `src/fce_web/templates/base.html`
- **Accept:** `<link rel="stylesheet">` for the design role's tokens and main stylesheet,
  in cascade order; page still renders with zero console errors and zero 404s
- **Depends on:** D-002 (the CSS files must exist first — a link to a missing file 404s and
  breaks B-003's zero-console-errors assertion, which is why F-001 ships without it)
- **Branch / PR:** not yet opened

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-001** — Minimal page shell: base layout and index template — `task/f-001-page-shell` #1,
  merged `176f7d5` (1 cycle, no rework)
