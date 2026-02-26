---
description: "Rebase the current branch against main and resolve any conflicts"
allowed-tools: Bash, Read, Edit, Write
---

# Rebase Check

Rebase the current branch onto the latest `origin/main`. Resolve conflicts if any arise, then verify with tests.

---

## Pre-flight

```bash
BRANCH=$(git branch --show-current)
```

- If on `main` or `master`, **STOP**: "Already on main. Nothing to rebase."
- If there are uncommitted changes (`git status --porcelain` is non-empty), **STOP**: "You have uncommitted changes. Commit or stash them first."

---

## Step 1 — Fetch and Rebase

```bash
git fetch origin main
git rebase origin/main
```

**If the rebase succeeds** (exit code 0) — go to Step 3.
**If conflicts** — go to Step 2.

---

## Step 2 — Resolve Conflicts

Loop until the rebase is fully complete:

1. List conflicted files:
   ```bash
   git diff --name-only --diff-filter=U
   ```
2. For **each** conflicted file:
   - Read the entire file using the Read tool.
   - Locate every conflict block:
     ```
     <<<<<<< HEAD
     (our changes)
     =======
     (their changes — from main)
     >>>>>>> <commit>
     ```
   - **Resolve** by merging both intents:
     - If both sides modify different parts, keep both.
     - If both sides modify the same code, combine them logically. Prefer the current branch's new work but incorporate fixes from main.
     - **Never silently drop changes** from either side.
   - Write the resolved file with **no conflict markers**.
   - Stage:
     ```bash
     git add <file>
     ```
3. Continue:
   ```bash
   git rebase --continue
   ```
4. If new conflicts appear, repeat from (1).

---

## Step 3 — Verify with Tests

Detect and run the project's test suite:

| Check | Command |
|-------|---------|
| `package.json` with `"test"` script | `npm test` |
| `pytest.ini` / `pyproject.toml` / `setup.py` | `pytest` |
| `*_test.go` files | `go test ./...` |
| `Cargo.toml` | `cargo test` |
| `Makefile` with `test` target | `make test` |

- **Tests pass**: Report success.
- **Tests fail**: Show output and tell the user to fix before proceeding.
- **No tests found**: Inform the user and continue.

---

## Step 4 — Report

```bash
git log --oneline -5
```

Show the updated commit history. Tell the user: "Rebase complete. Your branch is up to date with main."
