# FCE-site — design brief

The product concept. Every role reads this before doing user-facing work. When the brief
and an implementation instinct disagree, the brief wins; when the brief is silent, the
orchestrator asks rather than guessing.

---

## 1. What this is

A browser-based learning game in which high-school students do real particle-physics data
analysis on simulated Future Circular Collider (FCC-ee) data, and are scored on what they
find.

The physics is genuine. Students read real simulated collision events, apply real
selections, fill real histograms, and get real fitted significances. The game framing sits
*around* that, never *instead of* it. A student who finishes should have done, in miniature,
what a physicist actually does — and should be able to explain what an invariant mass peak
is and why 5σ matters.

**Audience.** 15–18, most with no physics beyond school. Assume the word "luminosity" is
new. Assume they click things in the wrong order. Assume roughly a single class period per
sitting.

**Setting.** A teacher runs one instance; the class connects over the local network. It
must also run on one laptop for one person. Possibly no internet in the room.

**Predecessor.** `kskovpen/fce` — a working Dear PyGui desktop app with correct physics, a
static tutorial, no progression and no persistence. We reuse its engine and replace
everything above it.

---

## 2. The core loop

```
read the mission brief
  → assemble an analysis from recipe cards
  → run it against real simulated data
  → watch the histogram fill
  → compare the result against the objective
  → miss it, and adjust; meet it, and the page gets stamped
```

Two properties this loop must have:

**Running must feel fast, and never silent.** A run takes seconds to minutes. Progress
streams live — phase label and bar — because silence reads as broken to a teenager. The
content-addressed cache means repeating an analysis returns almost instantly, and the UI
should say so rather than hiding it: *"recognised these cuts — reusing your earlier run."*

**Failing must be cheap and instructive.** Missing the objective is the normal case, not an
error state. The response is a margin note pointing at what the numbers suggest, never a
red banner. Students should feel free to try a cut just to see what happens.

---

## 3. Missions

Progression is an ordered campaign. Each mission declares an objective checked against real
engine output; meeting it unlocks the next. A free sandbox unlocks after the last one.

Missions are **data**, not code: `content/missions/*.yaml`, validated at startup. Adding or
rewriting a mission must never require touching Python. The user authors these.

A mission declares: id, order, title, brief, dataset (energy + detector), which card types
are available, the objective and how to check it, hints, and success copy.

**Card gating carries the teaching.** Mission 1 exposes only the cards it needs. Later
missions unlock more. Students are never shown a wall of controls they have no reason to
understand yet.

### The three V1 missions — 91 GeV, the Z pole

An arc of *see → clean → discover*.

**M-1 · First Light.** Plot the invariant mass of the two leading leptons and find the
peak. The student assembles the minimal pipeline — data, require two leptons, observable,
histogram — and reads a number off their own plot. Teaches the single most important idea
in the app: add two four-vectors, take the mass, and a peak appears at the mass of whatever
they came from. **Objective:** produce the histogram and identify the peak position within
tolerance of the Z mass.

**M-2 · Cleaning the Signal.** Same plot, now with everything else in it. Introduces
selections and the cutflow. Two backgrounds, two different lessons: `X2` (hadronic Z) is
huge and trivially removed by requiring two leptons — the satisfying first cut. `X3`
(Z + photon) is the real teaching moment, a genuine Z whose dilepton mass is measured too
low because a photon took energy away. **Objective:** apply cuts that push signal purity
past a threshold while retaining a stated fraction of signal. Teaches the real trade —
every cut that removes background removes some signal too — and, for students who get
there, that the better move is sometimes to *fix* the measurement rather than cut.

**M-3 · The Unknown.** A search. One signal sample is hiding in the data; the student must
find cuts that expose it and run a fit. **Objective:** reach significance Z above 3σ
(evidence), with 5σ as the stretch goal. Teaches μ, Z, and what "discovery" actually means.
This is the payoff the other two missions exist to set up. *Blocked: the signal must be
`X4` or `X5`, and neither is identified yet.*

### What the samples are

Decided 2026-08-15. `config/samples.json` names five simulated processes per energy plus
`data`; the reference repo does not document them. Three are now known:

| Sample | Process | Role in the missions |
|---|---|---|
| `X1` | Z → two leptons | **The signal for missions 1 and 2.** Two leptons, invariant mass at ≈ 91 GeV. This is the peak students are looking for. |
| `X2` | Z → two quarks | Two jets, no leptons. The Z decays hadronically far more often than leptonically, so this dominates the raw event count — and then a "require two leptons" cut removes essentially all of it. A satisfying first cut: enormous effect, obvious reason. |
| `X3` | Z → two leptons + a photon | A real Z that does not look like one. The photon carried energy away, so the *two-lepton* mass lands **below** 91 GeV, smearing the left side of the peak. |
| `X4` | *unknown* | — |
| `X5` | *unknown* | — |

**`X3` is the best teaching material in the dataset and must not be framed as junk.** It is
a correct Z decay that a naive analysis mismeasures. The intended arc: a student sees a
low-mass tail, learns why it is there, and either cuts it away (crude, loses real signal) or
adds the photon's four-vector back and watches it fall into the peak (correct). That is a
genuine physics insight reachable by a 16-year-old, and it is exactly what mission 2 should
be built around.

> **Still open — needs the user.** `X4` and `X5` are undocumented. **Mission 3 is blocked
> until they are identified**: it is a search, so its signal has to be one of them, and its
> objective significance has to be measured against the real datasets rather than guessed.
> Missions 1 and 2 can be authored now.

---

## 4. Building an analysis: recipe cards

A vertical stack of configurable cards, in pipeline order:

```
Data  →  Filter  →  Observable  →  Plot
```

This replaces the desktop app's drag-and-drop node canvas. Reasons: a 16-year-old learns it
in a minute, it works on a laptop trackpad and a tablet, and it still teaches that an
analysis *is* a pipeline — which is the structural lesson worth keeping.

The cards map onto the reference engine's node types, so the underlying config is
unchanged: `DataSource`, `Multiplicity`, `Selection`, `Observable`, `Histogram`.

Cards can be added, removed, reordered where meaningful, and collapsed once configured.
The stack reads top to bottom as a sentence describing the analysis. A student should be
able to point at it and say what it does.

Expression entry (`l1.pt > 20 and (l1.p4 + l2.p4).mass > 80`) stays available for students
who get that far — the HEP syntax is part of what is being taught. It is evaluated through
a strict AST whitelist, never `eval`. Rejection messages are written for a 16-year-old and
are part of the learning experience, not a stack trace.

The node canvas is **not** a V1 goal. It is a plausible sandbox-mode addition later.

---

## 5. Results

Python computes the histogram; the browser draws it.

The chart is **hand-written interactive SVG**: stacked backgrounds, data as points with
error bars — the convention the physics community actually uses, which students should
meet. Hover reads out a bin. The legend toggles samples. Bars draw in as results arrive.

An **export** button still produces the exact `mplhep` PNG from the reference engine, so a
student can put a publication-styled plot in a school report. Scientific credibility and
game feel are not in tension here; we ship both.

Alongside the plot: the **cutflow**, showing how many events survived each cut, and — once
a fit has run — **μ** and **Z**.

**Z is the score.** Draw it as a gauge with 3σ and 5σ marked as inked thresholds. Crossing
one is an event, not a number ticking over. Reaching 5σ is the single loudest moment in the
entire application, and the visual system is built so that it lands.

---

## 6. Progression and privacy

Students join with a **class code** (from the teacher) and a **nickname**. Progress is
stored server-side in SQLite, keyed on that pair, so it survives a browser refresh, a
switched machine, and the end of the lesson.

**Privacy is a hard constraint, not a preference.** Users are minors at a Belgian
university; GDPR applies.

- Nickname and class code only. **No real names, no emails, no IP logging**, no free-text
  fields that could carry personal data.
- The nickname field tells students not to use their real name, and validates length and
  character set.
- A teacher-invokable purge deletes a class's data completely, and is documented.
- No analytics, no telemetry, no third-party requests of any kind.

If a feature would need personal data, it does not ship — it gets raised with the user
first.

---

## 7. How it should feel

**Lab notebook.** Warm paper, real ink, ruled lines, notes in the margin, results taped in.
Sober; almost no colour; calm. Full direction in `.claude/design/CLAUDE.md` §2–3.

The hard part, stated plainly: **it must feel like a game without looking like a toy.** The
usual levers — saturated colour, glows, bouncy easing, confetti — are all unavailable,
because they would make the physics look unserious to exactly the students we want to take
it seriously.

So the game feel comes from **artefacts and ritual** instead:

- the **logbook fills in** — completed missions become written-on pages, locked ones are
  blank ruled paper, and progress is legible as how much of the book has been used
- completion **presses a stamp**, off-register, ink dense at the edges
- hints arrive as **handwritten margin notes**, as though a supervisor were leaning over
- charts **draw themselves in** like a pen moving
- there is exactly **one accent colour**, red-pen vermillion, rationed to significance
  thresholds, mission completion, and the signal sample — so that a student learns without
  being told that red means the physics did something

---

## 8. Not in V1

Deliberate exclusions. Each is a candidate later; none is a gap to be helpfully filled.

- The drag-and-drop node canvas
- Energies other than 91 GeV
- A teacher dashboard or class analytics
- A dark colour variant
- Accounts, login, email, SSO
- Multiplayer or live class leaderboards
- Mobile phone layouts — laptop and tablet only

---

## 9. Open questions

### Decided

- **Language — English, everywhere.** *(2026-08-15)* Interface, missions, hints, errors. The
  students are Flemish but the site is not translated, and there is no i18n layer; this is a
  decision, not a deferral. The obligation it creates: copy must read easily as a second
  language. Short sentences, plain words, no idiom, no wordplay. Physics vocabulary is the
  deliberate exception — it is the thing being taught.
- **Samples `X1`, `X2`, `X3`.** *(2026-08-15)* See §3. Missions 1 and 2 are unblocked.

### Still open

1. **Samples `X4` and `X5`.** Undocumented. **Blocks mission 3 entirely** — a search needs a
   signal, and it has to be one of these two. Also sets M-3's achievable significance, which
   must be measured, not guessed. Needs the user.
2. **Dataset distribution.** ROOT files come from `https://homepage.iihe.ac.be/~kskovpen/fce/datasets/`
   via a `files.txt` inventory. Total size for 91 GeV, and whether a teacher pre-downloads
   or the server fetches on first run, is unresolved.
3. **Objective tolerances.** How close is close enough on the M-1 peak position, and how
   forgiving should M-2's purity threshold be. Set from real data, then playtested.
