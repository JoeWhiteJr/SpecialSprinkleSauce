# Wasden Watch Dashboard

Automated trading system dashboard for the Wasden Watch pipeline.

## Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | Python FastAPI |
| Database | Supabase (PostgreSQL + pgvector) |
| Auth | Supabase Auth |
| Deploy (FE) | Vercel |
| Deploy (BE) | Render |

## Dashboard Pages

1. **Portfolio Monitoring** — P&L vs SPY, positions table, win/loss history
2. **Recommendations** — Daily feed with confidence scores, approve/reject
3. **Decision Journal** — Full audit trail per pipeline run
4. **Debates** — Bull (Claude) vs Bear (Gemini) transcript viewer
5. **Jury Votes** — 10-agent vote breakdown and stats
6. **Override Controls** — Approve/reject/escalate with mandatory reason
7. **Alerts** — Consecutive loss tracking, risk alerts
8. **Bias Monitor** — Verdict distribution, sector concentration, agreement rate
9. **Screening Funnel** — 5-tier visualization (500 -> 3-8 recommendations)
10. **Settings** — TRADING_MODE toggle, API status, risk constants

## Quick Start

```bash
# Frontend
cd frontend
npm install
npm run dev          # http://localhost:3000

# Backend
cd backend
pip install -r requirements.txt
TRADING_MODE=paper uvicorn app.main:app --reload   # http://localhost:8000
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values. `TRADING_MODE` is required — system halts if unset.

## Deployment

- **Frontend** → Vercel (root directory: `frontend/`)
- **Backend** → Render (root directory: `backend/`)

## Documentation

See `docs/` for project standards, knowledge base, and schedule.
