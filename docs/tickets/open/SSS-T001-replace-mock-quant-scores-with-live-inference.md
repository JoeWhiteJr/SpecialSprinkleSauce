---
id: SSS-T001
title: Replace mock quant scores with live model inference
status: open
priority: high
type: feature
owner: joe
created: 2026-04-10
updated: 2026-04-10
related-pr:
related-tickets:
---

# Replace mock quant scores with live model inference

## Problem
`src/intelligence/quant_models/mock_scores.py` is currently the single source of truth for quant scores across 10 pilot tickers. The decision pipeline, screening engine (Tier 3), and risk engine all consume these mock scores. This was acceptable for end-to-end wiring but blocks paper-trade readiness — we can't validate the live decision pipeline without real model outputs.

The 4-model ensemble is built (XGBoost, ElasticNet, ARIMA, Sentiment) and the `QuantModelOrchestrator.score_ticker()` exists, but nothing calls it end-to-end with live price data.

## Acceptance Criteria
- [ ] `QuantModelOrchestrator.score_ticker(ticker)` runs the 4 models against real OHLCV from the `price_history` table (migration 014) instead of returning mock data
- [ ] Feature engineer computes SMA/RSI/MACD/Bollinger from real price history, not fixtures
- [ ] Sentiment model pulls from live Finnhub + NewsAPI (env vars already configured)
- [ ] Composite score = mean of 4 live scores; std_dev flags high disagreement (>0.5)
- [ ] Falls back to mock scores ONLY when `USE_MOCK_DATA=true`
- [ ] New integration test: `test_quant_pipeline_live.py` runs end-to-end for 1 ticker with fixture price data (not mocks)
- [ ] Existing 154 backend tests still pass
- [ ] Pipeline runner UI shows "live" or "mock" badge on each quant score

## Context & Notes
- Mock scores live in `mock_scores.py` — the TSLA entry has `xgb=0.85, enet=0.35` specifically to exercise the high-disagreement path. Keep that as a fixture.
- Screening Tier 3 already calls `score_ticker()` — just needs USE_MOCK_DATA fallback logic
- Risk engine's model disagreement check (HIGH_MODEL_DISAGREEMENT_THRESHOLD = 0.50) reads from the orchestrator, not mock directly — should work unchanged
- Bloomberg data pipeline (PR #4) already populates `price_history`
- ADR worth writing: why we keep the mock path as a fallback vs removing entirely

## Implementation Plan
1. Audit all callers of `mock_scores.py` — map the surface area
2. Add `USE_MOCK_DATA` check inside `QuantModelOrchestrator.score_ticker()`
3. Wire feature_engineer to read from `price_history` table (already has the OHLCV)
4. Run sentiment model against live Finnhub/NewsAPI
5. Integration test with fixture
6. Manual validation: kick off pipeline run for NVDA and verify live scores differ from mock

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
