<\!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Command: Make Work

Read the following files to understand the project:

1. **docs/VISION.yaml** - Project goals and boundaries
2. **docs/ARCHITECTURE.yaml** - System design and components
3. **docs/road-map.yaml** - Release schedule and use case status
4. **docs/constitutions/design.yaml** - Documentation format rules and standards
5. **docs/specs/product-requirements/README.md** (if exists)
6. **docs/specs/use-cases/README.md** (if exists)

First, check the current state of work. Treat the issue tracker and the roadmap as claims to verify, not as ground truth — a later task that builds on "done" work fails if that work was never actually merged.

1. Run `gh issue list --repo <owner>/<repo> --state all` to see open and closed issues
2. Check what's in progress, what's completed, what's pending
3. **Check docs/road-map.yaml** for release schedule and use case status
4. **Verify claimed-complete work against the repository.** A closed issue or a "done" roadmap entry is a claim that code was merged, not proof of it. For each release or issue marked done that later work would depend on:
   - Confirm a merged pull request closed it. An issue closed as completed with no merged PR is not done (`gh issue view <n> --json stateReason` and check its linked PRs).
   - Confirm the implementation exists in the source tree, not just the spec. Grep for the types, functions, or files the issue said it would produce, and check `git log` for the commit that added them.
   - Watch for stubs: a function that returns an empty or placeholder result with a "implemented in a later release" comment is not an implementation.
   - If the project exposes a code-readiness check (for example `mage status`), run it and trust it over issue labels.
   Anything that fails these checks is unbuilt regardless of tracker state; plan an implementation task for it before any task that depends on it.
5. **Run `mage analyze`** to identify specification issues:
   - Orphaned PRDs (not referenced by use cases)
   - Missing test suites (use cases without test suites)
   - Broken references (invalid touchpoints, missing files)
   - Use cases not in roadmap

Then, summarize:

1. What problem this project solves
2. The high-level architecture (major components and how they fit together)
3. The current state of implementation (what's done, what's in progress)
4. **Current release**: Which release we are working on and which use cases remain
5. Current repo size: run `mage stats:loc` and include its output (Go production/test LOC, doc words)

Based on this, propose next steps using **release priority**:

1. **Focus on earliest incomplete release**: Prioritize completing use cases from the current release in road-map.yaml
2. **Early preview allowed**: Later use cases can be partially implemented if they share functionality with the current release
3. **Assign issues to releases**: Each issue should map to a use case in road-map.yaml; if uncertain, use release 99.0 (unscheduled)
4. If epics exist: suggest new issues to add to existing epics, or identify what to work on next
5. If no epics exist: suggest epics to create and initial issues for each
6. Identify dependencies - what should be built first and why?

When proposing issues (per crumb-format rule):

1. **Type**: Say whether each issue is **documentation** (markdown in `docs/`) or **code** (implementation).
2. **Required Reading**: List files the agent must read before starting (PRDs, ARCHITECTURE sections, existing code). This is mandatory for all issues.
3. **Files to Create/Modify**: Explicit list of files the issue will produce or change. For docs: output path. For code: packages/files to create or edit.
4. **Structure** (all issues): Requirements, Design Decisions (optional), Acceptance Criteria.
5. **Documentation issues**: Add **format rule** reference and **required sections** (PRD: Problem, Goals, Requirements, Non-Goals, Acceptance Criteria; use case: Summary, Actor/trigger, Flow, Success criteria).
6. **Code issues**: Requirements, Design Decisions, Acceptance Criteria (tests/behavior); no PRD-style Problem/Goals/Non-Goals.

**Code task sizing**: Target 300-700 lines of production code per task, touching no more than 5 files. This keeps tasks completable in a single session while being substantial enough to make meaningful progress. Split larger features into multiple tasks; combine trivial changes into one task.

**Task limit**: Create no more than 10 tasks at a time. If more work is needed, create additional tasks after completing some of the current batch.

Don't create any issues yet - just propose the breakdown so we can discuss it.

After we agree on the plan and you create issues:

- **Create each issue using `/gh-issue-push`**, not `gh issue create` directly. `/gh-issue-push` searches for ripple effects before drafting the issue body, ensuring every affected file and field is enumerated. Issues created without this step will miss cross-references.
- To link a sub-issue to a parent, use:

  ```bash
  gh api repos/<owner>/<repo>/issues/<parent>/sub_issues \
    --method POST \
    --field sub_issue_id=$(gh api repos/<owner>/<repo>/issues/<sub-number> --jq '.id')
  ```

After you implement work:

- Commit your changes with a clear message
- Log token usage: `gh issue comment <id> --repo <owner>/<repo> --body "tokens: N"`
- Close completed issues: `gh issue close <id> --repo <owner>/<repo>`
- File any new issues via `/gh-issue-push`; note them for the user if not created in this session
