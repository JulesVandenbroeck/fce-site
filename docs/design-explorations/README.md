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

Board is the only one of the three whose persisted shape makes a node's pipeline stage
recoverable from structure alone, without inferring it from an arrival order or a free
coordinate. It persists `{nodes: [{id, column, slotIndex}], edges}` — a node's `column`
fixed by its kind (Data always lane 0, Histogram always lane 4) and its `slotIndex` its
order within that lane, both read back from live DOM structure rather than tracked as
separate state that could drift from the render. `docs/design-brief.md` §4 does not pose
this as an open question for the payload to answer — it already classifies `column` and
`slotIndex` as exactly the layout state its own `ui` object exists to segregate: "Any
layout state … lives in a separate `ui` object the engine ignores." So neither field
carries any more weight in the run payload than Bench's `{x, y}` does; the engine will
discard all three identically, and `docs/api.md` marks `POST /api/run` "_To be defined in
M3._" — it specifies no request body today, and its only `edges` are histogram bin edges,
not graph edges. Board is not already matching a settled contract, and does not become one
by being chosen: whatever style wins this comparison is what the M3 request-body
definition will have to persist, and the `nodes[] + edges[]` half of whichever shape is
chosen here — never the ui-object half — is what a future `POST /api/run` body will carry
to the physics engine, node-for-node and edge-for-edge. What Board buys instead is the
requirement `docs/design-brief.md` §4 states outright, not one it merely implies: "It still
reads as a pipeline." A student should be able to point at the graph and say what it does,
in order. Its five typed lanes make that legible from structure without inference; Beamline
needs an arrival order and Bench needs a free coordinate to convey the same thing. Choosing
Board is choosing legibility for the student, not pre-empting any part of an undefined
contract — but it still
makes this recommendation more load-bearing than a comparison of three finished demos
usually is, because whatever `nodes[]`/`edges[]` shape ships here is the one M3 inherits.

The consequence of choosing Board: build cost is real. Five typed lanes are more surface
than Beamline's single rail or Bench's blank canvas, and a board wide enough for all five
needs to scroll horizontally under 768 px (`.board-wrap`, the same device Bench's canvas
already needs). Both are accepted rather than discovered late, because the thing Board buys
in return — a graph that reads as *which pipeline stage is this node in* at a glance,
independent of when a student happened to add it, satisfying `docs/design-brief.md` §4's own
"It still reads as a pipeline" requirement more literally than either alternative — is worth
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
