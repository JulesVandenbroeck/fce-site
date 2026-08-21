# Role: Back-end coder

You write the Python: the web server, the data layer, and the vendored physics engine.

Read `.claude/shared/CLAUDE.md` first. Then this. Then do only the task you were given.

---

## 1. Scope

**You own:**

```
src/fce_web/app.py          src/fce_web/routes/
src/fce_web/runs.py         src/fce_web/store.py
src/fce_web/missions.py     src/fce_web/safe_eval.py
src/fce_web/engine/         src/fce_web/objects.py    src/fce_web/paths.py
tests/                      content/missions/
pyproject.toml              .flake8                   docs/api.md
```

**You must not touch:** `src/fce_web/templates/`, `src/fce_web/static/`, or anything under
`.claude/`. You render templates by name from a route; you never edit their contents. If a
template needs to change for your work to function, stop and report it — the orchestrator
will raise a frontend task.

Your dispatched task narrows this further. The list above is the *outer* limit; the task's
file scope is the real one.

---

## 2. Test-driven development is mandatory

**Invoke `superpowers:test-driven-development` and follow it.** Not optional, not "when it
makes sense".

Red → green → refactor:

1. Write the failing test first. Run it. **See it fail**, and see it fail for the reason
   you expect — a test that passes before the implementation exists is testing nothing.
2. Write the minimum code to pass.
3. Run the whole suite, not just your test.
4. Refactor with the suite green.

`pytest` for everything. `pytest tests/ -q` must pass before you report done, and
`flake8 src/ tests/` must be clean.

Physics code gets tested against **known values**, not against whatever the code currently
returns. If you cannot state the expected number independently of the implementation, you
do not yet understand what you are testing.

### Mutation-test by monkeypatch. Never by editing a tracked file.

A new assertion is only worth having if you have watched it fail. But **how** you break the
code to watch it fail matters:

- **Do:** a `monkeypatch` fixture, a `conftest.py` plugin, or rebinding the symbol at collection
  time. Nothing tracked is ever modified, so there is no restore step that can be skipped.
- **Do not:** temporarily edit the source file and rely on a follow-up `git diff` to prove you
  put it back.

Both reach the same failure. The second has a failure mode the first does not: on 2026-08-21
four agents on this project died mid-turn to a session limit, and a crash landing between
*mutate* and *restore* leaves the mutation in your working tree — where the next `git add -A`
commits it. B-005 cycle 3 mutated `src/fce_web/paths.py` in place and restored it correctly; its
reviewer got the identical two failures with a plugin patching `tempfile.mkstemp`, touching no
tracked file at all. Same evidence, no exposure.

Report the mutation, its exact failure message, and the restored-green run — for every new
assertion, named individually.

---

## 3. Working on the engine

The engine is vendored from `kskovpen/fce`. It is validated physics. Treat it as such.

**The cardinal rule: never change a physics formula to make a test pass.** If a test
disagrees with the engine, the test is wrong until proven otherwise. If you genuinely
believe the physics is wrong, stop and report it — that is a conversation with the user,
who is a co-author of the original, not a change you make.

Any change to a numerical path needs a **regression test proving the output is
unchanged**: capture the reference output, refactor, assert identical. The ported tests
(`tests/test_fitter.py`, `test_path_filter.py`, `test_systematics.py`, `test_paths.py`)
are that net. Keep them passing.

Refactoring the engine's *structure* is expected and welcome. Refactoring its *arithmetic*
is not.

### 3.1 Killing the global state

`engine/analytical_loop.py` reads and writes `ui.state.RUN_STATE` — a module-level dict —
in about 25 places: `progress`, `status_msg`, `stop`, `current_phase`, `running`,
`active_nodes`, `cutflow_ready`, `n_workers`, `progress_ctx`.

Replace it with a `RunContext` object created per run and passed explicitly down the call
chain. Requirements:

- **No module-level mutable state anywhere in `engine/`.** This is the defect; do not
  reintroduce it in a new shape (no module-level registry dict, no singleton class).
- Each run gets its own context. Two runs in flight must not see each other's progress,
  status, or cancellation.
- Cancellation is per-run: setting `stop` on one context must not stop the other.
- `import fce_web.engine` must pull in **zero** UI or `dearpygui` dependencies. A test
  should assert this — e.g. that no imported module name starts with `dearpygui` or `ui.`.
- The engine must run headless, with no display.

`paths.get_fce_home()` caches a module-level path. That one is fine — it is immutable
after resolution — but make the cache explicit and testable.

### 3.2 Sandboxing student expressions

`engine/path_filter.py` currently calls `eval(expr, {"__builtins__": _SAFE_BUILTINS}, vars)`
at lines 255, 296, 368, 426, 606, 615 and 630, and `compile()`s an observable at line 393.
(This file said "eight places" until 2026-08-20. It is seven `eval`s plus one `compile`; the
B-006 coder checked the reference instead of trusting the number and reported the discrepancy.
Line numbers beat counts — a count is the failure shape this project keeps shipping.) Restricting `__builtins__` does **not** make `eval` safe: a student can
write `(1).__class__.__bases__[0].__subclasses__()` and walk out to arbitrary classes, and
from there to `os.system`. On a laptop that is nothing. On a teacher's machine with thirty
students connected, it is remote code execution.

Build `src/fce_web/safe_eval.py`:

- Parse with `ast.parse(expr, mode="eval")`.
- Walk the tree and **reject any node type not on an explicit allow-list.** Allow the
  arithmetic, comparison, boolean, attribute, name, constant, and call nodes students need.
  Reject `Lambda`, `comprehensions`, `Import`, assignments, walrus, f-strings, `Starred`,
  and anything you have not thought about. Default deny.
- **`Subscript` is rejected, and the `jets[0].btag` example below is wrong.** Corrected
  2026-08-20 after B-006 flagged the contradiction. The reference's eval namespace is
  `l1 l2 j1 j2 ph1 ph2 met` plus five counts — there is **no `jets` name**, so `jets[0].btag`
  raises `NameError` in the reference today; it describes a language the engine does not
  implement. An allow-list should be as narrow as what actually works. Note also that the
  escape example above, `(1).__class__.__bases__[0].__subclasses__()`, **needs a subscript** —
  so rejecting `Subscript` closes it a second time, independently of the underscore rule.
  If a later milestone exposes an indexable collection, widening the list is additive.
- **Reject any attribute name beginning with `_`.** This is what closes the escape.
- Allow calls only to the whitelisted names already in `_SAFE_BUILTINS`
  (`abs`, `max`, `min`, `len`, `sqrt`, `cos`, `sin`, `tan`, `exp`, `log`, …).
- Bound the input: cap expression length and AST node count so nobody submits a billion-
  laugh expression.
- Keep `preprocess_hep_expr()` (the `&&` → `and` translation) — students are taught HEP
  syntax.
- Raise a **student-legible** error on rejection. "Cannot use `_` names here" beats a
  traceback. These messages are part of the learning experience: a 16-year-old who mistypes
  a cut should learn something from the error, not be frightened by it.

**Everything students can currently write must keep working:** `nlep >= 2`,
`l1.pt > 20 and l2.pt > 10`, `(l1.p4 + l2.p4).mass > 80`, `j1.btag > 0.7`, `abs(l1.eta) < 2.5`.
Write tests for each of those *and* for a set of escape attempts, before you write the
evaluator.

---

## 4. Concurrency and long-running work

An analysis run takes seconds to minutes. It cannot block the event loop.

- Run the physics in a thread pool (the engine is I/O-bound on uproot and already threaded
  internally). Never do heavy work directly in an `async def` handler.
- Every run gets an id, a `RunContext`, and an entry in a job registry.
- Stream progress with **Server-Sent Events**, not polling. The desktop app has a progress
  bar and phase label; students need the same feedback or a two-minute run feels broken.
- Cap concurrent runs and queue beyond that. A classroom of thirty pressing Run at once
  must degrade into a queue, not into swap death. Make the cap configurable.
- Preserve the content-addressed cache. A cache hit should return in milliseconds, and
  that should be visible to the student ("recognised these cuts — reusing earlier results").

---

## 5. Data layer

SQLite through stdlib `sqlite3`. One file. No ORM.

- All SQL lives in `store.py`. Routes call functions; routes never write SQL.
- **Parameterised queries only.** No f-strings in SQL, no exceptions.
- Schema created on startup if absent, with a version number for future migrations.
- Use a connection per request or a thread-local; `sqlite3` connections are not thread-safe.
- Enable WAL mode — concurrent readers with one writer is exactly our shape.

**Privacy — this is a legal constraint, not a preference.** Users are minors at a Belgian
university, so GDPR applies.

- Store **nickname and class code only**. No real names, no emails, no IP addresses, no
  free-text fields that could carry personal data.
- The nickname field's UI copy must tell students not to use their real name; validate
  length and character set.
- Provide a teacher-invokable purge that deletes a class's data completely, and document it.
- Do not add analytics, telemetry, or third-party requests of any kind.

---

## 6. API design

Document every endpoint in `docs/api.md` **before** the frontend consumes it. That file is
the contract between you and the frontend role; when it changes, say so in your report.

- JSON in, JSON out, for anything the JS touches. HTML fragments for HTMX targets.
- Field names in the JSON are the field names the frontend will use — pick them once, well.
- Validate every input at the boundary with Pydantic models. Assume hostile input; assume
  confused input more.
- Errors return a proper status code and a JSON body with a message safe to show a
  student. Never leak a traceback to the browser.
- The chart contract is fixed: `{edges: number[], samples: [{name, counts, weightsSquared}], data: number[]}`.
  Confirm the exact shape in `docs/api.md` before changing it.

---

## 7. Missions are data

Mission definitions live in `content/missions/*.yaml` and are loaded and validated at
startup. Adding a mission must never require editing Python.

A mission declares: id, order, title, brief, dataset (energy + detector), which card types
are available, the objective and how to check it, hints, and success copy. Validate the
schema on load and fail loudly with the filename and the problem — the user will author
these, and a silent misparse wastes their afternoon.

Objective checking runs against real engine output. Do not fake it, and do not make the
tolerance so tight that a legitimate alternative analysis fails.

---

## 8. Before you report done

```bash
pytest tests/ -q          # all pass
flake8 src/ tests/        # clean
```

Both, actually run, with output pasted into your report. `superpowers:verification-before-completion`
applies: evidence before assertions. If something fails and you could not fix it within
scope, report the failure — do not report success.

Then use the format in `.claude/shared/CLAUDE.md` §7.

---

## 9. Anti-patterns

| Thought | Reality |
|---|---|
| "I'll write the test after, it's faster" | TDD is mandatory here. A test written after asserts what the code does, not what it should. |
| "The test expects 91.2 but the code gives 91.4, I'll update the test" | Stop. That is the physics regression net doing its job. |
| "A module-level dict is simpler than passing context" | That dict is the bug you were hired to remove. |
| "`eval` with restricted builtins is fine" | It is not. That is exactly the escape being fixed. |
| "I'll just tweak this template so the route works" | Templates are not yours. Report it. |
| "This endpoint is internal, validation is overkill" | Thirty teenagers on the same network. Validate. |
| "I'll add pandas, it'll be quicker" | New dependencies need orchestrator sign-off. |
| "The run takes 40s, that's fine without progress" | Silence reads as broken. Stream progress. |
