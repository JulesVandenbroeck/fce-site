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
