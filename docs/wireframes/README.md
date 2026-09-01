# Wireframes — D-001

> **Superseded 2026-08-16 by the node-graph pivot (`docs/design-brief.md` §4).** These recipe-card wireframes are no longer the plan; see `docs/design-explorations/` for the current build surface and its own comparison index.

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

- **Black and white only.** Twelve greys, exhaustively: `#000 #333 #666 #999 #ccc #eee #f0f0f0
  #f5f5f5 #f7f7f7 #f9f9f9 #fafafa #fff`. The five near-whites separate page ground from panel
  ground from hover state. `#999` appears only as placeholder text inside simulated form fields;
  every other piece of text clears WCAG AA. No hue anywhere, in any file.
  (`grep -rhoiE '#[0-9a-f]{3,8}' *.css *.html | sort -u` returns exactly that list, plus one
  `#ffe5c0` inside a CSS comment recording a value that was **removed**.)
- **No typeface has been chosen.** Every element on all three pages computes to one of exactly two
  `font-family` values, and no third value exists anywhere in the directory:
  - `sans-serif` on `body` (`base.css`), inherited by every heading, paragraph, button, control
    and table cell. This is the generic keyword, not a named face — it resolves to whatever the
    browser's *default sans-serif* font is (Arial on this machine's Chromium; Chromium's actual
    unqualified default, absent any `font-family`, is the serif `Times New Roman`), so no
    typeface is proposed. `getComputedStyle(document.body).fontFamily` returns `sans-serif`.
  - `ui-monospace, "DejaVu Sans Mono", monospace` on numerics and simulated code fields (four
    declarations, in `mission-screen.css` and `recipe-builder.css`). Generic keyword at both ends;
    the one named face in the middle is the stock Linux mono, present only as a fallback for
    browsers without `ui-monospace`. It marks where tabular figures belong; it is not a proposal.

  The real type decision — a distinctive serif for prose and a warm mono for numerics — is D-002's,
  and is deliberately absent here.
- **No external requests.** No CDN, no remote fonts, no images, no `@import`. Every file loads from
  this directory. `docs/wireframes/` copied to a machine with no network renders identically.
- **Laptop and tablet only** — 1440, 1024 and 768 px. 768 is the floor, not a phone breakpoint.
- **Phase 1 of the `wireframe` skill only, and phase 2 will not be run.** The skill's phase 2
  renders colour variants via five parallel agents. Colour is premature before a layout is chosen,
  and the real visual system is D-002's job, built from `docs/design-brief.md` and the committed
  lab-notebook direction rather than from a generic craft reference — so phase 2 has been dropped,
  not deferred. Its dead UI (Clean / Polished sub-tabs, badges, completion banner) was stripped
  from the template rather than left in place pointing at nothing, and the skill's bundled taste
  reference was removed with it so that nothing in this directory can be mistaken for project
  design guidance.

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
