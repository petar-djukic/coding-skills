---
description: "List beads or show details of a specific bead in the current repository."
---

Execute the /bd-issue-show command. The full workflow follows; treat any
text after the prompt invocation as its arguments ($ARGUMENTS).

List beads or show details of a specific bead in the current repository.

## Input

$ARGUMENTS

## Behavior

1. Sync beads to get the latest state:
   ```bash
   git pull
   bd sync
   ```

2. If no argument is provided, list all beads:
   ```bash
   bd list
   ```
   Present the output clearly: ID, title, and status for each bead.

3. If a bead ID is provided, show its full details:
   ```bash
   bd show <id>
   ```
   Display all fields: ID, title, status, description, and any metadata.
