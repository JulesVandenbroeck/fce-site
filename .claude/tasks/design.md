# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-001 — Wireframe exploration: mission screen and recipe builder
- **Scope:** `docs/wireframes/` (output only — no application files)
- **Accept:** `/wireframe` run for both the mission screen and the recipe-card builder;
  options explore genuinely different information architectures, not restyles of one
  layout; each is annotated with what it optimises for; a recommendation is stated with
  reasoning. **Output goes to the user for a decision — this is an M1 checkpoint.**
- **Depends on:** nothing (runs in parallel with the back-end chain)
- **Branch / PR:** `task/d-001-wireframes` — not yet opened
- **Status:** dispatched 2026-08-15
- **Note:** wireframes only, black and white, **phase 1 of the skill only** — the skill's
  phase 2 spawns parallel agents, which a sub-agent cannot do. No colour, no type, no
  visual system yet; those come after the user picks a layout direction.

## Ready

_none_

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css`, `src/fce_web/static/fonts/`
- **Accept:** every colour, spacing, type-scale, radius, and timing value defined as a
  custom property; the lab-notebook palette committed with measured AA contrast ratios
  documented in the file; self-hosted woff2 fonts, no CDN; a chosen serif and mono that
  are explicitly not Inter/Roboto/system-ui/Space Grotesk
- **Depends on:** D-001 (the user's layout choice)

## Blocked

_none_ — the baseline blocker cleared 2026-08-15. See `.claude/tasks/backend.md`.

## Done

_none_
