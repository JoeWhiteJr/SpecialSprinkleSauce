---
id: SSS-T002
title: Wire live Bloomberg/Finnhub data into Tier 1 screening
status: open
priority: high
type: feature
owner: joe
created: 2026-04-10
updated: 2026-04-10
related-pr:
related-tickets: [SSS-T001]
---

# Wire live Bloomberg/Finnhub data into Tier 1 screening

## Problem
Backend defaults to `USE_MOCK_DATA=true` — screening, risk, and pipeline runs all operate on fixture data. This is the gating step for paper-trade readiness: until Tier 1 (market cap > $5B filter) runs against live data, we can't validate that the full 5-tier funnel produces a realistic universe.

The data_source_chain (`services/data_source_chain.py`) already supports Supabase → Finnhub → Yahoo fallback. Bloomberg pipeline populates the snapshot table. But the screening engine's Tier 1 query still pulls from mock fixtures.

## Acceptance Criteria
- [ ] Screening engine Tier 1 queries `company_snapshot` table (populated by bloomberg_pipeline) when `USE_MOCK_DATA=false`
- [ ] Data freshness check integrated — if all snapshots are STALE or EXPIRED (>7 days), skip Tier 1 and emit warning instead of silent failure
- [ ] Tier 2 follows: Piotroski scoring, PEG, FCF yield all use live data when available
- [ ] `/api/screening/run` endpoint respects `USE_MOCK_DATA` env var
- [ ] End-to-end test: run full 5-tier screening against a small live universe (5-10 tickers), verify funnel produces expected shape
- [ ] Smoke test in paper mode: TRADING_MODE=paper, USE_MOCK_DATA=false, full screening run completes without errors

## Context & Notes
- Bloomberg errors are stored as typed codes (N/A_INVALID_FIELD, VALUE_ERROR) — screening should treat these as "missing data, skip ticker" not "pass with 0"
- `services/freshness.py` already returns DataFreshness enum — reuse it
- Finnhub rate limit: 60 calls/min free tier. Tier 1 against full Russell 3000 would exceed. Start with pilot 10 tickers.
- Blocked by: SSS-T001 for quant scores, but Tier 1 can go live before quant (market cap filter is just a column read)

## Implementation Plan
1. Toggle USE_MOCK_DATA=false in a dev branch, run screening, catalog every failure
2. Fix each failure with data_source_chain fallback
3. Add freshness gating
4. Add integration test with fixture `company_snapshot` rows
5. Document the rate-limit considerations in an ADR

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
