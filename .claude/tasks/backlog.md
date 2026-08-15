# Backlog

Two things land here:

1. **Suggested-minor** review findings — always, automatically. They never block a task.
   Group them by area; the orchestrator raises a single cleanup task per area once a group
   is worth sweeping.
2. **Suggested-major** findings the coder overruled on the grounds that they belong to a
   different future task. Record the coder's argument alongside, so the decision is
   auditable later.

Entries carry the task ID they came from, so context is recoverable.

---

## Backend

- **`.flake8` `exclude` omits `.venv`.** `.flake8:16`. The list replaces flake8's defaults,
  so a bare `flake8 .` from the repo root reports ~40,000 errors, all from `.venv/`. The
  specified `flake8 src/ tests/` is clean so nothing is blocked today, but CI or a
  pre-commit hook running `flake8 .` would be unusable. Fix: add `.venv, venv` to the
  exclude line. _(from B-001 review)_
- **PyYAML is only a transitive dependency.** `pyproject.toml:27`. `import yaml` works
  today solely because `pyhf` pulls it in. `missions.py` will need it directly per shared
  §7 — declare it explicitly rather than inheriting it by accident. _(from B-001 review)_
- **No `README.md`.** Packaging metadata has no long description, and the repo has no entry
  point for a human arriving cold. _(from B-001)_
- **No CI workflow.** `.flake8` excludes `.github`, implying one is expected. A workflow
  running `pytest` + `flake8` on push would catch regressions the reviewer currently
  catches by hand. Depends on the `.venv` exclude fix above. _(from B-001)_
- **`templates/` and `static/` do not survive a wheel build.** `pyproject.toml:52`.
  `[tool.setuptools.packages.find]` has no `package-data` and there is no `MANIFEST.in`, so
  `pip wheel --no-deps --no-build-isolation .` produces a wheel containing only
  `fce_web/__init__.py` and `dist-info/*` — an installed `fce-web` would have no page shell
  to render. Harmless while the app runs from the source tree, but it must be fixed before
  anyone installs this for a classroom. Verified by the reviewer, not merely suspected.
  _(from F-001 review; needs a back-end task, `pyproject.toml` is back-end owned)_
  **Raised again as suggested-major on B-002 and overruled there, in writing** — the
  orchestrator accepts the argument: the fix needs `[tool.setuptools.package-data]` or a
  `MANIFEST.in`, both outside B-002's scope of "only the httpx entry"; B-002 neither
  introduced it nor can own it, since mounting a package-relative `static/` is correct and
  it is the build config that is incomplete; and the gap applies equally to `templates/`,
  `static/` and `content/missions/*.yaml`, so a proper fix wants a build-a-wheel-and-inspect
  test covering every data file type. Three independent confirmations now. Nothing is
  blocked meanwhile: source checkouts, editable or not, are unaffected.
- **`httpx` is deprecated for `starlette.testclient`.** Starlette 1.6.0 emits
  `StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated;
  install 'httpx2' instead.` One warning, no failure, so nothing is blocked. Switching the
  dev extra to `httpx2` is a dependency decision and needs user sign-off, exactly as `httpx`
  itself did. _(from B-002)_
- **The module-level-state guard is allow-by-default.** `tests/test_app.py:45-48`.
  `MUTABLE_CONTAINERS` / `PER_APP_TYPES` enumerate the types they reject, so the scan only
  catches shapes it already knows: the reviewer showed a module-level `threading.Lock()` or
  a custom registry object holding a `dict` passes clean. The reference repo's defect was a
  `dict` and would be caught, but the next one need not be. Invert it to default-deny —
  allow only inert types (`str`, `int`, `float`, `bool`, `bytes`, `tuple`, `frozenset`,
  `Path`, module, class, function) and reject the rest — matching how the same principle is
  applied in `safe_eval`. _(from B-002 review)_
- **Dependencies unpinned, no lock file.** Fine now, but a scientific-Python stack drifts.
  Worth resolving before classroom deployment so a teacher's install matches the tested
  one. _(from B-001)_

## Frontend

- **Skip link ("skip to main content")** plus the visually-hidden class it needs, once
  navigation or site chrome exists. _(from F-001)_
- **`aria-live="polite"` containers** for run progress and results, when those views are
  built in M3. Progress that streams silently to a screen reader is progress that does not
  exist. _(from F-001)_
- **`<header>`/`<nav>`/`<footer>` landmarks** in `base.html`, once there is anything to put
  in them. F-001 deliberately shipped without them rather than emit empty landmarks.
- **Offline HTML validation.** No `tidy` or `vnu` on this machine, so template validity
  currently rests on the browser parse. A pip-installable validator in the e2e suite would
  make it checkable. _(from F-001; needs a backend task, `tests/` is backend-owned)_

## Design

- **`docs/wireframes/brain/design-taste.md`** is the wireframe skill's colour-phase
  reference, copied unmodified and unused in phase 1. Keep it only if a phase-2 run is ever
  wanted; otherwise delete. _(from D-001)_
- **Mission-1-only layout hybrid, worth playtesting rather than assuming:** run mission 1
  as mission-screen Option 3 (Focus Stage — its stepped rail is the best teaching device of
  the five) and hand the student the full spread from mission 2 on. Not drawn, and not
  recommended without evidence. _(from D-001)_
- **Two ideas from the losing builder options**, worth carrying into whichever wins:
  Option 5's face-down locked cards as the way to show card gating, and Option 3's per-step
  "events kept: 18 420 of 240 000" preview, which turns an abstract cut into a number that
  moves before the run is even started. _(from D-001)_

- **Placeholder text below AA.** `docs/wireframes/mission-screen.css:77` —
  `input::placeholder { color: #999 }` is 2.85:1 on white, the only text in the wireframes
  below AA. Acceptable in a throwaway document depicting a placeholder *state*, which is why
  it was minor — but **real placeholders must meet AA, so this pattern must not be carried
  into D-002.** `#767676` gives 4.54:1 and still reads as washed out. _(from D-001 review)_
- **Active tab state is class-only.** `docs/wireframes/mission-screen.html:20-25` and
  `recipe-builder.html` — selection lives in `class="tab-btn active"`, so keyboard operation
  and focus are fine but a screen-reader user cannot tell which option is displayed.
  `aria-current="true"` on the active button, removed alongside the class in the click
  handler, closes it. Worth carrying as a habit into real tabbed UI. _(from D-001 review)_

## Cross-cutting

- **Dark colour variant.** V1 commits to light only — the lab-notebook aesthetic is a light
  object and a badly-done dark mode is worse than none. A "darkroom" variant is a candidate
  once the light system is settled. _(from the design direction decision, not a review)_
