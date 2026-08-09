# coding-skills

Claude Code slash commands for spec-driven development through GitHub issues and pull requests, mirrored to Cursor, OpenCode, Codex, and GitHub Copilot.

When planning and execution share a context window, coding agents drift: the plan erodes as diffs and test output fill the buffer. This repository separates the two. Planning commands turn intent into GitHub issues that include acceptance criteria; execution commands pop each issue into its own git worktree and close it with a pull request. The issue tracker holds the plan, so no context window has to.

```mermaid
flowchart LR
    A[make-work] -->|plans units| B[gh-issue-push]
    B -->|creates| C[GitHub issues]
    C --> D[gh-issue-pop]
    D -->|worktree per issue| E[do-work]
    E -->|opens| F[Pull request]
    F -->|merge closes issue| C
```

## Scope and Status

The repository contains 14 commands, canonical under `.claude/` and generated for four other assistant surfaces. Commands cover the issue workflow (`gh-issue-push`, `gh-issue-pop`, `gh-issue-show`, and `bd-*` equivalents for beads repositories), orchestration (`make-work`, `do-work`), experiments (`exp-start`, `exp-stop`), releases (`gh-release-push`), and repository setup (`bootstrap`, `align-specs`, `test-clone`). The prose-quality skills and the writing commands moved to [writing-skills](https://github.com/petar-djukic/writing-skills) in August 2026, carrying their history; the two repositories compose by linking both `.claude` trees into a consuming project.

## Documentation

These commands are documented in the following articles:

- [Three Commands to a Crude Orchestrator](https://meshintelligence.substack.com/p/three-commands-to-a-crude-orchestrator) — `make-work`, `gh-issue-push`, `do-work`: the planning/execution split
- [Two Claude Skills and a Worktree Rule](https://meshintelligence.substack.com/p/two-claude-skills-and-a-worktree) — `gh-issue-pop` and the worktree-per-issue rule
- [How to Code with GLM 5.2 on OpenCode](https://meshintelligence.substack.com/p/how-to-glm-52-on-opencode) — running the full loop on OpenCode with a cheap model

## Methodology

All work passes through issues. `make-work` splits a goal into chunks that fit a single context window; `gh-issue-push` records each chunk as an issue, listing the files to change and the acceptance criteria; `gh-issue-pop` checks out a worktree branch (`../gh-<number>-<slug>`) for the task, then opens the PR. The main branch remains unchanged until a merge. Experiment commands (`/exp-start`, `/exp-stop`) execute locally by default, or, with `--remote <owner/repo>`, operate in a subtree-backed remote-sync mode, preserving a bidirectional `git subtree` link to another repository.

## Repository Structure

```
.claude/      canonical commands and rules
.cursor/      generated mirror for Cursor
.opencode/    generated mirror for OpenCode
.agents/      generated command skills for Codex, with root AGENTS.md
.github/      self-contained mirror for GitHub Copilot
scripts/      mirror sync
```

## Mirrors

Assistant configuration is canonical under `.claude/` and is generated outward by `scripts/sync-mirrors.sh` (the `--check` option reports drift). Cursor and OpenCode receive the commands; Codex reads `AGENTS.md` and finds command skills in `.agents/skills/`, each canonical command rewritten to stay within that subtree. The `.github/` mirror is self-contained. Prompts inline the complete workflow and never reference `.claude/`, therefore `ln -s .../.github .github` drops the configuration into a Copilot repository with no dangling references. See [.claude/README.md](.claude/README.md).

