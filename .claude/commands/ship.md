---
description: "Full pipeline: rebase, test, commit, push, create PR"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Ship — Full Git Workflow Pipeline

Execute every step below **in order**. If any step fails, stop immediately, report the error, and ask the user how to proceed. Do NOT skip steps.

---

## Pre-flight Checks

```bash
# Confirm we're in a git repo
git rev-parse --is-inside-work-tree

# Get the current branch
BRANCH=$(git branch --show-current)
```

- If the branch is `main` or `master`, **STOP**. Tell the user: "You're on the main branch. Create a feature branch first with `/branch`."
- If the branch is detached HEAD, **STOP**. Tell the user to checkout a branch.

```bash
# Check for uncommitted work
git status --porcelain
```

- If there are unstaged or untracked changes, list them and ask: "There are uncommitted changes. Should I commit these first, or do you want to handle them?"

---

## Step 1 — Rebase on Main

```bash
git fetch origin main
```

If fetch fails, report the network error and stop.

```bash
git rebase origin/main
```

**If the rebase succeeds** (exit code 0) — move to Step 2.

**If the rebase has conflicts:**

1. Run `git status` to list every conflicted file.
2. For **each** conflicted file:
   - Read the full file with the Read tool.
   - Find every conflict block (`<<<<<<<` / `=======` / `>>>>>>>`).
   - Analyze both sides:
     - **HEAD (ours)**: the current branch's changes.
     - **incoming (theirs)**: what's on main.
   - Resolve by combining the intent of both sides. Prefer our new work but incorporate upstream bug fixes or safety improvements.
   - Write the resolved file (no conflict markers remaining).
   - Stage it:
     ```bash
     git add <file>
     ```
3. Continue the rebase:
   ```bash
   git rebase --continue
   ```
4. If more conflicts appear, repeat. Loop until the rebase completes.

---

## Step 2 — Run Tests

Detect the test runner by checking these in order:

```bash
# Node.js
[ -f package.json ] && grep -q '"test"' package.json

# Python
[ -f pytest.ini ] || [ -f setup.py ] || [ -f pyproject.toml ]

# Go
ls *.go 2>/dev/null || ls **/*_test.go 2>/dev/null

# Rust
[ -f Cargo.toml ]

# Makefile
[ -f Makefile ] && grep -q 'test' Makefile
```

Run the appropriate test command:
- **Node.js**: `npm test`
- **Python**: `pytest`
- **Go**: `go test ./...`
- **Rust**: `cargo test`
- **Makefile**: `make test`

**If tests pass** — move to Step 3.
**If tests fail** — show the failure output and **STOP**. Tell the user: "Tests failed after rebase. Fix the failures before shipping."
**If no test runner found** — tell the user: "No test suite detected. Proceeding without tests." Then move to Step 3.

---

## Step 3 — Commit

```bash
git status --porcelain
```

If there are no uncommitted changes (everything was already committed), skip to Step 4.

If there are changes:

```bash
# See what changed
git diff
git diff --staged
```

1. Read through the diff output carefully.
2. Stage all relevant files:
   ```bash
   git add <file1> <file2> ...
   ```
   - Do **NOT** stage `.env`, `.env.*`, `credentials.json`, `*.pem`, `*.key`, or anything that looks like secrets. Warn the user if you see these.
3. Check `git log --oneline -5` for the commit message style used in this repo.
4. Write a commit message:
   - First line: imperative verb + concise summary (under 72 chars).
   - If the change is complex, add a blank line then a short body paragraph.
   - End with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
5. Commit using a heredoc:
   ```bash
   git commit -m "$(cat <<'EOF'
   <commit message here>

   Co-Authored-By: Claude Code <noreply@anthropic.com>
   EOF
   )"
   ```

---

## Step 4 — Push and Create PR

```bash
BRANCH=$(git branch --show-current)
git push -u origin "$BRANCH"
```

If push fails due to auth, tell the user to check SSH keys and stop.

Generate PR content:
```bash
git log origin/main.."$BRANCH" --oneline
git diff origin/main..."$BRANCH" --stat
```

1. Read the commit log and diff stat.
2. Write a PR title (under 70 chars, descriptive).
3. Write a PR body with:
   - `## Summary` — 1-3 bullet points covering what changed.
   - `## Test plan` — how to verify the changes.
   - Footer: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

Create the PR:
```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
- <bullet 1>
- <bullet 2>

## Test plan
- [ ] <verification step>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**If `gh` is not available or not authenticated:**
- Tell the user: "The `gh` CLI is not available. Create the PR manually at:"
- Provide the URL: `https://github.com/<owner>/<repo>/compare/main...<branch>`

---

## Step 5 — Report

Tell the user:
- The PR URL (or manual link).
- "Once the PR is merged, run `/cleanup` to delete the branch."
