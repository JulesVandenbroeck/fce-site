# The physics truth — what is in the data

> ## ⚠ This is the answer key.
>
> Every mission in this game asks a student to *discover* something. This file is the thing
> they are meant to discover, written down, so that the person authoring the mission knows
> what the right answer is.
>
> **Nothing in this file is student-facing copy.** Not the process names, not the cuts, not
> the observables. It must not be pasted into `content/`, into a mission brief, into a hint,
> or into an error message. A mission that hands the student the cut has no mission left.
>
> What it *is* for: setting an objective that is actually reachable, writing a hint that
> points without telling, and knowing whether a student's analysis is right or merely lucky.

**Provenance.** `.claude/bin/truth.pdf` — 19 slides from the author of the reference desktop
tool (`kskovpen/fce`), supplied by the user on 2026-09-22. Every row below cites the slide it
came from. **That PDF is deliberately not committed**: it is 4.1 MB and the repo does not carry
it. So this document has to stand on its own, and the slide citations are checkable only on a
machine that holds the file. If you need it and do not have it, ask the user.

**Scope: 91 GeV only** — the energy V1 ships. The PDF also catalogues 160, 240 and 365 GeV; see
*The `X<n>` ids are per-energy* below for the one thing you need to know about them.

---

## 1. The five Standard-Model samples

These are the simulated backgrounds. Each row is the analysis that isolates that process — the
reference tool's three boxes: a `skim`, a `passevent` cut, and an `observable`.

**The expressions in this table are the reference tool's language, not this app's.** They will
not run here as written. §3 translates them.

| Sample | Process | `skim` | `passevent` | `observable` | Binning | Slide |
|---|---|---|---|---|---|---|
| `X1` | e⁺e⁻ → ℓ⁺ℓ⁻ | `nelectrons >= 2 or nmuons >= 2` | `njets >= 0` | `mll` — `(electrons[0].p4+electrons[1].p4).m`, else the muon pair | 25 bins, 86–95 | 1 |
| `X2` | e⁺e⁻ → qq̄ | `njets >= 2` | `nphotons >= 0` | `(jets[0].p4+jets[1].p4).m` | 30 bins, 0–150 | 2 |
| `X3` | e⁺e⁻ → qq̄γ **and** e⁺e⁻ → ℓ⁺ℓ⁻γ | `nelectrons >= 2 or nmuons >= 2` | `nphotons >= 1` | `dR` — `leptons[0].p4.deltaR(photons[0].p4)` | 30 bins, 0–5 | 3 |
| `X4` | **e⁺e⁻ → νν̄γ** | `nphotons >= 1` | `nelectrons == 0 and nmuons == 0 and njets == 0 and MET.pt > 10` | `MET.pt` | 25 bins, 0–50 | 4 |
| `X5` | **e⁺e⁻ → γγ** | `nphotons >= 2` | `nelectrons == 0 and nmuons == 0 and njets == 0` | `(photons[0].p4+photons[1].p4).m` | 25 bins, 0–100 | 5 |

### What each one is for, pedagogically

- **`X1`** is the signal for missions 1 and 2. Two leptons, invariant mass at the Z mass.
- **`X2`** is the huge, trivially-removed background — the Z decays to quarks far more often
  than to leptons, so it dominates the raw count and then vanishes the moment a student asks
  for two leptons. The satisfying first cut.
- **`X3` is the best teaching material in the dataset.** A real Z that does not look like one:
  the photon carried energy away, so the dilepton mass lands *below* 91 GeV and smears the left
  side of the peak. Add the photon's four-vector back and it falls into place.
  **Correction to the older description:** `X3` is **not only** the dilepton channel. Slide 3
  captions it as both `qq̄γ` and `ℓ⁺ℓ⁻γ`. The hadronic half exists too.
- **`X4`** is the invisible one — two neutrinos and a photon. Nothing in the detector but a
  photon and a momentum imbalance. It is the reason `MET` has to be taught at all.
- **`X5`** is the cleanest signature in the set. The diphoton mass piles into a single bin at
  ≈ 91 GeV, because at the Z pole √s *is* the diphoton mass. Slide 5 shows it as one purple
  spike against a broad background.

---

## 2. The new physics hidden in `data`

**This is the payoff of the whole game, and it is the part that must never leak.**

Neither process below is in `X1`–`X5`. Both show up as an excess in the pseudo-data that no
amount of stacked simulation accounts for. The reference tool has a `Target:` selector
(`None` / `New physics`) that loads the signal template on top of the stack; slide 7 is taken
with `Target: New physics`, **slide 6 with `Target: None`** — meaning the lepton-flavour
violation is visible as an unexplained bump before any signal model is loaded at all. That is
exactly the experience a student should have.

### NP-1 — charged lepton flavour violation: e⁺e⁻ → Z → e⁺μ⁻  *(slide 6)*

| | |
|---|---|
| `skim` | `nelectrons == 1 and nmuons == 1` |
| `passevent` | `njets >= 0` |
| `observable` | `(electrons[0].p4+muons[0].p4).m` |
| Binning | 40 bins, 0–150 |

**Why it is impossible in the Standard Model:** a Z decays to a *same*-flavour lepton pair —
ee or μμ, never eμ. Lepton flavour is conserved. An electron and a muon whose invariant mass is
the Z mass cannot come from a Z, and yet there they are.

**What it looks like:** on slide 6, roughly **70 data events sit in the 90 GeV bin** over an
essentially empty prediction. The SM stack in that channel is a low, broad smear from 0 to
~70 GeV (`X2` and `X1` faking an eμ pair); the data follows it, and then there is a spike at
the Z mass with nothing underneath it.

**This is the easier of the two.** The cut is one line, and the observable is invariant mass —
the same gesture missions 1 and 2 already taught, pointed somewhere new.

### NP-2 — a long-lived heavy neutrino: e⁺e⁻ → Nν, N → ℓ qᵢq̄ⱼ  *(slide 7)*

| | |
|---|---|
| `skim` | `nelectrons >= 1 or nmuons >= 1` |
| `passevent` | `njets >= 0` |
| `observable` | `disp = abs(leptons[0].d0signif)` |
| Binning | 30 bins, **300–2000** |
| Mass | **m(N) = 70 GeV** |

**Why it is impossible in the Standard Model:** this one is about *geometry*, not mass. Standard
Model leptons are produced at the collision point. This heavy neutrino is long-lived — it travels
a measurable distance before decaying to a lepton and two quarks, so its lepton points back to
somewhere that is not the beam spot. Impact-parameter significance is how you measure that.

**What it looks like:** on slide 7 the SM stack (essentially all `X2`) dies out by `d0signif`
≈ 750, and the data keeps going, roughly flat, all the way to 2000. It is not a bump. It is a
tail in a region where the prediction has simply ended.

**This is the harder of the two** — a new concept, a new axis, and a quantity no other mission
touches.

---

## 3. Translating these cuts into *this* app

**Do not transcribe a slide into a mission.** The PDF's expressions are the reference desktop
tool's language. This app's evaluator is `src/fce_web/safe_eval.py`, whose vocabulary is
`EVENT_NAMES` (`safe_eval.py:86-90`) and `ALLOWED_ATTRS` (`safe_eval.py:128-131`). The names
differ, and a verbatim copy is rejected at submit with a 400.

| Slide expression | This app | Note |
|---|---|---|
| `nelectrons` / `nmuons` / `nphotons` | `nel` / `nmu` / `nphot` | renamed |
| `njets` | `njets` | unchanged |
| `MET.pt` | `met.pt` | lower case |
| `(electrons[0].p4+electrons[1].p4).m` | `(l1.p4 + l2.p4).mass` | `.m` → `.mass`; no indexing |
| `(jets[0].p4+jets[1].p4).m` | `(j1.p4 + j2.p4).mass` | " |
| `(photons[0].p4+photons[1].p4).m` | `(ph1.p4 + ph2.p4).mass` | " |
| `leptons[0].p4.deltaR(photons[0].p4)` | `l1.p4.deltaR(ph1.p4)` | `deltaR` is allowed |
| `abs(leptons[0].d0signif)` | `abs(l1.d0)` | **see the `d0` hazard below** |

So the two new-physics analyses, in this app's language:

```
NP-1  selection:   nel == 1 and nmu == 1
      observable:  (l1.p4 + l2.p4).mass

NP-2  selection:   nel >= 1 or nmu >= 1
      observable:  abs(l1.d0)
```

**Both are buildable with the vocabulary that exists today.** `abs` is in `SAFE_BUILTINS`
(`safe_eval.py:102`) and `CALLABLE_NAMES` (`:118`); `d0` is in `ALLOWED_ATTRS`. No backend
change is needed to author either mission.

### The flavour subtlety the rename hides

The slides branch explicitly on flavour — `if nelectrons >= 2: use electrons, else: use muons`.
This app has no such branch: `l1` and `l2` are the two **leading leptons regardless of flavour**.
After an `nel >= 2 or nmu >= 2` skim the two definitions usually coincide, but they are not the
same definition, and in a mixed-flavour event they differ. Know which one your objective assumes.

### ⚠ The `d0` hazard

**`.d0` in this app is not an impact parameter. It is an impact-parameter *significance*.**

Traced end to end: the ROOT branch is `d0signif` (`engine/analytical_loop.py:159`), read as
`electron_d0signif` / `muon_d0signif` (`engine/path_filter.py:622,630`), then **renamed to the
key `d0`** (`path_filter.py:700,710`) before `_make_lepton` stores it as `d0=`
(`path_filter.py:204`). Nothing downstream records that the rename happened.

This also explains slide 7's otherwise baffling 300–2000 axis: absurd for a distance in
millimetres, entirely ordinary for a significance (a ratio, so dimensionless).

**Consequences:**

- Any label, hint or axis title calling `d0` a distance — "impact parameter, mm" — is **wrong**,
  and it would be wrong in copy a student reads.
- `static/js/expr.js` gives every property a unit and a histogram range preset, `d0` included.
  **Check what it says before authoring M-4.** If it presents `d0` as a length, that is a live
  defect, not a future task.

---

## 4. What is still unknown

This document closes `X4` and `X5`. It does not make the dataset fully known.

### `X6` exists and is not identified

Upstream has **seven files, not six**: `X1` 158M, `X2` 92M, `X3` 51M, `X4` 19M, **`X6` 5.9M**,
`X5` 5.3M, `data` 4.8M — recorded in `.claude/handoff/archive/session-2026-09-07-b.md:43-46`
and `.claude/tasks/archive/backend.md:2005-2012`. `tests/fixtures/golden/zpeak-dilepton.json`
already carries `X6` bins, consumed by `tests/test_engine_parity.py`.

**The PDF covers `X1`–`X5` only.** `X6` is not in it. It blocks nothing today — the committed
fixture holds `X1`, `X2`, `X3` and `data` — but it is a real sample and the sample tables should
stop pretending there are five.

### No significance, no cross sections, no luminosity

Every slide's **"Significance (observed)"** and **"Significance (expected)"** panel is **blank**.
The PDF says what the processes are and how to isolate them; it says nothing about how big an
excess is or how many σ a student can reach.

So **the missions' objective thresholds still have to be measured, not guessed** — run the real
analysis against the real datasets and read the number off. `docs/design-brief.md` §8 already
carries this as an open item and this document does not close it.

### The `X<n>` ids are per-energy, not global process names

The PDF's later slides (out of V1 scope, not reproduced here) catalogue 160, 240 and 365 GeV —
and the same ids mean **completely different processes** at each. `X1` is Z → ℓℓ at 91 GeV and
tt̄ at 365 GeV. `X4` is νν̄γ here and Bhabha scattering at 160 GeV.

Never write code, copy or a mission that assumes `X1` means Z → ℓℓ. It means that *at 91 GeV*,
which is the only energy V1 ships — but the assumption will break the moment a second energy
is added.

---

## 5. Where this lands in the missions

| Mission | Signal | Sample / process | Buildable today? |
|---|---|---|---|
| **M-1** First Light | `X1` | Z → ℓℓ, the peak | yes |
| **M-2** Cleaning the Signal | `X1` vs `X2`, `X3` | the purity trade | yes |
| **M-3** The Unknown | **NP-1** | Z → eμ, the forbidden bump | yes |
| **M-4** *(name TBD)* | **NP-2** | the displaced tail | yes |

> **Naming, and it matters:** `M-1` … `M-4` with a hyphen are **missions**. `M1` … `M6` without
> one are **milestones** (`.claude/orchestrator/CLAUDE.md` §8). They are different things and
> they now overlap numerically. Always write the hyphen for a mission.

**The old assumption that mission 3's signal must be `X4` or `X5` was wrong.** `X4` and `X5` are
ordinary Standard-Model backgrounds. The new physics is a separate signal template, and there
are two of them — which is why there are now four missions rather than three. Ruled by the user,
2026-09-22.
