---
description: "Delete the local and remote branch after a PR has been merged"
allowed-tools: Bash
---

# Cleanup — Post-Merge Branch Cleanup

Remove the feature branch after its PR has been merged.

---

## Step 1 — Identify Branch

```bash
BRANCH=$(git branch --show-current)
echo "$BRANCH"
```

- If `main` or `master`, **STOP**: "Already on main. Nothing to clean up."
- Save the branch name for later steps.

---

## Step 2 — Check Merge Status

Try with `gh` first:

```bash
gh pr list --state merged --head "$BRANCH" --json number,title,url
```

**If `gh` works and returns a result** — the PR is merged. Continue.
**If `gh` returns empty** — the PR is NOT merged. **STOP**: "The PR for `<branch>` hasn't been merged yet. Merge it first."

**If `gh` is not available:**
- Ask the user directly: "Has the PR for `<branch>` been merged on GitHub? (yes/no)"
- If no, **STOP**.
- If yes, continue.

---

## Step 3 — Switch to Main and Pull

```bash
git checkout main
git pull origin main
```

Verify the pull succeeds. If it fails, report the error.

---

## Step 4 — Delete Local Branch

```bash
git branch -d "$BRANCH"
```

- If it succeeds — continue.
- If it fails with "not fully merged" — tell the user: "Branch `<branch>` appears not fully merged locally. This can happen if the PR was squash-merged." Ask: "Force delete with `git branch -D`?"
  - If user says yes:
    ```bash
    git branch -D "$BRANCH"
    ```

---

## Step 5 — Delete Remote Branch

**Ask the user first**: "Delete the remote branch `origin/<branch>` as well? (yes/no)"

If yes:
```bash
git push origin --delete "$BRANCH"
```

If no — skip.

---

## Step 6 — Report

```bash
git log --oneline -5
```

Tell the user: "Cleanup complete. Branch `<branch>` deleted. You're on main with the latest changes."
