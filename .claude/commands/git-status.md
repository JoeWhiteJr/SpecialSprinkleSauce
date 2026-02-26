---
description: "Quick overview of current branch, changes, and remote status"
allowed-tools: Bash
---

# Git Status Overview

Gather the full state of the repo and present a clean summary.

---

## Gather Data

Run all of these:

```bash
# Current branch
git branch --show-current

# Working tree status (staged, unstaged, untracked)
git status --short

# How far ahead/behind main
git rev-list --left-right --count origin/main...HEAD 2>/dev/null

# Commits ahead of main
git log origin/main..HEAD --oneline 2>/dev/null

# Stash list
git stash list

# Last commit info
git log -1 --format="%h %s (%cr)"
```

---

## Present Summary

Format the output as:

```
Branch:       <branch-name>
Last commit:  <hash> <message> (<time ago>)
Ahead of main: <N> commits
Behind main:  <N> commits

Staged:
  <list of staged files, or "none">

Unstaged:
  <list of modified but unstaged files, or "none">

Untracked:
  <list of untracked files, or "none">

Stashes: <count, or "none">
```

If ahead of main by >0 commits, list them with `git log origin/main..HEAD --oneline`.
