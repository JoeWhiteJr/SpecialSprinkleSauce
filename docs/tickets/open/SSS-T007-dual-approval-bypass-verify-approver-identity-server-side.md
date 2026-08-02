---
id: SSS-T007
title: Dual-approval bypass — verify approver identity server-side (reopen #57)
status: open
priority: high
type: security
owner: joe
created: 2026-07-09
updated: 2026-07-09
related-pr:
related-tickets:
---

# Dual-approval bypass — verify approver identity server-side (reopen #57)

## Problem
`approve_proposal` (`backend/app/routers/training.py:302-338`) takes `user_name` from the request body and stamps `joe_approved_at`/`jared_approved_at` accordingly. The only guard is `Field(pattern="^(joe|jared)$")` (`training.py:67`) — a *value* check, not an *identity* check. One caller can POST `{"user_name": "joe"}` then `{"user_name": "jared"}` and both approval timestamps get set, satisfying `AutoTuner.check_approval` (`auto_tuner.py:163-181`) with no verification that two distinct real people approved. `reject_proposal` and `rollback_proposal` require no identity at all. This reopens GitHub issue #57 (closed 2026-06-25 without the fix landing).

## Acceptance Criteria
- [ ] Approver identity is derived from the authenticated principal (per-person credential — distinct API key or Supabase Auth JWT for Joe and Jared), never from the request body
- [ ] A single authenticated session cannot record both the `joe_approved_at` and `jared_approved_at` timestamps on the same proposal
- [ ] Regression test: same authenticated identity attempts to approve twice under both names → second approval is rejected
- [ ] `reject_proposal` and `rollback_proposal` also require authenticated identity (currently require none)
- [ ] Issue #57 is reopened on GitHub and linked to this ticket, then closed only once the fix lands in code

## Context & Notes
Source: `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce.md` (Finding 2, CRITICAL) and `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce_opus.md` ("2. Dual-approval bypass (ticket #57) — CONFIRMED (vuln real); blast-radius OVERSTATED"). **Opus correction to the original claim:** the auth-bypass vulnerability itself is real and confirmed, but `apply_proposal` (`auto_tuner.py:183-202`) only writes an in-memory history entry — the live risk constants in `backend/app/services/risk/constants.py` are Python module literals and are **not** read from proposals anywhere. So today's exploit corrupts the training/approval audit trail and any future consumer of "applied" proposals, but does **not** currently mutate the running risk engine. The severity of the *auth flaw* stays high (identity spoofing on a security control); the *impact* is lower than originally stated — audit-trail integrity, not live risk-limit mutation. This depends on SSS-T005 landing real server-side auth first (single-caller self-approval is only exploitable because auth is currently off entirely).

## Implementation Plan
1. Land SSS-T005 (server-side auth with per-person identity) as a prerequisite
2. Change `approve_proposal` to read the approver identity from the authenticated request context, ignoring any `user_name` in the body
3. Track which authenticated identity has already approved a given proposal; reject a second approval attempt from the same identity
4. Add authentication requirements to `reject_proposal` and `rollback_proposal`
5. Add regression test: single identity attempts dual self-approval → rejected
6. Reopen issue #57, link this ticket, close once merged

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
