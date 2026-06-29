<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Command: Align Specs

Read **docs/constitutions/design.yaml** first and hold it as the authority for the rest of this session.

## 1. Inventory

Find all specification files in the project:

- `docs/VISION.yaml`
- `docs/ARCHITECTURE.yaml`
- `docs/SPECIFICATIONS.yaml` (if present)
- `docs/road-map.yaml` (if present)
- `docs/specs/product-requirements/prd*.yaml`
- `docs/specs/use-cases/rel*.yaml`
- `docs/specs/test-suites/test-rel*.yaml`
- `docs/engineering/eng*.yaml`

List every file found. Skip any that do not exist.

## 2. Align Each File

For each file, read it, then apply the constitution's format rules for that document type:

**Required fields**: Add any field that the constitution schema lists as required but is absent. Use a short placeholder value — do not invent content. Mark placeholders clearly (e.g. `# TODO: fill in`).

**Field names**: Rename any field whose key does not match the schema exactly.

**Style**: Apply the style rules from the constitution — active voice, present tense, remove forbidden terms, no bold in prose paragraphs, no horizontal rules. Do not rewrite substance; fix only what violates a rule.

**Naming conventions**: Check each file's name against the `naming_conventions` block in the constitution (e.g. `prd[NNN]-[feature-name].yaml`, `rel[NN].[N]-uc[NNN]-[short-name].yaml`). Rename the file if it does not match. Update any cross-references in other files that point to the old name.

**Traceability**: Apply the `traceability_invariants` block (T1–T5) from the constitution. Fix what you can in the spec files. Flag gaps you cannot resolve without human input as `# TODO: link missing`. Do not fabricate IDs.

Write each aligned file back to disk in place.

## 3. Validate

Run `mage analyze` after all files are written.

Fix any errors it reports. Re-run until it exits 0 or until remaining errors require human input (in which case list them clearly).

## 4. Commit

Commit all changes:

```
git add -A
git commit -m "Align specifications to design constitution"
```

Report: how many files were modified, what structural changes were made, and any TODOs that require human input.
