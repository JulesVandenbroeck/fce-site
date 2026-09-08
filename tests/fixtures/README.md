# `tests/fixtures/` — the committed ROOT fixture

## What this is

A small, offline-runnable slice of the real FCE 91 GeV / IDEA dataset, committed under
`tests/fixtures/datasets/IDEA/91GeV/{X1,X2,X3,data}.root` so `fce_web.engine.driver.run_analysis`
can be run and reviewed on a machine with no ROOT data and no internet access. It is the single
bounded exception in `.claude/shared/CLAUDE.md` §3: one small *fixture* ROOT set, not a real
dataset, and not a licence to add a second one.

## What this is not

- **Not synthetic.** An earlier version of this fixture generated leptons and jets from
  hand-written kinematics. The user overruled that approach mid-task (2026-09-07): a synthetic
  schema is a guess at what the engine's real ROOT files look like, and a fixture cut from real
  simulation carries a real Z peak rather than one constructed to pass a test. `make_fixture.py`
  is now a **downsampler**: every branch name, dtype and physics value in the fixture comes from
  the real files at
  <https://homepage.iihe.ac.be/~kskovpen/fce/datasets/IDEA/91GeV/>, unchanged except for event
  count.
- **Not the full dataset.** The real files are 51–166 MB each; this fixture keeps the first 2000
  events of each, ~750 KB total. It is not statistically representative of the full sample, only
  large enough to carry a real peak and exercise the pipeline.
- **Not X4/X5/X6.** Those exist upstream but are undocumented (`docs/design-brief.md` §3) and
  mission 3 is blocked on the user identifying them. Fabricating a fixture for them would be
  fabricating mission-3 content ahead of that ruling.

## Branch schema

Every fixture file's `ntuple` TTree carries exactly 30 branches, identical to the real source
files:

- The 26 branches `engine/analytical_loop.py`'s key filter selects
  (substring match on `pt`/`eta`/`phi`/`e`/`weight`/`btag`/`d0signif`/`z0signif`/`charge`,
  `analytical_loop.py:156-159`) and `engine/path_filter.py` reads by name
  (`path_filter.py:609-643`): `weight`, `MET_pt`, `MET_phi`, and `{electron,muon}_{pt,eta,phi,e,
  d0signif,z0signif}`, `jet_{pt,eta,phi,e,btag}`, `photon_{pt,eta,phi,e}`.
- 4 more the engine never reads by name but the real files carry regardless: `MET_e`, `MET_eta`,
  and one counter branch per variable-length object (`electron_n`, `muon_n`, `jet_n`,
  `photon_n`) — a structural requirement of the TTree format for any jagged branch, not
  something `path_filter.py` looks up. (`electron_n`/`jet_n` happen to also match the engine's
  substring filter, since they contain the letter "e"; `muon_n`/`photon_n` do not. Harmless
  either way — the engine only ever reads columns it names explicitly.)

`tests/test_fixture_dataset.py::test_branch_set_matches_the_real_fixture_schema` asserts this set
exactly, per sample.

## How to regenerate

```bash
python tests/fixtures/make_fixture.py
```

This **requires network access and a copy of the real dataset** — it downloads
`X1.root`/`X2.root`/`X3.root`/`data.root` from the URL above into
`~/.fce/datasets/IDEA/91GeV/` (or `$FCE_SOURCE_HOME/datasets/IDEA/91GeV/` if that environment
variable is set) if not already present there, then reads and rewrites the first 2000 events of
each. This is consistent with `.claude/shared/CLAUDE.md` §3's "no internet" constraint, which
binds the *app* and the *test suite* — `tests/test_fixture_dataset.py` never touches the network,
only this generator does.

**Reproducibility (criterion 7): byte-identical given the same source files and the same event
count — there is no seed.** There is no randomness left to seed: the physics is copied verbatim
from the real files, and the two remaining non-deterministic knobs uproot's writer would
otherwise introduce are pinned:

- `uproot.recreate`'s default `uuid_function` (`uuid.uuid1`) bakes in the wall-clock time and
  host MAC address — pinned to a fixed per-sample `uuid.UUID`.
- uproot's TFile/TTree/TBasket writers stamp `fDatime` fields with `datetime.datetime.now()` at
  several call sites with no override parameter — `make_fixture.py`'s `_frozen_clock()` patches
  `datetime.datetime` to a fixed instant for the duration of each write.

Verified by running `generate()` twice against the same cached source files and diffing the
output with `md5sum`: identical both times. If the real source files are ever unavailable (no
network, or the upstream URL moves), this script cannot regenerate the fixture at all — that is
the "why it cannot" this criterion asks for, made precise rather than papered over.

## Layout

```
tests/fixtures/
  datasets/IDEA/91GeV/{X1,X2,X3,data}.root   <- the committed fixture (this file's subject)
  make_fixture.py                             <- the downsampler (needs network + the real files)
  golden/                                      <- unrelated pre-existing fixtures, not this task's
```
