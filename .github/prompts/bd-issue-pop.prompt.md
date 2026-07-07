---
description: "Pop a bead into a worktree branch, work on it, and open a PR when done. Uses beads (`bd`) for task tracking and git for branch management. Every statu"
---

Execute the /bd-issue-pop command. The full workflow follows; treat any
text after the prompt invocation as its arguments ($ARGUMENTS).

Pop a bead into a worktree branch, work on it, and open a PR when done. Uses beads (`bd`) for task tracking and git for branch management. Every status change is committed and pushed so state is shared across machines.

## Input

$ARGUMENTS

If arguments contain a bead ID, use that bead. If no ID is given, run `bd list` and ask the user to pick one.

## Phase 0 -- Sync and Validate

1. Pull the latest state and sync beads:
   ```bash
   git pull
   bd sync
   ```

2. Confirm we are in the main repo directory on `main`, not inside a worktree:
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

6. Report the worktree path to the user. Work proceeds via `/do-work` inside the worktree.

## Phase 5 -- Open a Pull Request

Trigger Phase 5 when the work is complete.

1. Update the bead status to done, commit, and push:
   ```bash
   cd ../bd-<id>-<slug>
   bd update <id> --status done
   git add .beads/
   git commit -m "bd: complete bead <id>"
   git push
   ```

2. Push the final state of the feature branch:
   ```bash
   git push
   ```

3. Open a pull request against `main`:
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
   EOF
   )"
   ```

4. Merge the pull request and delete the remote feature branch:
   ```bash
   gh pr merge --repo <owner>/<repo> --merge --delete-branch
   ```

5. Pull the merged changes into main and sync beads:
   ```bash
   git pull origin main
   bd sync
   ```

6. Remove the worktree and delete the local branch:
   ```bash
   git worktree remove ../bd-<id>-<slug>
   git branch -d bd-<id>-<slug>
   ```

7. Report the PR URL and confirm the bead is marked done.

## Skill Tracing

Each skill records provenance as git trailers on the commits it authors:

- `bd-issue-pop` marker commits carry `Skill: bd-issue-pop` and `Called-by: user`.
- `do-work` implementation commits carry `Skill: do-work` and `Called-by: bd-issue-pop`.
