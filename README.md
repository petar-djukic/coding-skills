# coding-skills
Skills for spec-driven development through GitHub issues and pull requests

Experiment commands (`/exp-start`, `/exp-stop`) run local-only by default, or
in a subtree-backed remote sync mode (`--remote <owner/repo>`) that keeps a
two-way `git subtree` boundary with a second repository.

Assistant configuration is canonical under `.claude/` and mirrored to
`.cursor/` (commands and skills), `.opencode/` (commands), and `.github/`
(Copilot instructions pointing at the canonical sources). See
[.claude/README.md](.claude/README.md).
