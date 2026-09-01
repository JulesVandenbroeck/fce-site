# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

_none._

## Ready

_none._

## Blocked

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css`, `src/fce_web/static/fonts/`
- **Accept:** C1 every colour, spacing, type-scale, radius and timing value is a custom property;
  C2 the palette committed with measured AA ratios documented in the file — measured against the
  real paper token, and for labels sitting *on* saturated fills, not only on paper; C3 self-hosted
  woff2, no CDN; C4 a serif and a mono that are explicitly not Inter/Roboto/system-ui/Space
  Grotesk. checks=4.
- **Depends on:** the user's choice among Beamline / Bench / Board, presented at the **D-007**
  checkpoint, with `docs/design-explorations/tokens.css` as its input rather than a blank page.
  **D-007 merged `5839027` 2026-09-01 with the index and the recommendation in hand — the only
  thing still blocking D-002 is the user naming a style.** The recommendation is **Board**; it is
  advisory. Read it at `docs/design-explorations/README.md` `## Recommendation`, or open the index
  in a browser (preview worktree `~/d007-preview`, refresh it to the merged head first).
- **Owed forward:** the palette must now carry node-type hues, sample identity and lock state.
  `--ink-45` composites to 2.60:1 and fails AA for text — do not inherit it unstated. Take the
  **corrected** tab10 values (`#8c564b`/`#17becf`), not cycle 3's `#ff7f0e`/`#2ca02c`.
- **Branch / PR:** not yet opened
- **History:** [`archive/design.md`](archive/design.md)

#### Constraints the node-graph tasks established

The one axis CSS cannot swap is **what the graph persists**, and it is what later lands in
`POST /api/run`: **A · Beamline** ordered edge list only; **B · Bench** `{x, y}`;
**C · Board** `{column, slotIndex}` — the only one where the plot lives inside the graph as the
terminal node. What D-003 hands all of them: the figure is a **fixed intrinsic 650×460** CSS px
and does not reflow; harvest the **cycle-4** `--tab10-x2`/`--tab10-x3` values; `--ink-45` is
2.60:1 and not text-safe. Fuller case for each style: [`archive/design.md`](archive/design.md).

## Done

One line per task. Full entries in [`archive/design.md`](archive/design.md).

- **D-007** — comparison index and the recommendation (**M1 checkpoint**) — #21, `5839027`,
  2 cycles + 1 re-spec, clean gate `0R / 0M / 3m`. checks=8. **Recommends Board**; the user
  picks. m4/m5/m6 backlogged. Both majors were false cross-document *paraphrases* — C8 gates
  quotations only, which is why the cycle-2 dispatch also required a claim/`file:line` table.
- **D-006** — Board node graph, typed columns, terminal plot node — #20, `0aee604`, 3 cycles,
  final gate `1R / 0M / 0m`. **Merged on the user's ruling with C10 overruled in writing**
  (PR #20 comment `5497106719`). C6's fixed 650×460 plot, M1's "lanes must not read as empty"
  and C10's "the emptiness must not be papered over" are mutually unsatisfiable, and the Data
  lane provably cannot hold a second card — `VALID_CONNECTIONS` chains nothing to a second
  `DataSource`. **C10 was my defect twice:** first trivially satisfiable (the `aria-hidden`
  filler added for M1 became the element satisfying the metric), then unreachable by
  construction once the instrument was made honest. §2's *do the feasibility arithmetic before
  you impose a floor* was never done. checks=11, 10 met. C8/C9 closed D-005's m4 and m9.
- **D-005** — Bench node graph, free canvas, drag-to-connect — #16, `4720179`, 3 cycles,
  `0R / 0M / 4m`. Merged by the user by hand before its cycle-3 review ran — legitimate,
  confirmed 2026-09-01, closed. m4/m9 → D-006 C8/C9. **m7 still open** (the "chips render
  identically" body claim, three cycles uncorrected).
- **D-008** — CVD-safe node palette + the checker claim — #7, `2d0de23`, 3 cycles + 1 re-spec,
  first design task to close on a clean gate.
- **D-004** — Beamline node graph, shared palette and checker — #6, `bac2f62`, 3 cycles,
  §5.7 limit; 2 open → **D-008**.
- **D-003** — interactive plot component at reference parity — #5, `99ec8f3`, 4 cycles, merged on
  the user's explicit override.
- **D-001** — wireframes: mission screen and recipe builder — #2, `b580729`, 4 cycles, 1 open;
  superseded by the 2026-08-16 node-graph pivot.

## Floors in force

- **`verify.py --all` EXITS 1 on `main` as of `0aee604`**, with exactly one known-red section:
  `board-lane-fill`. That is D-006's overruled C10, left registered and red **on purpose** so the
  constraint stays visible if the node model or the plot's sizing ever changes.
  **A future task must not read that as a regression it introduced, and must not delete,
  disable, relabel or downgrade that section to make the run green.**
- `verify.py` on `main` at `0aee604`: **65** registered sections, **265** passing assertion
  lines. `grep -c 'all_results.append'` = **69**; `grep -c 'results.append\|line('` = **233**.
  A fall in either is `Required`. Superseded historical figure: 46 / 149 / 121 non-bench at
  `4720179`, whose 149 was measured by an unrecorded command and does not reproduce.
- D-008's six simultaneous palette floors: min CVD ΔE **5.129** (≥4.0), normal-vision node-node
  **14.170** (≥14.0), node-vs-reserved **13.442** (≥4.0), white-on-fill **4.595:1** (≥4.5),
  fill-vs-reserved hue gap **14.1°** (≥12.0°), clamping excess **+0.0051** (≤0.01). Asserted
  inside three registered sections, not six.
- **Do not re-derive:** `.board-wrap { overflow-x: hidden }` does *not* break a scroll-reachability
  check — `overflow: hidden` stays programmatically scrollable via `scrollLeft`. Established by
  D-006's cycle-2 reviewer.
