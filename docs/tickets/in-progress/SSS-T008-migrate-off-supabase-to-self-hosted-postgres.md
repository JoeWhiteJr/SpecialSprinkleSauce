---
id: SSS-T008
title: Migrate off Supabase to self-hosted Postgres + pgvector on daisy
status: in-progress
priority: high
type: infrastructure
owner: joe
created: 2026-07-10
updated: 2026-07-10
related-pr:
related-tickets: SSS-T005
assigned-team:
---

# Migrate off Supabase to self-hosted Postgres + pgvector on daisy

## Problem
Wasden Watch depends on **Supabase (cloud)** as its operational database (29 migrations), dashboard auth, and a direct data source for the Vercel frontend. We want off it for cost/control and to consolidate onto **daisy** (the self-hosted box, `/shared` = 1 TB), whose datastore stays private (daisy exposes only ports 22/80/443). See ADR `docs/decisions/0001-drop-supabase-self-host-postgres.md`.

Coupling audit (2026-07-10): backend auth is already API-key based (not Supabase Auth); the migration runner is already `DATABASE_URL`/psycopg2; all 129 backend DB calls route through the single `backend/app/services/supabase_client.py`; only 1 frontend file touches Supabase; 9 of 29 migrations are RLS/`auth.*`-specific (guard browser-direct access only).

## Approach
**A — compatibility shim.** Reimplement `supabase_client.py` over `psycopg`/`asyncpg`, preserving the `.table().select().eq().execute()` surface so the ~129 call sites are unchanged.

**RLS handling (refined 2026-07-15):** No policy references `auth.uid()`/`auth.jwt()` — they only grant to roles `authenticated`/`service_role`. So instead of excluding/stripping the 9 RLS-bearing migrations (6 of which also create needed tables), we create **empty stub roles** (`anon`, `authenticated`, `service_role`) and run all 29 migrations **unmodified**; RLS is inert because the app connects as owner `wasden` (owner bypasses RLS). Also fixes needed: the Python `run_migrations.py` file list is stale (stops at `024`, skips `025_goals`/`026_training_lab`/`027_audit_log`) — migrations applied via `psql` in sorted order for now; update the runner as follow-up.

## Acceptance Criteria
- [x] PostgreSQL 17 + pgvector running on daisy, bound to localhost, dedicated DB + role for the app ✅ 2026-07-15
- [x] All 29 migrations + seed applied via `psql` using stub roles (anon/authenticated/service_role) so RLS runs inert; app connects as owner `wasden` (bypasses RLS) ✅ 2026-07-15
- [x] `supabase_client.py` reimplemented as a Postgres-backed shim (psycopg3 + pool) covering the used surface: table/from_, select, insert, update, upsert(on_conflict), delete, eq/neq/gt/gte/lt/lte/in_/ilike, order/limit/range, single, execute; auto-adapts jsonb (Jsonb wrap) vs ARRAY (native list). 17/17 shim tests pass ✅ 2026-07-23
- [~] Backend runs against local Postgres with `USE_MOCK_DATA=false`: reads/writes work end-to-end through routers, BUT integration smoke surfaced pre-existing latent bugs in live-data router paths (columns that don't exist, e.g. `.order("timestamp")` on `risk_alerts` whose column is `created_at`; 6× across routers). Split to **SSS-T009**. `check_connection()` verifies local DB ✅
- [ ] The 1 frontend Supabase file re-pointed at the backend API; Supabase Auth login replaced with backend-issued auth
- [ ] Config: `SUPABASE_URL/ANON_KEY/SERVICE_KEY` and `NEXT_PUBLIC_SUPABASE_*` removed; `DATABASE_URL` (local) is the single source; docker-compose/render/deploy updated (backend likely moves to daisy on :443 behind a reverse proxy)
- [ ] Backend test suite passes on daisy against local Postgres; a real pipeline pass reads/writes local DB
- [ ] `supabase==2.31.0` and `@supabase/supabase-js` removed from deps
- [ ] pg_dump backup + restore verified; backup lands on `/shared` + one offsite copy

## Implementation Plan (phased)
1. **Postgres + pgvector on daisy** (localhost-only) — needs one sudo install from Joe
2. **Run migrations** (20 core; exclude RLS/auth) → schema on daisy
3. **Build the shim** in `supabase_client.py` → backend talks to local Postgres
4. **Rewire the 1 frontend file** + swap its Supabase login for backend auth
5. **Config/hosting**: `SUPABASE_*` → `DATABASE_URL`; move backend onto daisy (:443 reverse proxy)
6. **Verify**: test suite + real pipeline pass on daisy; set up pg_dump backups to `/shared` + offsite

## Context & Notes
Server: see memory `reference_calibrast_server` — daisy = `ssh jwhitejr@166.70.100.114`, repo cloned at `~/SpecialSprinkleSauce` (current `main`, ahead of Joe's local #33), Python 3.11 venv provisioned. Related: SSS-T005 (server-side auth) overlaps the frontend-auth rewire — coordinate so we don't build the login twice.

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
