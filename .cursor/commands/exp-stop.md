<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

Conclude and delete an experiment branch. Shows pending work and a diffstat for a final review, then deletes the remote branch, local worktree, and local branch.

## Input

$ARGUMENTS

The argument is the experiment slug (e.g. `transformer-perf`). If no argument is given, list existing `exp/*` branches and ask the user to pick one.

## Phase 1 -- Verify

1. Check that the worktree `../exp-<slug>` exists or the local branch `exp/<slug>` exists:
   ```bash
   git worktree list | grep "exp-<slug>"
   git branch --list "exp/<slug>"
   ```
   If neither exists, report that no experiment with this slug was found and stop.

2. Show the current state of the experiment — uncommitted changes and a diffstat against main:
   ```bash
   cd ../exp-<slug>
   git status --short
   ```
   ```bash
   git diff --stat main...exp/<slug>
   ```

3. Show the commit log for the experiment:
   ```bash
   git log --oneline main..exp/<slug>
   ```

4. Ask the user to confirm deletion. This is the last chance to distill keepers via `/gh-issue-push` + `/gh-issue-pop`. Do not proceed without explicit confirmation.

## Phase 2 -- Delete

After user confirmation:

1. Delete the remote branch:
   ```bash
   git push origin --delete exp/<slug>
   ```

2. Remove the worktree:
   ```bash
   git worktree remove --force ../exp-<slug>
   ```

3. Delete the local branch:
   ```bash
   git branch -D exp/<slug>
   ```

## Phase 3 -- Report

Print cleanup confirmation and instructions for other machines:

```
Experiment exp/<slug> deleted (remote branch, worktree, local branch).

Other machines that joined this experiment should run:
  git fetch --prune
  git worktree remove --force ../exp-<slug>
  git branch -D exp/<slug>

Note: deletion removes the branch from lists, fetches, and fresh clones,
but commits stay SHA-addressable on GitHub until garbage collection.
GitHub Support can purge on request.
```
