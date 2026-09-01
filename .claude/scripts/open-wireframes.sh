#!/usr/bin/env bash
#
# Open a design checkpoint page in the browser, for the user's decision.
#
#   .claude/scripts/open-wireframes.sh             # what exists, and what it asks you
#   .claude/scripts/open-wireframes.sh compare     # D-007 index -- THE LIVE CHECKPOINT
#   .claude/scripts/open-wireframes.sh beamline    # D-004 style A
#   .claude/scripts/open-wireframes.sh bench       # D-005 style B
#   .claude/scripts/open-wireframes.sh board       # D-006 style C
#   .claude/scripts/open-wireframes.sh plot        # D-003 plot component
#   .claude/scripts/open-wireframes.sh mission     # D-001 mission screen  (SUPERSEDED)
#   .claude/scripts/open-wireframes.sh recipe      # D-001 recipe builder  (SUPERSEDED)
#   .claude/scripts/open-wireframes.sh all         # the four live pages, one tab each
#
#   --print   emit file:// URLs instead of launching a browser (headless/ssh)
#
# ---------------------------------------------------------------------------
# WHY NO PATH HERE IS EVER UNDER /tmp
#
# The default browser on this machine is snap Firefox. A snap runs with a
# PRIVATE /tmp NAMESPACE, so a `file:///tmp/...` URL resolves to nothing inside
# the sandbox -- the tab opens and silently shows an empty or missing document,
# with no error that names the real cause. $HOME is readable, /tmp is not.
#
# Every design page is now merged to main, so this script serves them straight
# out of the primary checkout, which is under $HOME. There is no worktree to
# maintain any more.
#
# To preview a page on a branch that is NOT yet merged, make a detached
# worktree under $HOME by hand and open it from there:
#
#     git worktree add --detach ~/some-preview origin/task/<id>-<slug>
#
# `--detach` creates NO branch and moves NO branch, so nothing here touches the
# never-delete-a-branch rule. One worktree per ref: a worktree has one HEAD.
# ---------------------------------------------------------------------------

set -euo pipefail

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
EXPL="$ROOT/docs/design-explorations"
WIRE="$ROOT/docs/wireframes"
PRINT_ONLY=0
TARGET=""

for arg in "$@"; do
    case "$arg" in
        --print) PRINT_ONLY=1 ;;
        -h|--help) sed -n '3,36p' "$0" | sed 's|^# \{0,1\}||'; exit 0 ;;
        compare|beamline|bench|board|plot|mission|recipe|all) TARGET="$arg" ;;
        *) echo "unknown argument: $arg (try --help)" >&2; exit 2 ;;
    esac
done

# ---------------------------------------------------------------- browser

open_url() {
    case "$1" in
        file:///tmp/*|file:///var/tmp/*)
            echo "refusing to open $1 -- snap Firefox cannot read /tmp." >&2
            return 1 ;;
    esac
    if [ "$PRINT_ONLY" = 1 ]; then
        printf '%s\n' "$1"
        return
    fi
    for cmd in "${BROWSER:-}" xdg-open firefox google-chrome chromium chromium-browser; do
        [ -n "$cmd" ] || continue
        if command -v "$cmd" >/dev/null 2>&1; then
            nohup "$cmd" "$1" >/dev/null 2>&1 &
            return
        fi
    done
    echo "no browser found -- open this yourself:" >&2
    printf '%s\n' "$1"
}

open_page() {
    if [ ! -f "$1" ]; then
        echo "not on this checkout: $1 (try: git pull --ff-only)" >&2
        return 1
    fi
    open_url "file://$1"
}

# ------------------------------------------------------------------ status

status() {
    cat <<'EOF'
Design checkpoints — what you can actually look at right now
============================================================

  compare    D-007 comparison index    <- THE OPEN DECISION
  beamline   D-004 style A             merged
  bench      D-005 style B             merged
  board      D-006 style C             merged
  plot       D-003 plot component      merged
  mission    D-001 mission screen      merged, SUPERSEDED
  recipe     D-001 recipe builder      merged, SUPERSEDED

Everything is on main now, served from this checkout. Never from /tmp: the
default browser here is snap Firefox, which has a private /tmp namespace and
would show you an empty tab with no error.

D-007 — the comparison index, and the decision it wants from you
-----------------------------------------------------------------
  Beamline / Bench / Board, side by side, each linking to its own live page.

  The axis CSS cannot change later is WHAT THE GRAPH PERSISTS, because that is
  what ends up in POST /api/run:

    Beamline   an ordered edge list, and nothing else
    Bench      {x, y} — free canvas coordinates
    Board      {column, slotIndex} — and the plot lives inside the graph,
               as the terminal node

  The README recommends BOARD: it is the only one of the three whose persisted
  shape makes a node's pipeline stage recoverable from structure alone. That
  recommendation is advisory. Read the case for it, and what each option gives
  up, in docs/design-explorations/README.md under `## Recommendation`.

  Your choice unblocks D-002, the design-token foundation. Nothing else in
  design moves until it is made.

D-001 — superseded, but two things in it are still live
--------------------------------------------------------
  Drawn before the 2026-08-16 node-graph pivot, so the recipe-card stack they
  recommend no longer exists as a concept and the layout decision they ask for
  is dead. Still worth having: the domain inventory (every element a mission
  screen must hold) and the Summary tabs' reasoning about run comparison.

Run `.claude/scripts/open-wireframes.sh all` to open the four live pages.
EOF
}

# -------------------------------------------------------------------- main

case "$TARGET" in
    compare)  open_page "$EXPL/index.html" ;;
    beamline) open_page "$EXPL/beamline.html" ;;
    bench)    open_page "$EXPL/bench.html" ;;
    board)    open_page "$EXPL/board.html" ;;
    plot)     open_page "$EXPL/plot.html" ;;
    mission)  open_page "$WIRE/mission-screen.html" ;;
    recipe)   open_page "$WIRE/recipe-builder.html" ;;
    all)      open_page "$EXPL/index.html"; open_page "$EXPL/beamline.html"
              open_page "$EXPL/bench.html"; open_page "$EXPL/board.html" ;;
    "")       status ;;
esac
