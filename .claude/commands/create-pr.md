---
description: "Push the current branch and create a pull request"
allowed-tools: Bash, Read, Grep
---

# Create PR

Push the current branch to origin and create a pull request.

---

## Step 1 — Validate

```bash
BRANCH=$(git branch --show-current)
echo "$BRANCH"
```

- If `main` or `master`, **STOP**: "You're on the main branch. Create a feature branch first with `/branch`."

```bash
git status --porcelain
```

- If there are uncommitted changes, **STOP**: "You have uncommitted changes. Run `/smart-commit` first."

```bash
# Make sure we have commits ahead of main
git log origin/main.."$BRANCH" --oneline
```

- If there are **no commits** ahead of main, **STOP**: "No new commits on this branch. Nothing to create a PR for."

---

## Step 2 — Push

```bash
BRANCH=$(git branch --show-current)
git push -u origin "$BRANCH"
```

If push fails:
- **Authentication error**: Tell the user to check SSH keys or credentials.
- **Rejected (non-fast-forward)**: Tell the user to pull/rebase first with `/rebase-check`.

---

## Step 3 — Generate PR Content

Gather context for the PR:

```bash
# All commits on this branch
git log origin/main.."$BRANCH" --oneline

# File change summary
git diff origin/main..."$BRANCH" --stat

# Full diff for analysis
git diff origin/main..."$BRANCH"
```

Read the output. Then generate:

**Title** (under 70 characters):
- Descriptive, not generic. Based on what the commits actually do.
- Examples: "Add user authentication middleware", "Fix pagination offset bug"

**Body**:
```markdown
## Summary
- <bullet point describing key change 1>
- <bullet point describing key change 2>
- <bullet point describing key change 3 if needed>

## Test plan
- [ ] <specific verification step 1>
- [ ] <specific verification step 2>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## Step 4 — Create the PR

Detect the repository's remote URL to determine owner/repo:

```bash
git remote get-url origin
```

Parse the owner and repo name from the URL (works with both SSH and HTTPS formats).

Try creating with `gh`:

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
<body content>
EOF
)"
```

**If `gh` works** — report the PR URL.

**If `gh` is not available or not authenticated:**
- Extract owner/repo from the remote URL.
- Tell the user: "The `gh` CLI is not available. Create the PR manually:"
- Provide: `https://github.com/<owner>/<repo>/compare/main...<branch>`

---

## Step 5 — Report

- Display the PR URL (or manual creation link).
- Tell the user: "Once merged, run `/cleanup` to delete the branch."
