Run the full release workflow: analyze, test, tag, and push.

## Steps

1. Run `mage analyze`. If it fails, fix the problems and re-run (up to 3 attempts). Stop if still failing after 3 attempts.
2. Run `mage test:unit`. If it fails, fix the problems and re-run (up to 3 attempts). Stop if still failing after 3 attempts.
3. Record the current latest tag as the previous release: `git describe --tags --abbrev=0` (or empty if no tags exist yet).
4. Run `mage tag` to create a `v0.YYYYMMDD.N` tag. Capture the new tag name from the output or via `git describe --tags --abbrev=0`.
5. Generate a summary of changes since the last release. Run `git log --oneline <previous-tag>..<new-tag>` to get the commit list (or all commits if no previous tag). Summarize the changes into a concise changelog grouped by category (features, fixes, docs, etc.).
6. Replace the lightweight tag with an annotated tag carrying the summary: `git tag -d <new-tag> && git tag -a <new-tag> -m "<summary>"`. Print the summary to the user.
7. Push the current branch to `origin`. If `git remote | grep -q release` succeeds, also push the branch to `release`.
8. Push tags to `origin` with `git push origin --tags`. If the `release` remote exists, also push tags to `release` with `git push release --tags`.
9. Resolve the module path with `go list -m` and run `go get <module>@<new-tag>` to fetch the new version via the Go module proxy. Report any errors but do not fail the release.
10. Report the tag name, branch, which remotes received the push, and the change summary.
