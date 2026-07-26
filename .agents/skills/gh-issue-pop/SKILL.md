---
name: "gh-issue-pop"
description: "Pop a GitHub issue from the current repository, decompose it into GitHub sub-issues on a feature branch, and open a PR when all sub-issues are closed."
---

# gh-issue-pop command

Apply this command workflow. Treat any text after its invocation as the command input.

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
4. Probe available mage targets (the result gates all subsequent mage steps):
   ```bash
   mage -l 2>/dev/null || true
   ```
   Record which targets exist. If `mage` is not installed or the repo has no Magefile, treat all mage targets as absent and skip mage-dependent steps silently.
5. If the probe shows a consistency-check target — commonly `audit` or `analyze` — run it (`mage audit` or `mage analyze`) to identify spec issues. Otherwise skip.
6. If `stats` appeared in the probe, run `mage stats` for current LOC and documentation metrics. Otherwise skip.
7. Summarize the current project state.

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

### Create the sub-issues and the marker

With 2+ sub-issues, create each one (`gh issue create` with its Required
Reading, Files to Create/Modify, Requirements, Acceptance Criteria), then link
it to the parent so the progress checklist appears:

```bash
gh api repos/<owner>/<repo>/issues/<parent-number>/sub_issues \
  --method POST --field sub_issue_id=$(gh api repos/<owner>/<repo>/issues/<sub-number> --jq '.id')
```

With exactly one, skip sub-issue creation and claim the parent instead:
`gh issue edit <number> --repo <owner>/<repo> --add-assignee @me`.

Either way, commit the marker and push:

```bash
cd ../gh-<number>-<slug>
git commit --allow-empty -m "Pop GH-<number>: <title> into worktree

Sub-issues: <comma-separated #N>      # omit on the single-issue path

Skill: gh-issue-pop
Called-by: <invoking skill, or 'user' if run directly>"
git push -u origin gh-<number>-<slug>
```

Report the parent issue URL, and the sub-issue URLs if there are any.

### Epics and further breakdown

After `gh-issue-pop`, run `/do-work` — repeatedly for a multi-sub-issue epic (one sub-issue per pass) until every sub-issue is closed, then Phase 5 opens the PR. Decomposition is one level deep and one worktree per epic.

`/do-work` routes each sub-issue by deliverable: documentation, prose, or code. A sub-issue whose output is prose a person reads — a paper section, a README, a post — takes the Prose workflow, which learns the repository's voice from `writing-voice/` before drafting and scans the result with filter-tells. Nothing changes in a repository without that directory.

If, while running `/do-work`, a sub-issue turns out too big to finish in one pass, do not pop again — nested worktrees are not supported. Split that sub-issue into smaller **sibling** sub-issues under the same epic with `/gh-issue-push`, work them in the same worktree, and let the epic's single PR close them all. `gh-issue-pop` is only ever run from `main`, never from inside a worktree.

## Phase 4b -- Generator Mode (Alternative)

**Capability gate:** This phase requires the cobbler orchestrator. If the Phase 2 mage probe did not show `generator:start` in the target list, skip this entire section and do not mention generator mode to the user.

Use this phase instead of Phase 4 when the user explicitly requests autonomous execution
(e.g. "use generator mode", "run this automatically", or passes `--generator`)
and the repo has the cobbler orchestrator installed (`generator:start` exists in `mage -l`).

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

Trigger when the work is complete: on the single-issue path, when the parent's
work is done; on the multi-sub-issue path, when every sub-issue is closed.

1. **If the issue is recurring** (see Phase 6), do Phase 6 now — before merging
   — so the next instance exists before this one closes.

2. **Verify the units are actually done.** Multi-sub-issue path:

   ```bash
   gh api repos/<owner>/<repo>/issues/<number>/sub_issues \
     --jq '[.[] | {number, title, state}]'
   ```

   A sub-issue is not done until it has both a completion comment and an
   `Actual LOC:` line stated against its `Estimated LOC`. If any lacks either,
   stop and report which. Single-issue path: write that comment on the parent
   now.

3. **Push, then open the PR** against `main`, titled `GH-<number>: <title>`,
   with sections: Summary (2-3 sentences), Changes, Stats (`mage stats` deltas
   plus Estimated vs Actual LOC), and Test plan (consistency check, tests, docs
   — where those exist). End with one `Closes #N` line per issue: the parent
   and every sub-issue.

   Those `Closes` lines are what auto-close the issues at merge. Sub-issue
   commits carry their own as a redundant safeguard.

4. **Merge and clean up:**

   ```bash
   gh pr merge --repo <owner>/<repo> <pr-number> --merge --delete-branch
   git pull origin main            # from the main checkout, already on main
   git worktree remove ../gh-<number>-<slug>
   git branch -d gh-<number>-<slug>
   ```

5. **Verify every issue actually closed** — the parent and each sub-issue.
   GitHub's auto-close is not guaranteed:

   ```bash
   gh api repos/<owner>/<repo>/issues/<number>/sub_issues \
     --jq '[.[] | select(.state=="open") | {number, title}]'
   ```

   Anything still open, warn the user and close it explicitly with
   `gh issue close <N> --comment "Completed via PR #<pr>. Auto-close did not trigger."`

6. Report the PR URL and confirm all issues are closed.

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

## Skill Tracing

Each skill records provenance as git trailers on the commits it authors, so `git log` reconstructs which skills ran and which called which — no separate log file.

- `gh-issue-pop` marker commits carry `Skill: gh-issue-pop` and `Called-by: <invoking skill, or 'user'>`.
- `do-work` implementation commits carry `Skill: do-work` and `Called-by: gh-issue-pop`.

View the roster and the call graph:

```bash
# per-commit: which skill produced it
git log --pretty='%h %s [%(trailers:key=Skill,valueonly,separator=%x20)]'

# call graph: caller -> skill, with counts
git log --format='%(trailers:key=Called-by,valueonly,separator=%x20) -> %(trailers:key=Skill,valueonly,separator=%x20)' \
  | grep -vE '^ *-> *$' | sort | uniq -c | sort -rn
```

Limitation: `make-work` and `gh-issue-push` make no commits, so they do not appear in commit-trailer traces. Capturing them needs a provenance line on the issues they create (follow-up).
