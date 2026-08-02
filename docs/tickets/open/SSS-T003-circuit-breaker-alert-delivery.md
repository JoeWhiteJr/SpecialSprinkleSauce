---
id: SSS-T003
title: Add circuit-breaker and consecutive-loss alert delivery
status: open
priority: medium
type: feature
owner: joe
created: 2026-04-10
updated: 2026-04-10
related-pr:
related-tickets:
---

# Add circuit-breaker and consecutive-loss alert delivery

## Problem
The risk engine detects circuit-breaker conditions (`services/risk/circuit_breaker.py`: SPY -5% over 5 days) and consecutive-loss conditions (`services/risk/consecutive_loss.py`: 7 consecutive losses → pause + alert), but the notifications router has no configured transport. If a circuit breaker fires when nobody's watching the dashboard, the system halts trading but Joe never finds out.

This is a critical safety gap for paper-trade readiness and a hard blocker for live mode.

## Acceptance Criteria
- [ ] Notifications router supports at least one real transport (email via SMTP, SMS via Twilio, or webhook)
- [ ] Circuit-breaker trip → notification sent within 60 seconds
- [ ] Consecutive-loss threshold hit → notification sent
- [ ] Alert includes: timestamp, trigger (which check failed), affected positions/universe, current state (paused/cut/halted), link to emergency endpoint
- [ ] `/api/emergency/status` shows last N alerts with delivery status
- [ ] Failed delivery retries 3x with exponential backoff, then logs to audit.py and continues
- [ ] Test: unit test that trips each condition and verifies the notification payload
- [ ] Env var stub: `ALERT_EMAIL` or `ALERT_WEBHOOK_URL` — app boots cleanly if unset (warns but doesn't halt)

## Context & Notes
- Audit logging (`audit.py`) already captures these events internally — we just need to add external delivery
- Circuit breaker constants are in `risk/constants.py` (PROTECTED — don't modify trigger thresholds without Jared + Joe approval)
- Notification content should be terse: a trading-halt alert at 3am shouldn't require reading 5 paragraphs to understand the action needed
- Consider: rate-limit on alert sending so a flapping condition doesn't spam

## Implementation Plan
1. Pick the simplest transport for v1 (SMTP email is already used in other Joe projects, dependency exists)
2. Build `services/notifications/email_transport.py` with retry + backoff
3. Wire circuit_breaker trip handler → notifications router
4. Wire consecutive_loss trigger → notifications router
5. Add failure mode test
6. Update `/api/emergency/status` to surface alert log

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
