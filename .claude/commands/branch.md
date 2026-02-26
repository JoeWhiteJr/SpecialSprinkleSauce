---
description: "Create a new feature branch from the latest main"
allowed-tools: Bash
---

# Create Feature Branch

Create a new branch from the latest `origin/main`.

---

## Step 1 — Get Branch Name

If the user provided a branch name as an argument (e.g. `/branch feature/my-thing`), use it.

If not, ask: "What should the branch be called?" Suggest a name based on context using the convention:
- `feature/<name>` — for new functionality
- `fix/<name>` — for bug fixes
- `chore/<name>` — for maintenance tasks
- `refactor/<name>` — for code restructuring

---

## Step 2 — Check for Uncommitted Work

```bash
git status --porcelain
```

If there are uncommitted changes, warn the user: "You have uncommitted changes on `<current-branch>`. They will NOT carry over to the new branch." Ask: "Stash them, commit them, or proceed anyway?"

- **Stash**: `git stash push -m "auto-stash before branch switch"`
- **Commit**: Run `/smart-commit` first.
- **Proceed**: Continue (changes stay on the current branch's working tree — Git will carry unstaged changes if possible).

---

## Step 3 — Create the Branch

```bash
git fetch origin main
git checkout -b <branch-name> origin/main
```

If the branch name already exists locally:
```bash
git branch --list "<branch-name>"
```
- If it exists, tell the user and ask for a different name.

---

## Step 4 — Confirm

```bash
git branch --show-current
git log --oneline -1
```

Tell the user: "Created branch `<branch-name>` from latest main. You're ready to start working."
