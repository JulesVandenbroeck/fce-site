# API contracts

The contract between the back-end and front-end roles. **Owned by the back-end coder.**

The front-end codes against this file, not against the implementation. Backend: update it
*before* the frontend consumes an endpoint, and name the change in your completion report
so the orchestrator can raise the matching frontend task.

Status: the histogram, cutflow and fit payload contracts below are complete. The `Run
progress event` (M3) and `Mission objective result` (M5) sections remain stubs, populated
during those milestones.

---

## Conventions

- JSON in, JSON out for anything JavaScript touches. HTML fragments for HTMX targets.
- Every input validated at the boundary with a Pydantic model.
- Errors return a proper status code and a JSON body with a message that is safe to show a
  student. Never a traceback.
- Field names here are the field names the frontend will use. Choose once, well.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/run` | Submit an analysis recipe; returns a run id |
| `GET` | `/api/run/{id}/events` | SSE stream: progress, phase, completion |
| `GET` | `/api/run/{id}/result` | Histogram data, cutflow, fit results |
| `GET` | `/api/run/{id}/plot.png` | `mplhep` PNG export |

### `POST /api/run` request body

The student's graph, built with `fce_web.graph.build_run_config` (B-020) into the
`RunConfig.from_dict` shape before the engine runs it. `DataSource` is never in this body — it
is synthesised server-side from the mission's declared dataset (`docs/design-brief.md` §4).

```json
{
  "missionId": "string",
  "graph": {
    "nodes": [
      {"id": "string", "kind": "Multiplicity | Selection | Observable | Histogram", "config": {}}
    ],
    "edges": [["fromId", "toId"]]
  }
}
```

- `nodes[].kind` — the four palette kinds a student places (`docs/design-brief.md` §4,
  2026-09-01/02 rulings). `DataSource` is rejected if present; it is a client bug, not a legal
  input.
- `nodes[].config` — kind-specific, validated by `fce_web.graph.build_run_config`:
  - `Multiplicity`: `nlep`, `op_lep`, `njets`, `op_jet`, `ltype`, `nphot`, `op_phot` (the
    7-tuple `engine/runconfig.py`'s `mult_cuts` expects, per node).
  - `Selection`: `name`, `exprs` (list of strings, ANDed with any upstream `Selection`).
  - `Observable`: `mode` (one of `ObsGlobal`, `ObsObject`, `ObsVectorSum`, `ObsCustom` — mode
    is config, not identity), `expr`, `label`.
  - `Histogram`: `bins`, `min`, `max`, `target` (all strings — the digest formula concatenates
    them raw, see `engine/runconfig.py`), `name` (optional), `x_label` (optional, else the
    `Observable` node's `label`).
- `edges` — `[fromId, toId]` pairs. Illegal per `fce_web.graph.VALID_CONNECTIONS`, cyclic,
  disconnected, missing a `Histogram` terminal, or spanning branches whose `Multiplicity`
  chains disagree (the digest formula has one `mult_cuts` for the whole run, not one per
  branch) are all rejected with a `fce_web.graph.GraphError` naming the offending node or
  edge.

A rejected graph returns `400` with `{"error": "<student-legible message>"}`. A legal graph
that the loader itself rejects (a translation bug, not a student mistake) is a `500` — that
path should not be reachable from valid input.

### `POST /api/run` response

`200`, immediately — before the run finishes. It executes on a background thread, owned by
`fce_web.jobs.JobRegistry` (task B-021); nothing about this response implies completion.

```json
{"runId": "3f9a...", "cacheHit": false}
```

- `runId` — opaque string, the id `GET /api/run/{id}/result` (and B-022's
  `GET /api/run/{id}/events`) reads back.
- `cacheHit` — `true` when this exact config (same graph, resolved through
  `fce_web.graph.build_run_config`) already finished under an earlier run id in this
  registry. A cache-hit run is already `"done"` the instant this response is sent — the UI may
  say "recognised these cuts — reusing your earlier run" without polling first.

### `GET /api/run/{id}/result`

`404` with `{"error": "..."}` for an unknown `id` — including an id from a *different*
`JobRegistry` (each app owns its own; nothing is shared, `.claude/shared/CLAUDE.md` §6).

Otherwise `200` (or `202` while still running) with a `status` field:

| `status` | HTTP | Body |
|---|---|---|
| `"running"` | `202` | `{"status": "running"}` — poll again. |
| `"done"` | `200` | `{"status": "done", "cacheHit": bool, ...histogram payload}` — the [histogram payload](#histogram-payload) below, spread alongside `status`/`cacheHit`. |
| `"error"` | `200` | `{"status": "error", "error": "<student-legible message>"}` — e.g. no dataset found for this mission's detector/energy. Not a `4xx`: the request was fine, the run itself didn't produce a result. |
| `"cancelled"` | `200` | `{"status": "cancelled", "error": "<reason>"}` — `RunContext.cancel` (a `threading.Event`, one basket of granularity) was set before or during the run. |

Cancellation itself has no endpoint yet in this task — B-021 reuses the existing
`RunContext.cancel` seam (`fce_web.runs.RunContext`) rather than adding a new one; a future
task wires a `POST` to set it on a running job's context.

**Progress.** See "Run progress event" below for the wire format read off
`fce_web.jobs.Job.events`.

---

## Fixed contracts

### Naming convention

**Every field in these three payloads is camelCase**, matching
`docs/design-explorations/payload.json`: `xLabel`, `lumiUnc`, `weightsSquared`, `totalRaw`,
`efficiencyPct`, `significanceZ`. Do not introduce snake_case anywhere in this document or
in a producer that emits it — the frontend consumes the field names verbatim.

**A note on file citations below.** Every `engine/<file>.py:<line>` citation in this document
refers to the **reference repository `kskovpen/fce`**, not to this repository. Only
`engine/__init__.py` and `engine/systematics.py` are vendored into `src/fce_web/engine/` so
far — grepping this repo for `engine/plotter.py` or `engine/fitter.py` will find nothing.

### Histogram payload

There is no chart renderer in `src/fce_web/static/js/` yet — `static/js/` currently holds
only `app.js`. The payload shape below is the one the interactive chart will render once that
renderer exists, and it is the shape `docs/design-explorations/plot.js` (a design exploration,
not production code) already renders today. Changing this shape is a coordinated change
across both roles. This is the full, current shape — `meta`, `lumiUnc` and `systSources` were
added for the systematics band and are not optional extras; the worked instance is
`docs/design-explorations/payload.json` (41 edges / 40 bins, three samples `X1`, `X2`, `X3`,
two cutflow stages).

```jsonc
{
  "meta": {
    "mission": "M-1",
    "detector": "IDEA",
    "energy": "91 GeV",
    "xLabel": "m(l₁, l₂) [GeV]",
    "processNames": { "X1": "X1: Z→2ℓ", "X2": "X2: Z→2q", "X3": "X3: Z→2ℓ+γ" }
  },
  "edges": [80.0, 82.0, 84.0],        // bin edges, length = nbins + 1
  "lumiUnc": 0.025,                    // flat luminosity uncertainty, fraction (not per-bin)
  "systSources": ["jec", "lep", "btag"],
  "samples": [                         // stacked, in draw order
    {
      "name": "X1",
      "counts": [12.4, 30.1],          // weighted, length = nbins
      "weightsSquared": [4.1, 9.8],    // nullable -- see semantics below
      "systUp": {                      // one key per systSources entry, up-only
        "jec": [12.6, 30.5],
        "lep": [12.5, 30.3],
        "btag": [12.4, 30.4]
      }
    }
  ],
  "data": [15, 33]                     // pseudo-data, unweighted counts
}
```

#### Field reference

<!-- schema-table:start -->
| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `meta` | object | no | Run metadata describing what was plotted. |
| `meta.mission` | string | no | Mission id the run belongs to, e.g. `"M-1"`. |
| `meta.detector` | string | no | Detector design used, `"IDEA"` or `"CLD"`. |
| `meta.energy` | string | no | Centre-of-mass energy label, e.g. `"91 GeV"`. |
| `meta.xLabel` | string | no | Axis label for the histogrammed observable, may contain unicode (subscripts, Greek letters). |
| `meta.processNames` | object | no | Maps each sample name (`"X1"`, …) to its display label. Keys are a subset of `samples[].name`. |
| `edges` | number[] | no | Bin edges, length = `nbins + 1`. |
| `lumiUnc` | number | no | Flat, per-run luminosity uncertainty as a fraction (e.g. `0.025` = 2.5%). Broadcast identically to every bin — it is **not** a per-bin shape. |
| `systSources` | string[] | no | The systematic sources actually contributing **to this run** — not a fixed tuple. See semantics 2. |
| `samples` | object[] | no | Stacked MC samples, in draw order. |
| `samples[].name` | string | no | Sample id, e.g. `"X1"`. |
| `samples[].counts` | number[] | no | Weighted bin contents, length = `nbins`. Floats, since each simulated event carries a weight. |
| `samples[].weightsSquared` | number[] | **yes** | Sum of squared weights per bin, for statistical error bars. See semantics 8 — no producer exists today; nullable until one does. |
| `samples[].systUp` | object | no | Up-only systematic variation histograms, one key per source in `systSources`, present only for the sources this sample actually produced a template for. See semantics 1 and 2. |
| `samples[].systUp.jec` | number[] | no (when the key is present) | Up-varied bin contents for the `jec` source, same length as `counts`. Present only when this sample's reference run produced an `h_jec_up` template — see semantics 1 and 2. |
| `samples[].systUp.lep` | number[] | no (when the key is present) | Up-varied bin contents for the `lep` source. Same presence rule as `systUp.jec`. |
| `samples[].systUp.btag` | number[] | no (when the key is present) | Up-varied bin contents for the `btag` source. Same presence rule as `systUp.jec`. |
| `data` | number[] | no | Pseudo-data, raw (unweighted) counts, length = `nbins`. |
<!-- schema-table:end -->

`counts` are weighted — each simulated event carries a weight so the simulation reproduces
the real expected rate — so they are floats, not integers. `data` is a raw count and is an
integer. The frontend draws stacked backgrounds from `samples` and overlays `data` as
points with `sqrt(n)` error bars, which is the convention the physics community uses.

#### Semantics that are not obvious from the field list

1. **The systematics band is up-only, sums over samples before it takes a fraction, and
   includes a source from whichever samples happen to carry it — it does not require every
   sample to report every source.** There is no down variation anywhere in the reference
   engine. The band is built by summing `systUp` **over MC samples first**, then taking the
   per-bin fractional delta against the *summed* nominal, then adding `lumiUnc` in quadrature,
   then mirroring around the summed nominal. Verbatim, from `engine/plotter.py:107-118`:

   ```
   frac = sqrt( lumiUnc² + Σ_src ( (Σ_s systUp[s][src] − Σ_s counts[s]) / Σ_s counts[s] )² )
   band = Σ_s counts[s] × frac          # drawn as stack ± band, symmetric
   ```

   Here `Σ_s systUp[s][src]` sums **only over the samples that carry a `systUp[src]` key for
   that source** — a sample missing it simply contributes nothing to that sum, the way
   `engine/plotter.py:58-67` accumulates `mc_up[src]` only from samples where
   `f"h_{src}_up"` exists in that sample's output file. It does **not** fall back to that
   sample's nominal count, and the source is skipped entirely only if **no** sample carries
   it at all (`mc_up[src] is None`, `plotter.py:112`). This is the **opposite rule** from the
   fit's `histosys` modifiers (semantics 2 below), which drop a source if *any* contributing
   sample lacks it — the band and the fit read partial systematics coverage differently, and
   a re-implementation that borrows the fit's all-or-nothing rule for the band computes a
   different number than the reference plot whenever samples carry uneven source coverage.
   In `docs/design-explorations/payload.json` every sample happens to carry every source, so
   this divergence is invisible in that one payload — it is not invisible in general.

   `frac` is forced to `0` in bins where the summed stack (`Σ_s counts[s]`) is `≤ 0`. The
   `lumiUnc` term is a flat constant broadcast to every bin, not a spatially varying shape.
   A consumer that averages the per-sample variations, or takes the delta *before* summing
   over samples, computes a different band than the reference plot.

2. **`systSources` lists the sources used in *this* run, not a fixed `["jec","lep","btag"]`
   tuple.** The fit drops a source entirely from its `histosys` modifiers if *any*
   contributing sample lacks its `h_{src}_up` key (`engine/fitter.py:35,58-62,67-75,84-86`) —
   contrast semantics 1, where the band keeps a source alive from whichever samples carry it.
   Consumers must iterate `systSources` rather than hard-coding the three names — a future
   run may carry fewer, or (if the engine grows more sources) more.

3. **`significanceZ` is capped at `10.0`** (`_SIG_CAP = 10.0` at `engine/fitter.py:13`),
   applied identically on all three fit code paths (see `fit.mu` below). A UI reading
   exactly `10.0` must not present it as a measured value — it is a ceiling, not a result.

### Cutflow payload

```jsonc
{
  "cutflow": {
    "stages": ["Total", "≥ 2 leptons"],
    "samples": ["X1", "X2", "X3"],
    "counts": {
      "Total": { "X1": 20200, "X2": 215300, "X3": 4500 },
      "≥ 2 leptons": { "X1": 14000, "X2": 800, "X3": 3620 }
    },
    "totalRaw": 240000,
    "efficiencyPct": [100.0, 7.7]
  }
}
```

<!-- schema-table:start -->
| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `cutflow.stages` | string[] | no | Ordered stage labels. Stage 0 is always the literal string `"Total"`. |
| `cutflow.samples` | string[] | no | MC sample names included in the cutflow (pseudo-data `data` is excluded from this list). |
| `cutflow.counts` | object | no | **Nested** `{stage: {sample: int}}`, not a flat array. Every stage in `stages` and every sample in `samples` has an entry. |
| `cutflow.totalRaw` | integer | no | Raw event count summed over **all active samples including pseudo-data**, used as the efficiency denominator. |
| `cutflow.efficiencyPct` | number[] | no | Cumulative efficiency against stage 0, one entry per stage, `efficiencyPct[0] == 100.0`. See semantics 6. |
<!-- schema-table:end -->

#### Semantics that are not obvious from the field list

4. **Cutflow counts are raw and unweighted, and stage 0 comes from a structurally
   different source than every later stage.** Every entry in `counts` is
   `len(d["weight"])` — a raw, unweighted event count, never `sum(...)` of weights. Stage 0
   (`"Total"`) is a **raw ROOT header scan** (`num_entries`,
   `engine/analytical_loop.py:234-246`); every stage after it is read from npz selection
   cache lengths (`engine/cutflow_plotter.py:47`). A consumer must not assume one uniform
   producer feeds the whole `stages` array — stage 0 can be present even when no selection
   cache exists yet.

5. **Stage names are the selection node's label, not the selection expression.** Each
   non-`"Total"` stage name is `node_name`, falling back to the literal string
   `"Selection"` when the node has none (`engine/cutflow_plotter.py:40`) — it is never the
   cut's boolean expression string (e.g. `"nlep >= 2"`). Do not attempt to parse a stage
   name as an expression.

6. **`efficiencyPct` is cumulative against stage 0 and MC-only in composition, but its
   denominator is a mixed MC+pseudo-data total — a deliberate divergence.**
   `engine/cutflow_plotter.py:70-83` divides the *passing* count (summed over **all active
   samples including pseudo-data**) by `total_raw_all` (also including pseudo-data) to get
   each stage's efficiency — while the stacked-bar *composition* the same function draws is
   computed from **MC-only** samples (`:64-68`). Two sample sets and two formulas live in
   the one plot. This is a deliberate divergence, ruled by the user: mixing pseudo-data into
   the efficiency denominator alongside MC is arithmetically meaningless (pseudo-data has no
   well-defined "before cuts" count in the sense a single MC process does), but it is what
   the reference plot does, and this contract documents the reference's actual behaviour
   rather than a corrected one. A future task may split this into an MC-only efficiency and
   a separate pseudo-data acceptance; until then, `efficiencyPct` here is the
   mixed-denominator number, `cutflow.totalRaw` is the same mixed denominator, and
   `cutflow.counts` is MC-only.

### Fit payload

```jsonc
{
  "fit": {
    "mu": 1.02,                        // nullable -- see semantics 7
    "muErr": 0.15,
    "significanceZ": 5.8,              // nullable -- see semantics 7
    "method": "histfactory",
    "thresholds": { "evidence": 3.0, "discovery": 5.0 }
  }
}
```

<!-- schema-table:start -->
| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `fit.mu` | number | **yes** | Signal strength: 1.0 means exactly as predicted, 0 means absent. `null` when `run_fit` found no usable result — see semantics 7. Its *statistical meaning* when non-null depends on `fit.method`. |
| `fit.muErr` | number | **yes** | Uncertainty on `mu`. See semantics 8 — no producer exists today. |
| `fit.significanceZ` | number | **yes** | Standard deviations above background-only, capped at `10.0` (semantics 3). `null` under the same conditions as `fit.mu` — see semantics 7. |
| `fit.method` | string | **yes** | **Added by this contract, not present in `docs/design-explorations/payload.json` today** (a backlog item is filed to add it to the design payload). One of `"histfactory"`, `"counting-ratio"`, `"counting-fallback"` — see semantics 7. `null` until a producer sets it, and also `null` (along with `mu` and `significanceZ`) when there is no fit result at all. |
| `fit.thresholds` | object | no | The two significance thresholds the UI compares `significanceZ` against. |
| `fit.thresholds.evidence` | number | no | 3σ — conventionally "evidence". `fit.thresholds.evidence < fit.thresholds.discovery` always. |
| `fit.thresholds.discovery` | number | no | 5σ — conventionally "discovery". |
<!-- schema-table:end -->

#### Semantics that are not obvious from the field list

7. **`mu` and `significanceZ` silently switch statistical meaning depending on which of
   three code paths ran, and can both be absent entirely.** The reference engine's
   `run_fit` has three outcomes behind the same two field names, plus a family of early
   returns that produce neither:

   - **(a) `histfactory`** — a full pyhf HistFactory MLE fit (`engine/fitter.py`, the main
     path through `pyhf.infer.mle.fit`). `mu` is a profile-likelihood estimate;
     `significanceZ` comes from the fitted `p0`.
   - **(b) `counting-ratio`** — a plain counting ratio `mu = n_tot / s_tot` used when there
     is no background sample at all (`fitter.py:89-98`); `significanceZ` is the
     background-free approximation `sqrt(2*n)` (`_counting_significance`).
   - **(c) `counting-fallback`** — `mu = (n_sum - b_sum) / s_sum` and `significanceZ = s/√b`,
     used when a bare `except Exception` swallows a pyhf failure (`fitter.py:194-203`).

   `fit.method` is **added by this contract** to name which path ran; a consumer that
   treats all three `mu` values as "the pyhf fit result" is silently wrong for two of the
   three. It is absent from `docs/design-explorations/payload.json`, which this contract
   does not edit — it is specified **nullable**, on the same footing as `muErr`, until a
   producer sets it.

   Separately, `run_fit` returns the bare tuple `(None, None)` on **five** early-exit paths
   (`fitter.py:25,80,95,106,120` — no configured target, both signal and background empty
   after masking, signal sum `<= 0`, and two more structurally similar guards). This contract
   resolves that by specifying `fit.mu` and `fit.significanceZ` **nullable**, mirroring
   `muErr` and `method`, rather than requiring a producer to omit the `fit` key entirely when
   there is no result — a consumer already has to branch on `fit.method` being `null`, and
   folding "no result" into the same nullable pair keeps `fit` a single, always-present key
   the frontend can destructure without a second existence check. A producer must not invent
   a placeholder number (e.g. `0.0`) for either field when `run_fit` returned `None` — `null`
   is the only correct encoding of "no fit ran".

8. **`weightsSquared` and `fit.muErr` are nullable because neither has a producer today —
   this is a documentation decision, not an oversight left for later.** The reference
   builds its histograms with `boost_histogram`'s default `Double()` storage, so no
   sum-of-squared weights is tracked or persisted anywhere; a producer would need
   `storage=bh.storage.Weight()` on the histogram axis. `run_fit` returns a bare
   `(mu, sig)` tuple with no uncertainty on `mu`; a producer would need a Hessian or
   covariance extraction from `pyhf.infer.mle.fit`, which the reference never performs.
   `docs/design-explorations/verify.py:993-1001` already records that `weightsSquared` is
   unconsumed by the rendered error bars today. **No sumw2 storage and no engine change is
   made by this task** — ruled by the user; both fields stay `null` until a later task adds
   the producer.

### Run progress event

`GET /api/run/{id}/events` -- task B-022. `404` with `{"error": "..."}` for an unknown `id`,
returned before any stream opens (never an open connection that emits nothing). Otherwise
`200 text/event-stream`, one SSE frame per item read off `fce_web.jobs.Job.events`
(`data: <json>\n\n`), terminated by exactly one terminal frame. It never carries histogram,
cutflow or fit data -- that is `GET /api/run/{id}/result`'s job; this stream is progress only.

Each frame's JSON body is one of:

```jsonc
{"type": "progress", "value": 0.42, "runId": "3f9a..."}                          // 0..1
{"type": "log", "message": "reading X1...", "runId": "3f9a..."}
{"type": "phase", "phase": "selecting", "runId": "3f9a..."}
{"type": "node", "status": "active", "nids": [3, 5], "runId": "3f9a..."}         // or "completed"
{"type": "done", "status": "done", "runId": "3f9a..."}                           // "done" | "error" | "cancelled"
```

`done` is always the last frame and appears exactly once per stream; the connection closes
immediately after it. A cache-hit run's stream is a single `done` frame, and so is a second
stream (or a reconnect) opened against a run that has already finished -- neither produces a
synthesised progress sweep for a result that was already computed.

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `type` | string | no | One of `"progress"`, `"log"`, `"phase"`, `"node"`, `"done"`. |
| `runId` | string | no | The run this frame belongs to -- lets a caller holding more than one open stream tell them apart. |
| `value` | number | no (when `type` is `"progress"`) | Fraction complete, `0.0`-`1.0`. |
| `message` | string | no (when `type` is `"log"`) | A student-legible status line. |
| `phase` | string | no (when `type` is `"phase"`) | The run's current phase label. |
| `status` | string | no (when `type` is `"node"` or `"done"`) | `"active"`/`"completed"` for a `node` frame, `"done"`/`"error"`/`"cancelled"` for the terminal `done` frame. |
| `nids` | integer[] | no (when `type` is `"node"`) | Graph node ids whose status just changed. |

### Mission objective result

_To be defined in M5._
