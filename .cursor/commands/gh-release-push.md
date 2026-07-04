---
description: Run the full release workflow: audit, test, tag with annotated changelog, and push to all remotes.
---

Run the full release workflow: audit, test, tag, and push.

## Steps

1. Run `mage audit`. If it fails, fix the problems and re-run (up to 3 attempts). Stop if still failing after 3 attempts.
2. Run `mage test:unit`. If it fails, fix the problems and re-run (up to 3 attempts). Stop if still failing after 3 attempts.
3. Record the current latest tag as the previous release: `git describe --tags --abbrev=0` (or empty if no tags exist yet).
4. Run `mage tag` to create the root `v0.YYYYMMDD.N` tag and matching module-scoped tags: `agent-core/v0.YYYYMMDD.N`, `agent-profiles/v0.YYYYMMDD.N`, and `design-patterns/v0.YYYYMMDD.N`. Capture the root tag name from the output or via `git describe --tags --abbrev=0 --match 'v0.*'`.
5. Generate a summary of changes since the last release. Run `git log --oneline <previous-tag>..<new-tag>` to get the commit list (or all commits if no previous tag). Summarize the changes into a concise changelog grouped by category (features, fixes, docs, etc.).
6. Replace the root lightweight tag with an annotated tag carrying the summary: `git tag -d <new-tag> && git tag -a <new-tag> -m "<summary>"`. Keep the module-scoped tags on the same commit and print the summary to the user.
7. Push the current branch to `origin`. If `git remote | grep -q release` succeeds, also push the branch to `release`.
8. Push tags to `origin` with `git push origin --tags`; this includes the annotated root tag and the module-scoped tags. If the `release` remote exists, also push tags to `release` with `git push release --tags`.
9. Resolve the module path with `go list -m` and run `go get <module>@<new-tag>` to fetch the new version via the Go module proxy. Report any errors but do not fail the release.
10. Report the root tag name, module-scoped tag names, branch, which remotes received the push, and the change summary.
