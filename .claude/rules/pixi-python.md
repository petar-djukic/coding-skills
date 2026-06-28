<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Pixi for Python

We use pixi (https://pixi.sh/) to manage Python environments and dependencies. Do not use pip, pip3, conda, or virtualenv directly.

## Commands

| Task | Command |
|------|---------|
| Create a new workspace | `pixi init` (creates pixi.toml in current directory) |
| Add a conda package | `pixi add <package>` |
| Add a PyPI package | `pixi add --pypi <package>` |
| Enter the environment shell | `pixi shell` |
| Run a command in the environment | `pixi run <command>` |

## Setting Up Python

When Python is needed and no pixi.toml exists yet, initialize first:

```bash
pixi init
pixi add python
pixi add <any-other-packages>
```

Then run Python scripts with `pixi run python3 script.py` or enter `pixi shell` for interactive use.

## Rules

- Never run `pip install` or `pip3 install` outside of pixi.
- Never create virtualenvs manually. Pixi manages environments.
- Use `pixi add` to declare dependencies so they are tracked in pixi.toml and the lockfile.
- Use `pixi add --pypi <package>` for packages only available on PyPI (not in conda channels).
- Commit pixi.toml and pixi.lock to version control.
