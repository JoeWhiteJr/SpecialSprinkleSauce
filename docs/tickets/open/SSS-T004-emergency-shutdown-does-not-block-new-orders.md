---
id: SSS-T004
title: Emergency shutdown does not block new orders
status: open
priority: critical
type: security
owner: joe
created: 2026-07-09
updated: 2026-07-09
related-pr:
related-tickets:
---

# Emergency shutdown does not block new orders

## Problem
`ShutdownManager.emergency_shutdown()` (`backend/app/services/emergency/shutdown_manager.py:40-88`) sets `_shutdown_active = True` and records `"Halted new order submissions"` in `actions_taken`, but nothing enforces it. `POST /api/execution/order` (`backend/app/routers/execution.py:61-135`) never consults shutdown state — a repo-wide grep for callers of `ShutdownManager.is_shutdown_active()` (`shutdown_manager.py:187-193`) returns only the definition. `execution.py` doesn't even import a `ShutdownManager` instance; `emergency.py:20` holds its own module-level singleton (`_manager = ShutdownManager()`), so after a declared halt, orders still flow straight through pre-trade validation → risk checks → `AlpacaClient.submit_order()`. Compounding it, shutdown state is a plain in-memory bool: it is lost on process restart and is independent per uvicorn worker under multi-worker deployment. The audit log claims an action ("Halted new order submissions") the system does not actually take — dangerous for an incident responder who trusts it.

## Acceptance Criteria
- [ ] `submit_order` (and the rebalancing/pipeline execution paths) call `ShutdownManager.is_shutdown_active()` before validation and return `503 TRADING_HALTED` when shutdown is active
- [ ] Shutdown state is fail-closed: default/unknown state is treated as NOT safe to trade unless explicitly confirmed active=false
- [ ] Shutdown state is moved to a shared persistent store (Supabase table or file flag) so it survives process restart and is consistent across multiple uvicorn workers
- [ ] `"Halted new order submissions"` is removed from `actions_taken` until the enforcement above is real
- [ ] Regression test: trigger shutdown → submit order → assert rejected with `TRADING_HALTED`
- [ ] Regression test: restart the process with shutdown previously active → submit order → assert still rejected

## Context & Notes
Source: `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce.md` (Finding 1, CRITICAL) and `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce_opus.md` ("1. Emergency shutdown never blocks new orders — CONFIRMED"). Opus reconciliation: confirmed verbatim against current code — `execution.py:61-135` contains no shutdown check at all, and the two independent in-memory `ShutdownManager` singletons make the gap worse than a simple missing-check bug. Opus flags this as the clearest, control-is-100%-absent finding in the repo, and notes that with the current placeholder Alpaca keys orders are simulated — but wiring real paper/live keys would let every post-halt order reach Alpaca unimpeded. Reopens GitHub issue #60 in spirit (audit log has no persistent sink either — see SSS ticket board for that adjacent gap, not scoped to this ticket).

## Implementation Plan
1. Add a dependency/guard (e.g. `require_not_shutdown`) that calls `ShutdownManager.is_shutdown_active()` and raises `HTTPException(503, "TRADING_HALTED")`
2. Apply the guard to `POST /api/execution/order` and any other order-submission/rebalancing-execution routes
3. Replace the in-memory `_shutdown_active` bool with a persisted store (new Supabase table `system_state` or a file-based flag read/written by all workers)
4. Consolidate the two independent `ShutdownManager` instances (`emergency.py` and wherever `execution.py` would need one) into a single source of truth
5. Remove the false "Halted new order submissions" claim from `actions_taken` until enforced, or make it true immediately (do both in the same change)
6. Add regression tests: order-rejected-during-shutdown, and shutdown-state-survives-restart

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
