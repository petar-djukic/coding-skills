---
description: "Pop a bead (epic) into a worktree branch and decompose it into child beads, then hand off to `/do-work` — mirroring the gh flow (`gh-issue-pop` sets"
---

Execute the /bd-issue-pop command. The full workflow follows; treat any
text after the prompt invocation as its arguments ($ARGUMENTS).

Pop a bead (epic) into a worktree branch and decompose it into child beads, then hand off to `/do-work` — mirroring the gh flow (`gh-issue-pop` sets up; `/do-work` does the work). Uses beads (`bd`) for task tracking and git for branch management. Every status change is committed and pushed so state is shared across machines.

The division of labor matches `gh-issue-pop`: this command syncs, fetches the bead, gathers context, proposes the breakdown (the single interactive pause), and sets up the worktree plus the child-bead graph — then stops. `/do-work`, run repeatedly, works one ready child per pass on the shared worktree branch until all are done; the last pass merges the PR to `main` and closes the epic automatically. All the epic's work lands on the one `bd-<id>-<slug>` branch and closes via its single PR.

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
4. If the probe shows a consistency-check target — commonly `audit` or `analyze` — run it (`mage audit` or `mage analyze`). Otherwise skip.
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
   child, create a bead **labelled with the parent id** and capture its id, then
   record its dependency edges so it is blocked until its prerequisites are
   done, and link it under the parent so the parent is not workable until its
   children complete:
   ```bash
   bd create "<child title>" --label <id>     # label = parent id; capture <child-id>
   bd dep add <child-id> <prereq-child-id>    # one per prerequisite
   bd dep add <id> <child-id>                 # parent depends on the child
   ```
   The label ties each child to this parent so `/do-work` can scope the ready
   queue to them (`bd ready` is global — see "Working the epic"). The exact flags
   for the label and dependencies vary by `bd` version — confirm with `bd create --help`
   and `bd dep --help` and use the installed forms (the parent-depends-on-child
   edge is what makes the parent close only after its children). Keep the list
   of child ids you created; it is the fallback scope if the installed `bd`
   cannot filter `bd ready` by label. Then commit and push so the graph is
   shared across machines:
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

7. Report the worktree path and the child beads created. The work is done by
   `/do-work`, not here — hand off to it now (next section).

## Working the epic — run `/do-work` repeatedly

Popping set up the worktree and the child-bead graph; `/do-work` does the work,
exactly as in the gh flow. Run `/do-work` inside the worktree, once per pass —
it detects beads mode, picks the next ready child of this epic
(`bd ready --label <id>`, the parent-scoped queue), implements it on the shared
`bd-<id>-<slug>` branch under the real-work bar (no stubs), records `Actual LOC`,
and closes it with `bd update --status done` (which unblocks its dependents).
Repeat until no child of this epic is ready.

One worktree, one PR per epic: every child lands on this one branch; `/do-work`
never creates a branch or worktree per child. If a child turns out too big,
`/do-work` splits it into sibling children under this epic (same worktree) — it
does not pop again. When the last child closes, `/do-work` runs Phase 5
automatically — it merges the PR to `main`, closes the epic, and cleans up. For
a single-unit breakdown (no children), `/do-work` works the parent bead
directly, then runs Phase 5 the same way.

The invariant holds throughout: only ever implement beads that belong to this
epic — never a bead from another epic that happens to be ready.

## Phase 5 -- Merge and Close the Epic

The last `/do-work` pass reaches this automatically after it closes the final
child. It opens the PR, merges it to `main`, closes the epic, and cleans up — no
manual step. (Verify first that every child is done and the work is real; do not
merge a stub branch.)

1. Close the parent bead **on the branch**. All children are done, so its
   dependencies are satisfied. Beads has no git auto-close, so committing the
   close on the branch is the analogue of `Closes #` — it travels with the PR
   and lands on `main` at merge, with no direct commit to `main`:
   ```bash
   cd ../bd-<id>-<slug>
   bd ready --label <id>   # this epic's children — none should remain
   bd update <id> --status done
   git add .beads/ && git commit -m "bd: complete epic <id>" && git push
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

   <if a consistency-check target is available:>
   - [ ] the consistency check (`mage audit` / `mage analyze`) passes
   - [ ] All tests pass
   - [ ] Documentation reviewed for consistency

   Bead: <id>
   Actual LOC: <n> (est <m>)
   EOF
   )"
   ```

3. Merge the pull request and delete the remote branch:
   ```bash
   gh pr merge --repo <owner>/<repo> --merge --delete-branch
   ```

4. From the main repo directory, pull the merged changes and sync beads (the
   epic and all children are now closed on `main`):
   ```bash
   cd -                    # back to the main repo checkout on `main`
   git pull origin main
   bd sync
   ```

5. Remove the worktree and delete the local branch:
   ```bash
   git worktree remove ../bd-<id>-<slug>
   git branch -d bd-<id>-<slug>
   ```

6. Report the PR URL, that it merged, and that the epic and its children are
   closed.

## Skill Tracing

Each skill records provenance as git trailers on the commits it authors:

- `bd-issue-pop` marker commits carry `Skill: bd-issue-pop` and `Called-by: user`.
- `do-work` implementation commits carry `Skill: do-work` and `Called-by: bd-issue-pop`.
