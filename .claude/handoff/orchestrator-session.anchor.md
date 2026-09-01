# Orchestrator anchor — 2026-09-01, ~75%

## The M1 ruling is IN. Bench.
D-007 merged `5839027`. The user chose **Bench**, overruling the comparison's Board.
Five further decisions came with it. All five are now written in **two** places:
- `docs/design-brief.md` — §2 (never passive), §4 (four decisions), §9 Decided. **65 insertions,
  0 deletions** — the engine allowlist quotation at §4 was not touched, deliberately.
- `.claude/tasks/design.md` `## Decisions in force` — the block a dispatch is *given*.

## What changed in the lists
- **D-002 → Ready**, unblocked. Seven node hues now, not eight.
- **D-009 → Ready** (node interiors; carries the ≤3-line ruling note for
  `design-explorations/README.md`, which still says "Recommended: Board"). Parallel with D-002.
- **D-010** (three-region shell) blocked on D-009. **D-011** (completed-mission box) on D-009+M5.
  **D-012** (event displays) on **M6, by the user's ruling**.
- `backend.md` `## Contracts in force` gained the **`DataSource` synthesised at submit** line.

## The consequence most likely to be rediscovered the hard way
`DataSource` left the palette but is still the root of every chain the engine's
`_VALID_CONNECTIONS` will accept. The run payload synthesises one at submit from the mission's
dataset. **The student's graph and the engine's graph are not the same object.** M3 owns
writing that into `docs/api.md:29-34`, still undefined.

## Next step
Nothing is dispatched. D-002 and D-009 are Ready and can go in parallel (no shared files) when
the user says. Still held: B-008 (#19, at the §5.7 limit), B-013 (#17), B-014 (#18).
