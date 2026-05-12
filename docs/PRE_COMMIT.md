# Pre-Commit Hooks

Wasden Watch is a security-first project — real money will eventually
flow through it. To prevent the most common classes of "oops" from
reaching the repo, every commit runs a layered set of local checks
before it lands.

## Layer 1 — Repo-root `pre-commit` framework

Defined in `.pre-commit-config.yaml`. Installed by `make hooks-install`.

| Hook | Purpose |
|------|---------|
| **gitleaks** | Scans the staged diff for API keys, tokens, and credentials. This is the most important hook — never bypass it without explicit human review. |
| **ruff check** | Backend Python lint (matches CI: `--select=E,F,W --ignore=E501`). Auto-fixes when safe. |
| **ruff format** | Backend Python formatting. |
| **check-merge-conflict** | Blocks accidentally committing `<<<<<<<` markers. |
| **check-yaml** | Validates YAML syntax (CI workflows, docker-compose, render.yaml). |
| **check-json** | Validates JSON syntax (package.json, tsconfig, `.lintstagedrc`). |
| **end-of-file-fixer** | Ensures files end with a single newline. |
| **trailing-whitespace** | Strips trailing whitespace. |
| **no-commit-to-branch** | Blocks direct commits to `main`. Forces the feature-branch workflow. |
| **check-added-large-files** | Blocks adding any file >500KB. Catches forgotten datasets, model binaries, screenshots, etc. |
| **frontend-lint-staged** | Runs `eslint --fix` on staged `*.{ts,tsx,js,jsx}` files via lint-staged. |

All hook revisions are pinned to specific release tags — no floating
refs — so the toolchain is reproducible across machines and over time.

## Layer 2 — Frontend supplementary (husky + lint-staged)

`frontend/.husky/pre-commit` is created by `make hooks-install` but is
**not active by default**. The repo-root `pre-commit` framework owns
`.git/hooks/pre-commit` and already runs the same `lint-staged` step.

The husky file exists so a developer who only works in `frontend/` can
opt in by running `cd frontend && npx husky` themselves. Doing so sets
`core.hooksPath` to `frontend/.husky` and bypasses the root framework
(including the gitleaks secret scan) — so do **not** enable husky as the
active hook unless you have a specific reason.

## Install / Run

```bash
# One-time, after a fresh clone:
make hooks-install

# Run every hook against every file (CI-equivalent):
make hooks-run
# or:
pre-commit run --all-files

# Update pinned hook revisions:
pre-commit autoupdate
```

## Bypassing in genuine emergencies

`git commit --no-verify` skips every hook. This must be **rare**.
Every bypass must:

1. Be justified in the commit message itself (e.g. `[no-verify: gitleaks
   false positive on test fixture, scanned manually]`).
2. Be reviewed by another human before the PR merges.
3. Never be used to bypass `gitleaks`, `check-added-large-files`, or
   `no-commit-to-branch` without explicit human approval — these guard
   the three most common ways to leak secrets, blow up the repo, or
   ship straight to production.

If a hook is wrong in a recurring way, fix the hook config — don't keep
bypassing it.

## CI integration

`make ci` runs `hooks-run` before lint/typecheck/test/build, so a PR
that would fail locally also fails in CI. The GitHub Actions workflow
runs the same hooks via `pre-commit/action` (added in a follow-up task).
