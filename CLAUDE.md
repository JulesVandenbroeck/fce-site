# FCE-site

A browser-based learning game teaching high-school students particle-physics data analysis
on simulated Future Circular Collider (FCC-ee) data. Python engine, HTML/CSS frontend,
built by an agentic workflow of one orchestrator and four sub-agents.

**This file is an index. The content lives in the files it points to.**

---

## Start here

| You are | Read |
|---|---|
| **Orchestrating** (the main session) | Run `/orchestrate`, or read [`.claude/orchestrator/CLAUDE.md`](.claude/orchestrator/CLAUDE.md) |
| **Any role, always first** | [`.claude/shared/CLAUDE.md`](.claude/shared/CLAUDE.md) — stack, ownership, conventions, physics glossary |
| **Doing user-facing work** | [`docs/design-brief.md`](docs/design-brief.md) — the product concept |

## Roles

| Role | Manual | Sub-agent |
|---|---|---|
| Orchestrator — plans, dispatches, tracks. Writes no code. | [`.claude/orchestrator/CLAUDE.md`](.claude/orchestrator/CLAUDE.md) | *(main session)* |
| Back-end coder — FastAPI, SQLite, physics engine | [`.claude/backend/CLAUDE.md`](.claude/backend/CLAUDE.md) | `backend-coder` |
| Front-end coder — templates, HTMX, JS, accessibility | [`.claude/frontend/CLAUDE.md`](.claude/frontend/CLAUDE.md) | `frontend-coder` |
| Design coder — CSS, tokens, type, motion | [`.claude/design/CLAUDE.md`](.claude/design/CLAUDE.md) | `design-coder` |
| Code reviewer — tests everything, fixes nothing | [`.claude/review/CLAUDE.md`](.claude/review/CLAUDE.md) | `code-reviewer` |

## Task state

Separate list per part of the site. The orchestrator maintains these; they are the only
state that survives between sessions.

- [`.claude/tasks/backend.md`](.claude/tasks/backend.md)
- [`.claude/tasks/frontend.md`](.claude/tasks/frontend.md)
- [`.claude/tasks/design.md`](.claude/tasks/design.md)
- [`.claude/tasks/backlog.md`](.claude/tasks/backlog.md)

## Contracts

- [`docs/api.md`](docs/api.md) — JSON and SSE contracts between backend and frontend
  *(stub; populated in M3)*
- `content/missions/*.yaml` — mission definitions, authored as data

---

## Always use `rtk`

**Every shell command goes through [`rtk`](https://github.com/rtk-ai/rtk)** — a proxy that
filters verbose tool output down to what matters, saving 60–90% of the tokens the raw
command would cost. `rtk git status`, `rtk pytest tests/`, `rtk gh pr diff 12`.

A hook rewrites most commands automatically, so normally you just write the command and
`rtk` is applied for you. Write it explicitly when unsure. `rtk proxy <cmd>` runs something
unfiltered when you need the raw output to debug; `rtk gain` reports what has been saved.

This applies to every role, including sub-agents.

## The four rules that matter most

1. **The orchestrator never edits source.** It dispatches. Roles stay real only if the
   boundary does.
2. **File ownership is a hard boundary.** Backend owns Python, frontend owns markup and JS,
   design owns CSS. Checked on every review. See [`.claude/shared/CLAUDE.md`](.claude/shared/CLAUDE.md) §4.
3. **Every task is reviewed before it is done.** Zero *required* and zero *suggested-major*
   findings, or it goes back to the coder.
4. **One task, one branch, one PR — and only the orchestrator merges.** The coder opens the
   PR before the first review, and that PR is the *only* context the reviewer is given.
   Never rebase. Never delete a branch. Full policy in
   [`.claude/orchestrator/CLAUDE.md`](.claude/orchestrator/CLAUDE.md) §4.

## Hard prohibitions

No npm, no CDN, no build step, no React, no TypeScript, no inline `style=` attributes.
No rebasing, no branch deletion, no force-pushing, no merging by anyone but the
orchestrator. The app must run in a classroom with no internet. Full list in
[`.claude/shared/CLAUDE.md`](.claude/shared/CLAUDE.md) §3 and §6.
