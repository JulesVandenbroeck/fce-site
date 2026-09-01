# Context failsafe — the anchor at 50%, the handoff at 90%

*This is §8 of `.claude/shared/CLAUDE.md`, split out so that the ~200 lines only load when they
are needed. Read it when the watchdog fires, or when you can see you are heading for a limit.
Section numbers (§8.0 … §8.6) are unchanged; everything that cites "shared §8.x" means this file.*

---

A sub-agent that runs out of context mid-task does not fail politely. It gets compacted or
cut off, and what is lost is exactly the expensive part: the dead ends, the commands that
actually ran, the reason the third approach was abandoned. The work then has to be re-done
by a cold successor who repeats every one of those mistakes.

So: **at 50% you write an anchor and keep going; at 90% you stop and hand off.** Every role.
No exceptions except `scout`, which is covered at the end of this section.

### 8.0 The anchor at 50%

The handoff below is a *stop* procedure. Between "fine" and "stop" there was nothing, so a long
task that got compacted at 100k lost its reasoning with no artefact to show for it. The anchor
fills that gap, and it costs one file write.

**You cannot run `/compact`.** It is an interactive command; a sub-agent has no way to invoke it
and no way to shape what an automatic compaction keeps. A file on disk is the substitute, and it
is strictly better: compaction cannot touch it, and your successor can read it without loading
your transcript.

**At 50% — the watchdog will tell you — do two things and then carry on working.**

**1. Take a token audit.** Three questions, honestly:

- Am I re-reading files I already have in this transcript, or re-deriving facts I already
  established? Both are free to look up and expensive to repeat.
- Am I reading whole files where `grep -n` would answer the question? Read the range, not the file.
- Am I re-reading a file I just edited to check the edit landed? Never do this — `Edit` and
  `Write` fail loudly, so a silent success is proof enough.

**2. Write or refresh your anchor** at `.claude/handoff/<id>-<role>.anchor.md`, in the **primary
checkout** (§8.3 tells you how to find it — same rule as the handoff). **At most 25 lines:**

```markdown
# <id> <role> — anchor @ <pct>%
- Branch: `task/<id>-<slug>` @ <sha>, PR #<n>
- Criteria: C1-C6, checks=6 — met: C1 C2 C4 — open: C3 C5 C6
- Decided: <choice> because <reason>          <!-- one line each, the ones you would re-litigate -->
- Dead end: <what I tried> — <why it failed>  <!-- the expensive ones -->
- Next: <the exact next command or edit>
```

Refresh it whenever one of those lines stops being true — a decision made, a dead end hit, the
next step changing. It is cheap because it is a rewrite of 25 lines, never an append.

**The anchor is why the handoff is affordable.** At 90% you do not write §8.4 from scratch under
pressure; you *promote* the anchor — its "Dead end" lines are already the section §8.4 calls the
reason the handoff exists, and its criteria line is already the status table. Leave the anchor
file in place; the orchestrator archives both together.

### 8.1 When to trigger

Trigger the handoff the moment **any** of these is true:

- your context is at or past **90%** — a harness warning that context is low, that
  auto-compaction is imminent, or your own honest estimate;
- the orchestrator sends you the message `HANDOFF NOW` (it triggers this when *its* own
  session crosses 90%, so that the whole session can be handed over at once);
- you are about to start something you can see you do not have the budget to finish — a
  full-suite run plus its fixes, reading a 2000-line file, a fourth review cycle.

**You are not the only thing watching.** A `PostToolUse` hook —
`.claude/scripts/context-watchdog.sh`, registered in `.claude/settings.json` — reads your own
transcript after every tool call, sums the tokens of your last turn, and injects a warning at
50% (§8.0, the anchor), 75% (stop opening new work) and 90% (this section). It fires once per
threshold per session, for every role, because each role has its own transcript. When it fires
at 90% it is telling you to run this section now, and it is measuring rather than guessing, so
it wins over your own estimate.

It is a backstop, not a licence to stop paying attention. It cannot see a turn you are
*about* to take — the 2000-line file, the fourth review cycle — so the third trigger above is
still yours to judge. If your window is not 200k tokens, set `FCE_CONTEXT_LIMIT` in the
environment; the script assumes 200k otherwise.

**Do not gamble on finishing.** Being cut off two steps from done still loses the two steps
*and* everything you learned getting there. Crossing the line and continuing is the failure
this section exists to prevent — it has no upside, because the handoff makes the work
resumable at exactly the point you stopped.

**Compaction is not a substitute.** It keeps the summary and drops the specifics, and the
specifics are what the successor needs. That is also why §8.0's anchor lives on disk rather
than in your head: it is the one thing a compaction cannot take.

### 8.2 What to do, in this order

Order matters. Every step assumes the one before it happened.

1. **Stop.** Finish the edit currently in your hands — do not start another. Do not begin a
   new tool call that reads or generates a large amount of text.
2. **Commit and push everything.** Uncommitted work does not survive, and this project has
   already lost a session's work to exactly that. On your task branch:
   ```bash
   git add -A && git commit -m "wip(<task-id>): handoff at context limit — <one line>"
   git push -u origin task/<id>-<slug>
   git rev-parse HEAD          # the SHA goes in the handoff
   ```
   Commit even if tests are red. A red commit that is described is worth more than a clean
   working tree that is gone. Say plainly in the handoff that it is red.
3. **Write the handoff file** — template in §8.4, location in §8.3. If you have an anchor from
   §8.0, promote it: its dead ends and its criteria line go straight in, and you are writing
   the gaps rather than the whole thing. Leave the anchor file where it is.
4. **Report to the orchestrator** with the short form in §8.5, and stop. Do not pick the
   task back up "while you wait".

### 8.3 Where the handoff goes

Handoffs live in **`.claude/handoff/` in the primary checkout**, never on a task branch —
the orchestrator reads them from `main`, and a file that exists only on your branch is a
file it cannot see.

If you are working in a worktree, `.claude/handoff/` in *your* directory is the wrong one.
Resolve the primary checkout first:

```bash
MAIN=$(dirname "$(git rev-parse --git-common-dir)")   # primary checkout, from any worktree
mkdir -p "$MAIN/.claude/handoff"
```

Name the file **`<task-id>-<role>-<cycle>.md`**, lowercase: `b-014-backend-1.md`,
`d-009-design-2.md`, `f-006-review-1.md`. If that exact name already exists — you are the
second agent to hand off on the same task and cycle — append `-b`, and say in the file which
one you are continuing from.

**Do not commit the handoff onto your task branch.** That is why step 2 comes before step 3:
you commit and push your work first, then write the file, and it stays untracked until the
orchestrator picks it up from `main`. If you are working directly in the primary checkout with
your task branch checked out, leave it untracked — do not `git add` it, and do not let a later
`git add -A` sweep it in.

Handoff files are bookkeeping, not source. The orchestrator commits them to `main` under its
carve-out. **Nothing in `.claude/handoff/` is ever deleted**; consumed handoffs are moved to
`.claude/handoff/archive/`.

### 8.4 The handoff file

Write it for a successor who knows **nothing** — not your task, not this conversation, not
what you tried. It is the only thing they get besides the dispatch. Assume the orchestrator
that dispatched you is also gone.

Concrete beats complete: exact paths, exact commands, exact SHAs. If you find yourself
writing "the usual test command", write the command.

**Cite, do not paste** (§7) applies here too: no source excerpts, five lines at the outside.
The criteria are the deliberate exception — those stay verbatim, because a handoff may be the
only copy if the PR was never opened.

```markdown
# Handoff: <task ID> — <title>

- **Role:** backend-coder | frontend-coder | design-coder | code-reviewer
- **Written:** <YYYY-MM-DD HH:MM>, at ~<n>% context
- **Cycle:** <review cycle this belongs to, 1 if none yet>
- **Continues:** <earlier handoff file, or "nothing — first handoff on this task">

## The task as I was given it
<Goal, verbatim. Then the File scope, verbatim — the exact list of paths I was allowed to
touch. Then every acceptance criterion with its Check: and Expect: lines, verbatim.
Copy these; do not paraphrase them. The successor is re-dispatched from this file, and a
paraphrased scope is how a task quietly grows.>

## State of the branch
- Branch: `task/<id>-<slug>` — pushed: yes/no
- HEAD: `<full SHA>` — <one line on what that commit contains>
- PR: #<n> / not opened yet
- Working tree at handoff: clean / <what is dirty and why it could not be committed>
- Tests at HEAD: <command> → <real result, including "red — 3 failing, listed below">

## Acceptance criteria — where each one stands
- [x] <criterion> — met. `<command>` → `<output>`
- [ ] <criterion> — not met. `<command>` → `<output>`. <what is missing>
- [?] <criterion> — unknown, never run. <why not>

## Done
- `<file:line>` — <what changed and why>

## Not done, in the order I would do it
1. <the next concrete action, specific enough to start on without re-deriving anything>
2. <...>

## Dead ends — do not repeat these
- <what I tried, what happened, why it cannot work>

**This section is the reason the handoff exists.** Everything else can be recovered from
git and the dispatch; this cannot. Write it even when it is embarrassing, and especially
when the failure was subtle. If you truly tried nothing that failed, write "none".

## Open questions for the orchestrator
- <anything I would have stopped and asked about — wrong file scope, a criterion with no
  runnable command, a physics formula in the way. Or "none".>

## Environment notes
- <a running server on a port, a temp file, a venv in a fresh worktree, an export the
  successor needs — e.g. PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright. Or "none".>
```

**A reviewer's handoff carries one extra obligation.** A partial review is not a verdict.
List every criterion you ran with its real output so the successor does not re-run them, list
the findings you have so far at their honest severity, and end the file with
`VERDICT: pr=<n> cycle=<c> verdict=incomplete-handoff` — never `approve`, never `rework`.
An interrupted review that reports `approve` is how unreviewed code reaches `main`.

### 8.5 What you report back

Do not restate the file. The orchestrator may itself be near its limit.

```markdown
## Handoff: <task ID> — <title>

- Reason: context at ~<n>% / orchestrator requested
- Handoff file: `.claude/handoff/<file>.md`
- Branch: `task/<id>-<slug>` @ `<SHA>` — pushed, PR #<n> / no PR yet
- Criteria: <n> met, <n> not met, <n> unrun
- Next action: <one line>
- Blocking question: <one line, or "none">
```

### 8.6 `scout` never hands off

`scout` answers one narrow question and is cheap to re-run. If it is somehow near its limit,
it returns the facts it has already enumerated, says `partial: <what is not covered>`, and
stops. It writes no file. A handoff for a lookup costs more than the lookup.
