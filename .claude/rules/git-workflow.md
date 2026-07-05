<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Git Workflow

All work goes through issues and pull requests. Never commit directly to main.

## Rules

- Never commit to `main` directly. All changes require an issue and a PR.
- Use `/gh-issue-push` to create an issue before starting any work. In repos using beads, use `/bd-issue-push` instead.
- Use `/gh-issue-pop` to pop the issue into a worktree branch and open the PR when done. In repos using beads, use `/bd-issue-pop` instead.
- All implementation work happens inside the worktree (`../gh-<number>-<slug>` or `../bd-<id>-<slug>`), never in the main repo directory.
- One issue per logical change. Small fixes still need an issue.
- The only exceptions are an emergency hotfix explicitly authorized by the user in that session, and `exp/*` experiment branches which never merge to `main` and never get PRs or issues — keepers are distilled onto `gh-*` branches via the normal flow.
