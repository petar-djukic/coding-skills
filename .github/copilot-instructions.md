<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# GitHub Copilot Instructions

This repository's agent configuration is maintained canonically under
`.claude/` and mirrored to `.cursor/` and `.opencode/`. GitHub Copilot does
not support a one-to-one commands/skills layout, so this file documents the
conventions and points to the canonical sources instead of duplicating them.

## Where things live

| Surface | Location | Contents |
|---|---|---|
| Instructions | `.claude/instructions.md` | Quality gates, commit discipline, workflow |
| Rules | `.claude/rules/*.md` | Git workflow, documentation standards, formats |
| Commands | `.claude/commands/*.md` (mirrored in `.cursor/commands/`, `.opencode/commands/`) | Workflow templates: issue push/pop, experiments, releases |
| Skills | `.claude/skills/**` (mirrored in `.cursor/skills/`) | update-references, audit-references, match-voice, de-ai |

## Core conventions Copilot must respect

- All work goes through GitHub issues and pull requests; never commit to
  `main` directly. See `.claude/rules/git-workflow.md`.
- Implementation work happens in git worktrees (`../gh-<number>-<slug>` or
  `../bd-<id>-<slug>`), never in the main repo directory.
- `exp/*` experiment branches never merge to `main` and never get PRs or
  issues; keepers are distilled through the normal issue flow. Experiments
  can be local-only or subtree-synced with a second repository — see
  `.claude/commands/exp-start.md` and `exp-stop.md`.
- Python environments use pixi, never bare pip/virtualenv. See
  `.claude/rules/pixi-python.md`.
- Documentation follows `.claude/rules/documentation-standards.md`
  (YAML-first specs, active voice, forbidden-terms list).

When a Copilot feature gains support for commands or skills, mirror from
the canonical `.claude/` sources rather than authoring here.
