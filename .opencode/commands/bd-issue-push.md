<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

Create a bead (task) in the current repository using beads (`bd`). The bead is committed and pushed so it is visible on all machines.

## Input

$ARGUMENTS

## Steps

1. Verify that `.beads/` exists in the repository root. If not, initialize beads and commit:
   ```bash
   bd init
   git add .beads/
   git commit -m "bd: initialize beads"
   ```

2. **Search for ripple effects.** Before drafting the bead, identify every file and field that the change touches — not just the primary target. The executor will do exactly what the bead says and nothing else, so anything omitted will be missed.
   - Read the files involved to understand their structure.
   - `grep` for identifiers, names, or values being added, changed, renamed, or deleted. Search the full project, not just the obvious files.
   - For each hit, note the file path, the field or line, and what needs to change.
   - Check for status fields, summary fields, titles, index entries, cross-reference IDs, and out_of_scope references — these are the most commonly missed.

3. Draft a concise title and well-structured description.
   - Include a "Files to Create/Modify" section listing every file. Under each file, list the specific fields or lines to change.
   - Include an `Estimated LOC:` line for code tasks.

4. Create the bead:
   ```bash
   bd create "<title>"
   ```
   Capture the bead ID from the output.

5. Commit and push the `.beads/` changes so the bead is visible on all machines:
   ```bash
   git add .beads/
   git commit -m "bd: create bead <id> — <title>"
   git push
   ```

6. Report the bead ID and title.
