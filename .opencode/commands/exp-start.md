<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

Create or join an experiment branch. Experiments run on short-lived `exp/<slug>` branches in a dedicated worktree. They never merge to `main` and never get PRs or issues. Keepers are distilled onto `gh-*` branches via `/gh-issue-push` + `/gh-issue-pop`.

## Input

$ARGUMENTS

The argument is a kebab-case slug (e.g. `transformer-perf`, `new-prompt-style`). If no argument is given, ask the user for a slug.

## Phase 1 -- Validate

1. Validate the slug is kebab-case (`[a-z0-9]+(-[a-z0-9]+)*`). Reject anything else.
2. Confirm we are in the main repo directory, not inside a worktree. Check:
   ```bash
   git rev-parse --is-inside-work-tree && ! git rev-parse --show-superproject-working-tree 2>/dev/null | grep -q .
   ```
   If inside a worktree, refuse to run — experiment branches are created from the main repo only.
3. Confirm the current branch is `main`:
   ```bash
   git branch --show-current
   ```
   If not on `main`, warn the user and stop.

## Phase 2 -- Create or Join

1. Fetch from origin:
   ```bash
   git fetch origin
   ```

2. Check whether `origin/exp/<slug>` already exists:
   ```bash
   git ls-remote --heads origin exp/<slug>
   ```

### If the remote branch exists (join)

3a. Create a worktree tracking the remote branch:
   ```bash
   git worktree add ../exp-<slug> exp/<slug>
   ```

4a. Report that you joined an existing experiment. Print the worktree path.

### If the remote branch does not exist (create)

3b. Create a worktree with a new branch:
   ```bash
   git worktree add ../exp-<slug> -b exp/<slug>
   ```

4b. Initialize beads inside the worktree:
   ```bash
   cd ../exp-<slug>
   bd init
   ```

5b. Commit the initial state:
   ```bash
   cd ../exp-<slug>
   git add -A
   git commit -m "exp/<slug>: initialize experiment

   Skill: exp-start
   Called-by: user"
   ```

6b. Push the branch:
   ```bash
   git push -u origin exp/<slug>
   ```

## Phase 3 -- Report

Print the worktree path and the convention reminders:

```
Experiment ready at ../exp-<slug> (branch exp/<slug>).

Reminders:
- Never merge exp/* to main. Never open a PR or GitHub issue from it.
- Treat every push as potentially permanent — no secrets or sensitive data.
- To keep a result, distill it onto a gh-* branch via /gh-issue-push + /gh-issue-pop.
- To conclude the experiment, run /exp-stop <slug>.
- On other machines, run /exp-start <slug> to join this experiment.
```
