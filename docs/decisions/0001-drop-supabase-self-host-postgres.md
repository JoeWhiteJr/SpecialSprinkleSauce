# 0001 — Drop Supabase, self-host Postgres + pgvector on daisy

- **Status:** Accepted
- **Date:** 2026-07-10
- **Deciders:** Joe, Jared
- **Related ticket:** SSS-T008

## Context

Wasden Watch currently uses **Supabase (cloud)** for three roles: the operational Postgres database (29 migrations — decision journal, recommendations, positions, jury votes, pgvector embeddings for the Wasden RAG), dashboard **Auth**, and a data source the Vercel frontend reads **directly** (`NEXT_PUBLIC_SUPABASE_URL`).

Two forces push us off it:
1. **Cost / control** — we don't want to depend on or pay a cloud vendor for the core datastore; the Supabase free tier also caps storage at 500 MB, which cannot hold the training datasets.
2. **Consolidate onto one box** — Emery Holden has provisioned "daisy" (Debian 13, 4 vCPU / 8 GB, 99 GB local + a 1 TB shared NFS at `/shared`), which is now the project's compute home. Running the datastore there puts data, backend, and training in one place.

Audit of the coupling (2026-07-10) found the migration is smaller than a typical Supabase extraction:
- Backend **auth is already API-key based** (`backend/app/auth.py`), *not* Supabase Auth — nothing to replace server-side.
- The migration runner (`database/run_migrations.py`) is already **psycopg2 + `DATABASE_URL`** — Postgres-native, never needed Supabase.
- All **129 backend DB call sites route through one file**, `backend/app/services/supabase_client.py`.
- Only **1 frontend file** touches Supabase directly.
- Of 29 migrations, **9 are RLS/`auth.*`-specific** — needed only to guard *browser-direct* DB access, which this change removes.

## Decision

Migrate the datastore to **self-hosted PostgreSQL 17 + pgvector on daisy**, bound to localhost, and **remove the Supabase dependency entirely**.

Data-access approach: **compatibility shim (Approach A)** — reimplement `supabase_client.py` as a small query-builder over `psycopg`/`asyncpg` that preserves the Supabase `.table().select().eq().execute()` surface, so the ~129 call sites remain unchanged. A later, optional pass may migrate call sites to SQLAlchemy table-by-table.

RLS/auth migrations (`013`, `014b`, and RLS blocks) are **dropped, not ported**, since only the backend (service-level, over localhost) connects to the DB. The frontend reaches data only through the backend API.

## Consequences

**Positive:** no cloud dependency or storage cap; DB, backend, and training co-located on daisy; Postgres never exposed to the internet (daisy opens only 22/80/443; DB stays localhost); ~129 call sites untouched by the shim.

**Negative / risks:** we now own Postgres ops (backups, upgrades, availability — no managed HA); the shim is bespoke code to maintain until/unless we move to SQLAlchemy; the frontend's 1 direct-Supabase file and its Supabase Auth login must be re-pointed at the backend; the backend likely must **move off Render onto daisy** (Render pointed at a localhost DB is unreachable) with a reverse proxy on :443; daisy is a single point of failure (mitigate with `/shared` + offsite backups).

## Alternatives considered

- **B. Full rewrite to SQLAlchemy/raw SQL** across all 129 call sites — cleanest long-term but days of work and broad regression risk; deferred as optional follow-up.
- **Self-host the full Supabase stack (Docker)** — keeps client libs unchanged but re-introduces the whole Supabase surface (Auth, PostgREST, Realtime, Studio, Kong) we're trying to shed, and is heavier on an 8 GB box.
- **Keep Supabase cloud as a thin app DB**, datasets on `/shared` — least work, but fails the cost/control and one-box goals.
