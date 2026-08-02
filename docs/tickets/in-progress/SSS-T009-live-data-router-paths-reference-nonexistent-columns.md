---
id: SSS-T009
title: Live-data router paths reference columns that don't exist (masked by mock mode)
status: open
priority: high
type: bug
owner: joe
created: 2026-07-23
updated: 2026-07-23
related-pr:
related-tickets: SSS-T008, SSS-T001, SSS-T002
assigned-team:
---

# Live-data router paths reference columns that don't exist (masked by mock mode)

## Problem
The app has only ever run with `USE_MOCK_DATA=true`, so the real DB code paths in the routers were never executed. Integration-testing the SSS-T008 Postgres migration (`USE_MOCK_DATA=false`, live local Postgres) surfaced a class of latent bugs: routers query columns that do not exist in the migrated schema.

Confirmed instance: `backend/app/routers/alerts.py:44` runs `.order("timestamp", desc=True)` on `risk_alerts`, but that table's timestamp column is **`created_at`** (schema: `id, created_at, alert_type, severity, message, ticker, details, acknowledged, acknowledged_by, acknowledged_at`). Result: `psycopg.errors.UndefinedColumn: column "timestamp" does not exist` → HTTP 500.

`.order("timestamp")` appears **6×** across routers, so this specific mismatch is likely repeated; there may be other column/table drifts between router code and the migration schema. These would have failed on Supabase too — this is not a migration regression, it's pre-existing dead-path drift that the migration made visible.

## Acceptance Criteria
- [ ] Audit every router DB call (`.order`/`.eq`/`.gte`/`.lte`/`.in_`/`.select(cols)`/`.insert`/`.update`) against the actual migrated schema; produce a list of every column/table mismatch
- [ ] Fix each mismatch (align router code to the schema, or add a migration if the schema is the thing that's wrong)
- [ ] `.order("timestamp")` sites resolved (use the real column, likely `created_at`)
- [ ] Integration smoke: every GET route returns 2xx against the live local DB with seed/empty tables (no 500s from bad columns)
- [ ] Add a lightweight integration test that hits each read route against a real Postgres so this can't silently regress again

## Context & Notes
Discovered during SSS-T008 (Supabase→self-hosted Postgres). The migration mechanism (Postgres + `supabase_client.py` shim) is verified working — this ticket is purely the app-side column drift it exposed. Overlaps SSS-T001/T002 (wire live data into screening/inference), which touch the same live-data paths. Server context: memory `reference_calibrast_server` (daisy), repo at `~/SpecialSprinkleSauce`.

## Audit results (2026-08-02)
AST audit of all router DB calls vs. the live schema found **9 column mismatches** across 6 routers, but the deeper finding is a **systemic model↔schema divergence** — the Pydantic response models in `backend/app/models/schemas.py` were written to match the mock-data generators and never reconciled with the migration schema. This is bigger than renaming columns:

| Response model ↔ table | model wants but table lacks | table has but model ignores |
|---|---|---|
| VetoOverride ↔ veto_overrides | `timestamp` | `created_at`, outcome_note, outcome_pnl |
| TradeRecommendation ↔ trade_recommendations | `timestamp`, `recommended_position_size` | `created_at`, `reasoning` |
| RiskAlert ↔ risk_alerts | `timestamp`, `title`, `rule_violated` | `created_at`, `alert_type`, `details` |
| ScreeningRun ↔ screening_runs | `timestamp`, `stages` (nested), `pipeline_run_ids` | `run_date`, `tier1..5_count`, final_recommendations, data_freshness_summary |
| decision_journal (journal.py) | `timestamp`, `final_decision->>action` | `created_at`; `final_decision` lives on `pipeline_runs`, not this table |

Column-order/filter sites needing fixes: alerts.py:44, journal.py:57/59/61/63, overrides.py:43, recommendations.py:39, screening.py:30/54.

**Shim already handles the mechanics** (verified): jsonb path filters (`col->>key`) now render correctly (`"col"->>'key'`); the failures are purely the routers/models referencing columns that don't exist.

## Decision needed — reconciliation direction
This requires product judgment (what is an alert's `title`? how do `tier1..5_count` become `stages`?) and cascades differently:
- **A — Adapter (model-as-truth):** per-endpoint DB-row→model mapping in the routers (rename created_at→timestamp, derive stages from tier counts, default absent fields). Keeps the API/frontend contract stable; no migration or frontend changes. **Recommended.**
- **B — Schema-as-truth:** change models + mock generators + **frontend** to match DB column names/shapes. Cleaner data model, but breaks the current API contract.
- **C — Migrate schema:** add missing columns (`title`, `rule_violated`, `final_decision`, …). Works for scalar fields but not derived/structural ones (`stages`).

Overlaps SSS-T001/T002 (wire live data into screening/inference), which touch these same paths.

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
