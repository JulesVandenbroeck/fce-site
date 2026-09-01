# Shared context — every role reads this first

You are working on **FCE-site**, a browser-based learning game that teaches high-school
students particle-physics data analysis using simulated data from the Future Circular
Collider (FCC-ee).

Read this file, then read your own role manual in `.claude/<role>/CLAUDE.md`. Do not start
work until you have read both.

---

## 1. What we are building

Students play as physicists searching for new particles. Each **mission** gives them a
physics objective ("recover the Z boson peak"), a dataset, and a set of analysis tools.
They assemble an analysis, run it against real simulated collision data, and see whether
their result meets the objective. Completing a mission unlocks the next.

The physics is real. The data is real simulation. The numbers students produce are the
numbers a physicist would produce. That is the entire point — the game framing must never
come at the cost of the physics being correct.

**Audience:** 15–18 year olds, most with no physics background beyond school. Assume they
have never heard the word "luminosity". Assume they will click things in the wrong order.

**Language: English, everywhere.** Interface, mission text, error messages, hints. The
students are Flemish, but the site is not translated and there is no i18n layer — decided,
not deferred. Write copy simple enough to read as a second language: short sentences, plain
words, no idiom. Physics terms are the exception and are taught rather than avoided.

**Setting:** a teacher runs one instance; a classroom of students connects to it over the
local network. It must also run on one laptop for a single user.

The full concept and every product decision is in **`docs/design-brief.md`**. Read it
before doing any work that touches user-facing behaviour.

---

## 2. Where this comes from

There is a working desktop predecessor: **`kskovpen/fce`** (Dear PyGui, on PyPI as `fce`).
Its physics engine is correct and validated, and we are reusing it. Its UI is not being
reused.

We **vendor** these from the reference repo into `src/fce_web/`:

| Reference path | Our path | Change |
|---|---|---|
| `engine/` | `src/fce_web/engine/` | Decoupled from global state; `eval` replaced |
| `objects.py` | `src/fce_web/objects.py` | Unchanged |
| `paths.py` | `src/fce_web/paths.py` | Mostly unchanged |
| `tests/` | `tests/` | Ported as the physics regression net |

We do **not** vendor `fce.py`, `ui/`, or anything importing `dearpygui`.

Two known defects in the reference engine that we must fix, not inherit:

1. **Global mutable state.** `engine/analytical_loop.py` reads and writes a single
   module-level `ui.state.RUN_STATE` dict in ~25 places. Fine for one desktop user; two
   concurrent students would corrupt each other's runs. Replaced by an explicit
   `RunContext` object.
2. **Unsafe expression evaluation.** `engine/path_filter.py` runs student-typed
   expressions through `eval()` with a restricted `__builtins__`. That does not stop
   attribute-traversal escapes and is remote code execution on a shared host. Replaced by
   an AST-whitelist evaluator in `src/fce_web/safe_eval.py`.

One property of the reference engine worth preserving deliberately: the disk cache is
**content-addressed** by a hash of the analysis config. On a shared server this means the
second student to try the same cuts gets an instant result. Do not break this.

---

## 3. Stack

Fixed. Do not introduce alternatives without the orchestrator escalating to the user.

| Layer | Choice | Why |
|---|---|---|
| Language (server) | Python ≥ 3.10 | Constraint from the developer; the engine is Python |
| Web framework | FastAPI + Uvicorn | Async, so Server-Sent Events for live run progress are clean |
| Templates | Jinja2 | Server-rendered HTML, no build step |
| Interactivity | HTMX (vendored single file) + vanilla ES modules | Keeps logic in Python; no npm, no bundler |
| Storage | SQLite via stdlib `sqlite3` | One file, zero setup, no ORM to learn |
| Physics | uproot, boost-histogram, vector, pyhf, numpy, scipy | Carried over from the reference engine |
| Static plots | matplotlib + mplhep | PNG export only; the interactive chart is our own SVG |
| Python tests | pytest | |
| Browser tests | Playwright (Python bindings) | pip-installable, so no npm enters the project |
| Lint | flake8, config carried from the reference repo | |

**Hard prohibitions — these apply to every role:**

- No npm, no `package.json`, no `node_modules`, no bundler, no build step.
- No CDN links, no external fonts fetched at runtime, no remote scripts. Everything is
  served from `static/`. The app must work on a classroom network with no internet.
- No React, Vue, Svelte, or any SPA framework.
- No TypeScript.
- Never edit files owned by another role (see §4).
- Never commit dataset files (ROOT files) to git.

---

## 4. Repo layout and file ownership

```
CLAUDE.md                     # root index
docs/
  design-brief.md             # the product concept — read before user-facing work
  api.md                      # JSON + SSE contracts between backend and frontend
content/
  missions/*.yaml             # mission definitions — data, not code
src/fce_web/
  app.py                      # FastAPI app factory
  routes/                     # HTTP endpoints
  runs.py                     # RunContext, job registry, SSE progress
  store.py                    # SQLite: class codes, nicknames, progress
  missions.py                 # mission loading + objective validation
  safe_eval.py                # AST-whitelist expression evaluator
  engine/                     # vendored physics engine
  objects.py  paths.py        # vendored
  templates/                  # Jinja2
  static/js/                  # ES modules
  static/css/                 # stylesheets + design tokens
  static/vendor/              # htmx.min.js
tests/                        # pytest, including the physics regression net
```

Ownership is a hard boundary. The reviewer checks it on every task.

| Role | Owns (may create/edit) | Must not touch |
|---|---|---|
| **backend** | `app.py`, `routes/`, `runs.py`, `store.py`, `missions.py`, `safe_eval.py`, `engine/`, `objects.py`, `paths.py`, `tests/`, `content/`, `pyproject.toml`, `docs/api.md` | `templates/`, `static/` |
| **frontend** | `templates/`, `static/js/`, `static/vendor/` | `static/css/`, any Python |
| **design** | `static/css/`; and in `templates/`, **only** class attributes and purely presentational wrapper elements | HTMX attributes (`hx-*`), form field `name`/`id`, `data-*` bindings, template logic (`{% %}`, `{{ }}`), any Python, any JS |

**The frontend/design seam is the one place two roles share a file.** The rule:
frontend owns what the markup *means* and *does*; design owns what it *looks like*.
If design needs a hook that does not exist, it adds a class. If design believes the
markup structure itself is wrong, it does not change it — it reports that to the
orchestrator, which raises a frontend task.

---

## 5. Physics glossary

The frontend and design roles are not expected to know physics. This is enough to work
from. Nothing here needs to be memorised — refer back to it.

**The collider.** FCC-ee smashes electrons into positrons. The **centre-of-mass energy**
(√s, in GeV) is the total energy of the collision, and it is chosen deliberately: at
**91 GeV** you make Z bosons in vast numbers (the "Z pole"), at **160 GeV** pairs of W
bosons, at **240 GeV** Higgs bosons, at **365 GeV** top quarks. V1 uses 91 GeV only.

**An event** is one collision and everything it produced. **Objects** are the particles
reconstructed in an event: electrons, muons, photons, and **jets** (a spray of particles
from a quark or gluon, treated as one object). A **b-tag** is a score saying how likely a
jet came from a bottom quark. **MET** — missing transverse energy — is a momentum
imbalance that betrays particles that escaped undetected, like neutrinos.

**Kinematics.** Every object has `pt` (momentum perpendicular to the beam), `eta` (how
far forward it went; 0 is straight out sideways), `phi` (angle around the beam), and `e`
(energy). Its **four-vector** `p4` bundles energy and momentum together.

**This is the key idea students learn:** add the four-vectors of two objects and take
`.mass`, and you get the **invariant mass** of the system. If those two objects came from
the decay of a particle, that number *is* the parent particle's mass. Two muons from a Z
decay give ≈ 91 GeV. Histogram that quantity over many events and a **peak** appears at
the parent mass. That peak is what discovery looks like, and it is the emotional payload
of the whole game.

**Signal and background.** *Signal* is the process being hunted. *Background* is every
other process that happens to look similar. A **selection** (or **cut**) is a boolean
condition applied to each event. Cuts remove background — but they remove signal too, so
the craft is finding cuts that improve the ratio. A **cutflow** shows how many events
survive each successive cut.

**Samples.** Each simulated process is a separate dataset. In FCE they are named `X1`…`X5`
plus `data`, which is the pseudo-data students actually analyse. Each simulated event
carries a **weight** so the simulation reproduces the real expected rate.
**Luminosity** measures how much data was collected; event counts scale with it.

What the samples are:

| Sample | Process | What it looks like in the detector |
|---|---|---|
| `X1` | Z → two leptons | Two leptons whose invariant mass is the Z mass, ≈ 91 GeV. This is the clean case, and the thing mission 1 is about. |
| `X2` | Z → two quarks | Two **jets**, no leptons. Far more common than X1 — the Z decays to quarks most of the time — so it dominates the raw event count and is removed almost entirely by asking for two leptons. |
| `X3` | Z → two leptons **and** a photon | Two leptons plus a photon. The catch: the photon carried energy away, so the *two-lepton* mass comes out **below** 91 GeV and smears out the left side of the peak. Add the photon's four-vector back and the Z mass reappears. |
| `X4` | *not yet documented* | — |
| `X5` | *not yet documented* | — |

`X3` is the interesting one pedagogically: it is a real Z that does not *look* like one
unless you account for the photon. Do not present it as junk background.

`X4` and `X5` are unknown as of 2026-08-15 and the orchestrator has raised it with the
user. Mission 3 — the search — needs one of them, so **no mission-3 content may be
authored until they are identified.**

**Scoring the result.** A fit (via `pyhf`) returns two numbers. **Signal strength μ** is
how much signal was found relative to prediction — 1.0 means exactly as predicted, 0 means
absent. **Significance Z** is how many standard deviations the excess sits above a
background-only expectation: **3σ is "evidence", 5σ is "discovery"**. Z is effectively the
score of the game and should be treated as such in the UI.

**Uncertainties** come in two kinds: *statistical* (you only collected so many events) and
*systematic* (you do not perfectly know your detector or your theory).

**Formats and tools.** Data lives in **ROOT** files, the HEP standard binary format, read
with **uproot**. **IDEA** and **CLD** are two candidate FCC-ee detector designs with
different resolutions.

---

## 6. Conventions

### Python
- PEP 8, enforced by flake8. Config lives in `.flake8`, carried over from the reference
  repo: `max-line-length = 120`, and `E221, E222, E272, E127, E402, W503, W504` ignored
  because aligned-column style is deliberate in the physics loops.
- Type hints on every public function. Docstrings on every module and public function,
  explaining *why* where the code cannot.
- No module-level mutable state. Ever. This is what broke the reference engine.
- Standard library first; a new third-party dependency needs orchestrator sign-off.

### HTML
- Semantic elements. `<button>` for things that do, `<a>` for things that go. Landmarks
  (`<main>`, `<nav>`, `<section>`) on every page.
- No `<div>` where a semantic element exists.
- **No inline `style=` attributes, ever.** Add a class; the design role styles it.
- Every interactive control is reachable and operable by keyboard.

### CSS
- All colour, spacing, type, and radius values come from custom properties defined in one
  tokens file. No hard-coded hex values outside it.
- Class naming is consistent and readable; no utility-class soup.
- WCAG AA contrast minimum on all text.
- Every animation respects `prefers-reduced-motion`.

### JavaScript
- ES modules, no transpiling. Modern syntax is fine; target current evergreen browsers.
- HTMX handles server interaction. Hand-written JS is for the chart renderer and card
  interactions only.
- No global variables. No `innerHTML` with server data — build nodes or use `textContent`.

### Shell commands
Always run commands through **`rtk`** — a proxy that filters verbose tool output down to
what matters, cutting 60–90% of the tokens a raw command would cost. `rtk git status`,
`rtk pytest tests/`, `rtk gh pr view 12`. A hook rewrites most commands automatically, so
in practice you write the command normally and `rtk` is applied for you; write it
explicitly when you are unsure. Two escape hatches: `rtk proxy <cmd>` runs a command with
no filtering, for when you need the raw output to debug something, and `rtk gain` reports
what the filtering has saved.

### Previewing a page in a real browser

**Never hand the user a `file:///tmp/...` URL.** The default browser on this machine is
**snap Firefox**, and a snap runs with a *private `/tmp` namespace*: a `/tmp` path resolves
to nothing inside the sandbox, so the tab opens on an empty document and reports no error
that names the cause. `$HOME` is readable; `/tmp` is not. This bites anything that stages
files for viewing — `git archive` into a temp dir, a scratch copy, a generated report.

For a page that is not on `main`, preview it from a **git worktree under `$HOME`**:

```bash
git worktree add --detach ~/wireframes-preview origin/task/d-001-wireframes-clean
```

`--detach` creates no branch and moves no branch, so this does not touch the
never-delete-a-branch rule. A worktree has exactly one `HEAD`, so it is one worktree per
ref. The two that exist:

| Worktree | Ref | Holds |
|---|---|---|
| `~/wireframes-preview` | `origin/task/d-001-wireframes-clean` | `docs/wireframes/` — D-001, superseded |
| `~/wireframes-preview-d003` | `origin/task/d-003-plot-component` | `docs/design-explorations/plot.html` — D-003 |

`.claude/scripts/open-wireframes.sh` maintains both and opens the right page; run it with no
argument for what currently exists and what does not. Headless or over ssh, `--print` emits
the URLs instead of launching anything.

### Worktrees you are given, versus worktrees you make

**If the orchestrator dispatched you with `isolation: "worktree"`, you are already in one.
Do not run `git worktree add`.** Doing both is what produced twelve orphaned
`worktree-agent-*` branches against six merged PRs — a second worktree whose directory is
later cleaned up while its branch stays behind forever, because branches are never deleted.

Check before you create one:

```bash
git rev-parse --git-common-dir     # differs from .git => you are in a worktree already
```

Removing a worktree is permitted and is not branch deletion (`git worktree remove <path>`);
the branch it was checked out on stays. Creating one you were not asked for is what to avoid.

Screenshots are the other half of this: `scripts/screenshot.py <route>` drives the real app
headless and writes PNGs. That one is unaffected — it never asks a browser to read `/tmp`.

### Git — branch per task, PR before review

**Every task is developed on its own branch and reviewed as a pull request.** You never
work on `main`. The full policy is `.claude/orchestrator/CLAUDE.md` §4; this is your half
of it.

1. **Branch first, before you write anything.** From current `main`:
   ```bash
   git checkout main && git pull --ff-only && git checkout -b task/<id>-<short-slug>
   ```
   e.g. `task/b-004-run-context`. If you find yourself committing on `main`, stop and
   report it — something went wrong upstream of you.

2. **Commit as you go.** Small, focused commits. Message format
   `<role>: <what changed>` — e.g. `backend: replace RUN_STATE with RunContext`. On this
   branch you commit freely; you do not need to ask.

3. **Open the PR before you report done.** Not after — the orchestrator cannot start the
   review without it.
   ```bash
   git push -u origin task/<id>-<short-slug>
   gh pr create --base main --title "<id> — <title>" --body-file <path>
   ```

4. **The PR body is the only thing the reviewer will see.** Not your report, not the task
   you were dispatched with, not a summary from the orchestrator — the PR alone. So the
   body must stand on its own and contain:

   - the task ID and title
   - the goal, in a sentence
   - the **file scope** you were given, verbatim
   - the **acceptance criteria** you were given, verbatim, **with their `C<n>` IDs**, each
     marked met or not, and the total check count on its own line
   - your **verification output** — the real commands and their real results
   - deviations from the task, and why

   Write it as though for someone who has never seen this project's task list. A thin PR
   body produces a blind review, and the review is the gate on your work.

   **This body is the project's only verbatim copy of the criteria.** Re-dispatches cite them
   by ID and cite this PR rather than re-pasting them (`.claude/orchestrator/CLAUDE.md` §3,
   §5.3), so on a later cycle you append the new criteria here — you never rewrite or drop the
   earlier ones, and the check count never falls. Template:

   ````markdown
   ## <task ID> — <title>

   <the goal, in one sentence>

   ### File scope
   Given to me as, verbatim:
   - `<path>`
   - `<path>`

   ### Acceptance criteria
   Total checks: <n>
   - [x] C1 <criterion> — <how it is met>
   - [ ] C2 <criterion> — <why it is not>

   ### Verification
   ```
   $ <command>
   <real output>
   ```

   ### Deviations
   <what I did differently and why — or "none">
   ````

5. **Review fixes go on the same branch.** Commit them, push; the PR updates itself. Never
   open a second PR for the same task.

6. **Never paste source into the PR body.** Cite `path:line` and let the reader open the diff —
   it is attached to the PR. See "Cite, do not paste" in §7.

**Never, under any circumstances:**

- **Never merge.** Only the orchestrator merges, and only after the review is clean.
- **Never rebase** — no `git rebase`, no `git pull --rebase`. If your branch is behind
  `main`, merge `main` into your branch.
- **Never delete a branch**, yours or anyone's. No `git branch -d`, no `git push --delete`.
- **Never force-push.** It destroys history the same way a rebase does.
- **Never `git checkout` another task's branch.** Parallel tasks run concurrently; touching
  someone else's branch corrupts their work.

---

## 7. Reporting back to the orchestrator

Every coder role ends its turn with exactly this structure. The orchestrator parses it.

```markdown
## Task complete: <task ID> — <title>

### Branch and PR
- Branch: `task/<id>-<slug>`
- PR: #<n> — <url>

### What changed
```
<the output of `git diff --stat main...HEAD`, unedited>
```
- <file:line> — <one line on what and why>

### Verification run
- <command> → <actual result, e.g. "17 passed, 0 failed">
- <command> → <actual result>

### Notes for other roles
- <e.g. "added .mission-card__stamp in mission.html, needs styling" — or "none">

### Deviations from the task
- <anything you did differently, and why — or "none">

### Backlog candidates
- <things you noticed but did not do, because out of scope — or "none">
```

**"Verification run" must contain commands you actually executed and their real output.**
Never write a verification line you did not run. If something failed and you could not fix
it, say so plainly in that section — a reported failure is useful, a hidden one is not.

### Cite, do not paste

**Never paste source into a report, a PR body, or a handoff.** The diff is attached to the PR
and the files are on disk; a pasted copy is a second copy of something the reader can already
open, and it goes stale the moment the branch moves. Cite `path:line` — `runs.py:88-104` — and
say what is there. `git diff --stat` is how you show the shape of a change; the diff itself is
how someone reads it.

The one carve-out: **up to five lines** of code, when the point is genuinely unintelligible
without them — a regex, a formula, a changed signature. Five lines, not a function.

The same rule governs your prose. No preamble, no recap of the dispatch you were given, no
narration of your approach. The orchestrator asked for the six headings above; give it those.

---
## 8. Context failsafe — the anchor at 50%, the handoff at 90%

**Full protocol: [`.claude/shared/context-failsafe.md`](context-failsafe.md).** It is split out
so you do not pay ~200 lines on every dispatch for a procedure most tasks never reach. Read it
the moment the watchdog fires, and read it *before* starting anything you can see you lack the
budget to finish.

What you must know without opening it:

- **50% — anchor.** Take a token audit, then write or refresh
  `.claude/handoff/<id>-<role>.anchor.md` in the primary checkout, at most 25 lines: decisions
  and why, dead ends already ruled out, criteria still open, the exact next step. Then keep
  working. You cannot run `/compact`; this file is the substitute, and compaction cannot touch it.
- **90%, or the message `HANDOFF NOW`, or a step you cannot afford — stop and hand off.** Commit
  and push (red is fine, say so), promote the anchor into
  `.claude/handoff/<id>-<role>-<cycle>.md` in the **primary checkout**, report the short form,
  stop. Do not gamble on finishing.
- A `PostToolUse` hook measures your own transcript and fires at 50 / 75 / 90%. It is measuring
  where you are guessing, so it wins.
- `scout` never hands off — it re-runs cheaply.

Everything else — the exact templates, where the primary checkout is, what goes in the dead-ends
section, what the orchestrator gets back — is in that file. Open it, do not reconstruct it.
