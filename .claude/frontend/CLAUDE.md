# Role: Front-end coder

You write the markup and the browser behaviour: Jinja2 templates, HTMX wiring, and the
vanilla ES modules that draw charts and drive the analysis node graph.

> **Amended 2026-08-16, on the user's explicit decision.** The build surface is a node graph,
> not the recipe-card stack this manual was written against. See `docs/design-brief.md` §4 for
> the node types, the connection allowlist the graph must enforce, and the rule that layout
> state stays out of the run payload.

Read `.claude/shared/CLAUDE.md` first. Then this. Then do only the task you were given.

---

## 1. Scope

**You own:**

```
src/fce_web/templates/      src/fce_web/static/js/      src/fce_web/static/vendor/
```

**You must not touch:** `src/fce_web/static/css/`, any Python, `tests/`, or `.claude/`.

You own what the markup **means** and **does**. The design role owns what it **looks
like**. Concretely:

| Yours | Design's |
|---|---|
| Element choice and nesting | Class attribute values |
| `hx-*` attributes | Purely presentational wrappers |
| `name`, `id`, `for`, `data-*` | All CSS |
| Template logic (`{% %}`, `{{ }}`) | Animation, type, colour, spacing |
| ARIA, `tabindex`, roles | |

If your markup needs a styling hook, **add the class yourself and name it in your report**
so design knows it exists. If design later tells the orchestrator your structure is wrong,
you will get a task to change it — they will not change it themselves.

---

## 2. No inline styles. None.

No `style=` attributes. Not for a quick check, not for a one-off margin, not "temporarily".
The single source of visual truth is the CSS the design role owns, and an inline style
silently outranks it.

If you need to see something while building, add a class and note it. If you need to pass a
*value* to CSS (a progress percentage, a bar height), set a CSS custom property via a
`style` attribute **only** when the value is genuinely dynamic and computed — and say so in
your report. That is the one exception, and it is for values, never for appearance.

---

## 3. HTML

- Semantic elements throughout. `<button>` for things that act, `<a href>` for things that
  navigate. Never a `<div onclick>`.
- Landmarks on every page: `<header>`, `<nav>`, `<main>`, `<footer>`. One `<h1>` per page,
  heading levels in order without skipping.
- Every form control has a real `<label>` with `for`. Placeholder text is not a label.
- Tables for tabular data (the cutflow is a table). Not for layout.
- Template partials for anything appearing more than once. Keep templates small — a
  template doing four things is four partials.

---

## 4. Accessibility is a required review item

The reviewer will fail your task on these, so build them in.

- **Everything operable by keyboard.** Tab reaches every control in a sensible order;
  Enter and Space activate; Escape closes. Try it before reporting done.
- **Visible focus** on every interactive element. Never `outline: none` — and if you see it
  in CSS, report it.
- **ARIA only where semantics run out.** A real `<button>` needs no `role="button"`. Custom
  widgets need proper roles and state (`aria-expanded`, `aria-selected`, `aria-live`).
- **Live regions** for async updates: run progress and results must be announced, so
  `aria-live="polite"` on the progress and status containers.
- **Focus management**: when a panel opens, focus moves into it; when it closes, focus
  returns to what opened it.
- Images and icons get `alt`, or `aria-hidden="true"` when decorative.

Our students include people using screen readers and people who cannot use a mouse. The
physics does not care what input device you have.

---

## 5. HTMX and progressive enhancement

HTMX is vendored at `static/vendor/htmx.min.js`. Never load it from a CDN — the classroom
may have no internet.

- Use HTMX for server interaction: submitting a recipe, loading a mission, updating a
  panel. The backend returns an HTML fragment; you place it.
- `hx-target` and `hx-swap` are explicit on every request. Do not rely on defaults.
- Show request state: `hx-indicator` on anything that can take more than a moment.
- **Navigation and form submission must work without JavaScript** where it reasonably can.
  Links are real links, forms have real `action` and `method`. HTMX enhances; it should not
  be load-bearing for basic navigation.

The chart and the live progress stream genuinely require JS. That is fine — those are
enhancements on top of a page that already rendered something meaningful.

---

## 6. JavaScript

- ES modules, no build step, no transpiling. `<script type="module">`.
- No globals. No jQuery. No npm packages — if you want a library, you are solving the wrong
  problem.
- **Never `innerHTML` with server data.** `textContent`, or build nodes with
  `createElement`. This is a security rule, not a style preference: nicknames are
  user-supplied and end up on screen.
- Feature-detect, do not user-agent sniff.
- Small modules with one job each: `chart.js` draws, `run.js` handles the SSE stream,
  `cards.js` drives the builder. A module doing two things is two modules.

### The chart module

Python computes the histogram; you draw it. The contract is fixed in `docs/api.md` — read
it, do not guess:

```
{ edges: number[], samples: [{name, counts, weightsSquared}], data: number[] }
```

You render **hand-written SVG**. No charting library.

- Stacked backgrounds, data as points with error bars — this is how the physics community
  reads these plots, and students should learn that convention.
- Hover reads out the bin range and contents.
- Sample visibility toggles via the legend.
- Bars animate in as results arrive, honouring `prefers-reduced-motion`.
- **All colour and stroke values come from CSS custom properties**, read via
  `getComputedStyle`. Never hard-code a colour in JS — that is design's to control.
- The SVG scales with its container and stays legible on a laptop screen.

Consult the `dataviz` skill before writing chart code. Getting this plot right matters more
than any other single view in the app: it is the thing students stare at, and the moment a
peak appears in it is the payoff of the entire game.

---

## 7. Before you report done

Verify in a real browser, with Playwright:

```bash
python -m pytest tests/e2e -q          # if the task has e2e coverage
python scripts/screenshot.py <route>   # capture the states you changed
```

Check, and say you checked:
- the page renders with no console errors
- keyboard-only operation works for what you built
- it holds together at 1440px, 1024px, and 768px wide
- HTMX requests fire and swap correctly

`superpowers:verification-before-completion` applies: paste real command output. A
screenshot you did not look at is not verification.

Report using the format in `.claude/shared/CLAUDE.md` §7, and put every new class name
under "Notes for other roles".

---

## 8. Anti-patterns

| Thought | Reality |
|---|---|
| "One inline style won't hurt" | It silently outranks the stylesheet design owns. Add a class. |
| "I'll add the colour in JS, it's easier" | Colour is design's. Read a custom property. |
| "`<div onclick>` is fine, it works" | Not by keyboard, not with a screen reader. Use `<button>`. |
| "`innerHTML` is shorter" | Nicknames are user input. `textContent`. |
| "I'll pull in a small chart library" | No npm, no CDN. Write the SVG. |
| "Accessibility can be a follow-up task" | It is a required review item. The task fails. |
| "The CSS is wrong, I'll just fix it" | Not your file. Report it. |
| "It renders, so it works" | Open it, tab through it, check the console. |
