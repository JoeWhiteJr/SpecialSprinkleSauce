---
id: SSS-T006
title: Populate RiskContext so risk checks actually bind
status: open
priority: high
type: security
owner: joe
created: 2026-07-09
updated: 2026-07-09
related-pr:
related-tickets:
---

# Populate RiskContext so risk checks actually bind

## Problem
`execution.py:110-116` builds `RiskContext` with only `ticker`, `proposed_position_pct`, `portfolio_value`, and `cash_balance` populated. Every other field defaults empty/zero per `risk_engine.py:40-55`: `existing_positions=[]`, `correlations={}`, `stress_correlations={}`, `sector=""`, `model_std_dev=0.0`. As a result, checks 3 (correlation), 4 (stress-correlation), 5 (sector-concentration), 6 (gap-risk), and 7 (model-disagreement) all pass trivially on every order — empty iterables and `sector==""` hit an early-return-pass at `risk_engine.py:148-153`. Only position-size and cash-reserve (checks 1-2) actually constrain trades. The documented "7 sequential risk checks" are effectively 2 in production, silently letting through concentrated or correlated positions the standards were designed to block.

## Acceptance Criteria
- [ ] `RiskContext` is populated from live Alpaca positions (`AlpacaClient.get_positions()`, already exists) and the model orchestrator's outputs before `run_risk_checks` is called
- [ ] `existing_positions`, `correlations`, `stress_correlations`, `sector`, and `model_std_dev` all carry real values on every order submission
- [ ] All 7 documented risk checks are exercised (not trivially passed) in a new test that asserts each check can independently reject an order given the right context
- [ ] Falls back to fail-closed (reject) rather than silently-pass when the context cannot be populated (e.g., Alpaca positions API unreachable)

## Context & Notes
Source: `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce_opus.md`, "New findings Fable missed — A. Risk engine runs with an empty context on every live order — 5 of 7 checks are no-ops." This is a new finding from the Opus deep re-audit not present in the original Fable pass (`special-sprinkle-sauce.md`); Opus rates it HIGH and independent of the auth issues (SSS-T005) — even with auth fixed, the risk engine would still silently under-check every order.

## Implementation Plan
1. Audit `RiskContext` construction in `execution.py:110-116` and enumerate every field the 7 checks read
2. Wire `AlpacaClient.get_positions()` into `existing_positions`
3. Compute `correlations`/`stress_correlations` from the model orchestrator or a dedicated correlation service (check what's already available from SSS-T001's quant pipeline)
4. Populate `sector` from ticker metadata and `model_std_dev` from the composite score's disagreement metric
5. Add a fail-closed path: if any required context field can't be computed, reject the order rather than defaulting to a pass-through value
6. Write a test that constructs a fully-populated `RiskContext` and asserts each of the 7 checks can independently fail an order (one test per check, or a parametrized test)

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
