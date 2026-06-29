<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Git Workflow

All work goes through issues and pull requests. Never commit directly to main.

## Rules

- Never commit to `main` directly. All changes require an issue and a PR.
- Use `/git-issue-push` to create an issue before starting any work.
- Use `/git-issue-pop` to pop the issue into a worktree branch and open the PR when done.
- All implementation work happens inside the worktree (`../gh-<number>-<slug>`), never in the main repo directory.
- One issue per logical change. Small fixes still need an issue.
- The only exception is an emergency hotfix explicitly authorized by the user in that session.
