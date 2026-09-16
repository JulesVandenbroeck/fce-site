# M4 — Recipe card builder: node interiors reach `RunConfig`

Status: **design approved by the user 2026-09-16; plan awaiting review.**
Predecessor: [`plan-m3-vertical-slice.md`](plan-m3-vertical-slice.md).

## Goal

A student configures every node on the canvas — how many leptons, which cuts, what to plot,
how to bin it — and the run uses those settings. Today only `Observable.mode` leaves the
browser; every other value is absent, so every run is the same run.

## What already exists (scout, 2026-09-16 — do not re-derive)

- **The backend already reads every field.** `build_run_config` (`src/fce_web/graph.py`) reads:
  Multiplicity — the 7 `_MULT_CUT_FIELDS` (`nlep, op_lep, njets, op_jet, ltype, nphot, op_phot`);
  Selection — `exprs: list[str]`; Observable — `mode`, `expr`, `label` (optional);
  Histogram — `bins`, `min`, `max` (strings), optional `target`, `name`, `x_label`.
- **The Observable mode is browser-side only.** The engine compiles and evaluates `expr`
  identically for all four modes (`path_filter.py:466, 607`). The mode decides which controls
  build `expr`; nothing else.
- **Expression vocabulary** (`safe_eval.py:86-131`): objects `l1 l2 j1 j2 ph1 ph2 met`; attributes
  `pt eta phi e` on all, `charge flavour d0 z0` on leptons, `btag` on jets, `.p4.mass`/`.p4.pt`;
  counts `nlep nel nmu njets nphot`; comparisons `< <= > >= == !=`; `and`/`or`/`not`; `**` forbidden.
- **Validation timing.** Selection expressions are rejected before the run touches a cache
  (`analytical_loop.py:217-243`); observable expressions fail at compile, before the first basket.
- **No interior controls exist.** F-006 deleted them because nothing read them (`graph.js:29`).

## Decisions (the user, 2026-09-16)

1. **Structured controls, not typed expressions.** The student picks object, property, comparison
   and number; the node builds the string. `ObsCustom` is the one free-text field.
2. **The full engine vocabulary, plain-labelled.** M5 adds unlock filtering on top; M4 does not
   know missions exist.
3. **Nodes are placed with defaults that run.** A freshly built chain produces a peak. M5 revisits
   the defaults as part of mission starts.

## The design

All controls are native elements (`<select>`, `<input type="number">`, radios) inside the existing
`<details>` interior. Labels are plain words with the physics term alongside:
*"transverse momentum (pt)"*, *"1st lepton"*.

| Node | Controls | Default | `config` emitted |
|---|---|---|---|
| Multiplicity | count + comparison for leptons, jets, photons; lepton type any / e / μ | exactly 2 leptons; jets and photons unconstrained | the 7 `_MULT_CUT_FIELDS` |
| Selection | rows *object · property · comparison · number*; "add condition"; rows ANDed | one row: 1st lepton pt > 5 GeV | `exprs: ["l1.pt > 5", ...]` |
| Observable | **Global:** a count or MET pt · **Object:** object + property · **VectorSum:** tick objects, then mass or pt · **Custom:** text | VectorSum, l1 + l2, mass | `mode`, `expr`, `label` (generated) |
| Histogram | bins, min, max | 50 bins, 0-150 GeV; range re-presets when the observable's quantity changes | `bins`, `min`, `max`, `x_label` |

**One expression module.** The vocabulary table (name, plain label, unit, range preset) and the
`buildExpr` functions live in one ES module under `static/js/`. Every interior uses it. It carries
one runnable check: each builder's output compiles under `safe_eval` (the server is the authority,
so the check submits, it does not re-implement the allowlist in JS).

**Errors.** A rejected graph shows its message. Whether that message can be attached to the node
that caused it depends on whether the error carries a node id — open question Q2 below. If it does
not, M4 shows it in the run status region and records that as its ceiling.

**Security is unchanged.** The dropdowns can only emit allowlisted names, but that is a convenience,
not the guard. `safe_eval` on the server stays the only trust boundary; `ObsCustom` text and any
hand-crafted POST go through it exactly as today.

## Tasks

| ID | Role | Outcome | Depends on |
|---|---|---|---|
| **F-011** | frontend | Observable and Selection interiors; the expression module; `graph.js` emits their `config`; one e2e check that a non-default graph changes the returned histogram | Q1 |
| **F-012** | frontend | Multiplicity and Histogram interiors, range presets | F-011 (shares `graph.js`) |
| **B-026** | backend | *Only if Q2 says no:* rejected-graph errors name the offending node | Q2 |
| **D-018** | design | style the four interiors | F-012 |

F-011 → F-012 → D-018 is serial (same markup, then its styling). B-026, if raised, runs in parallel
with F-011 — backend files only.

**Contract task:** F-011's expression module is consumed read-only by F-012 and D-018's markup.
Its exported table goes verbatim into PR F-011's body, and nothing merges against an open finding on it.

## Open questions — answered by `scout` before the dispatch that needs them

- **Q1 (before F-011).** Does `build_run_config` accept an empty `exprs` list, and what are the exact
  `op_*` strings `_MULT_CUT_FIELDS` accepts, and `ltype` values?
- **Q2 (before F-011).** Do `GraphError` / run-error responses carry a node id?
- **Q3 (before F-012).** Is `Histogram.bins/min/max` validated server-side as numeric and ordered
  (`min < max`, `bins > 0`, a cap on `bins`)? If not, that is a trust-boundary gap and becomes a
  backend task, not a client check.

## Out of scope

Unlock filtering (M5), mission-driven defaults (M5), the "show expression" toggle (M6 if missions
need it), event displays during a run (D-012, M6), missions 2-3 content.
