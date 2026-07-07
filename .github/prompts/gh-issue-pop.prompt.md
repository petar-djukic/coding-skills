---
description: "Pop a GitHub issue from the current repository, decompose it into GitHub sub-issues on a feature branch, and open a PR when all sub-issues are closed."
---

Follow the workflow defined in `.claude/commands/gh-issue-pop.md` in this
repository. Read that file and execute its steps exactly — it is the
canonical definition of the /gh-issue-pop command; this prompt is a thin adapter
so the command stays single-sourced. Treat any text after the prompt
invocation as the command's arguments ($ARGUMENTS).
