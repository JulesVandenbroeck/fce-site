# D-006 Board — anchor (cycle 2, resumed after user-interrupted cycle 1)

Worktree: ~/fce-worktrees/d-006-board, branch task/d-006-board.
Cycle-1 work (board.html 811L, board.css 689L, verify.py +1330L check_board_* funcs)
was uncommitted; committed as f4fdb03. Merged main (bookkeeping only) after -- merge
commit on top of f4fdb03, no conflicts on the 3 in-scope files.

## State of verify.py board work (as of merge)
- ~14 `check_board_*` functions exist (verify.py:4895-6040ish): persistence,
  connection_gestures, keyboard_path, pairs, inventory, paint_sweep, contrast,
  terminal_plot_budget, focus_walk, reduced_motion, network_and_errors,
  no_exhaustive_prose, unflagged_file_url. NOT YET wired into main() -- no
  `if args.board:` block, no `--board` argparse flag, no `run_section("board-...")`
  calls exist yet. This is the main remaining work for C1-C7.
- C8 (ast launch-flag check) and C9 (ast all-sections-wrapped check) do NOT exist
  yet at all -- need new check_board_no_launch_flags / check_board_all_sections_wrapped
  functions using `ast` module over verify.py's own source, PLUS need to retrofit
  run_section() around the beamline block (verify.py:6055-6129 roughly, before bench
  block) which currently uses raw `all_results.append(("beamline-x", check_x(...)))`
  WITHOUT run_section wrapper -- C9 requires this fixed for beamline AND board.
- Need to check whether existing check_board_* function names/behavior actually match
  required section names exactly: board-persistence-shape, board-connect-gestures,
  board-pairs, board-inventory, board-widths, board-palette-floors-*, board-plot-node-budget,
  board-unflagged-file-url, board-no-launch-flags, board-all-sections-wrapped.
  Existing funcs use different section-string names in their `section(...)` calls
  (e.g. check_board_persistence's section() call may say something other than
  "board-persistence-shape") -- MUST VERIFY by grep, not assume.

## Next step
1. grep each check_board_* function's `section(...)` first-arg string to check it matches
   required grep-target names exactly (case C1-C7).
2. Read argparse setup (search `add_argument.*--bench` in verify.py) to add `--board`.
3. Wire `if args.all or args.board:` block into main(), mirroring bench block structure,
   reusing D-008 floor functions against board.html per C5.
4. Write check_board_no_launch_flags (ast) and check_board_all_sections_wrapped (ast) for C8/C9;
   retrofit run_section around beamline block too (needed for C9 to pass generally).
5. Do NOT re-read full files -- use sed -n ranges / grep -n throughout, context is tight.
6. Floors to measure: grep -c 'all_results.append' (was 46 pre-task) and
   grep -c 'results.append\|line(' -- measure on merge-base (b054481) and HEAD, paste both.

Context was at 51% before board.html/css/verify.py content had been read in detail --
budget is tight; work fast, avoid full-file Reads, prefer targeted sed/grep.
