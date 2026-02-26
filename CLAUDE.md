# CLAUDE.md — Wasden Watch Dashboard

## Project
Wasden Watch is an automated trading system dashboard. This repo contains:
- `frontend/` — Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts
- `backend/` — Python FastAPI
- `database/` — Supabase PostgreSQL migrations and seed data
- `docs/` — Project documentation (CLAUDE_v2.md, KNOWLEDGE_BASE_v2.md, PROJECT_STANDARDS_v2.md, SCHEDULE_v1.md)

## Critical Rules
1. **TRADING_MODE** must be explicitly set to "paper" or "live". System halts if unset. No defaults.
2. **Pre-trade validation** is SEPARATE from Decision Arbiter. Never merge these code paths.
3. **Risk constants** (MAX_POSITION_PCT=0.12, etc.) are read-only in the dashboard. Changes require human approval.
4. **5-5 jury ties** always escalate to human. Never auto-resolve.
5. Never hardcode API keys or credentials.

## Running
```bash
# Frontend
cd frontend && npm run dev   # http://localhost:3000

# Backend
cd backend && uvicorn app.main:app --reload   # http://localhost:8000
```

## Deploy
- Frontend: Vercel (root dir: `frontend/`)
- Backend: Render (root dir: `backend/`)

## Git Workflow Commands
Custom slash commands available in `.claude/commands/`:

| Command | Description |
|---------|-------------|
| `/ship` | Full pipeline — rebase, test, commit, push, create PR |
| `/rebase-check` | Rebase against main + resolve conflicts |
| `/smart-commit` | Review diff, generate commit message, commit |
| `/create-pr` | Push branch + open PR with auto-generated summary |
| `/cleanup` | Delete branch after PR is merged |
| `/git-status` | Quick overview of branch, changes, and remote status |
| `/branch` | Create a new feature branch from latest main |
| `/diff-summary` | Summarize all branch changes vs main |

When the user finishes coding, suggest `/ship` to handle the full git workflow. For individual steps, suggest the specific command.

## Key Docs
- `docs/PROJECT_STANDARDS_v2.md` — Decision journal schema, risk constants, data freshness grades
- `docs/CLAUDE_v2.md` — Protected components, TRADING_MODE rules
- `docs/KNOWLEDGE_BASE_v2.md` — Bloomberg snapshot, dashboard views, pilot tickers
