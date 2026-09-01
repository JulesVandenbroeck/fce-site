# Orchestrator anchor — 2026-09-01 (session 2)

**Consumed** the previous `SESSION.md` (D-006 merged, D-007 unblocked). Reconciled against git:
`origin/main` = `4625273`, PRs #17/#18/#19 open exactly as it said. It is now stale except for
one correction below, and must be archived once D-007 closes.

## Decisions this session
- **User ruling: D-007 only.** B-008 stays at cycle 2 (§5.7 limit, escalate not cycle 4);
  #17/#18 stay held. Do not resume without the user.
- **User ruling: `docs/design-explorations/index.css` added to D-007's scope.** The recorded
  entry had only index.html + README.md, which left no legal place for CSS (no inline `style=`,
  no shared index stylesheet). D-001's index had its own index.css — same shape.
- `README.md` in D-007's scope means `docs/design-explorations/README.md`, a new file. **There is
  no README at the repo root** and none in that directory today. Confirmed, not assumed.
- C6 written as a **main-vs-branch differential**, not an absolute count, because my own two
  records disagreed (design.md 65, SESSION.md 63). The differential is immune to which is stale.

## Enumerated, not inherited (2026-09-01)
- `verify.py`: **65** registered sections, **64** pass, `board-lane-fill` the only red, `--all`
  exits 1. `all_results.append` grep = **69** (4 comment mentions), `results.append\|line(` = **233**.
- **`SESSION.md`'s "63 sections / 62 pass" was WRONG. design.md's 65 is right.**
- verify.py **globs nothing** — four hard-coded page paths at `verify.py:83,89,92,95`. A new
  `index.html` in that directory cannot affect it. This was the one risk to D-007's scope; closed.

## Dead ends ruled out
- Do **not** put D-007's CSS in a `<style>` block or reuse `frame.css` — both considered, both
  rejected by the user's ruling.
- Do **not** edit `.claude/scripts/open-wireframes.sh` to add a preview target. Cheaper path:
  `git worktree add --detach ~/d007-preview origin/task/d-007-index`, then a `file://$HOME/...`
  URL. Snap Firefox cannot read `/tmp` — never hand out a `/tmp` URL.

## Exact next step
D-007 is **in flight**, cycle 1, `task/d-007-index`, design-coder in a worktree at effort high.
On its report: §5.1 free gate in a fresh worktree (re-run its own numbers, incl. both falsification
transcripts) → `gh pr view` for body adequacy → dispatch `code-reviewer` with the PR number only,
**effort medium** (the review is cross-file: index claims vs the three pages' code) → merge at
0R/0M → **STOP. D-007 is the checkpoint.** Then: record the user's style choice in design.md,
unblock D-002, and `git mv .claude/handoff/SESSION.md .claude/handoff/archive/session-2026-09-01.md`.

## Criteria still open
All six. checks=6. Plan: `~/.claude/plans/claude-handoff-session-md-start-plan-fo-swift-horizon.md`.
