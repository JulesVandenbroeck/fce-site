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

**And never passive.** Added 2026-09-01. A progress bar tells a student their run is alive; it
does not give them anything to do while it is. The requirement is **interaction**, not just
reassurance: a run should hold attention rather than merely ask for patience. The intended
vehicle is **showing the data itself as it is read** — event displays streaming past, ideally
ones the student can poke at — so that waiting is spent among collisions rather than in front
of a bar. Deferred
to **M6** by the user's ruling: M3 ships the phase label and bar above, and that is deliberate
rather than an oversight.

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

## 4. Building an analysis: the node graph

> **Amended 2026-08-16, on the user's explicit decision.** This section previously specified
> a vertical stack of recipe cards and stated that the node canvas was "not a V1 goal". That
> is reversed: the analysis is now built on an interactive node graph. The card stack is no
> longer the plan and no longer a fallback. Recorded rather than silently rewritten, because
> the superseded model was a committed decision that shaped D-001's ten wireframes, and
> because `docs/wireframes/` still reads as current unless you know this happened.

> **Amended again 2026-09-01, on the user's ruling at the M1 checkpoint.** The style is
> **Bench** — a free canvas, drag-to-connect, persisting `{id, x, y}` per node. The D-007
> comparison recommended *Board*; the user overruled it. Four further decisions came with that
> ruling and are written into this section below: the `DataSource` node leaves the palette, the
> canvas becomes the logbook, the page has three named regions, and node interiors are
> explicitly *not* inherited from the reference tool. `docs/design-explorations/README.md`
> still carries the superseded Board recommendation; it is a historical document.

Students assemble the analysis as a **graph of nodes** that can be added, connected, and
removed. The graph *is* the analysis: it is what runs, and it is what grows as the campaign
progresses.

Nodes are the reference engine's node types, unchanged, so the underlying config is the
engine's config: `DataSource`, `Multiplicity`, `Selection`, `Observable` (and its subtypes
`ObsGlobal`, `ObsObject`, `ObsVectorSum`, `ObsCustom`), `Histogram`.

**But `DataSource` is not one the student places.** V1 ships one energy (91 GeV, §8) and each
mission declares its own dataset (§3), so a dataset node would be a node with exactly one legal
value — a decision the student cannot get wrong and therefore cannot learn from. Decided
2026-09-01. The concept splits in two, and the split matters because only one half is visible:

| | What it holds |
|---|---|
| **The palette** — what the student places | **four** kinds: `Multiplicity`, `Selection`, `Observable`, `Histogram` |
| **The run payload** — what the engine reads | those nodes with `Observable` resolved to its engine subtype, **plus a `DataSource` synthesised at submit** from the mission's declared dataset |

The engine, and the allowlist below, are untouched: `DataSource` remains the root of every
chain the engine sees. It is simply supplied rather than drawn. Future missions at other
energies are separate missions, not a chooser inside one.

**And the four `Obs*` subtypes are one palette node, not four.** Decided 2026-09-02, replacing
the `seven` count above. `ObsGlobal`, `ObsObject`, `ObsVectorSum` and `ObsCustom` are **not four
things a student chooses between at placement time** — they are four ways of answering one
question, *what number am I plotting?*. The student places one **`Observable`** node and toggles
its mode inside the node.

This is a design decision that costs nothing structurally, because the four subtypes are
already interchangeable everywhere the graph is concerned: **all four have identical legal
connections** — `Observable* → Histogram`, and nothing else, which is why the allowlist below
writes them as a single row rather than four. Nothing about which graphs are legal changes.
What changes is that a 15-year-old picks a node by what it *does* rather than by a taxonomy
they have not learned yet, and discovers the four modes by opening the node instead of by
reading four palette labels.

The mode is `config`, not identity: the run payload resolves it back to the engine's subtype at
submit, exactly as `DataSource` is synthesised at submit. **The student's graph and the engine's
graph are deliberately not the same object** — this is now true in two places, not one.

**Which connections are legal is not a design choice.** The reference app defines an explicit
allowlist (`ui/graph.py`, `_VALID_CONNECTIONS`), and the web version enforces the same one:

```
DataSource   → Multiplicity, Selection
Multiplicity → Multiplicity, Selection
Selection    → Selection (an AND-chain), Observable*
Observable*  → Histogram
Histogram    → terminal
```

Two consequences worth designing *for* rather than around. `Selection → Selection` chains
cuts with AND, so a chain of filters is a visible conjunction rather than an ordering
accident. And `ObsVectorSum` is exactly the mission-2 lesson in node form — adding the
photon's four-vector back to recover the Z mass — which makes it the most valuable unlock in
the campaign. Under the 2026-09-02 ruling it unlocks as a **mode** of the `Observable` node
rather than as a palette entry, so the unlock has to read inside the node.

**The three reasons the card stack was originally chosen are now requirements the graph must
meet.** They were good reasons; dropping the stack does not drop them.

1. **A 16-year-old learns it in a minute.** The graph must be legible on first contact, not
   after a tutorial.
2. **It works on a laptop trackpad and a tablet.** Whatever the connection gesture is, it
   must survive both, and it must have a keyboard path — that is a review item, not a
   nice-to-have.
3. **It still reads as a pipeline.** A student should be able to point at the graph and say
   what it does, in order.

**The canvas is the logbook.** Decided 2026-09-01. When a mission is completed, the graph that
completed it is **frozen where it stands and boxed**, labelled with the mission it closed; the
next mission is built beside it on the same canvas. The canvas therefore accumulates rather
than clearing, and a student scrolling back over it is reading their own record of what they
built. This is §7's stamp metaphor in the one place the student actually works — the same idea
as "the logbook fills in", not a rival to it, and the two should be designed as one gesture.

**The page has three regions, and only one of them is permanent.** Decided 2026-09-01.

- The **graph canvas** is always present. It is never covered, collapsed, or navigated away
  from; everything else arranges itself around it.
- **"Add a Node"** sits on the **left** and **collapses**, because once a student knows the
  seven kinds the palette is mostly in the way.
- The **mission panel** sits on the **right** and **expands** — briefly by default, opened to
  read the mission in full, and it is also how a student pages back to a previous mission.

No payload change follows from any of this: "What the run payload carries", below, already
classifies collapse state as `ui` state the engine ignores.

**Node interiors are not inherited.** Decided 2026-09-01. In the reference desktop tool the
inside of a node was fixed — the same dense property grid the engine's config implies. That is
the one part of the reference UI this project does **not** take: how a cut is expressed, how an
observable is chosen and configured, what a node shows when it is collapsed versus opened, are
open design questions to be answered for a 15–18-year-old who has never seen a physics tool.
Legible and hard-to-get-wrong beats complete. The engine's config is the *output* of that
design, not its layout. **D-009 is where this is settled**, and it is a checkpoint.

**Complexity ramps through the campaign.** Mission 1 exposes a minimal graph; later missions
unlock further node types, and the graph grows with them. Node gating carries the teaching
exactly as card gating did (§3): a locked node type is *shown and inert*, labelled with the
mission that opens it, never hidden.

**What the run payload carries.** A typed `nodes[] + edges[]` list, and nothing else the
engine has to understand. Any layout state — coordinates, slot indices, collapse state —
lives in a separate `ui` object the engine ignores. This keeps the physics config independent
of the visual direction, so changing how the graph is drawn stays front-end work.

Expression entry (`l1.pt > 20 and (l1.p4 + l2.p4).mass > 80`) stays available for students
who get that far — the HEP syntax is part of what is being taught. It is evaluated through
a strict AST whitelist, never `eval`. Rejection messages are written for a 16-year-old and
are part of the learning experience, not a stack trace.

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

> **Amended 2026-08-16, on the user's explicit decision.** The rationing rule below is
> reversed: colour is now used generously to highlight what matters. The *ground* is
> unchanged — light paper, dark ink — and the artefact devices are unchanged. What changed is
> that saturation is no longer forbidden, because the interface is now a node graph and
> colour is how a graph stays readable. Recorded, not silently rewritten.

**Light ground, loud marks.** Warm paper, real ink, ruled lines, notes in the margin, results
taped in — and saturated colour on top of it, carrying meaning. Full direction in
`.claude/design/CLAUDE.md` §2–3.

Light is not up for negotiation, and the reason is practical rather than aesthetic: **physics
plots are conventionally drawn on white**, so the charts sit on this ground instead of
fighting it. A dark variant remains out of scope (§8).

The hard part, restated for the new direction: **it must feel like a game without looking
like a toy.** Saturated colour is now available; cartoon easing, glows on everything and
confetti still are not. The test is whether a colour *means* something. Colour that encodes
node type, sample identity, lock state, or a crossed threshold is doing work. Colour applied
to liven something up is the failure mode, and it is still a failure mode.

Colour now carries these, and should carry little else:

- **node type** — each kind of node owns a hue, so a graph is readable at a glance
- **sample identity** — a sample's colour is the same in the graph, the legend and the plot
- **lock state** — a gated node type is visibly inert, not merely greyer
- **thresholds crossed** — significance passing 3σ and 5σ

And the game feel still comes substantially from **artefacts and ritual**, which colour does
not replace:

- the **logbook fills in** — completed missions become written-on pages, locked ones are
  blank ruled paper, and progress is legible as how much of the book has been used
- completion **presses a stamp**, off-register, ink dense at the edges
- hints arrive as **handwritten margin notes**, as though a supervisor were leaning over
- charts **draw themselves in** like a pen moving
- **red-pen vermillion stays held back** for significance thresholds, mission completion and
  the signal sample. This is the one part of the old rationing rule kept deliberately: in a
  palette that is now loud everywhere else, a colour still held in reserve is *louder*, not
  quieter. A student should learn without being told that red means the physics did
  something. The reference app already agrees — it paints its "Discovered:" badge in a
  saturated green reserved for exactly that moment (`engine/plotter.py`).

---

## 8. Not in V1

Deliberate exclusions. Each is a candidate later; none is a gap to be helpfully filled.

- ~~The drag-and-drop node canvas~~ — **struck 2026-08-16.** The node graph is now the V1
  build surface; see §4.
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
- **The node-graph style — Bench.** *(2026-09-01)* Chosen at the M1 checkpoint from the three
  built explorations. A free canvas, drag-to-connect, persisting `{id, x, y}` per node plus an
  edge list; the plot lives outside the graph in its own results region. The D-007 comparison
  recommended *Board* and was overruled. Four further decisions came with the ruling and are
  written into §4, plus one into §2 — the `DataSource` node leaving the palette, the canvas as
  logbook, the three page regions, node interiors not inherited, and a run that is never
  passive. The obligation it creates: `docs/design-explorations/` is now history, not a menu.

### Still open

1. **Samples `X4` and `X5`.** Undocumented. **Blocks mission 3 entirely** — a search needs a
   signal, and it has to be one of these two. Also sets M-3's achievable significance, which
   must be measured, not guessed. Needs the user.
2. **Dataset distribution.** ROOT files come from `https://homepage.iihe.ac.be/~kskovpen/fce/datasets/`
   via a `files.txt` inventory. Total size for 91 GeV, and whether a teacher pre-downloads
   or the server fetches on first run, is unresolved.
3. **Objective tolerances.** How close is close enough on the M-1 peak position, and how
   forgiving should M-2's purity threshold be. Set from real data, then playtested.
