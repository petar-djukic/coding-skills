---
description: "Pop a bead into a worktree branch, do the work, and open a PR — in one continuous run. Uses beads (`bd`) for task tracking and git for branch manage"
---

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

Decompose the bead into child beads — the beads-native equivalent of an epic's
sub-issues. For each child, specify:

- Title and type (documentation or code)
- Required Reading: mandatory list of files
- Files to Create/Modify: explicit file list
- Structure: Requirements, Design Decisions (optional), Acceptance Criteria
- `Estimated LOC` for code children
- Dependencies: which sibling children must finish first
- Code task sizing: 300-700 lines of production code, no more than 5 files per child

Present the children and their dependency ordering explicitly (a short list or
a small graph — "C depends on A, B") for approval. This is the single
interactive pause. Do not create any beads until the user agrees.

If the natural breakdown is a single unit of work, say so — no child beads are
created; the parent bead is worked directly (the single-unit path in Phase 4).

## Phase 4 -- Create Worktree and Start Work

After user approval:

1. Derive a slug from the bead title (kebab-case, max 30 chars).

2. Create a git worktree with a new branch:
   ```bash
   git worktree add ../bd-<id>-<slug> -b bd-<id>-<slug>
   ```
   All subsequent work happens inside this worktree.

3. Update the parent bead status to in_progress, commit, and push:
   ```bash
   bd update <id> --status in_progress
   git add .beads/
   git commit -m "bd: start bead <id>"
   git push
   ```

4. Create the child beads (multi-child breakdown only). For each approved
   child, create a bead and capture its id, then record its dependency edges so
   it is blocked until its prerequisites are done, and link it under the parent
   so the parent is not workable until its children complete:
   ```bash
   bd create "<child title>"                 # capture <child-id>
   bd dep add <child-id> <prereq-child-id>    # one per prerequisite
   bd dep add <id> <child-id>                 # parent depends on the child
   ```
   The exact flags for dependencies vary by `bd` version — confirm with
   `bd dep --help` and `bd create --help` and use the installed forms (the
   parent-depends-on-child edge is what makes the parent close only after its
   children). Then commit and push so the graph is shared across machines:
   ```bash
   git add .beads/
   git commit -m "bd: decompose <id> into child beads"
   git push
   ```
   For a single-unit breakdown, skip this step — there are no children and the
   parent bead is the unit of work.

5. Commit an initial marker in the worktree:
   ```bash
   cd ../bd-<id>-<slug>
   git commit --allow-empty -m "Pop bd-<id>: <title> into worktree

   Skill: bd-issue-pop
   Called-by: user"
   ```

6. Push the branch:
   ```bash
   git push -u origin bd-<id>-<slug>
   ```

7. Continue immediately to Phase 4b — do not stop here. Popping the bead only set up the branch and the child graph; the work has not been done yet.

## Phase 4b -- Implement the Work

Do the work inside the worktree — this phase is where the bead is actually implemented, and it runs without a further hand-off.

1. Verify the worktree branch before starting:
   ```bash
   cd ../bd-<id>-<slug>
   git branch --show-current  # should show bd-<id>-<slug>
   ```

2. Work the children off the ready queue, in dependency order. Repeat until no
   child of this parent is ready:
   ```bash
   bd ready        # the unblocked beads; confirm the flags with `bd ready --help`
   ```
   For the next ready child of this parent:
   - implement it with `/do-work` inside the worktree, committing as you go with
     `Skill: do-work` / `Called-by: bd-issue-pop` trailers;
   - a child is not done until its work is real — the files in its breakdown
     exist and are implemented (not stubs), and any available checks pass
     (`mage audit`/tests if present);
   - record its `Actual LOC` against its estimate, then close it, which unblocks
     its dependents:
     ```bash
     bd comment <child-id> "Actual LOC: <n> (est <m>). <one-line summary>"
     bd update <child-id> --status done
     git add .beads/ && git commit -m "bd: complete child <child-id>" && git push
     ```
   Then re-run `bd ready` and take the next one. `bd ready` reflects the
   dependency edges, so this walks the children in a valid order and never
   starts a blocked child.

   For a single-unit breakdown (no children), implement the parent bead directly
   with `/do-work` under the same real-work bar, and record its `Actual LOC`:
   ```bash
   bd comment <id> "Actual LOC: <n> (est <m>). <one-line summary>"
   ```
   (If the installed `bd` has no `comment`, put the line in the bead notes via
   `bd update`, or carry it into the PR body.)

3. Do not proceed to Phase 5 with an empty or stub branch, or while any child of
   this parent is still open.

When every child is done (or the single unit is complete) and verified, proceed
to Phase 5. Leave the parent bead `in_progress` — it closes only after the PR
merges (Phase 6).

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

1. Mark the parent bead done and sync. All its children are already closed
   (Phase 4b), so the parent's dependencies are satisfied; confirm none is still
   open before closing the parent:
   ```bash
   bd ready              # no child of <id> should appear
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
