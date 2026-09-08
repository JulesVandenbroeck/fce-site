"""Downsamples the real FCE 91 GeV / IDEA dataset into the committed fixture at
``tests/fixtures/datasets/IDEA/91GeV/`` (task B-018).

**This is a downsampler, not a generator.** The user ruled mid-task (2026-09-07)
that a synthetic fixture is a guess at what the engine's ROOT files actually
look like, and that the real files -- published at
``https://homepage.iihe.ac.be/~kskovpen/fce/datasets/IDEA/91GeV/`` -- are
ground truth: their branch names, dtypes and physics are what the fixture
should carry, cut down only in event count. This script therefore:

1. Opens a real source file's ``ntuple`` TTree (``uproot.open``).
2. Reads its first ``N_EVENTS`` entries, every branch, with no filtering --
   ``tr.arrays(entry_stop=N_EVENTS, library="ak")`` -- so every branch name
   and dtype the real file has, the fixture file has too, unchanged.
3. Writes those entries back out with ``uproot.recreate()``/``mktree`` (the
   same write path ``engine/path_final.py`` already uses), with a fixed
   per-sample UUID so the output is byte-identical across runs (criterion 7)
   -- ``uproot.recreate``'s default ``uuid_function`` is ``uuid.uuid1``, which
   bakes in the wall-clock time and would otherwise be the one source of
   non-determinism here.

**Running this script requires network access and the real dataset.** That is
consistent with ``.claude/shared/CLAUDE.md`` §3's "no internet" constraint,
which binds the *app* and the *test suite* -- neither of which this script is.
``tests/test_fixture_dataset.py`` runs offline against the already-committed
fixture only; nothing under ``tests/`` other than this file ever reaches the
network.

Source layout expected: ``<FCE_SOURCE_HOME>/datasets/IDEA/91GeV/{sample}.root``,
where ``FCE_SOURCE_HOME`` defaults to ``~/.fce`` (``fce_web.paths.
get_fce_home``'s own default candidate) and can be overridden with the
``FCE_SOURCE_HOME`` environment variable. If a source file is missing, it is
downloaded from the URL above into that directory first.

Run directly to regenerate the fixture: ``python tests/fixtures/make_fixture.py``.
"""
from __future__ import annotations

import contextlib
import datetime
import os
import urllib.request
import uuid

import awkward as ak
import uproot

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "datasets", "IDEA", "91GeV")

SOURCE_URL_BASE = "https://homepage.iihe.ac.be/~kskovpen/fce/datasets/IDEA/91GeV"
SOURCE_HOME = os.environ.get("FCE_SOURCE_HOME", os.path.expanduser("~/.fce"))
SOURCE_DIR = os.path.join(SOURCE_HOME, "datasets", "IDEA", "91GeV")

# X4/X5/X6 exist upstream but are undocumented (design-brief.md §3) and out of
# scope for this fixture -- mission 3 is blocked on the user identifying them.
SAMPLES = ("X1", "X2", "X3", "data")

# Object-kind prefixes the real files group their jagged branches under
# (``electron_pt``, ``electron_eta``, ... share one ``electron_n`` counter).
# Everything else (``weight``, ``MET_*``) is a flat, per-event branch.
_OBJECT_PREFIXES = ("electron", "muon", "jet", "photon")

# Chosen so the four downsampled files stay comfortably under criterion 6's
# 5 MB cap while keeping enough events for a real Z-mass peak in X1/X3 (real
# per-event size is dominated by the jagged branches: ~150-175 bytes/event
# in the source files, so 2000 events/sample lands the fixture around 1.3 MB
# total -- see the PR body for the measured figure).
N_EVENTS = 2000

# A fixed per-sample UUID (see module docstring) so regeneration is
# byte-identical given the same source files and the same N_EVENTS.
BASE_SEED = 91_200


_FROZEN_INSTANT = datetime.datetime(2026, 1, 1)


class _FrozenDatetime(datetime.datetime):
    """A ``datetime.datetime`` whose ``now()`` always returns the same
    instant. uproot's TFile/TTree/TBasket writers stamp ``fDatime`` fields
    with ``datetime.datetime.now()`` at several call sites
    (``uproot/writing/_cascade.py``, ``_cascadentuple.py``,
    ``_cascadetree.py``) with no override parameter -- unlike
    ``uuid_function`` above, which uproot does expose. Freezing the clock is
    what makes regeneration byte-identical (criterion 7) despite that.
    """

    @classmethod
    def now(cls, tz=None):
        return _FROZEN_INSTANT if tz is None else _FROZEN_INSTANT.astimezone(tz)


@contextlib.contextmanager
def _frozen_clock():
    real_datetime = datetime.datetime
    datetime.datetime = _FrozenDatetime
    try:
        yield
    finally:
        datetime.datetime = real_datetime


def _ensure_source(sample: str) -> str:
    """Return the path to *sample*'s real ROOT file under ``SOURCE_DIR``,
    downloading it there first if absent.
    """
    os.makedirs(SOURCE_DIR, exist_ok=True)
    path = os.path.join(SOURCE_DIR, f"{sample}.root")
    if not os.path.exists(path):
        url = f"{SOURCE_URL_BASE}/{sample}.root"
        print(f"downloading {url} -> {path}")
        urllib.request.urlretrieve(url, path)
    return path


def _regroup(columns: ak.Array) -> dict:
    """Re-group the flat field list ``tr.arrays(..., library="ak")`` returns
    into one record per object kind (electron/muon/jet/photon) plus the flat
    branches unchanged, dropping each object's own ``<kind>_n`` field.

    This is needed only because reading every branch as independent top-level
    fields (rather than as the original per-object grouping) loses the
    shared-length relationship uproot's *reader* already knew about --
    ``columns["electron_pt"]`` and ``columns["electron_eta"]`` are two
    unrelated jagged arrays as far as the *writer* is concerned once
    extracted this way. Without regrouping, ``mktree`` cannot tell they share
    a counter and emits one synthetic counter branch per field (``nelectron_pt``,
    ``nelectron_eta``, ...) instead of the single ``electron_n`` the real file
    has. ``ak.zip`` puts that shared relationship back, and ``mktree``'s
    ``counter_name`` (below) reproduces the real file's ``<kind>_n`` naming
    instead of its own default ``n<kind>`` prefix.
    """
    grouped = {}
    for prefix in _OBJECT_PREFIXES:
        fields = {
            name[len(prefix) + 1:]: columns[name]
            for name in columns.fields
            if name.startswith(prefix + "_") and name != f"{prefix}_n"
        }
        grouped[prefix] = ak.zip(fields)
    for name in columns.fields:
        if not any(name.startswith(p + "_") for p in _OBJECT_PREFIXES):
            grouped[name] = columns[name]
    return grouped


def generate() -> None:
    """Downsample every sample's real ROOT file into ``FIXTURE_DIR``."""
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    for offset, sample in enumerate(SAMPLES):
        source_path = _ensure_source(sample)
        with uproot.open(source_path) as f:
            tr = f["ntuple"]
            columns = tr.arrays(entry_stop=N_EVENTS, library="ak")
        grouped = _regroup(columns)

        out_path = os.path.join(FIXTURE_DIR, f"{sample}.root")
        fixed_uuid = uuid.UUID(int=BASE_SEED + offset)
        with _frozen_clock(), uproot.recreate(out_path, uuid_function=lambda: fixed_uuid) as f:
            # uproot >= 5.7 defaults dict-assignment (``f["ntuple"] = ...``)
            # to RNTuple; the engine reads a classic TTree
            # (``uproot.open(...)["ntuple"]`` -- ``analytical_loop.py:157``),
            # so this writes one explicitly. ``counter_name`` reproduces the
            # real file's ``<kind>_n`` naming (see ``_regroup``) instead of
            # uproot's own default ``n<kind>``.
            f.mktree("ntuple", grouped, counter_name=lambda counted: f"{counted}_n")
        print(f"{sample}: {N_EVENTS} events -> {out_path}")


if __name__ == "__main__":
    generate()
    print(f"Wrote fixture ROOT files to {FIXTURE_DIR}")
