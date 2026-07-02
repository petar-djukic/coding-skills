---
description: List open GitHub issues in the current repository, or show full details of a specific issue by number.
---

If no argument is provided, list open issues in the current repository.
If an issue number is provided, show the full details of that issue.

## Input

$ARGUMENTS

## Behavior

- No argument: run `gh issue list` and display the results
- With issue number: run `gh issue view $ARGUMENTS` and display the full issue including body and comments

Present the output clearly. For issue lists, summarize the number, title, and state. For a single issue, show all relevant details: number, title, state, labels, assignees, body, and recent comments.
