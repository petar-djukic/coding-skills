---
description: "Test the orchestrator library by deploying it into a target Go repository and running the test plan. Failures indicate bugs in the orchestrator code, "
---

Follow the workflow defined in `.claude/commands/test-clone.md` in this
repository. Read that file and execute its steps exactly — it is the
canonical definition of the /test-clone command; this prompt is a thin adapter
so the command stays single-sourced. Treat any text after the prompt
invocation as the command's arguments ($ARGUMENTS).
