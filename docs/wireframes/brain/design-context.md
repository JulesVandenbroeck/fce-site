# Design Context — FCE-site

Generated: 2026-08-15 (task D-001)

> The `wireframe` skill's first-run flow asks for 2–3 screenshots of the current app and
> writes this file from codebase research. **There is no current app.** The repo contains a
> backend package skeleton, no templates, no CSS, no rendered view of any kind. The
> predecessor `kskovpen/fce` is a Dear PyGui **desktop** program whose UI is explicitly not
> being reused, so screenshotting it would seed the wrong patterns.
>
> So this file is written from the authoritative written sources instead:
> `docs/design-brief.md`, `.claude/shared/CLAUDE.md`, `.claude/design/CLAUDE.md`.
> No screenshots were requested from the user, because there is nothing to screenshot.
>
> Consequence for the wireframes: **Option 1 "the safe option" cannot mean "extends the
> existing app"** — there is no existing app. It means the conventional, lowest-risk answer
> a reader will recognise from other tools: the two-column workspace.

## App Overview

A browser-based learning game teaching 15–18 year olds real particle-physics data analysis
on simulated FCC-ee collision data. Students assemble an analysis from a vertical stack of
"recipe cards", run it against real simulation, read the resulting histogram, and are
scored on what they find. A teacher runs one server; a class connects over the local
network. Possibly no internet in the room.

## Target Platform

**Desktop / Web, laptop and tablet only.** Phone layouts are an explicit non-goal
(`design-brief.md` §8). Design widths: 1440 (laptop), 1024 (tablet landscape), 768 (tablet
portrait). 768 is the floor, not a phone breakpoint.

## Layout Patterns

Nothing exists yet, so this section is constraints rather than observations:

- Server-rendered Jinja2 + HTMX. Fragments swap in place; there is no client router. A
  layout that needs whole-page state juggling in JS is the wrong shape for this stack.
- Flex and grid, relative units. Wide content (the cutflow table, the chart) scrolls inside
  its own container; the page body never scrolls horizontally.
- No build step, no npm, no CDN, no remote fonts. Everything ships from `static/`.

## Navigation

- A campaign of ordered missions: done / current / locked. Completing one unlocks the next.
- A free sandbox unlocks after the last mission.
- Students identify with a class code + nickname. No accounts, no login screen beyond that.
- **Where the campaign lives in the layout is an open question these wireframes answer
  differently in each option** — it is one of the main things being decided here.

## Page Types

### Mission screen (wireframed here)

Carries, all at once: the mission brief, the objective, the analysis being assembled, the
run control and its live progress, the resulting histogram, the cutflow, and — from mission
3 — the fitted μ and the significance gauge. Plus some sense of the campaign around it.

### Recipe-card builder (wireframed here)

A vertical pipeline: `Data → Filter → Observable → Plot`. Cards can be added, removed,
reordered where meaningful, and collapsed once configured. It must read top to bottom as a
sentence describing the analysis. Card availability is gated per mission — mission 1 shows
only the cards it needs.

### Others, not wireframed in this task

Join (class code + nickname), the campaign/logbook overview, the sandbox, mission complete.

## Interaction Patterns

- **Run progress must never be silent.** A run takes seconds to minutes and streams phase
  label + progress over SSE. Silence reads as broken to a teenager. Progress needs a real,
  reserved home in the layout — not a toast, not a spinner in a corner.
- **The cache is a feature, and the UI says so.** A repeated analysis returns almost
  instantly and the interface tells the student why: *"recognised these cuts — reusing your
  earlier run."*
- **Failure is the normal case.** Missing the objective is expected, not an error. The
  response is a margin note pointing at what the numbers suggest. Never a red banner, never
  an error state.
- Expression entry (`l1.pt > 20 and (l1.p4 + l2.p4).mass > 80`) stays available for students
  who get that far. Rejection messages are written for a 16-year-old.
- The chart is hand-written interactive SVG: stacked backgrounds, data as points with error
  bars, hover reads out a bin, legend toggles samples.
- Every interactive control is reachable and operable by keyboard.

## Content Hierarchy

- Mission title → brief (short prose) → objective (a checkable statement) → the analysis →
  the result → the verdict.
- **Z (significance) is the score.** Drawn as a ruled gauge with 3σ and 5σ as labelled
  threshold lines. Crossing one is an event, not a number ticking over.
- Copy is English, written to be read as a second language: short sentences, plain words,
  no idiom. Physics vocabulary is the deliberate exception — it is what is being taught.

## Screenshot Observations

None. See the note at the top — there is no UI to screenshot.

## UX Conventions to Maintain

- **No drag-and-drop node canvas.** Rejected in the brief (§4, §8). Any option that smells
  like one is out of bounds.
- **Card gating carries the teaching.** Students are never shown a wall of controls they
  have no reason to understand yet.
- **The stack is a sentence.** A student should be able to point at their analysis and say
  what it does.
- Semantic HTML, landmarks on every page, no `<div>` where a semantic element exists.
- Aesthetic direction (committed, out of scope for these B&W wireframes but it constrains
  layout): lab notebook — warm paper, real ink, ruled lines, marginalia; one rationed
  accent, red-pen vermillion, reserved for significance thresholds, mission completion, and
  the signal sample. Game feel comes from artefacts and ritual — stamps, a logbook that
  fills in, ink-draw reveals — never from saturated colour.
