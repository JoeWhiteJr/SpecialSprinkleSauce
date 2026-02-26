---
description: "Review changes, generate a meaningful commit message, and commit"
allowed-tools: Bash, Read, Grep
---

# Smart Commit

Analyze all changes in the working tree, generate a descriptive commit message, and commit.

---

## Step 1 — Gather Changes

```bash
git status --porcelain
```

- If output is empty, **STOP**: "No changes to commit."

```bash
# Unstaged changes
git diff

# Staged changes
git diff --staged

# Untracked files
git ls-files --others --exclude-standard
```

Read through all output carefully. Understand **what** changed and **why** based on the code context.

---

## Step 2 — Security Check

Scan the changed/untracked files for secrets. **Do NOT stage** any of these:
- `.env`, `.env.*`, `.env.local`, `.env.production`
- `credentials.json`, `serviceAccountKey.json`
- `*.pem`, `*.key`, `*.p12`, `*.pfx`
- Files containing strings like `PRIVATE KEY`, `sk-`, `api_key=`, `secret=`, `password=`

If any are found, warn the user: "Found potentially sensitive files: `<list>`. These will NOT be staged."

---

## Step 3 — Stage Files

Stage all non-secret changed and untracked files:

```bash
git add <file1> <file2> <file3> ...
```

List each file explicitly — do **not** use `git add -A` or `git add .` to avoid accidentally staging secrets or unrelated files.

If there are changes spanning **multiple unrelated concerns** (e.g., a bug fix AND a new feature), ask the user: "These changes cover multiple concerns. Should I commit everything together, or would you like to split them into separate commits?"

---

## Step 4 — Generate Commit Message

```bash
# Check existing commit style
git log --oneline -5
```

Write a commit message following these rules:
- **First line**: imperative mood verb + concise summary (max 72 characters).
  - `Add` = wholly new feature
  - `Fix` = bug fix
  - `Update` = enhancement to existing feature
  - `Refactor` = code restructure, no behavior change
  - `Remove` = deletion
  - `Docs` = documentation only
- **Body** (if changes are complex): blank line, then 1-3 sentences explaining *why*, not *what*.
- Match the existing commit style if the repo has a clear convention.

---

## Step 5 — Commit

```bash
git commit -m "$(cat <<'EOF'
<first line>

<optional body>

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

## Step 6 — Confirm

```bash
git log --oneline -3
```

Show the user the last 3 commits to confirm the new one looks right.
