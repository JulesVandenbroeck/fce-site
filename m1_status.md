 What are the tasks still required for M1 milestone to have  node-graph styles for the user to choose from?

Three tasks, in a fixed serial order. Two of the three styles already exist.

Already done
- D-004 — Beamline (style A) — merged bac2f62, 3 cycles, closed at the §5.7 loop limit with 2 open findings.
- D-008 — CVD-safe node palette + checker — merged 2d0de23, the first design task to close on a clean gate. This is what unblocked the remaining two styles: tokens.css's eight --node-* fills are now final and read-only for D-005/D-006.

Still required

1. D-005 — Bench (style B) — Ready
  - Scope: create docs/design-explorations/bench.{html,css,js}, append a --bench section to verify.py. tokens.css read-only.
  - Model: persists {x, y} per node on a free canvas; drag-to-connect accepted, click-to-connect refused. Same 64/13/51 enumeration, same inventory denominators, same three-width sweep as D-004.
2. D-006 — Board (style C) — Ready
  - Scope: create board.{html,css,js}, append a --board section to verify.py. tokens.css read-only.
  - Model: persists {column, slotIndex} in typed columns, accepts both gestures plus keyboard connection. The plot lives inside the graph as the terminal node, so it must budget for D-003's fixed intrinsic 650×460 figure and be shown doing so at 768px.
3. D-007 — Comparison index and the recommendation — Blocked on D-004+D-005+D-006. This is the checkpoint you read to choose.
  - Scope: docs/design-explorations/index.html, README.md, plus a two-line "superseded" note atop docs/wireframes/README.md. No page files, no tokens.css, no verify.py.
  - Accept: the index links all three styles and states, per style, what the graph persists and which gesture connects; the README states a recommendation with reasoning and names what each option gives up.

Constraints that bind the dispatch

- D-005 then D-006 serially, never in parallel — both append a new section to verify.py, and the worktree rule protects the branch, not the merge, so two coders in flight collide.
- --node-data is #966746, not D-004's #8d5548 — anything harvested from the D-004 era is stale.
- Floors currently in force and enforced by review: verify.py at 31 sections / 48 assertions (a fall in either is Required), plus D-008's six palette floors.
- The axis CSS cannot swap is what the graph persists, and it lands directly in POST /api/run: A ordered edge list only, B {x, y}, C {column, slotIndex} — C is the pre-registered recommendation and the only one where the plot is the terminal node.

After you choose at D-007, D-002 (token foundation) unblocks with docs/design-explorations/tokens.css as its input, and F-002 (link the stylesheets into base.html) unblocks behind that.
