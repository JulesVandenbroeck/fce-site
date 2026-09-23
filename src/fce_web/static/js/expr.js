// The one place the engine's expression vocabulary (safe_eval.py:86-131)
// is named in the browser. graph.js's Observable and Selection interiors
// build every expression string through the functions below; neither holds
// an expression string of its own (F-011, docs/plan-m4-recipe-builder.md).
//
// This is a *convenience* copy for building dropdowns, not a second source
// of truth for what is safe -- safe_eval.compile_expr on the server is the
// only trust boundary (plan, "Security is unchanged"). tests/e2e/test_interiors.py
// proves every string this module can produce compiles there.
//
// F-012 (Multiplicity/Histogram interiors) and D-018 (styling) consume this
// table read-only -- it is a contract, not an implementation detail.

// The seven per-event objects (safe_eval.EVENT_NAMES, minus the bare
// scalars nlep/nel/nmu/njets/nphot, which are COUNTS below, not objects).
export const OBJECTS = [
  { name: "l1", label: "1st lepton" },
  { name: "l2", label: "2nd lepton" },
  { name: "j1", label: "1st jet" },
  { name: "j2", label: "2nd jet" },
  { name: "ph1", label: "1st photon" },
  { name: "ph2", label: "2nd photon" },
  { name: "met", label: "missing transverse energy (MET)" },
];

// The objects a vector sum can be built from -- physical four-vectors only.
// `met` is excluded: the engine only ever uses it as a scalar (met.pt), not
// summed into a vector sum, in the reference corpus safe_eval.py cites.
export const VECTOR_SUM_OBJECTS = OBJECTS.filter((o) => o.name !== "met");

// Every attribute name safe_eval.ALLOWED_ATTRS accepts on an event object,
// plain-labelled with a unit and a histogram range preset (consumed by
// F-012's Histogram interior when the observable's quantity changes).
export const PROPERTIES = [
  { name: "pt", label: "transverse momentum (pt)", unit: "GeV", range: [0, 150] },
  { name: "eta", label: "pseudorapidity (eta)", unit: "", range: [-5, 5] },
  { name: "phi", label: "azimuthal angle (phi)", unit: "rad", range: [-3.2, 3.2] },
  { name: "e", label: "energy (e)", unit: "GeV", range: [0, 200] },
  { name: "charge", label: "charge", unit: "", range: [-1, 1] },
  { name: "flavour", label: "flavour", unit: "", range: [0, 20] },
  { name: "d0", label: "impact parameter significance (d0)", unit: "", range: [-50, 50] },
  { name: "z0", label: "longitudinal impact parameter (z0)", unit: "mm", range: [-1, 1] },
  { name: "btag", label: "b-tag score", unit: "", range: [0, 1] },
];

// Which of PROPERTIES apply to which OBJECTS -- pt/eta/phi/e on everything,
// charge/flavour/d0/z0 only on leptons, btag only on jets (safe_eval.py's
// module docstring, "The language surface").
const LEPTON_ONLY = ["charge", "flavour", "d0", "z0"];
const JET_ONLY = ["btag"];
const BASE = ["pt", "eta", "phi", "e"];
export const OBJECT_PROPERTIES = {
  l1: [...BASE, ...LEPTON_ONLY],
  l2: [...BASE, ...LEPTON_ONLY],
  j1: [...BASE, ...JET_ONLY],
  j2: [...BASE, ...JET_ONLY],
  ph1: BASE,
  ph2: BASE,
  met: BASE,
};

// The bare per-event scalars -- Observable's Global mode.
export const COUNTS = [
  { name: "nlep", label: "number of leptons (nlep)", range: [0, 6] },
  { name: "nel", label: "number of electrons (nel)", range: [0, 6] },
  { name: "nmu", label: "number of muons (nmu)", range: [0, 6] },
  { name: "njets", label: "number of jets (njets)", range: [0, 6] },
  { name: "nphot", label: "number of photons (nphot)", range: [0, 6] },
];

// The comparisons safe_eval's Compare node type allows, minus `**` (never
// a comparison anyway) -- ast.Eq/NotEq/Lt/LtE/Gt/GtE.
export const COMPARISONS = [
  { op: "<", label: "less than (<)" },
  { op: "<=", label: "at most (<=)" },
  { op: ">", label: "greater than (>)" },
  { op: ">=", label: "at least (>=)" },
  { op: "==", label: "equal to (==)" },
  { op: "!=", label: "not equal to (!=)" },
];

// Observable's VectorSum mode plots one of these off the summed 4-vector.
export const VECTOR_SUM_QUANTITIES = [
  { name: "mass", label: "invariant mass (mass)", unit: "GeV", range: [0, 150] },
  { name: "pt", label: "transverse momentum (pt)", unit: "GeV", range: [0, 150] },
];

function objectLabel(name) {
  return OBJECTS.find((o) => o.name === name).label;
}

function propertyLabel(name) {
  return PROPERTIES.find((p) => p.name === name).label;
}

// ---- Selection: one row -> one expression string ----------------------

export function buildSelectionExpr(object, property, comparison, value) {
  return `${object}.${property} ${comparison} ${value}`;
}

// ---- Observable: mode -> { expr, label } -------------------------------

export function globalConfig(quantity) {
  if (quantity === "met_pt") {
    return { expr: "met.pt", label: "missing transverse energy (MET) pt [GeV]" };
  }
  const count = COUNTS.find((c) => c.name === quantity);
  return { expr: count.name, label: count.label };
}

export function objectConfig(object, property) {
  return {
    expr: `${object}.${property}`,
    label: `${objectLabel(object)} ${propertyLabel(property)}`,
  };
}

export function vectorSumConfig(objects, quantity) {
  const sum = objects.map((o) => `${o}.p4`).join(" + ");
  const expr = `(${sum}).${quantity}`;
  const label = `${quantity === "mass" ? "m" : "pt"}(${objects.join(", ")})`;
  return { expr, label };
}

export function customConfig(expr) {
  return { expr, label: expr };
}

// ---- Multiplicity: comparison + lepton-type vocabulary (F-012) --------

// engine/path_filter.py:668-689 accepts only these three comparisons for a
// Multiplicity cut -- plain-labelled per the plan's "the design" table
// (count + comparison per object).
export const MULT_COMPARISONS = [
  { op: "==", label: "exactly" },
  { op: "<=", label: "at most" },
  { op: ">=", label: "at least" },
];

export const LEPTON_TYPES = [
  { value: "Any", label: "Any" },
  { value: "Electron", label: "Electron" },
  { value: "Muon", label: "Muon" },
];
