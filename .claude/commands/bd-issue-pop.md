<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

Pop a bead into a worktree branch, do the work, and open a PR — in one continuous run. Uses beads (`bd`) for task tracking and git for branch management. Every status change is committed and pushed so state is shared across machines.

This command is a single sequence, not a set of independently-invoked steps: Sync → Fetch → Context → Breakdown → Worktree → **Implement** → PR. The only interactive pause is the Phase 3 breakdown approval. After approval it runs straight through to an open PR — popping the bead is the *start* of the work, not the end of it. Do not stop after creating the worktree.

## Input

$ARGUMENTS

If arguments contain a bead ID, use that bead. If no ID is given, run `bd list` and ask the user to pick one.

## Phase 0 -- Sync and Validate

1. Detect the repo (used for the PR commands in Phase 5):
   ```bash
   gh repo view --json nameWithOwner -q .nameWithOwner
   ```
   Use the result as `<owner>/<repo>` throughout.

2. Pull the latest state and sync beads:
   ```bash
   git pull
   bd sync
   ```

3. Confirm we are in the main repo directory on `main`, not inside a worktree:
   ```bash
   git branch --show-current
   ```
   If not on `main`, warn and stop.

## Phase 1 -- Fetch the Bead

1. Fetch the bead details:
   ```bash
   bd show <id>
   ```
2. If the bead is already done, stop and report its state.
3. Display the bead title and description to the user.

## Phase 2 -- Gather Project Context

1. Read docs/VISION.yaml, docs/ARCHITECTURE.yaml, docs/road-map.yaml, and `docs/constitutions/design.yaml` if they exist.
2. Read READMEs for product requirements and use cases relevant to the bead.
3. Probe available mage targets (the result gates all subsequent mage steps):
   ```bash
   mage -l 2>/dev/null || true
   ```
   Record which targets exist. If `mage` is not installed or the repo has no Magefile, treat all mage targets as absent and skip mage-dependent steps silently.
4. If `audit` appeared in the probe, run `mage audit`. Otherwise skip.
5. If `stats` appeared in the probe, run `mage stats`. Otherwise skip.
6. Summarize the current project state.

## Phase 3 -- Propose Breakdown

Using the bead as the task description, propose the work breakdown:

- Type: documentation or code
- Required Reading: mandatory list of files
- Files to Create/Modify: explicit file list
- Structure: Requirements, Design Decisions (optional), Acceptance Criteria
- Code task sizing: 300-700 lines of production code, no more than 5 files

Present the proposal to the user for approval. Do not create anything until the user agrees.

## Phase 4 -- Create Worktree and Start Work

After user approval:

1. Derive a slug from the bead title (kebab-case, max 30 chars).

2. Create a git worktree with a new branch:
   ```bash
   git worktree add ../bd-<id>-<slug> -b bd-<id>-<slug>
   ```
   All subsequent work happens inside this worktree.

3. Update the bead status to in_progress, commit, and push:
   ```bash
   bd update <id> --status in_progress
   git add .beads/
   git commit -m "bd: start bead <id>"
   git push
   ```

4. Commit an initial marker in the worktree:
   ```bash
   cd ../bd-<id>-<slug>
   git commit --allow-empty -m "Pop bd-<id>: <title> into worktree

   Skill: bd-issue-pop
   Called-by: user"
   ```

5. Push the branch:
   ```bash
   git push -u origin bd-<id>-<slug>
   ```

6. Continue immediately to Phase 4b — do not stop here. Popping the bead only set up the branch; the work has not been done yet.

## Phase 4b -- Implement the Work

Do the work inside the worktree — this phase is where the bead is actually implemented, and it runs without a further hand-off.

1. Verify the worktree branch before starting:
   ```bash
   cd ../bd-<id>-<slug>
   git branch --show-current  # should show bd-<id>-<slug>
   ```

2. Implement the approved breakdown by running `/do-work` inside the worktree. If the bead was decomposed into child beads, run `/do-work` once per child until every child is `done`; otherwise do the single unit of work. Commit as you go, with `Skill: do-work` / `Called-by: bd-issue-pop` trailers.

3. The bead is not complete until the work is real: the files in the breakdown exist and are implemented (not stubs), and any available checks pass (`mage audit`/tests if present). Do not proceed to Phase 5 with an empty or stub branch.

4. Record an `Actual LOC` figure (production/test lines produced, from `mage stats` deltas if available) against the bead's estimate, as a note on the bead:
   ```bash
   bd comment <id> "Actual LOC: <n> (est <m>). <one-line summary of what was built>"
   ```
   If the installed `bd` has no `comment` subcommand, put the same line in the bead's notes via `bd update`, or carry it into the PR body.

When the work is complete and verified, proceed to Phase 5.

## Phase 5 -- Open a Pull Request

Trigger Phase 5 when the work is complete and verified (Phase 4b done).

1. Push the final state of the feature branch:
   ```bash
   cd ../bd-<id>-<slug>
   git push
   ```

2. Open a pull request against `main`:
   ```bash
   gh pr create --repo <owner>/<repo> \
     --base main \
     --head bd-<id>-<slug> \
     --title "bd-<id>: <title>" \
     --body "$(cat <<'EOF'
   ## Summary

   <2-3 sentence summary of what this delivered>

   ## Changes

   <bulleted list of what was produced>

   ## Test plan

   <if mage audit is available:>
   - [ ] `mage audit` passes
   - [ ] All tests pass
   - [ ] Documentation reviewed for consistency

   Bead: <id>
   Actual LOC: <n> (est <m>)
   EOF
   )"
   ```

3. Report the PR URL and stop for review. Do not self-merge — a merge is a second party's decision. Leave the bead `in_progress`; it becomes `done` only when the PR merges (Phase 6).

## Phase 6 -- After the PR merges

Run this once the PR has been merged (by the user, or on their explicit approval). The bead is done only when the work is on `main`.

1. Mark the bead done and sync:
   ```bash
   bd update <id> --status done
   git add .beads/
   git commit -m "bd: complete bead <id>"
   git push
   ```

2. Pull the merged changes into main and sync beads:
   ```bash
   git pull origin main
   bd sync
   ```

3. Remove the worktree and delete the local branch:
   ```bash
   git worktree remove ../bd-<id>-<slug>
   git branch -d bd-<id>-<slug>
   ```

4. Report that the bead is marked done and the worktree is cleaned up.

## Skill Tracing

Each skill records provenance as git trailers on the commits it authors:

- `bd-issue-pop` marker commits carry `Skill: bd-issue-pop` and `Called-by: user`.
- `do-work` implementation commits carry `Skill: do-work` and `Called-by: bd-issue-pop`.
