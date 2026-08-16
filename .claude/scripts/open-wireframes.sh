#!/usr/bin/env bash
#
# Open a design checkpoint page in the browser, for the user's decision.
#
#   .claude/scripts/open-wireframes.sh            # what exists, and what does not
#   .claude/scripts/open-wireframes.sh index      # D-001 index — both screens, 10 options
#   .claude/scripts/open-wireframes.sh mission    # D-001 mission screen — 5 options
#   .claude/scripts/open-wireframes.sh recipe     # D-001 recipe builder — 5 options
#   .claude/scripts/open-wireframes.sh plot       # D-003 plot component (PR #5, unmerged)
#   .claude/scripts/open-wireframes.sh all        # every page above, one tab each
#
#   --print   emit file:// URLs instead of launching a browser (headless/ssh)
#
# ---------------------------------------------------------------------------
# WHY EVERY PATH IS UNDER $HOME, AND NEVER /tmp
#
# The default browser on this machine is snap Firefox. A snap runs with a
# PRIVATE /tmp NAMESPACE, so a `file:///tmp/...` URL resolves to nothing inside
# the sandbox -- the tab opens and silently shows an empty or missing document,
# with no error that names the real cause. $HOME is readable, /tmp is not.
#
# So a branch that is not merged is previewed from a git worktree under $HOME,
# never from a temp directory:
#
#     git worktree add --detach ~/wireframes-preview origin/task/d-001-wireframes-clean
#
# That is what this script maintains for you. One worktree per ref, because a
# worktree has exactly one HEAD.
# ---------------------------------------------------------------------------
#
# `git worktree add --detach` creates NO branch and moves NO branch, so nothing
# here touches the never-delete-a-branch rule. Detached HEAD only.

set -euo pipefail

# ref -> preview worktree. Both live under $HOME for the reason above.
D001_REF="origin/task/d-001-wireframes-clean"
D001_DIR="$HOME/wireframes-preview"
D003_REF="origin/task/d-003-plot-component"
D003_DIR="$HOME/wireframes-preview-d003"

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
PRINT_ONLY=0
TARGET=""

for arg in "$@"; do
    case "$arg" in
        --print) PRINT_ONLY=1 ;;
        -h|--help) sed -n '3,32p' "$0" | sed 's|^# \{0,1\}||'; exit 0 ;;
        index|mission|recipe|plot|all) TARGET="$arg" ;;
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

# ------------------------------------------------------- preview worktrees

# ensure_worktree <dir> <ref> -- create it, or move it to <ref> if it is
# elsewhere and clean. Prints the directory on stdout.
ensure_worktree() {
    local dir="$1" ref="$2" want have
    if ! want=$(git -C "$ROOT" rev-parse --verify --quiet "$ref^{commit}"); then
        echo "ref not found: $ref (try: git fetch origin)" >&2
        return 1
    fi
    if [ ! -d "$dir/.git" ] && [ ! -f "$dir/.git" ]; then
        echo "creating preview worktree: $dir -> $ref" >&2
        git -C "$ROOT" worktree add --detach "$dir" "$ref" >&2
    else
        have=$(git -C "$dir" rev-parse HEAD)
        if [ "$have" != "$want" ]; then
            if [ -n "$(git -C "$dir" status --porcelain)" ]; then
                echo "warning: $dir has local changes and is at ${have:0:7}, not $ref." >&2
                echo "         leaving it alone -- showing what is there." >&2
            else
                echo "moving preview worktree $dir to $ref (${want:0:7})" >&2
                git -C "$dir" checkout --detach "$ref" >&2
            fi
        fi
    fi
    printf '%s\n' "$dir"
}

# ------------------------------------------------------------------ pages

open_d001() {
    local dir
    dir=$(ensure_worktree "$D001_DIR" "$D001_REF") || return 1
    open_url "file://$dir/docs/wireframes/$1"
}

open_plot() {
    local dir
    dir=$(ensure_worktree "$D003_DIR" "$D003_REF") || return 1
    open_url "file://$dir/docs/design-explorations/plot.html"
}

# ------------------------------------------------------------------ status

status() {
    cat <<'EOF'
Design checkpoints — what you can actually look at right now
============================================================

  index / mission / recipe   D-001 wireframes           MERGED, SUPERSEDED
  plot                       D-003 plot component       PR #5, IN REVIEW
  (nothing)                  D-004 node-graph options   NOT BUILT YET

Every page is opened from a git worktree under $HOME. Never from /tmp: the
default browser here is snap Firefox, which has a private /tmp namespace and
would show you an empty tab with no error.

  ~/wireframes-preview        <- origin/task/d-001-wireframes-clean
  ~/wireframes-preview-d003   <- origin/task/d-003-plot-component

D-001 — 10 options, black and white, merged and readable
--------------------------------------------------------
  mission screen : 1 Split Bench · 2 Notebook Spread · 3 Focus Stage
                   4 Result First · 5 Long Column · Summary
  recipe builder : 1 Card Stack · 2 Sentence Strip · 3 Two Pane
                   4 Guided Slots · 5 Deck and Tray · Summary

  Drawn before the node-graph pivot and marked SUPERSEDED in
  .claude/tasks/design.md. The recipe-card stack they recommend no longer
  exists as a concept, so the layout decision they ask for is dead. Two things
  in them are still live: the domain inventory (every element a mission screen
  must hold) and the Summary tabs' reasoning about run comparison.

D-003 — the plot component, PR #5, in review (cycle 2)
-------------------------------------------------------
  Wants a ruling from you. Its "Two open questions for the checkpoint" panel:
    1. legend placement — parity (framed, inside, upper-right) vs. an
       outside-axes position for narrow embeddings
    2. sample colour mapping — a frozen per-sample map with X1 pinned to
       vermillion (breaks reference parity) vs. following the reference

D-004 — the three node-graph wireframes, and the real front-end direction
--------------------------------------------------------------------------
  Beamline / Bench / Board, differing on what the graph persists and how
  connections are made. BLOCKED on D-003 and not yet drawn, so there is
  nothing to open. This is the checkpoint that gives the front-end its
  direction; D-001 cannot, and D-003 only settles the plot.

Run `.claude/scripts/open-wireframes.sh all` to open everything that exists.
EOF
}

# -------------------------------------------------------------------- main

case "$TARGET" in
    index)   open_d001 index.html ;;
    mission) open_d001 mission-screen.html ;;
    recipe)  open_d001 recipe-builder.html ;;
    plot)    open_plot ;;
    all)     open_d001 index.html; open_d001 mission-screen.html
             open_d001 recipe-builder.html; open_plot || true ;;
    "")      status ;;
esac
