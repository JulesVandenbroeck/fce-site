# M3 — First Vertical Slice: Implementation Plan

> **This plan is written for the FCE-site orchestrator, not for a solo engineer.**
> Tasks are executed by dispatched sub-agents under `.claude/orchestrator/CLAUDE.md` — one
> task, one branch, one PR, one review gate, and only the orchestrator merges. Consequently
> this plan contains **no implementation code**: the orchestrator neither writes nor reads
> source (§1), and a plan that pasted code would be the orchestrator doing a coder's job.
> What each task gets instead is a file scope, an interface contract, and acceptance criteria
> that name the command that decides them.
>
> Each coder invokes `ponytail:ponytail` before writing anything and leaves **one** runnable
> check for non-trivial logic (`shared/CLAUDE.md` §6). The reviewer runs `ponytail:ponytail-review`
> and returns a flat `F<n>` list closed by `verdict=`.

**Goal:** A student opens the app, edits a node graph on the Bench canvas, presses Run, watches
real progress stream in, and sees the Z peak drawn as an interactive SVG histogram from bins the
real physics engine computed.

**Architecture:** The browser serialises the canvas graph to `{nodes[], edges[], ui{}}` and POSTs
it. The server validates the graph against the engine's connection allowlist, synthesises the
`DataSource` root and resolves the `Observable` mode to its engine subtype, builds a `RunConfig`,
registers a run id, and executes `run_analysis` on a background thread. The engine's existing
`RunContext` callbacks feed a queue that a Server-Sent Events endpoint drains as progress. The
engine writes histograms to disk exactly as it always has; a separate reader turns those into the
already-fixed `HISTOGRAM_SCHEMA` JSON, served from its own endpoint. **The engine is not
modified.**

**Tech stack:** FastAPI + Uvicorn, Jinja2, HTMX (vendored), vanilla ES modules, uproot,
boost-histogram, pytest, Playwright. No npm, no build step, no CDN.

**Spec:** [`docs/design-brief.md`](design-brief.md) — §2 (the core loop), §4 (the node graph and
the run payload), §5 (results). Decisions in force: [`.claude/tasks/design.md`](../.claude/tasks/design.md).

---

## Rulings this plan is built on

Four came from the user on 2026-09-07, at the M3 brainstorming gate. They are recorded here
because they overrule text that still stands elsewhere.

1. **The full Bench shell and canvas ship in M3, editable.** `docs/design-explorations/`
   (`shell.html`, `shell.css`, `bench.html`, `interiors.html`, `interiors.css`) is ported into
   the real app rather than deferred to M4. This overrules the milestone map's "one hardcoded
   recipe" framing in `.claude/orchestrator/CLAUDE.md` §8.
2. **`POST /api/run` accepts the student's real graph.** Not a hardcoded recipe. The canvas is
   functional, not cosmetic. **Consequence: this largely absorbs M4**, which is re-scoped after
   the M3 checkpoint to mission gating, the cutflow, and the Z gauge.
3. **The chart is ported from D-003, minus the extras.** The interactive SVG renderer lands in
   `static/js/`; legend toggling, the `mplhep` PNG export, the cutflow and the Z gauge are
   explicitly **not** M3.
4. **A small fixture ROOT file is committed.** A bounded exception to `shared/CLAUDE.md` §3's
   never-commit-ROOT rule, now written there, and a partial answer to brief §9 open question 2.
   It is a test fixture so the pipe is runnable and reviewable offline; it says nothing about
   how a classroom gets real data.

One architectural call made by the orchestrator, not the user, and open to reversal:

5. **SSE carries progress only; the payload comes from a separate `GET /result`.** The stream
   ends with a terminal `done` event. Rationale: push-only progress is testable in isolation, a
   reconnecting client does not re-stream the bins, and a content-addressed cache hit becomes a
   `done` that arrives immediately — which is what brief §2 asks to be surfaced as
   *"recognised these cuts — reusing your earlier run."*

## Global constraints

Every task's criteria implicitly include these. Copied verbatim from the sources named.

- **No npm, no `package.json`, no `node_modules`, no bundler, no build step.** No CDN links, no
  external fonts at runtime, no remote scripts. No React/Vue/Svelte. No TypeScript. No inline
  `style=` attributes, ever. (`shared/CLAUDE.md` §3, §6)
- **File ownership is a hard boundary** (`shared/CLAUDE.md` §4). Backend owns Python, `tests/`
  outside `tests/e2e/`, `content/`, `docs/api.md`, and the e2e *harness* (`tests/e2e/conftest.py`).
  Frontend owns `templates/`, `static/js/`, `static/vendor/`, and browser *assertions* in
  `tests/e2e/` test files. Design owns `static/css/`, and in `templates/` **only** class
  attributes and purely presentational wrappers.
- **Never rebase, never delete a branch, never force-push, never squash, never merge your own
  PR.** (`shared/CLAUDE.md` §6)
- **A new third-party dependency needs orchestrator sign-off.** Stdlib first.
- **Type hints on every public function; docstrings on every module and public function.**
  PEP 8 via flake8, `max-line-length = 120`.
- **No module-level mutable state. Ever.** This is the defect M2 existed to remove; the job
  registry introduced in this milestone is the first thing since that could reintroduce it.
- **Copy is English, written to be read as a second language.** Short sentences, plain words,
  no idiom. Physics vocabulary is the deliberate exception. (`shared/CLAUDE.md` §1)
- **Accessibility is never simplified away.** Every interactive control is keyboard-reachable
  and operable; the connection gesture on the canvas must have a keyboard path (brief §4,
  requirement 2). WCAG AA contrast minimum. `prefers-reduced-motion` respected.
- **Privacy:** no analytics, no telemetry, no third-party requests of any kind (brief §6).
- **Environment:** export `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright` before running the
  suite; the container default `/cache` is not writable. A fresh worktree needs its own venv;
  the browser cache is shared.

---

## File structure

What M3 creates and modifies, and what each unit is responsible for. Ownership in brackets.

**New backend units**

| Path | Responsibility | Owner |
|---|---|---|
| `tests/fixtures/` | The committed fixture dataset and whatever config names its samples. Exists so the pipe runs offline. | backend |
| `src/fce_web/graph.py` | The connection allowlist and graph→`RunConfig` translation: validate edges, synthesise `DataSource`, resolve `Observable` mode to its engine subtype. Pure functions, no HTTP, no I/O. | backend |
| `src/fce_web/payload.py` | Read a completed run's histograms off disk and build the `HISTOGRAM_SCHEMA` JSON. Pure read, no HTTP. | backend |
| `src/fce_web/jobs.py` | The run registry: run ids, background execution, per-run progress queue, cancellation. The one place concurrent state lives, and therefore the one place to keep it off the module level. | backend |
| `src/fce_web/routes/api.py` | `POST /api/run`, `GET /api/run/{id}/result`, `GET /api/run/{id}/events`. HTTP only — every decision it makes belongs to one of the three modules above. | backend |

Each of the four modules is separately testable without a running server, which is the point of
splitting them out of `routes/api.py`. `routes/api.py` should stay thin enough that its tests are
about status codes and content types, not about physics or graphs.

**New and modified frontend units**

| Path | Responsibility | Owner |
|---|---|---|
| `src/fce_web/templates/` | The three-region shell, ported from `shell.html`; the canvas and node markup, ported from `bench.html` and `interiors.html`. | frontend |
| `src/fce_web/static/js/graph.js` | Canvas behaviour: place, drag, connect, the `{id, x, y}` model, the edge list, keyboard path. | frontend |
| `src/fce_web/static/js/run.js` | Serialise the graph, POST it, consume the SSE stream, render phase and progress. | frontend |
| `src/fce_web/static/js/chart.js` | The interactive SVG histogram, ported from `plot.html`. Consumes the `HISTOGRAM_SCHEMA` payload. | frontend |

**New design units**

| Path | Responsibility | Owner |
|---|---|---|
| `src/fce_web/static/css/` | The shell, canvas, node and results stylesheets, ported against the real markup and built on the existing `tokens.css`. | design |

**Unchanged, deliberately:** everything under `src/fce_web/engine/`, `objects.py`, `paths.py`.
M3 adds callers, not engine edits. A task that believes the engine must change stops and reports
it (`shared/CLAUDE.md` §6) — that is an orchestrator decision, not a coder's.

---

## Wave plan

Parallelism is **within a wave only**. Two tasks are independent only if they share no files and
neither consumes the other's output. Every agent is dispatched with `isolation: "worktree"`,
including single dispatches — the 2026-08-18 D-004 incident is why.

```
wave 1   B-018  fixture dataset + samples config       -+ parallel
         B-020  graph -> RunConfig  (CONTRACT)          |
         F-004  port the three-region shell            -+

wave 2   B-019  engine output -> HISTOGRAM_SCHEMA (CONTRACT)  -+ parallel
         F-005  port the bench canvas                         -+

wave 3   B-021  job registry + POST /api/run + GET /result   -+ parallel
         F-006  node interiors, Observable mode toggle        |
         D-015  shell + canvas + node CSS                    -+

wave 4   B-022  SSE endpoint + the progress-event contract   -+ parallel
         F-003  the deferred woff2 proof (released by D-015) -+
         <<< CHECKPOINT — a run is submittable and streams by curl >>>

wave 5   F-007  serialise, POST, consume SSE, render progress -+ F-008 after F-007
         F-008  the SVG chart, wired to /result               |
         D-016  results region + chart CSS                   -+ after F-008
         <<< M3 CHECKPOINT — a student sees their peak >>>
```

**Two contract tasks** (`.claude/orchestrator/CLAUDE.md` §2): **B-020** and **B-019** produce
values another task consumes read-only. They run before every consumer, they are reviewed at
raised effort, and **neither is merged with an open finding against the shared value**. D-004 is
the precedent for what ignoring that costs: it merged as "a CSS task" with two findings open
against a token set three other tasks consumed, and produced D-008, which took three more cycles
on the same eight colours.

**Sequencing risk worth naming now.** Wave 5 is three tasks on the same page, and frontend and
design on the same page are *never* parallelisable. F-008 needs F-007's fetch in place; D-016
needs F-008's markup. If wave 5 runs long it splits rather than compresses.

---

## Facts this plan was written from

Enumerated by `scout` on 2026-09-07, not assumed. `.claude/orchestrator/CLAUDE.md` §2: *never
write a count you did not enumerate.* Every task below cites these rather than restating them.

**Engine seams M3 attaches to** — none of which M3 modifies:

| Fact | Where |
|---|---|
| `run_analysis(config: RunConfig, ctx: RunContext, env: Optional[Mapping[str,str]] = None) -> RunResult` | `engine/driver.py:98-185` |
| `RunContext` callbacks: `on_progress`, `on_log`, `on_phase`, `on_node`; plus `n_workers`, `cancel` | `runs.py:78` |
| `RunResult` fields: `processed_any`, `cutflow_ready`, `cancelled`, `reason` — **no bin data** | `runs.py:118` |
| Histograms written as `os.path.join(hdir, "output", f"hist{plot_idx}_{s}.root")` | `analytical_loop.py:201` |
| Histogram object is `bh.Histogram`, persisted with `uproot.recreate()` | `analytical_loop.py:208-212` → `path_final.py:23-27` |
| Dataset layout `{fce_home}/datasets/{detector}/{energy}/{sample}.root`; **samples discovered by listing `.root` files, not from a config** | `driver.py:78-79, 91-94` |
| ROOT tree name `"ntuple"`; branches `pt, eta, phi, e, weight, btag, d0signif, z0signif, charge` | `analytical_loop.py:154-159` |
| `RunConfig` — 13 fields; `from_dict` at `:378`; raises `RunConfigError` on digest mismatch | `engine/runconfig.py:335-450, 414-424` |
| Reference checkout resolved via `FCE_PARITY_REFERENCE_ROOT`, default `~/Documents/Phd/teaching/fce-project/fce` | `tests/test_engine_parity.py:49` |
| The reference reads bins back with `uproot.open(...)`, `f_res["h"]`, `.values()`, `.axes[0].edges()`, variations `f"h_{src}_up"` | reference `engine/plotter.py:51-63` — **not vendored** |
| `HISTOGRAM_SCHEMA`, 18 rows, row-parity tested against `docs/api.md` | `tests/test_api_contract.py:100-121` |
| `docs/api.md` stubs M3 must fill: `## Endpoints` (line 27), `### Run progress event` (line 298) | `docs/api.md` |
| `### Mission objective result` (line 302) is **M5's**, not M3's | `docs/api.md` |

**The connection allowlist does not exist in this repo.** `grep` over `src/`, `tests/` and
`docs/api.md` returns nothing for `_VALID_CONNECTIONS`. It lives only in the reference's `ui/`,
which is deliberately not vendored (`shared/CLAUDE.md` §2). Two copies of it *do* exist as
prose and as JavaScript — `docs/design-brief.md` §4 and `bench.html:258` (`isLegal()`) — and
**B-020 is where it becomes a single authoritative Python definition.**

**Explorations being ported** — line counts, so a coder knows the size of what it is moving:

| File | Lines | Ported by | Note |
|---|---|---|---|
| `shell.html` / `shell.css` | 312 / 439 | F-004, D-015 | Regions at `shell.html:12, :19, :53, :67`; inline `<script type="module">` at `:90-310`. No `hx-*`, no inline `style=`. |
| `bench.html` / `bench.css` | 727 / 653 | F-005, D-015 | `graphState` at `:289-292` — `nodes: new Map() // id -> {kind, x, y}`, `edges: [] // [fromId, toId][]`. 27 functions. All client-side; **it POSTs nowhere.** |
| `observable.html` / `observable.css` | 225 / 332 | F-006, D-015 | **D-013's merged `Observable` node** — this is the one with the mode toggle. |
| `interiors.html` / `interiors.css` | 702 / 311 | *nobody* | D-009's four separate `Obs*` exemplars, **superseded by the 2026-09-02 one-node ruling.** Do not port. |
| `plot.html` / `plot.js` / `plot.css` | 323 / 817 / 243 | F-008, D-016 | 16 functions; `FIG.w = 650, FIG.h = 460` at `plot.js:142`. Payload enters as an embedded `<script type="application/json" id="payload-data">` at `plot.html:167` — **F-008 replaces that with a fetch.** No external dependencies. |

`tokens.css` ships 62 custom properties and four `@font-face` `src:` lines at `:54, :62, :70, :78`.
`static/js/app.js` is a comment-only stub with no behaviour.

### The `verify.py` question, answered rather than deferred

`docs/design-explorations/verify.py` is 8907 lines carrying **81 AST registrations across 77
unique section names**, and it reads **only** files under `docs/design-explorations/`
(the eight paths at `verify.py:83-99`). It does not read `src/fce_web/`.

**Ruling for M3: `verify.py` is not touched, not re-pointed, and not extended.** It stays
guarding the explorations as a frozen historical record, so its registration count cannot fall
and `board-lane-fill` (`verify.py:7696`) stays deliberately red exactly as
`.claude/tasks/design.md` §Floors requires. Re-aiming 8907 lines of file-scraping checks at a
live server is a larger job than the port it would be guarding, and brief §9 already records
that `docs/design-explorations/` is history rather than a menu.

**What replaces it for the shipped app:** the checks that matter are driven through the real app
by the existing e2e harness — `PageActivity` with `console_errors`, `requested_urls` and
`bad_responses` (B-017's contract), which is a live-browser instrument the exploration harness
never had. Design tasks assert against the running app, not against a file on disk.

**The divergence this creates, named so it is not rediscovered:** once `shell.css` is ported,
the exploration copy and the app copy are two files. **The app copy is authoritative and the
exploration copy is frozen.** This already happened once — D-002 backlogged m5 when the
exploration `tokens.css` copy diverged from the shipped one. It is accepted here deliberately
rather than prevented, because the alternative is maintaining two live copies forever.

**Baseline on `main` at `cb85f17`, re-run by the orchestrator in the primary checkout
2026-09-07:** `596 passed, 1 warning in 132.56s`; `flake8 src/ tests/ scripts/` → `0`.
Every task's suite floor is measured against this. Use `.venv/bin/python`, and export
`PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright` — the system `python3` collects 286 tests
with 14 errors and is not the environment this project is verified in.

---

# Wave 1

Three tasks, no shared files, no consumed outputs. Parallel, each in its own worktree.

---

### B-018 — A committed fixture dataset the pipeline can actually run on

**Role:** backend · **Effort:** medium · **Blocks:** B-019, B-021, and every review after them

**Why it is first.** There is no ROOT data on this machine and no `config/samples.json`. Until
this lands, `run_analysis` cannot be executed by anyone — no coder can verify a run, and no
reviewer can drive one. It is the single hard blocker on the milestone.

**Files**
- Create: `tests/fixtures/datasets/IDEA/91GeV/{X1,X2,X3,data}.root`
- Create: `tests/fixtures/make_fixture.py` — the generator, so the fixture is reproducible
- Create: `tests/test_fixture_dataset.py`
- Modify: `tests/fixtures/README.md` (create) — what this is, what it is not, how to regenerate

**Interfaces**
- Consumes: nothing.
- Produces: a dataset root at `tests/fixtures/datasets/`, laid out as
  `{root}/datasets/{detector}/{energy}/{sample}.root` per `driver.py:78-79`. Consumers point
  the engine at it through `run_analysis`'s existing `env` parameter (`driver.py:98`). **No new
  seam is added to the engine for this** — the `env` parameter already exists, from B-011.

**Acceptance criteria**
- [ ] **C1** Each fixture file contains a TTree named `ntuple` carrying exactly the branches the
      engine reads: `pt, eta, phi, e, weight, btag, d0signif, z0signif, charge`
      (`analytical_loop.py:154-159`).
      Check: open each with `uproot` and assert the branch-name set.
- [ ] **C2** The sample set matches the three documented processes plus pseudo-data — `X1` (Z→2ℓ),
      `X2` (Z→2q), `X3` (Z→2ℓ+γ), `data` (brief §3). `X4`/`X5` are **not** fabricated: they are
      undocumented and mission 3 is blocked on the user identifying them.
- [ ] **C3** The fixture is physically meaningful, not noise: the invariant mass of the two
      leading leptons in `X1` peaks at the Z mass within tolerance.
      Check: compute m(l₁,l₂) over `X1` directly from the file; assert the modal bin is within
      ±3 GeV of 91.2. **This is the criterion that makes the fixture worth committing** — a
      fixture that runs but has no peak proves the plumbing and hides the physics.
- [ ] **C4** `X3`'s dilepton mass sits *below* the peak, as brief §3 describes, so mission 2's
      teaching case is present in the data rather than asserted in prose.
- [ ] **C5** `run_analysis` completes against the fixture with no network access, returning
      `processed_any=True`, and writes `hist{plot_idx}_{sample}.root` under `output/`.
      Check: run it with the network unavailable and assert the output files exist.
- [ ] **C6** Total committed size of `tests/fixtures/` ≤ **5 MB**. Report the actual figure.
      Check: `du -sb tests/fixtures/`. The carve-out in `shared/CLAUDE.md` §3 is for a fixture,
      and a fixture that makes the clone expensive has stopped being one.
- [ ] **C7** `make_fixture.py` regenerates byte-identical files from a fixed seed, or documents
      precisely why it cannot.
- [ ] **C8** Suite ≥ **596 + the new tests**; `flake8 src/ tests/ scripts/` → 0.

**Verification.** `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright .venv/bin/python -m pytest tests/ -q`
→ 596 + new, 0 failed. Report `du -sb tests/fixtures/` and the measured peak position.

**Notes.** Synthetic generation via `uproot.recreate()` is the expected route — the engine's own
write path already uses it (`path_final.py:23-27`), so the reader and writer are the same
library. Do not download anything; the classroom constraint is no internet, and so is this task.

---

### B-020 — The connection allowlist and graph → `RunConfig` translation

**Role:** backend · **Effort:** medium · **CONTRACT TASK** — F-005 and F-007 consume this shape
read-only. It runs before both, is reviewed at raised effort, and **is not merged with an open
finding against the payload shape** (`.claude/orchestrator/CLAUDE.md` §2).

**Files**
- Create: `src/fce_web/graph.py`, `tests/test_graph.py`
- Modify: `docs/api.md` — fill the `## Endpoints` stub at line 27 with the `POST /api/run`
  request body. Leave `### Run progress event` (line 298) alone; that is B-022's.
  Leave `### Mission objective result` (line 302) alone; that is M5's.

**Interfaces**
- Consumes: `RunConfig.from_dict` (`engine/runconfig.py:378`) and the 13 keys it accepts —
  `energy, detector, observable, bins, min, max, target, h5, h5_sel, mult_cuts, sel_exprs,
  histograms, selections`.
- Produces, and later tasks depend on these names:
  - `VALID_CONNECTIONS` — the allowlist, as data.
  - a validation entry point that takes the student payload plus the mission's dataset and
    returns a `RunConfig`, raising a typed error naming the offending node or edge.
  - a typed error class for an illegal graph, distinct from `RunConfigError`.
  - The exact signatures are the coder's to choose and the PR body's to record verbatim;
    F-005 and F-007 are dispatched against whatever this PR documents.

**Acceptance criteria**
- [ ] **C1** `VALID_CONNECTIONS` reproduces brief §4's allowlist exactly, all five rows:
      `DataSource → Multiplicity, Selection`; `Multiplicity → Multiplicity, Selection`;
      `Selection → Selection, Observable*`; `Observable* → Histogram`; `Histogram → terminal`.
- [ ] **C2** It agrees with the reference's `_VALID_CONNECTIONS` in `ui/graph.py` when the
      reference resolves, and **skips rather than fails** when it does not — the reference is
      not vendored and is not present in every checkout. Follow the resolution pattern already
      established at `tests/test_engine_parity.py:49` (`FCE_PARITY_REFERENCE_ROOT`). Do not
      import from `ui/`; read the definition.
      Check: the parity test is `skipped` with no reference and `passed` with one. Show both.
- [ ] **C3** An illegal edge is rejected with an error naming the offending pair, not a generic
      failure. Rejection messages are read by 16-year-olds (brief §4) — write them accordingly.
- [ ] **C4** `DataSource` is **synthesised** from the mission's declared dataset and is the root
      of the chain handed to the engine; a student payload that *contains* a `DataSource` is
      rejected. It left the palette on the 2026-09-01 ruling (`design.md` §Decisions in force),
      so its presence in a submitted graph is a client bug, not a legal input.
- [ ] **C5** The `Observable` node's mode resolves to exactly one of `ObsGlobal`, `ObsObject`,
      `ObsVectorSum`, `ObsCustom`. Mode is `config`, not identity (2026-09-02 ruling).
- [ ] **C6** A graph that is cyclic, disconnected, or has no `Histogram` terminal is rejected,
      each with its own message.
- [ ] **C7** The translated output is accepted by `RunConfig.from_dict` without raising
      `RunConfigError`. **This is the criterion that proves the translation is real** — the
      others prove it rejects; only this one proves it produces something the engine takes.
- [ ] **C8** `graph.py` is pure: no HTTP, no filesystem, no module-level mutable state
      (`shared/CLAUDE.md` §6 — the defect M2 existed to remove).
      Check: assert against the AST that the module imports no `fastapi`, no `os`/`pathlib` I/O.
- [ ] **C9** `docs/api.md`'s `## Endpoints` stub at line 27 is replaced by the request-body
      schema, and the existing row-parity meta-test (`tests/test_api_contract.py`, B-014) still
      passes — an edit to the doc that breaks agreement with the schema tuples fails it.
- [ ] **C10** Suite ≥ **596 + new**; flake8 0.

**Verification.** Run the suite twice for C2 — once with `FCE_PARITY_REFERENCE_ROOT` unset and
once pointed at the reference — and paste both. Report the `RunConfig` produced for the mission-1
graph in full.

**Notes.** The allowlist already exists twice in this repo as non-authoritative copies: prose in
`docs/design-brief.md` §4, and JavaScript at `bench.html:258` (`isLegal()`). This task makes the
Python one authoritative. **Do not edit `bench.html`** — it is frontend's file and F-005 is
porting it; if you find the JS disagrees with the brief, report it and the orchestrator will
raise it against F-005 rather than have two roles edit one file.

---

### F-004 — Port the three-region shell into the app

**Role:** frontend · **Effort:** medium · **Blocks:** F-005, D-015

**Files**
- Create: `src/fce_web/templates/mission.html` (or a shell template plus partials — the coder's
  call, recorded in the PR body), `src/fce_web/static/js/shell.js`
- Modify: `src/fce_web/templates/base.html`, `src/fce_web/routes/pages.py` **— no.** `pages.py`
  is backend's (`shared/CLAUDE.md` §4). **If a new route is needed, stop and report it**; the
  orchestrator raises a backend task. Render into the existing `GET /` if that is enough.
- Create: `tests/e2e/test_shell.py` — browser assertions about frontend's own markup, which the
  2026-09-07 seam ruling puts on frontend's side of `tests/e2e/`.

**Interfaces**
- Consumes: `PageActivity` from `tests/e2e/conftest.py` — `console_errors`, `requested_urls`,
  `bad_responses: list[tuple[str, int]]`, the last gated at **status >= 400** so redirects are
  not failures (B-017's contract, cited verbatim in `.claude/tasks/backend.md`). Fixtures
  available: `live_server`, `browser`, `page`, `index`.
- Produces: the region class names and `data-state` attributes D-015 styles against, and the
  canvas container F-005 mounts into. **List them explicitly in the PR body** — D-015 is
  dispatched against that list and cannot see your diff.

**Acceptance criteria**
- [ ] **C1** The three regions from the 2026-09-01 ruling are present as landmarks: the graph
      canvas (always present, never covered or collapsed), "Add a Node" on the **left** and
      collapsible, the mission panel on the **right** and expandable.
      Source: `shell.html:12, :19, :53, :67`.
- [ ] **C2** Palette collapse and panel expand both work, and both are **operable by keyboard**,
      not only by pointer. Accessibility is never simplified away (`shared/CLAUDE.md` §6).
      Check: drive it with keyboard only in Playwright and assert the state attribute flips.
- [ ] **C3** No inline `style=` attributes and no inline `<script>`: `shell.html:90-310`'s module
      script becomes `static/js/shell.js`. The exploration's inline form is an artefact of being
      a single standalone file.
      Check: assert zero `style=` and zero inline `<script>` bodies in the rendered HTML.
- [ ] **C4** Loading the page produces **no console errors and no responses with status >= 400**.
      Check: `PageActivity.console_errors == []` and `PageActivity.bad_responses == []`.
- [ ] **C5** Collapse state is UI state and **never enters the run payload** (brief §4). Nothing
      in this task serialises it anywhere a run could read.
- [ ] **C6** Semantic elements throughout; no `<div>` where a semantic element exists; every
      interactive control keyboard-reachable (`shared/CLAUDE.md` §6, HTML).
- [ ] **C7** Suite ≥ **596 + new**; flake8 0; `tests/e2e/` nodeid count reported.

**Verification.** Full suite plus the e2e nodeid count before and after.

**Notes.** This is a port, not a redesign. `shell.html` was reviewed across D-010 (3 cycles) and
D-014 (2 cycles + a re-spec); its structure is settled and R3 is closed. Carry the markup over
and change it only where a standalone demo file differs from a server-rendered template.
**Do not write CSS** — `static/css/` is design's, and D-015 styles this in wave 3. The page will
look unstyled when you are done, and that is the expected state.

---

# Wave 2

---

### B-019 — Engine output → the `HISTOGRAM_SCHEMA` payload

**Role:** backend · **Effort:** medium · **Depends on:** B-018 · **CONTRACT TASK** — F-008
consumes this read-only. Not merged with an open finding against the payload.

**Why this is the crux.** `RunResult` carries `processed_any, cutflow_ready, cancelled, reason`
and **no bin data** (`runs.py:118`). The engine writes histograms to
`output/hist{plot_idx}_{sample}.root` (`analytical_loop.py:201`) and stops. Nothing in this repo
reads them back. This task is the missing half of the pipe.

**Files**
- Create: `src/fce_web/payload.py`, `tests/test_payload.py`
- Modify: nothing else. **`docs/api.md`'s histogram section is already complete** (lines 54-165)
  and row-parity tested — this task conforms to it, it does not edit it.

**Interfaces**
- Consumes: the on-disk output of B-018 + `run_analysis`; `HISTOGRAM_SCHEMA`
  (`tests/test_api_contract.py:100-121`).
- Produces: a function taking a completed run's output directory and returning a dict valid
  against `HISTOGRAM_SCHEMA`. F-008 is dispatched against the signature this PR records.

**Acceptance criteria**
- [ ] **C1** The returned dict validates against `HISTOGRAM_SCHEMA` — all 18 rows, respecting
      each row's `REQUIRED` / `NULLABLE` / `OPTIONAL` presence state.
      Check: reuse the existing validator in `tests/test_api_contract.py`; do not write a second.
- [ ] **C2** `edges` and each `samples[].counts` come from the engine's actual output file, read
      the way the reference reads it — `uproot.open(...)`, `f_res["h"]`, `.values()`,
      `.axes[0].edges()` (reference `engine/plotter.py:51-63`). **Reuse that read path rather
      than inventing one** (ponytail rung 2); `plotter.py` is not vendored, so port the reading
      logic, not the plotting.
- [ ] **C3** Systematic variations are read from the `f"h_{src}_up"` keys the reference uses, and
      land under `samples[].systUp.{jec,lep,btag}`. A run with no variations produces a valid
      payload with those `OPTIONAL` keys absent — not present-and-empty.
- [ ] **C4** `len(counts) == len(edges) - 1` for every sample, and `data` matches. An off-by-one
      here is invisible in JSON and fatal in the chart.
- [ ] **C5** The end-to-end path holds: `run_analysis` on B-018's fixture → this function → a
      payload whose `X1` distribution peaks at the Z mass within ±3 GeV.
      **This is the criterion that proves the whole pipe**, and it is why B-018 came first.
- [ ] **C6** A missing or truncated output file raises a typed error rather than returning a
      half-built payload. Error handling that prevents a wrong number reaching a student is
      never simplified away.
- [ ] **C7** `payload.py` is pure read: no HTTP, no module-level mutable state.
- [ ] **C8** Suite ≥ B-018's floor + new; flake8 0.

**Notes.** `docs/design-explorations/payload.json` (788 lines) is D-003's hand-built exemplar of
this exact shape. It is the best available description of the target and a legitimate thing to
diff against — but it is **not** authoritative; `HISTOGRAM_SCHEMA` is.

---

### F-005 — Port the Bench canvas

**Role:** frontend · **Effort:** medium · **Depends on:** F-004

**Files**
- Create: `src/fce_web/static/js/graph.js`
- Modify: the shell template from F-004 (the canvas container), `tests/e2e/test_shell.py` or a
  new `tests/e2e/test_graph.py`

**Interfaces**
- Consumes: F-004's canvas container; `bench.html:200-725`'s 27 functions as the source to port.
- Produces: the client-side graph model — **`nodes` as a *list* of `{id, kind, x, y}`**, and
  `edges` as `[fromId, toId]` pairs (`bench.html:289-292`). F-007 serialises exactly this.
  **Record the exported shape in the PR body**; F-007 is dispatched against it.
  **Corrected 2026-09-09, F-005 cycle 1 F2.** This line originally said "`nodes` keyed by id
  holding `{kind, x, y}`", and that was wrong: the only consumer, `build_run_config`
  (`graph.py:338`), reads `nodes` as a **list** of `{id, kind, config?}` — `id`/`kind` at
  `graph.py:120,122-123`, optional `config` at `:135`; `edges` as `[from, to]` pairs at
  `:144-146` (confirmed by `scout`, not inferred). Keying by id would have made F-007 inherit a
  shape translation for no gain. `x`/`y` ride along as extra keys the server does not read.

**Acceptance criteria**
- [ ] **C1** The palette offers exactly **four** kinds — `Multiplicity`, `Selection`,
      `Observable`, `Histogram` (2026-09-02 ruling). Not seven, not eight. `bench.html`'s extra
      buttons are the superseded artefact D-009's M2 finding already identified.
- [ ] **C2** Nodes can be placed, dragged, and connected by pointer; positions persist as
      `{id, x, y}` and edges as an ordered pair list, per `bench.html:289-292`.
- [ ] **C3** **There is a full keyboard path to constructing a graph** — placing a node, arming
      an output, completing a connection, and moving a node. Brief §4 requirement 2 makes this a
      review item, not a nice-to-have; `bench.html` already has `handleOutKey`, `handleInKey`,
      `handleHandleKey` and `clearKeyboardArm` to port.
      Check: build a complete mission-1 graph in Playwright using keyboard only.
- [ ] **C4** Illegal connections are refused at the client, matching B-020's `VALID_CONNECTIONS`.
      The client check is a courtesy; **the server check is the authority** and B-020 owns it.
      A client that disagrees with the server is a bug in the client.
- [ ] **C5** No `DataSource` node is placeable — it left the palette on 2026-09-01 and the server
      synthesises it (B-020 C4).
- [ ] **C6** Locked node kinds are **shown and inert**, labelled with the mission that opens
      them, never hidden (brief §4, "complexity ramps").
- [ ] **C7** No console errors, no `bad_responses`; no global variables; no `innerHTML` with
      server data (`shared/CLAUDE.md` §6, JavaScript).
- [ ] **C8** Suite ≥ F-004's floor + new; flake8 0; e2e nodeid count reported.

**Notes.** Do not write CSS. Do not POST anything — F-007 owns submission, and `bench.html` POSTs
nowhere today, which is correct for this task too.

---

# Wave 3

---

### B-021 — Job registry, `POST /api/run`, `GET /api/run/{id}/result`

**Role:** backend · **Effort:** medium · **Depends on:** B-019, B-020

**Files**
- Create: `src/fce_web/jobs.py`, `src/fce_web/routes/api.py`, `tests/test_jobs.py`,
  `tests/test_api_run.py`
- Modify: `src/fce_web/app.py` (include the new router), `docs/api.md` (the two endpoint rows)

**Interfaces**
- Consumes: B-020's validation entry point and error type; B-019's payload builder;
  `run_analysis` (`driver.py:98`), `RunContext` (`runs.py:78`).
- Produces: a run-id concept and a registry object; the two endpoints. B-022 attaches its SSE
  endpoint to the same registry and consumes whatever progress queue this task defines —
  **name it in the PR body.**

**Acceptance criteria**
- [ ] **C1** `POST /api/run` accepts the graph payload, returns a run id, and returns **before**
      the run completes. The run executes on a background thread.
- [ ] **C2** An invalid graph returns a 4xx carrying B-020's message; it never starts a run.
- [ ] **C3** **Two concurrent runs keep separate state** — separate progress, separate results,
      neither corrupting the other. This is the defect the entire M2 milestone existed to
      remove (`shared/CLAUDE.md` §2); reintroducing it at the HTTP layer would undo it.
      Check: submit two runs at once and assert their results and progress are disjoint.
- [ ] **C4** The registry holds **no module-level mutable state**. It is constructed and owned by
      the app, reachable through the app, and a second app instance shares nothing with the first.
      Check: build two apps in one process and assert their registries are independent.
- [ ] **C5** `GET /api/run/{id}/result` returns B-019's payload for a finished run, a documented
      not-ready status for a running one, and 404 for an unknown id.
- [ ] **C6** Cancellation works, through the existing seam — `RunContext.cancel` is a
      `threading.Event` and granularity is one basket (`backend.md` §Contracts in force).
- [ ] **C7** A cache hit is **distinguishable** in the response, so the UI can say
      *"recognised these cuts — reusing your earlier run"* (brief §2). The content-addressed
      cache is a property worth preserving deliberately (`shared/CLAUDE.md` §2); surfacing it is
      what makes it visible rather than merely fast.
- [ ] **C8** Both endpoint rows in `docs/api.md` are specified; the row-parity meta-test passes.
- [ ] **C9** Suite ≥ wave-2 floor + new; flake8 0.

---

### F-006 — The merged `Observable` node interior

**Role:** frontend · **Effort:** medium · **Depends on:** F-005

**Files**
- Create/modify: node markup in the shell template, `src/fce_web/static/js/graph.js`
- Test: `tests/e2e/test_graph.py`

**Acceptance criteria**
- [ ] **C1** One `Observable` node with an in-node mode toggle offering exactly four modes —
      `ObsGlobal`, `ObsObject`, `ObsVectorSum`, `ObsCustom` (2026-09-02 ruling). Source:
      **`observable.html` (225 lines), D-013's deliverable.** Not `interiors.html`, which is
      D-009's superseded four-node exploration.
- [ ] **C2** The node **grows in place** when opened. There is no flyout inspector — D-009's page
      recommended one and the user overruled it, the same shape as the D-007/Bench overrule.
- [ ] **C3** The mode is carried as node **config**, not as node identity: the kind stays
      `Observable` in the client model, and B-020 resolves it server-side.
- [ ] **C4** The opened footprint is consistent with D-013's measured contract — the opened
      `.inode` is **328.0 × 300.0px** (`ObsVectorSum`, the tallest mode; `ObsCustom` 301.5,
      `ObsObject` 290.5, `ObsGlobal` 237.0), collapsed 80.5px. Report the measured values; a
      deviation is acceptable if argued in writing, an *unreported* deviation is not.
- [ ] **C5** The toggle is keyboard-operable and its control has an accessible name. D-009's
      Required and M1 were both against the *instrument* — three checks that structurally could
      not fail, including unlabelled controls certified GREEN. Write a check that can go red.
- [ ] **C6** An opened node overlapping what sits beneath it on the free canvas is handled — the
      two-footprint consequence the 2026-09-02 ruling assigned to the shell, which D-010 solved
      with a fixed 704×512 canvas surface and the region scrolling.
- [ ] **C7** No console errors, no `bad_responses`; suite ≥ floor + new; flake8 0.

---

### D-015 — The shell, canvas and node stylesheets

**Role:** design · **Effort:** high — a new visual system carried into a new medium ·
**Depends on:** F-004, F-005, F-006 · **Releases:** F-003

**Files**
- Create: `src/fce_web/static/css/` — the shell, canvas and node stylesheets
- Modify: in `templates/`, **class attributes and purely presentational wrappers only**
- **Must not touch:** `hx-*`, form `name`/`id`, `data-*` bindings, template logic, any JS, any
  Python, and **`docs/design-explorations/verify.py`** (see the ruling above)

**Acceptance criteria**
- [ ] **C1** Every colour, spacing, type and radius value comes from `tokens.css`'s 62 custom
      properties. **No hard-coded hex outside the tokens file.**
      Check: enumerate *computed* styles in a real browser, not by grepping for `#`. D-001 spent
      four cycles because `grep -rhoiE '#[0-9a-f]{3,8}'` structurally cannot see a UA-default
      `rgb(0,0,238)`, and a blue link stayed the first tab stop for three of them.
- [ ] **C2** WCAG AA contrast on all text, measured in the running app. `--ink-45` is **2.60:1
      and is not text-safe** (`design.md` §Constraints) — it is available for rules and
      furniture, not for type.
- [ ] **C3** Node type, sample identity and lock state each carry their assigned hue (brief §7),
      using D-008's palette. Its six simultaneous floors still hold: min CVD ΔE **5.129**,
      normal-vision node-node **14.170**, node-vs-reserved **13.442**, white-on-fill **4.595:1**,
      fill-vs-reserved hue gap **14.1°**, clamping excess **+0.0051**.
- [ ] **C4** Vermillion stays held back — significance thresholds, mission completion, the signal
      sample, and nothing else (brief §7).
- [ ] **C5** Every animation respects `prefers-reduced-motion`.
- [ ] **C6** The canvas is never horizontally scrolled by the page: no page-level h-scroll at
      1440, 1024 and 768, across all four palette/panel states. D-014 shipped exactly this guard
      as `shell-page-no-h-scroll` over 12 layouts; the property is settled, the medium is new.
- [ ] **C7** `docs/design-explorations/verify.py` is **unmodified**, and its 81 AST registrations
      and deliberately-red `board-lane-fill` are untouched.
      Check: `git diff main...HEAD --name-only` contains no path under `docs/design-explorations/`.
- [ ] **C8** File scope holds: `git diff main...HEAD --name-only` — three-dot, against the merge
      base, because the orchestrator commits bookkeeping to `main` while tasks are in flight and
      a two-dot diff reports those as differences of the branch (D-007 C5, 2026-09-01).
- [ ] **C9** No console errors, no `bad_responses`; suite ≥ floor + new; flake8 0.

**Notes.** The exploration `shell.css` (439 lines) and `bench.css` (653) are the source. Once
ported, **the app copy is authoritative and the exploration copy is frozen** — do not attempt to
keep them in sync.

---

# Wave 4 — and the first checkpoint

---

### B-022 — The SSE progress stream

**Role:** backend · **Effort:** medium · **Depends on:** B-021

**Files**
- Create: the SSE endpoint in `src/fce_web/routes/api.py`, `tests/test_api_events.py`
- Modify: `docs/api.md` — fill the `### Run progress event` stub at line 298

**Interfaces**
- Consumes: B-021's registry and progress queue; `RunContext`'s `on_progress`, `on_log`,
  `on_phase`, `on_node` callbacks (`runs.py:78`), which already exist and are **the reason no
  engine change is needed**.
- Produces: the wire format F-007 parses. Specify it in `docs/api.md`, not only in the PR.

**Acceptance criteria**
- [ ] **C1** `GET /api/run/{id}/events` streams `text/event-stream` and terminates with a single
      `done` event. Progress only — **the bins come from `GET /result`** (ruling 5).
- [ ] **C2** Phase label and progress fraction both stream, because brief §2 requires a run to be
      visibly alive, and a bar with no phase is not.
- [ ] **C3** A cache hit yields an immediate `done` rather than a fabricated progress sweep. A
      progress bar that animates over work that did not happen is a lie told to a student.
- [ ] **C4** An unknown run id is a 404, not an open stream that never emits.
- [ ] **C5** A client disconnecting mid-run does not leak the thread or wedge the registry.
- [ ] **C6** Two concurrent streams for two runs do not interleave.
- [ ] **C7** `docs/api.md:298`'s stub is replaced; the row-parity meta-test passes.
- [ ] **C8** Suite ≥ wave-3 floor + new; flake8 0.

---

### F-003 — Prove the four woff2 are actually served

**Role:** frontend · **Effort:** medium · **Depends on:** D-015 · Already specified in
[`.claude/tasks/frontend.md`](../.claude/tasks/frontend.md) `## Deferred` — carried here unchanged.

The dependency it was waiting on is D-015: the first task to apply `font-family: var(--font-body)`
to a real selector in `src/fce_web/static/css/`. Until then "no font 404s" passed vacuously,
because `tokens.css` applied `font-family` to nothing and no face was ever fetched.

- [ ] **C1** Loading a page whose CSS actually uses `var(--font-body)` and `var(--font-mono)`
      requests **all four** woff2 and every one returns 200.
- [ ] **C2** The check asserts the four are **requested**, not merely that nothing failed. The
      vacuity is the entire point of the task.
- [ ] **C3** Falsifiability is shown by breaking one `src:` path — `tokens.css:54, :62, :70, :78`,
      all relative (`url("../fonts/<name>.woff2")`), resolving against `/static/css/` — and
      watching the named test go red. Paste both states.

---

> ## ◼ CHECKPOINT 1 — the pipe is real
>
> **What now works, as something to go and try:** submit a graph by `curl`, watch progress
> stream, and fetch back real bins the physics engine computed from the fixture.
>
> The orchestrator stops here and reports: what runs, the exact commands, what was overruled or
> backlogged, and the M4 re-scope (ruling 2 absorbs most of it). Wave 5 does not start until the
> user has seen this.

---

# Wave 5

Frontend and design on the same page are never parallelisable. F-008 follows F-007; D-016
follows F-008. If this wave runs long it splits rather than compresses.

---

### F-007 — Serialise, submit, stream, show progress

**Role:** frontend · **Depends on:** F-005, F-006, B-020, B-021, B-022

**Files:** `src/fce_web/static/js/run.js`; the shell template's results region; `tests/e2e/`

- [ ] **C1** The canvas graph serialises to the shape B-020's PR body documents —
      `{nodes[], edges[], ui{}}` — with layout state confined to `ui` and **nothing the engine
      must understand outside it** (brief §4).
- [ ] **C2** Collapse state, coordinates and slot indices live in `ui` and are ignored by the run.
- [ ] **C3** The SSE stream is consumed and phase + progress render live.
- [ ] **C4** A cache hit renders as *"recognised these cuts — reusing your earlier run"* rather
      than as a suspiciously instant bar (brief §2).
- [ ] **C5** A failed or rejected run renders B-020's message as a **margin note, never a red
      banner** — missing is the normal case, not an error state (brief §2).
- [ ] **C6** Network failure is handled: no unhandled rejection, no silent dead UI.
- [ ] **C7** No console errors, no `bad_responses`; suite ≥ floor + new; flake8 0.

---

### F-008 — The interactive SVG histogram

**Role:** frontend · **Depends on:** B-019, F-007

**Files:** `src/fce_web/static/js/chart.js`; the results region; `tests/e2e/`

- [ ] **C1** The renderer is ported from `plot.js` (817 lines, 16 functions) and keeps its fixed
      intrinsic **650 × 460** CSS px (`plot.js:142`), which does not reflow (`design.md`
      §Constraints).
- [ ] **C2** Bin data enters by **fetch from `GET /api/run/{id}/result`**, replacing the embedded
      `<script type="application/json" id="payload-data">` at `plot.html:167`.
- [ ] **C3** Stacked backgrounds; data as points with error bars — the convention the physics
      community uses, which students should meet (brief §5).
- [ ] **C4** Hover reads out a bin, and there is a keyboard equivalent.
- [ ] **C5** Bars draw in as results arrive (brief §5) and the animation respects
      `prefers-reduced-motion`.
- [ ] **C6** **Explicitly out of scope** (ruling 3): legend toggling, the `mplhep` PNG export,
      the cutflow, the Z gauge. Do not build them. `plot.js`'s `drawLegend` and
      `renderCutflowFigure` are ported dormant or left behind — say which in the PR body.
- [ ] **C7** The rendered peak sits at the Z mass, read off the running app, not off a fixture
      JSON. **This is the criterion that closes the milestone.**
- [ ] **C8** No console errors, no `bad_responses`; suite ≥ floor + new; flake8 0.

---

### D-016 — Results region and chart styling

**Role:** design · **Depends on:** F-008

**Files:** `src/fce_web/static/css/`; class attributes only in `templates/`

- [ ] **C1** Tokens only; computed styles enumerated in a browser (D-015 C1's method).
- [ ] **C2** Sample identity colour is **the same in the graph, the legend and the plot**
      (brief §7). One sample, one hue, three places.
- [ ] **C3** The plot sits on the light ground rather than fighting it — light is not negotiable
      because physics plots are conventionally drawn on white (brief §7).
- [ ] **C4** AA contrast measured in the running app; `--ink-45` not used for text.
- [ ] **C5** `verify.py` unmodified; file scope by `git diff main...HEAD --name-only`.
- [ ] **C6** Suite ≥ floor + new; flake8 0.

---

> ## ◼ CHECKPOINT 2 — M3 complete
>
> A student opens the app, builds a graph, presses Run, watches it stream, and sees the Z peak.
> The orchestrator reports and the user decides what M4 becomes.

---

## What M3 deliberately does not build

Each is a candidate later; none is a gap to be helpfully filled.

- The cutflow, μ, and the Z gauge (brief §5) — M4.
- Legend toggling and the `mplhep` PNG export (ruling 3) — M4.
- Missions as data, gating, unlocking, SQLite persistence, class code and nickname — **M5**.
  M3 runs one mission's dataset; it does not load `content/missions/*.yaml`.
- The completed-mission box on the canvas (**D-011**) — needs M5, since nothing can be completed.
- Event displays during a run (**D-012**) — deferred to **M6** by the user's 2026-09-01 ruling.
  M3 ships the phase label and the bar, and that is deliberate rather than an oversight.
- Mission 3 content — **blocked** on the user identifying samples `X4` and `X5` (brief §9).

## Risks

- **B-018 is a single point of failure.** If a synthetic fixture cannot be made to produce a
  credible peak, B-019 C5, F-008 C7 and both checkpoints lose their evidence. Detected at the
  end of wave 1; the fallback is the user supplying a truncated real file.
- **B-020 has no authoritative source for the allowlist.** Brief §4 prose and `bench.html:258`
  disagree in principle and nothing has ever compared them. C2's reference parity check is the
  mitigation, and it *skips* where the reference is absent — so a checkout without it gets less
  assurance than one with it. Say so in the PR body rather than reporting a green that is thin.
- **Wave 5 serialises three tasks on one page.** The likeliest place for the milestone to run
  past its budget.
- **This is 13 tasks against a 5-hour usage limit shared by every agent at once.** The plan is
  explicitly expected to span sessions; §10's handoff protocol is the mechanism, not a failure.
