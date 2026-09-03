# Orchestrator anchor — 2026-09-03, refreshed at the 75% soft threshold

**Budget:** 76% of the 5h limit at the time of writing; window resets 17:00. **No new work
dispatched from here.** One agent is in flight: B-013 cycle 4 (backend-coder, worktree).

## In flight
- **B-013 #17 cycle 4** — dispatched after the user's ruling at the §5.7 limit. Head at dispatch
  `5782fa8`. Collect it, run the §5.1 gate, and if it is clean dispatch the cycle-4 reviewer.
  If the budget will not carry a review, leave the PR open and say so — do not merge unreviewed.

## Not dispatched, ready to go next session
- **D-010 #25 cycle 2** — the review is posted (comment `5524842859`) and the findings are written
  into `design.md` in full. R1, R2, M1, M3, M4 are all "the instrument cannot fail"; **M2 is the
  only finding against the design** (fixed 704x512 canvas in a collapsible region: at 768 the
  region is 80px and shows nothing). Dispatch design-coder at high effort with the comment URL and
  the finding IDs. checks stay 9 — R1/R2 repair existing checks, they do not add criteria.
- **B-008 #19** — §5.7 limit already, M3 open. Re-dispatch is **cycle 3, not 4**; escalate if it
  does not close 0R/0M.
- **B-014 #18** — cycle 1, gate reproduced, reviewer never returned a verdict. Re-dispatch the
  reviewer, still cycle 1.
- **F-002** — links `tokens.css` into `base.html`; first thing to render the shipped woff2.

## The lesson this session paid for twice, in two different roles
**An `Expect:` that enumerates adversarial examples is a floor, not a proof.** B-013 cycles 2 and 3
and D-010's R1/R2/M4 are the same defect: I specified *which mutations must fail* instead of
requiring an instrument that is decidable. The reviewer then defeats it with the mutation I did
not think of. Before writing an `Expect:`, ask whether the property is decidable by that
instrument **at all** — a regex over English is not, in either direction.

## Dead ends
- Do not extend B-013's negation cue list. That is the retracted approach; C6/C7 are retired and
  replaced by C8's golden-string pin, my decision, on the user's ruling.
- Do not read D-010's "a truer wording goes red" as a finding once C8 lands — under a golden pin
  that is correct behaviour.
- A bare `pytest` in a fresh worktree collects nothing; use its own `./.venv/bin/python -m pytest`.
- `verify.py --all` needs ~14 min; give it 1200s. It exits 1 by design with `board-lane-fill` red.
