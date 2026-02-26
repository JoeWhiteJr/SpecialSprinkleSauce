---
description: "Summarize all changes on the current branch vs main"
allowed-tools: Bash, Read, Grep
---

# Diff Summary

Generate a human-readable summary of everything that changed on this branch compared to main.

---

## Step 1 — Gather Data

```bash
BRANCH=$(git branch --show-current)

# File-level summary
git diff origin/main..."$BRANCH" --stat

# Number of commits
git log origin/main.."$BRANCH" --oneline

# Full diff
git diff origin/main..."$BRANCH"
```

If on `main`, **STOP**: "You're on main. Switch to a feature branch first."

If there are no differences, **STOP**: "No changes on this branch compared to main."

---

## Step 2 — Analyze

Read the full diff output. Categorize the changes by area:

- **Backend / API**: changes to server code, routes, controllers, models
- **Frontend / UI**: changes to components, styles, templates
- **Tests**: new or modified test files
- **Config / Build**: changes to configs, CI, dependencies
- **Docs**: README, comments, documentation files
- **Database**: migrations, schema changes

---

## Step 3 — Present

Format as:

```
Branch: <branch-name>
Commits: <N>
Files changed: <N>
Lines: +<added> / -<removed>

## Changes by area

### <Area 1>
- <file>: <what changed and why>
- <file>: <what changed and why>

### <Area 2>
- <file>: <what changed and why>

## Summary
<2-3 sentence plain-English description of what this branch accomplishes>
```

Keep it concise but complete. The goal is that someone reading this summary understands the branch without looking at the code.
