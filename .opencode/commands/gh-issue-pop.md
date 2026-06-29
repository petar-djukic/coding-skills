---
description: Pop a GitHub issue into a worktree, decompose it into sub-issues, execute the work, and open a PR when done.
---

Pop a GitHub issue from the current repository, decompose it into GitHub sub-issues on a feature branch, and open a PR when all sub-issues are closed.

If the decomposition yields only one sub-issue, skip sub-issue creation entirely: work directly on the parent issue, add a comment describing what was done, and close it via the PR.

Sub-issue progress is visible directly on the parent issue page.

## Input

$ARGUMENTS

If arguments contain an issue number (e.g. `42` or `#42`), use that issue. If arguments contain a URL, extract the issue number. If no number is given, list open issues and ask the user to pick one.

## Phase 0 -- Detect Repository

1. Run `gh repo view --json nameWithOwner -q .nameWithOwner` and use the result as `<owner>/<repo>` for all `gh` commands below.

## Phase 1 -- Fetch the GitHub Issue

1. Fetch the issue:
   ```bash
   gh issue view <number> --repo <owner>/<repo> --json number,title,body,labels,state
   ```
2. If the issue is not open, stop and report its state.
3. Display the issue title, body, and labels to the user.

## Phase 2 -- Gather Project Context

1. Read docs/VISION.yaml, docs/ARCHITECTURE.yaml, docs/road-map.yaml, and `docs/constitutions/design.yaml`.
2. Read READMEs for product requirements and use cases relevant to the issue.
3. List open sub-issues already attached to this parent (in case this is a resumed session):
   ```bash
   gh api repos/<owner>/<repo>/issues/<number>/sub_issues --jq '[.[] | {number: .number, title: .title, state: .state}]'
   ```
4. Run `mage analyze` to identify spec issues.
5. Run `mage stats` for current LOC and documentation metrics.
6. Summarize the current project state.

## Phase 3 -- Propose Sub-Issues

Using the GitHub issue as the epic, propose sub-issues that decompose it into actionable work:

- Type: documentation or code
- Required Reading: mandatory list of files the agent must read
- Files to Create/Modify: explicit file list
- Structure: Requirements, Design Decisions (optional), Acceptance Criteria
- Code task sizing: 300-700 lines of production code, no more than 5 files
- No more than 10 sub-issues

Present the proposed breakdown to the user for approval. Do not create anything until the user agrees.

**Single-sub-issue rule:** If the natural breakdown is exactly one sub-issue, tell the user: "This fits in a single task — I'll work directly on the parent issue without creating a sub-issue." Proceed to Phase 4 (single-issue path) after approval.

## Phase 4 -- Create Worktree and Sub-Issues

After user approval:

1. Ensure the main repo is on `main` (the worktree keeps main untouched):

   ```bash
   git checkout main
   ```

2. Create a git worktree with a new branch:

   ```bash
   git worktree add ../gh-<number>-<slug> -b gh-<number>-<slug>
   ```
   The worktree lives at `../gh-<number>-<slug>` (sibling of the current repo directory).
   All subsequent work happens inside this worktree. Record the path: `WT=../gh-<number>-<slug>`

### If there are 2 or more sub-issues

1. Create each sub-issue on GitHub:
   ```bash
   gh issue create --repo <owner>/<repo> \
     --title "<sub-issue title>" \
     --body "<structured description with Required Reading, Files to Create/Modify, Requirements, Acceptance Criteria>"
   ```
   Capture the issue number returned for each sub-issue.

2. Link each sub-issue to the parent using the GitHub sub-issues API:
   ```bash
   gh api repos/<owner>/<repo>/issues/<parent-number>/sub_issues \
     --method POST \
     --field sub_issue_id=<sub-issue-database-id>
   ```
   Get the database ID with: `gh api repos/<owner>/<repo>/issues/<sub-number> --jq '.id'`
   Repeat for each sub-issue. The parent issue will show a progress checklist.

3. Commit an initial marker in the worktree:
   ```bash
   cd ../gh-<number>-<slug>
   git commit --allow-empty -m "Pop GH-<number>: <title> into worktree

   Sub-issues: <comma-separated list of #N>"
   ```

4. Push the branch:
   ```bash
   git push -u origin gh-<number>-<slug>
   ```

5. Report the parent issue URL and the list of sub-issue URLs to the user.

### If there is exactly 1 sub-issue (single-issue path)

1. Assign yourself to the parent issue to claim it:
   ```bash
   gh issue edit <number> --repo <owner>/<repo> --add-assignee @me
   ```

2. Commit an initial marker in the worktree:
   ```bash
   cd ../gh-<number>-<slug>
   git commit --allow-empty -m "Pop GH-<number>: <title> into worktree"
   ```

3. Push the branch:
   ```bash
   git push -u origin gh-<number>-<slug>
   ```

4. Report the parent issue URL to the user. Work proceeds directly on the parent issue — no sub-issue tracking needed.

All subsequent `/do-work` happens inside the worktree at `../gh-<number>-<slug>`. Before starting work, verify the worktree branch:

```bash
cd ../gh-<number>-<slug>
git branch --show-current  # should show gh-<number>-<slug>
```

The main repo stays on `main` throughout.

## Phase 4b -- Generator Mode (Alternative)

Use this phase instead of Phase 4 when the user explicitly requests autonomous execution
(e.g. "use generator mode", "run this automatically", or passes `--generator`).

The generator mode drives `mage generator:start/run` rather than creating GitHub sub-issues
manually. Claude proposes tasks autonomously via `cobbler:measure` and executes them via
`cobbler:stitch`. The interactive path (Phase 4) is the default.

### Prerequisites

Before starting, verify the following in the repo's `configuration.yaml`:

```yaml
cobbler:
  issues_repo: <owner>/<repo>     # must match current repo
claude:
  args:
    - --dangerously-skip-permissions
    - -p
    # other required args
```

For library repos where Go source must not be deleted, also confirm:

```yaml
generation:
  preserve_sources: true
```

Verify Claude credentials exist:

```bash
ls .secrets/claude.json  # or the configured token file
```

### Steps

1. Ensure the main repo is on `main` and the worktree is clean:

   ```bash
   git checkout main
   ```

2. Start a generation from the current branch, naming it after the issue slug:

   ```bash
   COBBLER_GEN_NAME=gh-<number>-<slug> mage generator:start
   ```

   This creates a `generation-gh-<number>-<slug>` branch and (unless `preserve_sources`
   is true) resets Go sources. Note the generation branch name printed in the output.

3. Run autonomous measure+stitch cycles:

   ```bash
   mage generator:run
   ```

   Claude proposes tasks via measure and executes them via stitch. Runs continue until
   no open issues remain or the configured cycle limit is reached. Monitor progress in
   the log output.

4. If the run is interrupted, resume it:

   ```bash
   mage generator:resume
   ```

5. When `generator:run` reports completion (no open issues), the generation branch holds
   all the work. Proceed to **Phase 5** using the generation branch as the feature branch:
   set `<slug>` to the generation branch name (e.g. `generation-gh-<number>-<slug>`)
   and substitute it for `gh-<number>-<slug>` in Phase 5 steps.

### Tradeoff Summary

| | Interactive (Phase 4) | Generator (Phase 4b) |
| -- | -- | -- |
| Decomposition | Claude reads issue, proposes sub-issues | Claude proposes tasks autonomously via measure |
| Review opportunity | Before execution (sub-issues visible on GitHub) | After execution (PR review) |
| Execution | Agent runs /do-work per sub-issue | Claude runs stitch autonomously |
| Best for | Tasks needing decomposition review | Well-specified epics with clear specs |

## Phase 5 -- Open a Pull Request

For the **single-issue path**, trigger Phase 5 when the work is complete (no sub-issue count to check).
For the **multi-sub-issue path**, trigger Phase 5 when ALL sub-issues on the parent are closed.

1. If the issue is recurring (see Phase 6), execute Phase 6 now — before merging — so the next instance exists before this one closes.

2. For the multi-sub-issue path only — verify all sub-issues are closed:
   ```bash
   gh api repos/<owner>/<repo>/issues/<number>/sub_issues \
     --jq '[.[] | select(.state=="open")] | length'
   ```
   If the count is not 0, do not proceed — report which sub-issues are still open.

3. For the single-issue path — add a comment to the parent issue summarizing what was done:
   ```bash
   gh issue comment <number> --repo <owner>/<repo> --body "<summary of work: what changed, files touched, tokens used>"
   ```

4. Push the final state of the feature branch:
   ```bash
   git push
   ```

5. Open a pull request against `main`:
   ```bash
   gh pr create --repo <owner>/<repo> \
     --base main \
     --head gh-<number>-<slug> \
     --title "GH-<number>: <title>" \
     --body "$(cat <<'EOF'
   ## Summary

   <2-3 sentence summary of what this delivered>

   ## Changes

   <bulleted list of what was produced>

   ## Stats

   <output of mage stats with deltas from start of work>

   ## Test plan

   - [ ] `mage analyze` passes
   - [ ] All tests pass
   - [ ] Documentation reviewed for consistency

   Closes #<number>
   EOF
   )"
   ```

   The `Closes #<number>` line auto-closes the parent GitHub issue when the PR merges.

6. Merge the pull request and delete the remote feature branch:
   ```bash
   gh pr merge --repo <owner>/<repo> --merge --delete-branch
   ```

7. Pull the merged changes into main (the main repo is already on `main`):
   ```bash
   git pull origin main
   ```

8. Remove the worktree and delete the local branch:

   ```bash
   git worktree remove ../gh-<number>-<slug>
   git branch -d gh-<number>-<slug>
   ```

9. Verify the parent GitHub issue was closed by the merge:
   ```bash
   gh issue view <number> --repo <owner>/<repo> --json state -q .state
   ```
   If still open, close it explicitly:
   ```bash
   gh issue close <number> --repo <owner>/<repo> --comment "Completed via PR #<pr-number>"
   ```

10. Report the PR URL and confirm the issue is closed.

**Note:** Phase 5 may happen in a later session. When running `/do-work` and closing the last sub-issue, check the open sub-issue count and execute Phase 5 automatically if it reaches 0.

## Phase 6 -- Re-create Recurring Issues

A GitHub issue is recurring if its title starts with "Recurring:" or its body contains a "## Recurrence" section. After Phase 5 closes a recurring issue, re-create it so the next run can pick it up.

1. Detect recurrence: check whether the original issue title starts with `Recurring:` or the body contains `## Recurrence`.

2. If recurring, create a new issue with the same title, labels, and body as the original, except update the "Previous Runs" or "Previous Audits" section to append a line referencing the just-closed issue:
   ```
   - #<number> (<date>): <one-line summary of what this run produced>. PR #<pr-number>.
   ```

3. Create the new issue:
   ```bash
   gh issue create --repo <owner>/<repo> \
     --title "<same title>" \
     --label "<same labels, comma-separated>" \
     --body "<updated body>"
   ```

4. Report the new issue URL so the user knows the recurring issue is ready for the next run.
