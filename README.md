# coding-skills

Claude Code skills and slash commands for spec-driven development through GitHub issues and pull requests, mirrored to Cursor, OpenCode, Codex, and GitHub Copilot.

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

The repository contains 17 commands and 11 skills, canonical under `.claude/` and generated for four other assistant surfaces. Commands cover the issue workflow (`gh-issue-push`, `gh-issue-pop`, `gh-issue-show`, and `bd-*` equivalents for beads repositories), orchestration (`make-work`, `do-work`), experiments (`exp-start`, `exp-stop`), releases (`gh-release-push`), and a writing pipeline (`brainstorm-article`, `write-article`, `seo-pass`). Skills are a prose-quality pipeline (`humanize`, `filter-tells`, `match-voice`, `match-outline`, `match-structure`, `tighten-style`, `tune-anchors`), reference management (`update-references`, `audit-references`), `patent-disclosure`, and `pattern-language`.

## Documentation

These commands are documented in the following articles:

- [Three Commands to a Crude Orchestrator](https://meshintelligence.substack.com/p/three-commands-to-a-crude-orchestrator) — `make-work`, `gh-issue-push`, `do-work`: the planning/execution split
- [Two Claude Skills and a Worktree Rule](https://meshintelligence.substack.com/p/two-claude-skills-and-a-worktree) — `gh-issue-pop` and the worktree-per-issue rule
- [How to Code with GLM 5.2 on OpenCode](https://meshintelligence.substack.com/p/how-to-glm-52-on-opencode) — running the full loop on OpenCode with a cheap model

## Methodology

All work passes through issues. `make-work` splits a goal into chunks that fit a single context window; `gh-issue-push` records each chunk as an issue, listing the files to change and the acceptance criteria; `gh-issue-pop` checks out a worktree branch (`../gh-<number>-<slug>`) for the task, then opens the PR. The main branch remains unchanged until a merge. Experiment commands (`/exp-start`, `/exp-stop`) execute locally by default, or, with `--remote <owner/repo>`, operate in a subtree-backed remote-sync mode, preserving a bidirectional `git subtree` link to another repository.

## Repository Structure

```
.claude/      canonical commands, skills, and rules
.cursor/      generated mirror for Cursor
.opencode/    generated mirror for OpenCode
.agents/      generated skills for Codex, with root AGENTS.md
.github/      self-contained mirror for GitHub Copilot
scripts/      mirror sync and environment preflight
```

## Mirrors

Assistant configuration is canonical under `.claude/` and is generated outward by `scripts/sync-mirrors.sh` (the `--check` option reports drift). Cursor and OpenCode receive both commands and skills; Codex reads `AGENTS.md` and finds the skill definitions in `.agents/skills/`, so each canonical command becomes a command skill with its paths rewritten to stay within that subtree. The `.github/` mirror is self-contained. Prompts inline the complete workflow and never reference `.claude/`, therefore `ln -s .../.github .github` drops the configuration into a Copilot repository with no dangling references. See [.claude/README.md](.claude/README.md).

## Environment

[pixi](https://pixi.sh/) handles Python dependencies. Each agent folder includes a `pixi.toml` and a `pixi.lock`, and `scripts/ensure-env.sh` creates the locked environment when the repo is opened, installing pixi if it is missing. Because the manifest travels with the symlinked agent directory, a fresh machine needs no manual setup. Credentials (`SERPAPI_KEY`, `ANTHROPIC_API_KEY`, optional `SEMANTIC_SCHOLAR_API_KEY`) come from the environment, not pixi.
