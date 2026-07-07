---
name: gh-issue-show
description: List GitHub issues in the current repository, or show details of a specific issue. Use when the user wants to browse issues, look up an issue by number, or inspect issue metadata and comments.
argument-hint: [issue-number]
allowed-tools: Bash(gh issue list), Bash(gh issue view *)
---

# Gh Issue Show

If no argument is provided, list open issues in the current repository.
If an issue number is provided, show the full details of that issue.

## Behavior

- No argument (`/gh-issue-show`): run `gh issue list` and display the results
- With issue number (`/gh-issue-show 42`): run `gh issue view $ARGUMENTS` and display the full issue including body and comments

Present the output clearly. For issue lists, summarize the number, title, and state. For a single issue, show all relevant details: number, title, state, labels, assignees, body, and recent comments.
