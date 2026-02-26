# PARTNER_SYNC.md — Cross-Session Context for Joe & Jared

> **Purpose:** This file bridges context between Joe's and Jared's separate Claude Code sessions.
> Both partners work on the same GitHub repo from different machines. Since each Claude Code session
> starts fresh, this document ensures both sessions have full context on what's been done,
> what's live, how to set up, and how to collaborate.
>
> **Update this file whenever you make a significant change to the project.**

---

## Current State (as of Feb 25, 2026)

- **Week 1: COMPLETE** — Foundation, environment, deployment, data assets confirmed
- **Starting: Week 2** — Data Pipeline & Database Schema
- Dashboard is deployed and functional at the URLs below
- Supabase database is seeded with initial data
- All API accounts created (Alpaca paper, Finnhub, NewsAPI)
- Repo structured: `frontend/`, `backend/`, `database/`, `docs/`

---

## Live URLs & Services

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://special-sprinkle-sauce.vercel.app |
| Backend (Render) | https://specialsprinklesauce.onrender.com |
| Supabase Dashboard | https://supabase.com/dashboard/project/tdipkiutsigmuzpfxsvj |
| GitHub Repo | https://github.com/JoeWhiteJr/SpecialSprinkleSauce |

---

## Local Setup (for Jared's Machine)

```bash
# 1. Clone the repo
git clone https://github.com/JoeWhiteJr/SpecialSprinkleSauce.git
cd SpecialSprinkleSauce

# 2. Set up environment variables
cp .env.example .env
# Then fill in real values — get credentials from Joe (see Env Vars section below)

# 3. Run the frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000

# 4. Run the backend (in a separate terminal)
cd backend
pip install -r requirements.txt
TRADING_MODE=paper uvicorn app.main:app --reload
# → http://localhost:8000
```

**Database:** Migrations have already been applied to Supabase. You do NOT need to re-run them unless new migration files are added. If new migrations appear in `database/migrations/`, apply them against Supabase.

---

## Environment Variables Reference

All env vars are listed in `.env.example` at the repo root. **Never commit `.env`** — it's gitignored.

| Variable | Where It's Set | Notes |
|----------|---------------|-------|
| `SUPABASE_URL` | Local `.env`, Render, Vercel | Supabase project URL |
| `SUPABASE_ANON_KEY` | Local `.env`, Render, Vercel | Public anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Local `.env`, Render | Server-side only — never expose to frontend |
| `DATABASE_URL` | Local `.env`, Render | Connection pooler URL (port 6543) |
| `ALPACA_API_KEY` | Local `.env`, Render | Paper trading key |
| `ALPACA_SECRET_KEY` | Local `.env`, Render | Paper trading secret |
| `FINNHUB_API_KEY` | Local `.env`, Render | Market data |
| `NEWSAPI_KEY` | Local `.env`, Render | News sentiment |
| `TRADING_MODE` | Local `.env`, Render | Must be `paper` or `live` — system halts if unset |

**Jared:** Get credential values directly from Joe. They are NOT stored in the repo.

**Where to configure on hosted services:**
- **Render:** Dashboard → Environment → Environment Variables
- **Vercel:** Dashboard → Settings → Environment Variables

---

## Deployment Architecture

```
┌─────────────┐     push to main     ┌─────────────────┐
│  GitHub Repo │─────────────────────→│  Vercel          │
│  (main)      │                      │  Frontend        │
│              │─────────────────────→│  (Next.js)       │
│              │     push to main     ├─────────────────┤
│              │─────────────────────→│  Render          │
│              │                      │  Backend         │
└─────────────┘                      │  (FastAPI)       │
                                     ├─────────────────┤
                                     │  Supabase        │
                                     │  PostgreSQL      │
                                     │  + pgvector      │
                                     └─────────────────┘
```

| Component | Platform | Config |
|-----------|----------|--------|
| Frontend | Vercel | Auto-deploy on push to `main`. Root Directory = `frontend`. No `vercel.json` in repo — all config in Vercel dashboard. |
| Backend | Render | Auto-deploy on push to `main`. Root Directory = `backend`. `PYTHON_VERSION=3.11.0`. |
| Database | Supabase | PostgreSQL with pgvector. Migrations in `database/migrations/`. Seed data in `database/seed/`. |

---

## Git Workflow for Two-Person Team

1. **Always `git pull` before starting work** — avoid merge conflicts
2. Both partners can work on `main` for small changes
3. Use **feature branches** for significant work:
   ```bash
   git checkout -b feature/your-feature-name
   # ... do work ...
   git push -u origin feature/your-feature-name
   # Create a PR for review
   ```
4. Create PRs for review when possible — gives the other person visibility
5. **Pushes to `main` auto-deploy** to both Vercel and Render immediately
6. Communicate before force-pushing or rebasing shared branches

---

## Sharing Claude Code Context

Each machine runs its own Claude Code session with **independent context** — they do not share memory.

**How to keep both sessions aligned:**

1. **This file (`PARTNER_SYNC.md`)** is the primary bridge. Update it when making significant changes.
2. **`CLAUDE.md`** at repo root is loaded by Claude Code automatically on every session. Keep it current with project rules, commands, and structure.
3. **After completing major work**, add a dated entry to the Change Log section at the bottom of this file.
4. **Commit and push** both this file and `CLAUDE.md` so the other session picks up changes on next `git pull`.

---

## Known Issues & Gotchas

- **WSL2 IPv6 routing:** WSL2 can't route to IPv6-only hosts. Use the Supabase **connection pooler** (port `6543`), not the direct connection.
- **Password encoding:** If your Supabase password contains `!`, it must be URL-encoded as `%21` in `DATABASE_URL`.
- **Render cold starts:** Free tier has ~30s cold start on first request after inactivity. The backend will feel slow after periods of no traffic.
- **Extra env vars won't crash backend:** `backend/app/config.py` uses `extra = "ignore"` — adding new env vars to `.env` that aren't in the config schema won't cause errors.
- **Supabase storage limit:** Free tier = 500MB. Large training datasets (Bloomberg bulk, Emery OHLCV) should go on the 4TB server when it's ready (Week 5+).
- **TRADING_MODE is mandatory:** The system halts immediately if `TRADING_MODE` is unset or set to anything other than `paper` or `live`. Always set it.

---

## Team

| Person | Notes |
|--------|-------|
| **Joe** | Co-founder |
| **Jared** | Co-founder |

Both contribute across all areas — no fixed roles.

---

## What's Next (Week 2)

Refer to `docs/SCHEDULE_v1.md` — Week 2: Data Pipeline & Database Schema

**Key Week 2 tasks:**
- Implement fundamental data schema in Supabase
- Build Bloomberg export pipeline: CSV → validate → Supabase with provenance metadata
- Load Dow Jones historical CSV and Emery 10-year OHLCV dataset into Supabase
- Build `TRADING_MODE` env var check — halt if unset or invalid
- Audit datasets for survivorship bias
- Begin `wasden_philosophy.md`

---

## Change Log

| Date | Who | Summary |
|------|-----|---------|
| Feb 25, 2026 | Joe | **Week 1 complete.** Repo created, frontend deployed to Vercel, backend deployed to Render, Supabase configured with migrations and seed data. `.env.example` created. All API accounts set up. GitHub auto-deploy working for both frontend and backend. PARTNER_SYNC.md created. |

---

*End of PARTNER_SYNC.md*
