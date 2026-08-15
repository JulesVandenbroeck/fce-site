# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-001 — Minimal page shell: base layout and index template
- **Scope:** `src/fce_web/templates/base.html`, `src/fce_web/templates/index.html`,
  `src/fce_web/static/js/app.js`
- **Accept:** `base.html` is a valid HTML5 document — `<html lang="en">`, `<meta charset>`,
  `<meta viewport>`, `<title>{{ title }}</title>`, a `<main>` landmark, a
  `{% block content %}`; `index.html` extends it and renders `{{ title }}` in an `<h1>`
  plus one plain sentence; `static/js/app.js` is an empty ES module referenced as
  `<script type="module" src="/static/js/app.js" defer>`; no stylesheet link, no inline
  `style=`, no HTMX, no CDN, no `<div>` where a semantic element exists
- **Contract:** the templates take exactly one context variable, `title` (str). Static
  assets are referenced by literal path under `/static/` — B-002 mounts there.
- **Depends on:** nothing
- **Branch / PR:** `task/f-001-page-shell` — not yet opened
- **Status:** dispatched 2026-08-15
- **Why this exists:** B-002 was originally scoped to serve HTML from a Jinja2 template and
  mount `/static`, but `templates/` and `static/` belong to **frontend**, not backend
  (shared §4). Backend cannot author them and `StaticFiles` cannot mount a directory that
  does not exist. So the page shell is its own front-end task and B-002 now depends on it.
  This moves the first front-end task from M3 to M1; the API contract is not needed for a
  shell that takes one string.

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

_none_
