---
description: "Work one unit from the epic you popped. Pick the workflow by deliverable:"
---

Execute the /do-work command. The full workflow follows; treat any
text after the prompt invocation as its arguments ($ARGUMENTS).

# Command: Do Work

Work one unit from the epic you popped. Pick the workflow by deliverable:
**Documentation** for YAML under `docs/`, **Prose** for writing a person reads
start to finish, **Code** for implementation.

## Precondition — run inside a worktree

`do-work` never creates a branch; it runs inside the worktree a pop command
made. Confirm that first, and stop if it fails — nothing gets implemented on
`main`.

```bash
branch=$(git branch --show-current)
case "$branch" in
  gh-*|bd-*) : ;;
  *) echo "Not on a worktree branch ('$branch'). Run /gh-issue-pop <issue> or /bd-issue-pop <bead> first."; exit 1 ;;
esac
```

## Tracker mode — gh issues or beads

```bash
[ -d .beads ] && echo "beads mode" || echo "gh mode"
```

The steps below are written in gh mode. In beads mode substitute:

| Step | gh mode | beads mode |
|---|---|---|
| Parent/epic id | issue number from `gh-<n>-<slug>` | bead id from `bd-<id>-<slug>` |
| List open units | `gh api …/sub_issues` (open) | `bd ready --label <id>` (this epic's unblocked children) |
| Read a unit | `gh issue view <n> --json body` | `bd show <child-id>` |
| Claim a unit | `gh issue edit <n> --add-assignee @me` | `bd update <child-id> --status in_progress` |
| Log completion | `gh issue comment <n> …` | `bd comment <child-id> "Actual LOC: …"` |
| Close a unit | `Closes #<n>` in the commit, auto-closes at merge | `bd update <child-id> --status done`, then `bd sync` |
| All units done → PR | `/gh-issue-pop` Phase 5 | `/bd-issue-pop` Phase 5 |
| File follow-up | `gh issue create` | `bd create "<title>" --label <id>` |

Confirm `bd` flags against the installed version (`bd ready --help`).
Everything else — how to write the doc or the code, the real-work bar, the
Stats block — is identical in both modes.

**Beads state is tracker state, not PR payload.** One database lives in the
main checkout (`.beads/beads.db`, gitignored); worktrees reach it through a
`.beads/redirect` that beads writes on first use. If `bd` cannot find the
database, run `bd sync`. Only `issues.jsonl` is tracked, and it sits on
`main` — so the code branch carries code and nothing else:

- close each child with `bd update <child-id> --status done`, then `bd sync`
  to persist;
- never `git add .beads/` on the code branch, and never put `Closes …` in a
  commit for a bead;
- `bd ready` reflects closes immediately, so the queue advances mid-session.

gh mode is the opposite: the commit's `Closes #<n>` does the closing at merge.
In beads mode the merge closes nothing.

## Choosing and sizing a unit

Prefer documentation units over code units — the design should exist before
the implementation does.

If a unit is bigger than you can finish reliably in one pass (your judgment,
not a line count), do not implement it and do not pop again — nested worktrees
are unsupported. Split it into **sibling** units under the same epic
(`/gh-issue-push`, or `bd create --label <epic-id>` plus `bd dep add` edges),
close the oversized one as decomposed with a comment linking the new ones, and
keep working in the current worktree. One worktree, one PR per epic;
decomposition stays flat.

## Pick a unit

The parent id is in the branch name (`gh-42-…` → #42, `bd-<id>-…` → that epic).
List its open units, read their bodies to classify them, and claim one:

```bash
gh api repos/<owner>/<repo>/issues/<parent>/sub_issues \
  --jq '[.[] | select(.state=="open") | {number, title}]'
gh issue view <number> --repo <owner>/<repo> --json body -q .body
gh issue edit <number> --repo <owner>/<repo> --add-assignee @me
```

| Deliverable | Workflow | Recognise it by |
|---|---|---|
| **Documentation** | [Documentation](#documentation-workflow) | output under `docs/`; names a format rule or required sections |
| **Prose** | [Prose](#prose-workflow) | continuous English a person reads start to finish — paper section, README, post |
| **Code** | [Code](#code-workflow) | output under `pkg/`, `internal/`, `cmd/`; acceptance stated as tests or behaviour |

Documentation and Prose split on whether the output has a voice: a PRD is read
by field, a paper section is read as writing, and how it sounds is part of
whether it is right.

---

## Finishing a unit

Identical for every deliverable type. The workflow sections below state only
what differs.

1. **Verify the Acceptance Criteria** from the sub-issue body.
2. **Run the repo's consistency check** — `mage audit`, or `mage analyze` where
   the target is named that way. Fix what it reports. Skip if the repo defines
   neither.
3. **Log completion.** The `Actual LOC` line is required; a unit is not done
   without it.

   ```bash
   gh issue comment <number> --repo <owner>/<repo> --body "Completed in commit <sha>.

   <summary of work>

   Actual LOC: <from mage stats deltas> (Estimated: <this issue's Estimated LOC>)
   tokens: <count>"
   ```

   **gh mode:** do not close the sub-issue by hand — the commit's
   `Closes #<number>` auto-closes it at merge. **Beads mode is the opposite:**
   nothing auto-closes, so close the child now with
   `bd update <child-id> --status done` then `bd sync`, and never
   `git add .beads/` on the code branch.

4. **Commit and push.** Code commits must name the PRDs they implement.

   ```bash
   git add -A
   git commit -m "<what changed> (GH-<parent>)

   Closes #<sub-issue>

   Stats:
     Lines of code (Go, production): <prod_loc> (+<delta>)
     Lines of code (Go, tests):      <test_loc> (+<delta>)
     Words (documentation):          <doc_words> (+<delta>)

   Skill: do-work
   Called-by: gh-issue-pop"   # beads mode: Called-by: bd-issue-pop
   git push
   ```

5. **File follow-up work** you found: `gh issue create`, or
   `bd create "<title>" --label <epic-id>`.

## Finishing the last unit

When no open unit remains, before handing off:

1. Review everything the epic produced for consistency — docs read together,
   code inspected for naming, error handling, duplication, and coverage gaps.
2. Verify the parent issue's acceptance criteria.
3. Run the full test suite.
4. Evaluate use-case completion; if the criteria are met, mark it done in
   `road-map.yaml`.
5. File follow-ups for gaps and technical debt.
6. If implementation revealed design changes, ask before editing architecture
   or PRD docs.
7. **Execute the matching pop command's Phase 5 in full** — it opens the PR,
   merges to `main`, and closes the epic.

---

## Documentation Workflow

**YAML documentation** under `docs/`: PRDs, use cases, test suites,
ARCHITECTURE, engineering guidelines, SPECIFICATIONS.

Read `docs/VISION.yaml` and `docs/ARCHITECTURE.yaml` for context, plus the
existing files of the same type for consistency.

From the sub-issue body take the **output path**, the **format rule**, and the
**Required Reading** list — read all of it. Read the format rule itself from
`docs/constitutions/design.yaml` (`document_types`).

Produce the deliverable at the exact output path, with every field the format
rule requires, following the repo's documentation standards. Then
[finish the unit](#finishing-a-unit).

## Prose Workflow

Use this workflow when the deliverable is **prose a person reads**: a paper or
article section, a README, a design narrative, a post. Not YAML specs — those
are the Documentation workflow.

Task selection, the completion comment with `Actual LOC`, the commit and Stats
block, and the last-unit Phase 5 handoff are all identical to the Documentation
workflow. Only the writing differs, and only in two ways.

### 1. Learn the voice before drafting

If the repository carries a `writing-voice/` directory (the discovery rule
walks up from the output file), **invoke the `match-structure` skill** to
retrieve the exemplars nearest this deliverable in topic and register, and
match what they do: sentence rhythm, how much hedging, how claims get made,
whether the prose explains or asserts. No `writing-voice/`, no change — write
to the repo's documentation standards.

Do this before drafting, not after. A draft written without a target register
and then corrected toward one keeps its original skeleton and reads like a
translation. The samples are cheap to read and expensive to retrofit.

### 2. Scan the prose before committing

**Invoke the `filter-tells` skill** on your own output. Prose written by a
model is exactly what its detectors exist for, and shipping unchecked because
you wrote it yourself is the failure mode.

Fix what fires. A flag is a prompt to look, not a verdict — a term of art that
trips the lexical scan stays, and you say so in the completion comment rather
than damaging the sentence to silence a grep.

When the prose has to stop sounding model-written and rewriting it yourself is
not getting there, **invoke `match-voice`**: it sends the passage to a
different model family with the same anchors and gates the result.

### 3. External check (optional, usually skipped)

`filter-tells` is a denylist you have just been writing against, so its silence
is weak evidence that the prose reads as human. Its external-detector step is
independent of that, and most repositories will not have it configured — no
key means **skip it and move on**, which is the normal state, not a degraded
one, and it never blocks committing prose.

If a key is present, it still is not permission: the check uploads the document
to a third party that retains it. Ask about this specific file first, every
time, per the upload rule in the `writing-voice/` directory rule.

Each skill owns its own invocation details. Naming their scripts here is how a
rename turns into an eight-file edit.

---

## Code Workflow

**Implementation**: packages, internal logic, cmd, workers, tests. Code must
correspond to existing PRDs and architecture (the code-prd-architecture-linking
rule), and commits must name the PRDs.

Read `docs/VISION.yaml` and `docs/ARCHITECTURE.yaml`, the PRDs the sub-issue
names, and its Requirements / Design Decisions / Acceptance Criteria in full.
Read every file in Required Reading before touching it — **never propose
changes to code you have not read**.

Implement to the Requirements and Design Decisions. Write the tests the
sub-issue or PRD specifies, and verify the Acceptance Criteria hold as
behaviour, not as intent.

Do not write comments that rot. No `release 00.X`, `stub`, `placeholder`, `for
now`, `not yet`, or `will be` unless they mark genuinely deferred work, and
when you touch a file, resolve any existing comment that references a completed
release, a removed symbol, or a deferral that is no longer true. Sweep before
committing:

```bash
grep -nE "release 0|stub|placeholder|removed now|not yet|will be|for now" <changed files>
```

Then [finish the unit](#finishing-a-unit).

## Worktree discipline

**One worktree, one PR per epic.** Every unit lands on the same pop-created
branch; `do-work` never branches per unit. Work from inside the worktree
(`pwd` should be `../gh-<n>-<slug>` or `../bd-<id>-<slug>`) — the main checkout
stays on `main`.

Push after every commit. Always run `mage stats` and include the full Stats
block. Update `road-map.yaml` when a use case completes.

When no open unit remains — sub-issue count reaches zero, or
`bd ready --label <id>` returns nothing for this epic — run the matching pop
command's Phase 5 automatically. The last `do-work` pass finishes the epic end
to end.
