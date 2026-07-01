---
description: Pick and execute the next open sub-issue on the current branch's parent epic, using the documentation or code workflow as appropriate.
---

Pick **one** of the two workflows below depending on the deliverable type. Use **Documentation workflow** for docs under `docs/`, **Code workflow** for implementation under `pkg/`, `internal/`, `cmd/`.

## Precondition — run inside a worktree

`do-work` runs inside the git worktree that `/gh-issue-pop` created; it never creates the branch itself. Before anything else, confirm you are on a feature branch, not `main`:

```bash
branch=$(git branch --show-current)
case "$branch" in
  gh-*) : ;;   # ok: a pop-created worktree branch
  *) echo "Not on a worktree branch (current: '$branch'). Call /gh-issue-pop <issue> first, then run /do-work inside the worktree."; exit 1 ;;
esac
```

If this check fails, stop — report "call /gh-issue-pop first" and do not implement anything on `main`.

## Task Priority

When selecting from available sub-issues, **prefer documentation sub-issues over code sub-issues**. Documentation establishes the design before implementation begins.

## When a Sub-Issue Is Too Big

If a sub-issue turns out larger than one `do-work` pass (more than ~700 LOC or ~5 files, or spanning multiple subsystem boundaries), do not implement it and do not run `/gh-issue-pop` — nested worktrees are not supported. Split it into smaller **sibling** sub-issues under the same epic with `/gh-issue-push`, attach them to the epic, and close the oversized sub-issue as decomposed (a comment linking the new ones). Keep working the new sub-issues in the current worktree. One worktree, one PR per epic; decomposition stays flat.

## How to Choose

1. Determine the parent issue number from the current branch name:

   ```bash
   git branch --show-current  # e.g. gh-42-add-scaffold-validation -> parent is #42
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

| Deliverable       | Workflow                                                  | Indicators                                                                                                                          |
|-------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **Documentation** | [Documentation Workflow](#documentation-workflow)         | Output path under `docs/`; has "Required sections", "Format rule", or doc format name                                              |
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
2. **Run `mage analyze`** to validate documentation consistency. Fix any issues before proceeding.
3. **Calculate metrics**: tokens used; run `mage stats:loc` for LOC and doc word counts
4. **Log metrics and close**:

   ```bash
   gh issue comment <number> --repo <owner>/<repo> --body "tokens: <count>"
   gh issue close <number> --repo <owner>/<repo>
   ```

5. **Commit** changes:

   ```bash
   git add -A
   git commit -m "Add <doc name> (<output path>) (GH-<parent>#<sub-issue>)

   Stats:
     Lines of code (Go, production): <prod_loc> (+<delta>)
     Lines of code (Go, tests):      <test_loc> (+<delta>)
     Words (documentation):          <doc_words> (+<delta>)

   Skill: do-work
   Called-by: gh-issue-pop"
   git push
   ```

6. If you found follow-up work, file it with `gh issue create`

## 5. After completing the last sub-issue (documentation)

When you close a sub-issue and the open count drops to 0:

1. **Review all docs** created or modified during the epic for consistency
2. **Verify parent issue acceptance criteria**
3. **Evaluate use case completion**:
   - Identify which use case(s) this epic contributes to
   - If all criteria are met, update road-map.yaml to mark the use case status as "done"
4. **File follow-up issues** for any gaps via `gh issue create`
5. **Execute `/gh-issue-pop` Phase 5** in full to open and merge the PR

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

## 4. After implementation

1. **Run any tests** to verify your work
2. **Calculate metrics**: tokens used; run `mage stats:loc` for LOC deltas
3. **Log metrics and close**:

   ```bash
   gh issue comment <number> --repo <owner>/<repo> --body "tokens: <count>"
   gh issue close <number> --repo <owner>/<repo>
   ```

4. **Commit** changes. **Commit message must mention which PRDs are implemented**:

   ```bash
   git add -A
   git commit -m "Implement X (prd-feature-name) (GH-<parent>#<sub-issue>)

   - Description of changes

   Stats:
     Lines of code (Go, production): <prod_loc> (+<delta>)
     Lines of code (Go, tests):      <test_loc> (+<delta>)
     Words (documentation):          <doc_words> (+<delta>)

   Skill: do-work
   Called-by: gh-issue-pop"
   git push
   ```

5. If you discovered new work, file it with `gh issue create`

## 5. After completing the last sub-issue (code)

When you close a sub-issue, check the open count:

```bash
gh api repos/<owner>/<repo>/issues/<parent>/sub_issues \
  --jq '[.[] | select(.state=="open")] | length'
```

If it reaches 0, perform a **thorough code inspection**:

1. **Read all files** created or modified during the epic
2. **Check for inconsistencies**: naming conventions, error handling, duplication, test coverage gaps
3. **Verify parent issue acceptance criteria**
4. **Run full test suite** and any integration tests
5. **File follow-up issues** for technical debt or improvements via `gh issue create`
6. **Check for doc updates needed**: if implementation revealed design changes, ask the user before updating architecture or PRD docs
7. **Evaluate use case completion**:
   - Identify which use case(s) this epic contributes to
   - If all criteria are met, update road-map.yaml to mark the use case status as "done"
8. **Execute `/gh-issue-pop` Phase 5** in full to open and merge the PR
9. **Summarize epic completion**: run `mage stats:loc` and report what was built, total metrics, deviations, follow-up work, use case status

---

## Important Notes

- All tracking is via `gh issue` and `gh api`
- Token usage goes in a GitHub comment: `gh issue comment <number> --body "tokens: <count>"`
- Follow-up work goes in new GitHub issues: `gh issue create --repo <owner>/<repo>`
- Always run `mage stats:loc` and include the full Stats block in commit messages
- Always push after every commit: `git push`
- **Update road-map.yaml** when use cases are completed

## Worktree Discipline

1. **Verify you are inside the correct worktree** before starting work:

   ```bash
   pwd                        # should be ../gh-<number>-<slug>
   git branch --show-current  # should show gh-<number>-<slug>
   ```

   If you are in the main repo directory, `cd ../gh-<number>-<slug>` first. The main repo stays on `main`.

2. **All commits go to the worktree branch** (run `git add` and `git commit` from inside the worktree). Push after every commit.

3. **When the open sub-issue count reaches 0**, execute `/gh-issue-pop` Phase 5 automatically.
