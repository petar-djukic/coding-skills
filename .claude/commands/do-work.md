<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Command: Do Work

Pick **one** of the three workflows below depending on the deliverable type. Use **Documentation workflow** for YAML docs under `docs/`, **Prose workflow** for writing a person reads start to finish (paper sections, README, posts), **Code workflow** for implementation under `pkg/`, `internal/`, `cmd/`.

## Precondition — run inside a worktree

`do-work` runs inside the git worktree that `/gh-issue-pop` or `/bd-issue-pop` created; it never creates the branch itself. Before anything else, confirm you are on a pop-created feature branch, not `main`:

```bash
branch=$(git branch --show-current)
case "$branch" in
  gh-*|bd-*) : ;;   # ok: a pop-created worktree branch (gh issues or beads)
  *) echo "Not on a worktree branch (current: '$branch'). Call /gh-issue-pop <issue> (or /bd-issue-pop <bead>) first, then run /do-work inside the worktree."; exit 1 ;;
esac
```

If this check fails, stop — report "call the matching pop command first" and do not implement anything on `main`.

## Tracker mode — gh issues or beads

`do-work` works either tracker. Detect which the repo uses and apply the matching operations throughout:

```bash
[ -d .beads ] && echo "beads mode" || echo "gh mode"
```

- **gh mode** (`gh-*` branch, no `.beads/`): parent issue and sub-issues via `gh api` / `gh issue`, as written in each step below.
- **beads mode** (`bd-*` branch, `.beads/` present): the epic and its child beads via `bd`. Translate each tracker operation:

  | Step | gh mode | beads mode |
  |---|---|---|
  | Parent/epic id | issue number from `gh-<n>-<slug>` | bead id from `bd-<id>-<slug>` |
  | List open units | `gh api …/sub_issues` (open) | `bd ready --label <id>` (this epic's unblocked children, per the parent-id label) |
  | Read a unit | `gh issue view <n> --json body` | `bd show <child-id>` |
  | Claim a unit | `gh issue edit <n> --add-assignee @me` | `bd update <child-id> --status in_progress` |
  | Log completion | `gh issue comment <n> …` | `bd comment <child-id> "Actual LOC: …"` |
  | Close a unit | `Closes #<n>` in the commit (auto-close on merge) | `bd update <child-id> --status done`, then `bd sync` (persists the tracker; never `git add .beads/` on the code branch) |
  | All units done → PR | `/gh-issue-pop` Phase 5 | `/bd-issue-pop` Phase 5 |
  | File follow-up | `gh issue create` | `bd create "<title>" --label <id>` |

  Confirm the exact `bd` flags with `bd ready --help` / `bd update --help` and use the installed forms. Everything else — how to write the doc or the code, the real-work bar, `mage stats`, the Stats block — is identical in both modes.

  **Beads and worktrees — read this before running `bd` in the worktree.** Beads keeps one database (`.beads/beads.db`, gitignored) in the *main* repo checkout; only `issues.jsonl` is tracked. A git worktree does not have its own database — it uses a `.beads/redirect` file that points at the main repo's `.beads/`, so every worktree shares the one database. Beads creates that redirect automatically the first time you run `bd` inside a worktree; if a `bd` command in the worktree reports it cannot find the database, run `bd sync` (which sets up the redirect and rebuilds from `issues.jsonl`), or write the relative path to the main repo's `.beads/` into `.beads/redirect`.

  Because of that, **bead state is tracker state, not PR payload.** It lives in the shared database and its `issues.jsonl`, which sits on `main` — it is not carried on the code branch and does not merge with the code PR. So in beads mode:
  - close each child explicitly with `bd update <child-id> --status done`, then `bd sync` to persist the tracker to git (beads handles the `issues.jsonl` write and commit/push);
  - **do not** `git add .beads/` on the code branch, and do not put a `Closes …` line in the commit for a bead — the code branch carries only code;
  - `bd ready` reflects the close immediately (shared db), so the queue advances during `do-work`.
  gh mode is different: there the `Closes #<n>` in the commit auto-closes the sub-issue at merge. Beads has no such auto-close — the merge closes nothing; `bd` + `bd sync` do.

## Task Priority

When selecting from available sub-issues, **prefer documentation sub-issues over code sub-issues**. Documentation establishes the design before implementation begins.

## When a Sub-Issue Is Too Big

If a unit is bigger than you can complete reliably in one `do-work` pass — your own judgment, not a fixed line or file count — do not implement it and do not run a pop command (nested worktrees are not supported). Split it into smaller **sibling** units under the same epic — `/gh-issue-push` in gh mode, or `bd create "<title>" --label <epic-id>` plus `bd dep add` edges in beads mode — each sized to what you can finish reliably on its own, and close the oversized unit as decomposed (a comment linking the new ones). Keep working the new units in the current worktree. One worktree, one PR per epic; decomposition stays flat.

## How to Choose

The steps below show gh mode; in beads mode substitute the beads operations from the Tracker mode table (epic id from the `bd-<id>-<slug>` branch, `bd ready --label <id>` for the open units, `bd show`/`bd update` to read and claim).

1. Determine the parent issue number from the current branch name:

   ```bash
   git branch --show-current  # gh-42-... -> parent #42;  bd-<id>-... -> epic <id>
   ```

2. List open sub-issues on the parent:

   ```bash
   gh repo view --json nameWithOwner -q .nameWithOwner  # get <owner>/<repo>
   gh api repos/<owner>/<repo>/issues/<parent>/sub_issues \
     --jq '[.[] | select(.state=="open") | {number: .number, title: .title}]'
   ```

3. Read the body of each open sub-issue to determine type:

   ```bash
   gh issue view <number> --repo <owner>/<repo> --json body -q .body
   ```

4. Pick a sub-issue and claim it by assigning yourself:

   ```bash
   gh issue edit <number> --repo <owner>/<repo> --add-assignee @me
   ```

| Deliverable      | Workflow                                                  | Indicators                                                                                                                          |
|------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **Documentation** | [Documentation Workflow](#documentation-workflow)         | Output path under `docs/`; has "Required sections", "Format rule", or doc format name                                             |
| **Prose**         | [Prose Workflow](#prose-workflow)                          | Output is continuous English a person reads start to finish: paper or article sections, README, blog post, design narrative. Markdown or LaTeX, not a YAML schema |
| **Code**          | [Code Workflow](#code-workflow)                           | Output under `pkg/`, `internal/`, `cmd/`; has Requirements, Design Decisions, Acceptance Criteria with tests or observable behaviour |

Documentation and Prose split on whether the output has a voice. A PRD fills in
a schema and is read by field; a paper section is read as writing, and how it
sounds is part of whether it is right.

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

## Important Notes

- Tracking is via `gh issue`/`gh api` in gh mode, or `bd` in beads mode (see the Tracker mode table). In beads mode, persist tracker changes with `bd sync` (it writes and pushes `issues.jsonl` from the shared main-repo database); do not hand-commit `.beads/` on the code branch
- Token usage goes in a completion comment: `gh issue comment` (gh) or `bd comment` (beads)
- Follow-up work goes in a new unit: `gh issue create` (gh) or `bd create "<title>" --label <epic-id>` (beads)
- Always run `mage stats` and include the full Stats block in commit messages
- Always push after every commit: `git push`
- **Update road-map.yaml** when use cases are completed

## Worktree Discipline

One worktree, one PR per epic. Every unit of work — every sub-issue or child bead — is implemented on the same shared worktree branch; `do-work` never creates a branch or worktree per unit.

1. **Verify you are inside the correct worktree** before starting work:

   ```bash
   pwd                        # should be ../gh-<n>-<slug> or ../bd-<id>-<slug>
   git branch --show-current  # should show the pop-created branch
   ```

   If you are in the main repo directory, `cd` into the worktree first. The main repo stays on `main`.

2. **All commits go to the shared worktree branch** (run `git add` and `git commit` from inside the worktree). Push after every commit. Do not branch per unit — the epic's children all land on this one branch and close via its single PR.

3. **When no open unit remains** (open sub-issue count reaches 0, or `bd ready --label <id>` returns no child of this epic), execute the matching pop command's Phase 5 automatically — it merges the PR to `main` and closes the epic. The last `do-work` pass finishes the epic end to end.
