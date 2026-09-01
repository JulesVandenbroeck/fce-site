# Design explorations — D-007 comparison

**Open [`index.html`](index.html) in a browser** — no server, no internet, no build step.
It links the three complete node-graph explorations built for this checkpoint —
[`beamline.html`](beamline.html) (D-004), [`bench.html`](bench.html) (D-005) and
[`board.html`](board.html) (D-006) — side by side, and this file carries the recommendation
that picks one. That choice is the sole input D-002 (the design token foundation) is
blocked on; nothing past this checkpoint is decided until it is read.

---

## Recommendation

**Recommended:** Board

Board is the only one of the three whose persisted shape already answers the question
`docs/design-brief.md` §4 poses about the run payload's own "ui object": which pipeline
stage a node is in, read directly from structure rather than inferred from an arrival
order or a free coordinate. It persists `{nodes: [{id, column, slotIndex}], edges}` — a
node's `column` fixed by its kind (Data always lane 0, Histogram always lane 4) and its
`slotIndex` its order within that lane, both read back from live DOM structure rather than
tracked as separate state that could drift from the render. `docs/api.md` marks
`POST /api/run` "_To be defined in M3._" — it specifies no request body today, and its only
`edges` are histogram bin edges, not graph edges. So this is not a case of Board already
matching a settled contract; it is the reverse. Whatever style wins this comparison is what
the M3 request-body definition will have to persist: the engine will still ignore
`column`/`slotIndex` exactly as it would ignore Bench's `{x, y}` (design-brief.md §4 — "any
layout state … lives in a separate `ui` object the engine ignores"), but the `nodes[] +
edges[]` half of whichever shape is chosen here is what a future `POST /api/run` body will
carry to the physics engine, node-for-node and edge-for-edge. Choosing Board now is choosing
to define that undefined contract as one where a node's pipeline stage is recoverable from
structure rather than inferred — which makes this recommendation more load-bearing than a
comparison of three finished demos usually is, not less.

The consequence of choosing Board: build cost is real. Five typed lanes are more surface
than Beamline's single rail or Bench's blank canvas, and a board wide enough for all five
needs to scroll horizontally under 768 px (`.board-wrap`, the same device Bench's canvas
already needs). Both are accepted rather than discovered late, because the thing Board buys
in return — a graph that reads as *which pipeline stage is this node in* at a glance,
independent of when a student happened to add it, satisfying design-brief.md §4's own "it
still reads as a pipeline" requirement more literally than either alternative — is worth
that cost for a teaching tool whose whole point is that pipeline.

---

## What each option gives up

### Beamline

Gives up all spatial arrangement: a student cannot place a node anywhere, and cannot use
position to say "these two belong together". Its ordered edge list is the simplest of the
three shapes to persist and to reason about, and it is the only style with a genuine answer
at 768 px — the rail wraps rather than needing a scrolling canvas — but that simplicity is
also a ceiling: nothing about *where* a node sits, or which stage it occupies, is ever
visible or recoverable from the persisted state itself.

### Bench

Gives up a graph reading the same way twice. Two students building an identical pipeline
can leave it looking entirely different, because `{id, x, y}` records wherever a student
happened to drop a node rather than anything about its role in the pipeline. In exchange it
buys real spatial freedom — grouping, spreading a wide pipeline out, matching a diagram from
class — which neither Beamline nor Board offers. It has no strong story at narrow widths:
a free canvas needs real room to be worth having, and 768 px is where that runs out first.

### Board

Gives up Bench's free arrangement — a node cannot sit next to an unrelated one just because
a student wants them near each other, since column is fixed by kind — and gives up
Beamline's single-glance simplicity, since five lanes read as more machinery than one rail
before a student has added anything. What it buys instead is answering a question neither
of the other two can from the persisted state alone: which pipeline stage a node is in,
at a glance, independent of add order. This is the recommendation above, and its costs are
accepted, not overlooked.
