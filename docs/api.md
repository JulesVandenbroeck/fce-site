# API contracts

The contract between the back-end and front-end roles. **Owned by the back-end coder.**

The front-end codes against this file, not against the implementation. Backend: update it
*before* the frontend consumes an endpoint, and name the change in your completion report
so the orchestrator can raise the matching frontend task.

Status: **stub.** Populated during M3 (first vertical slice) and M5 (missions and
progression).

---

## Conventions

- JSON in, JSON out for anything JavaScript touches. HTML fragments for HTMX targets.
- Every input validated at the boundary with a Pydantic model.
- Errors return a proper status code and a JSON body with a message that is safe to show a
  student. Never a traceback.
- Field names here are the field names the frontend will use. Choose once, well.

---

## Endpoints

_To be defined in M3._

Expected shape, subject to design during the milestone:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/run` | Submit an analysis recipe; returns a run id |
| `GET` | `/api/run/{id}/events` | SSE stream: progress, phase, completion |
| `GET` | `/api/run/{id}/result` | Histogram data, cutflow, fit results |
| `GET` | `/api/run/{id}/plot.png` | `mplhep` PNG export |

---

## Fixed contracts

### Histogram payload

Fixed in `.claude/shared/CLAUDE.md`. The chart module in `static/js/chart.js` renders
exactly this. Changing it is a coordinated change across both roles.

```jsonc
{
  "edges": [80.0, 82.0, 84.0],        // bin edges, length = nbins + 1
  "samples": [                         // stacked, in draw order
    {
      "name": "X1",
      "counts": [12.4, 30.1],          // weighted, length = nbins
      "weightsSquared": [4.1, 9.8]     // for statistical error bars
    }
  ],
  "data": [15, 33]                     // pseudo-data, unweighted counts
}
```

`counts` are weighted — each simulated event carries a weight so the simulation reproduces
the real expected rate — so they are floats, not integers. `data` is a raw count and is an
integer. The frontend draws stacked backgrounds from `samples` and overlays `data` as
points with `sqrt(n)` error bars, which is the convention the physics community uses.

### Run progress event

_To be defined in M3._

### Mission objective result

_To be defined in M5._
