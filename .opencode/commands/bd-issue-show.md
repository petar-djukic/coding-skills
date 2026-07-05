<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

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
