# Wireframes — D-001

**Open [`index.html`](index.html) in a browser.** Everything else hangs off it. Double-click the
file; it needs no server, no internet, and no build step.

This is an **M1 checkpoint**. It exists so one person can make two decisions:

1. which information architecture the **mission screen** uses
2. which information architecture the **recipe-card builder** uses

Everything downstream — the design tokens (D-002), the visual system, and all front-end markup
from M3 on — is built on the two layouts chosen here. So the value is in the *differences*
between the options, not in the polish of any one of them.

---

## What is here

| File | What it is |
|---|---|
| [`index.html`](index.html) | **Start here.** Both screens, the five options each, and both recommendations. |
| [`mission-screen.html`](mission-screen.html) | Screen 1 — five options + a summary tab with comparison tables and the recommendation. |
| [`recipe-builder.html`](recipe-builder.html) | Screen 2 — five options + a summary tab with comparison tables and the recommendation. |
| `index.css`, `mission-screen.css`, `recipe-builder.css` | Per-page wireframe CSS. |
| `base.css` | Shared framework CSS (tabs, panels, the browser frame, annotation styling). Adapted from the `wireframe` skill's template. |
| `brain/design-context.md` | The persistent design context the `wireframe` skill keeps. Written from `docs/design-brief.md` and the role manuals, because there is no existing UI to research or screenshot. |
| `brain/design-taste.md` | The skill's bundled craft-principles reference, copied unmodified. Not used in phase 1; it feeds the colour phase, which was not run. |

Nothing in this directory is application code. No CSS, template, token, font or Python file was
created or touched outside `docs/wireframes/`.

---

## The two recommendations, in short

**Mission screen — Option 2, Notebook Spread.** Two facing pages: the method on the left (brief and
card stack as one continuous written thing), a run log on the right that grows downward instead of
being overwritten. It is the only option where a new run does not destroy the previous one, so
"change one thing and compare" — the method the app exists to teach — is done by the layout rather
than asked of a 15-year-old's memory. It is also the only one where missing the objective looks
like ordinary work rather than an error state, which the brief requires. It costs the most to
build, and at 768 px the two pages stack into Option 5, so choosing it means building both.
*Cheaper fallback: Option 5, Long Column. The one to avoid, despite being the most familiar, is
Option 1 — it looks professional and quietly removes the comparison students most need.*

**Recipe-card builder — Option 1, Card Stack, with one change borrowed from Option 2:** a collapsed
card renders as a *clause of a sentence* ("Take data at 91 GeV from the IDEA detector.") rather
than as a settings summary ("Data · 91 GeV · IDEA"). That costs nothing to build and is the
difference between a stack that reads as a sentence — which the brief requires — and one that
merely lists what you picked. *Close alternative: Option 4, Guided Slots, if playtesting shows
students floundering in mission 1. The underlying config is identical either way, so switching
later is front-end work, not a rebuild.*

Both recommendations are written out at length, with what they cost, in each page's **Summary** tab.

---

## Ground rules these were drawn under

- **Black and white only.** `#000 #333 #666 #ccc #eee #f7f7f7 #fff`, plus `#999` for placeholder
  text inside simulated form fields. No colour anywhere, including in the CSS files.
- **No typeface has been chosen.** The browser's default sans is used deliberately, so nothing here
  reads as a type decision. Numerics use a generic monospace stack to show where tabular figures
  belong, not to propose a font.
- **No external requests.** No CDN, no remote fonts, no images, no `@import`. Every file loads from
  this directory. `docs/wireframes/` copied to a machine with no network renders identically.
- **Laptop and tablet only** — 1440, 1024 and 768 px. 768 is the floor, not a phone breakpoint.
- **Phase 1 of the `wireframe` skill only.** The skill's phase 2 renders colour variants via five
  parallel agents; it was not run, deliberately. Colour is premature before a layout is chosen, and
  the sub-agent that produced this cannot reliably dispatch parallel agents. The dead phase-2 UI
  (Clean / Polished sub-tabs, badges, completion banner) was stripped from the template rather than
  left in place pointing at nothing.

## Constraints that bounded the options

From `docs/design-brief.md`, before anything was drawn:

- No drag-and-drop node canvas (§4, §8). Nothing in any of the ten options drags.
- No phone layouts (§8).
- A run must never feel silent (§2), so live progress has a permanently reserved home in every
  option — the layout never jumps when a run starts.
- Failure is the normal case and must not read as an error (§2), so a miss is a margin note in the
  flow of the page. No banners, no modals.
- Card gating carries the teaching (§3): mission 1 shows only the cards it needs.

## Next step after a decision

D-002 — the design token foundation — is blocked on these two choices. Once they are made, the
picked layouts get the committed lab-notebook treatment: warm paper, ink, ruled lines, marginalia,
and one rationed vermillion accent for significance thresholds, mission completion and the signal
sample.
