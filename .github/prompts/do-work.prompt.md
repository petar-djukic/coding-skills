---
description: "Pick **one** of the two workflows below depending on the deliverable type. Use **Documentation workflow** for docs under `docs/`, **Code workflow** fo"
---

Execute the /do-work command. The full workflow follows; treat any
text after the prompt invocation as its arguments ($ARGUMENTS).

# Command: Do Work

Pick **one** of the two workflows below depending on the deliverable type. Use **Documentation workflow** for docs under `docs/`, **Code workflow** for implementation under `pkg/`, `internal/`, `cmd/`.

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
  | Close a unit | `Closes #<n>` in the commit (auto-close on merge) | `bd update <child-id> --status done`, then `git add .beads/ && commit && push` |
  | All units done → PR | `/gh-issue-pop` Phase 5 | `/bd-issue-pop` Phase 5 |
  | File follow-up | `gh issue create` | `bd create "<title>" --label <id>` |

  Confirm the exact `bd` flags with `bd ready --help` / `bd update --help` and use the installed forms. Everything else — how to write the doc or the code, the real-work bar, `mage stats`, the Stats block — is identical in both modes.

  **Closing has no automatic path in beads.** gh mode relies on `Closes #<n>` in the commit to auto-close the sub-issue when the PR merges. Beads has no git-integrated auto-close: a `Closes …` line in a commit or PR body does nothing to a bead. So in beads mode you must close each child explicitly with `bd update <child-id> --status done` and commit the `.beads/` change to the worktree branch. That committed close travels with the PR and lands on `main` when it merges — the beads analogue of `Closes #` — while `bd ready` on the branch already sees the child closed, so the queue advances during `do-work`. Never rely on the merge to close a bead. The parent epic is closed the same way — explicitly, on the branch — as the first step of `/bd-issue-pop` Phase 5, so it travels with the PR too.

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
| **Code**          | [Code Workflow](#code-workflow)                           | Output under `pkg/`, `internal/`, `cmd/`; has Requirements, Design Decisions, Acceptance Criteria with tests or observable behaviour |

---

## Documentation Workflow

Use this workflow when the deliverable is **YAML documentation** under `docs/`: PRDs, use cases, test suites, ARCHITECTURE, engineering guidelines, SPECIFICATIONS.

Read docs/VISION.yaml and docs/ARCHITECTURE.yaml for context. For PRDs scan existing `docs/specs/product-requirements/`; for use cases `docs/specs/use-cases/`; for test suites `docs/specs/test-suites/`.

## 1. Select a documentation task

1. List open sub-issues and pick a documentation one (output path under `docs/`)
2. Assign yourself to claim it:

   ```bash
   gh issue edit <number> --repo <owner>/<repo> --add-assignee @me
   ```

## 2. Before writing

1. **Read the sub-issue body** and note:
   - **Output path** (exact file)
   - **Format rule** (e.g., prd-format, use-case-format, architecture-format)
   - **Required Reading** file list — read all of them
   - **Acceptance Criteria**

2. **Read the format rule** from `docs/constitutions/design.yaml` (document_types section)

3. Read any referenced existing content for consistency

## 3. Write the doc

1. Produce the deliverable at the exact output path given in the sub-issue body
2. Include all required fields from the format rule
3. Follow documentation standards from design.yaml (concise, active voice, no forbidden terms)
4. Verify the Acceptance Criteria

## 4. After writing

1. **Check completeness** against Acceptance Criteria and the format rule checklist
2. **Run the repo's consistency check** — `mage audit`, or `mage analyze` in repos that name the target that way — to validate documentation consistency. Fix any issues before proceeding. Skip if the repo defines neither.
3. **Calculate metrics**: tokens used; run `mage stats` for LOC and doc word counts
4. **Log completion** — the `Actual LOC` line is required; the sub-issue is not done without it:

   ```bash
   gh issue comment <number> --repo <owner>/<repo> --body "Completed in commit <sha>.

   <summary of work>

   Actual LOC: <production/test lines from mage stats deltas> (Estimated: <this issue's Estimated LOC>)
   tokens: <count>"
   ```

   gh mode: do not close the sub-issue manually — the commit's `Closes #<number>` auto-closes it when the PR merges. Beads mode is the opposite: there is no auto-close, so close the child now with `bd update <child-id> --status done` and commit the `.beads/` change (a `Closes …` line would do nothing to a bead).

5. **Commit** changes:

   ```bash
   git add -A
   git commit -m "Add <doc name> (<output path>) (GH-<parent>)

   Closes #<sub-issue>

   Stats:
     Lines of code (Go, production): <prod_loc> (+<delta>)
     Lines of code (Go, tests):      <test_loc> (+<delta>)
     Words (documentation):          <doc_words> (+<delta>)

   Skill: do-work
   Called-by: gh-issue-pop"   # beads mode: Called-by: bd-issue-pop
   git push
   ```

6. If you found follow-up work, file it with `gh issue create`

## 5. After completing the last sub-issue (documentation)

After completing work on a sub-issue, check whether all sub-issues have completion comments. If all have been completed:

1. **Review all docs** created or modified during the epic for consistency
2. **Verify parent issue acceptance criteria**
3. **Evaluate use case completion**:
   - Identify which use case(s) this epic contributes to
   - If all criteria are met, update road-map.yaml to mark the use case status as "done"
4. **File follow-up issues** for any gaps via `gh issue create`
5. **Execute the matching pop command's Phase 5 in full** (`/gh-issue-pop` or, in beads mode, `/bd-issue-pop`) — it opens the PR, merges it to `main`, and closes the epic (beads mode closes the parent bead on the branch first, so it merges too)

---

## Code Workflow

Use this workflow when the deliverable is **implementation**: packages, internal logic, cmd, workers, tests.

Follow the **code-prd-architecture-linking** rule: code must correspond to existing PRDs and architecture; commits must mention PRDs.

Read docs/VISION.yaml and docs/ARCHITECTURE.yaml for context.

## 1. Select a code task

1. List open sub-issues and pick a code one (output under `pkg/`, `internal/`, `cmd/`)
2. Assign yourself to claim it:

   ```bash
   gh issue edit <number> --repo <owner>/<repo> --add-assignee @me
   ```

## 2. Before implementing

1. **Identify related PRDs and docs** from the sub-issue body. Read them.
2. Read the sub-issue body (Requirements, Design Decisions, Acceptance Criteria) in full.
3. **Read existing code** that you will modify or extend:
   - Read all files listed in Required Reading
   - **NEVER propose changes to code you haven't read first**
   - Understand existing patterns, conventions, and interfaces

## 3. Implement

1. Implement according to Requirements and Design Decisions and the related PRDs/architecture
2. Verify the Acceptance Criteria are met (tests, behaviour, observability if specified)
3. Write tests if the sub-issue or PRD specifies them
4. Where appropriate, add a short comment listing implemented PRDs
5. Do not write comments that rot: no `release 00.X`, `stub`, `placeholder`, `for now`, `not yet`, or `will be` tags unless they mark genuinely deferred, unbuilt work. When you touch a file, update or delete any existing comment that references a now-completed release, a removed symbol, or a deferral that is no longer true. Before committing, sweep the files you changed — `grep -nE "release 0|stub|placeholder|removed now|not yet|will be|for now" <changed files>` — and resolve every stale hit.

## 4. After implementation

1. **Run any tests** to verify your work
2. **Calculate metrics**: tokens used; run `mage stats` for LOC deltas
3. **Log completion** — the `Actual LOC` line is required; the sub-issue is not done without it:

   ```bash
   gh issue comment <number> --repo <owner>/<repo> --body "Completed in commit <sha>.

   <summary of work>

   Actual LOC: <production/test lines from mage stats deltas> (Estimated: <this issue's Estimated LOC>)
   tokens: <count>"
   ```

   gh mode: do not close the sub-issue manually — the commit's `Closes #<number>` auto-closes it when the PR merges. Beads mode is the opposite: there is no auto-close, so close the child now with `bd update <child-id> --status done` and commit the `.beads/` change (a `Closes …` line would do nothing to a bead).

4. **Commit** changes. **Commit message must mention which PRDs are implemented**:

   ```bash
   git add -A
   git commit -m "Implement X (prd-feature-name) (GH-<parent>)

   Closes #<sub-issue>

   - Description of changes

   Stats:
     Lines of code (Go, production): <prod_loc> (+<delta>)
     Lines of code (Go, tests):      <test_loc> (+<delta>)
     Words (documentation):          <doc_words> (+<delta>)

   Skill: do-work
   Called-by: gh-issue-pop"   # beads mode: Called-by: bd-issue-pop
   git push
   ```

5. If you discovered new work, file it with `gh issue create`

## 5. After completing the last sub-issue (code)

After completing work on a sub-issue, check whether all sub-issues have completion comments. If all have been completed, perform a **thorough code inspection**:

1. **Read all files** created or modified during the epic
2. **Check for inconsistencies**: naming conventions, error handling, duplication, test coverage gaps
3. **Verify parent issue acceptance criteria**
4. **Run full test suite** and any integration tests
5. **File follow-up issues** for technical debt or improvements via `gh issue create`
6. **Check for doc updates needed**: if implementation revealed design changes, ask the user before updating architecture or PRD docs
7. **Evaluate use case completion**:
   - Identify which use case(s) this epic contributes to
   - If all criteria are met, update road-map.yaml to mark the use case status as "done"
8. **Execute the matching pop command's Phase 5 in full** (`/gh-issue-pop` or, in beads mode, `/bd-issue-pop`) — it opens the PR, merges it to `main`, and closes the epic (beads mode closes the parent bead on the branch first, so it merges too)
9. **Summarize epic completion**: run `mage stats` and report what was built, total metrics, deviations, follow-up work, use case status

---

## Important Notes

- Tracking is via `gh issue`/`gh api` in gh mode, or `bd` in beads mode (see the Tracker mode table) — commit and push `.beads/` after every bead status change so state is shared across machines
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
