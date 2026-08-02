---
id: SSS-T005
title: Enable server-side auth on all state-changing endpoints
status: open
priority: high
type: security
owner: joe
created: 2026-07-09
updated: 2026-07-09
related-pr:
related-tickets:
---

# Enable server-side auth on all state-changing endpoints

## Problem
`require_api_key` (`backend/app/auth.py:16-18`) returns `None` (auth disabled) whenever `settings.api_key` is empty. The root `/home/joe/Special-Sprinkle-Sauce/.env` has no `API_KEY=` entry and `render.yaml` declares no `API_KEY` env var either — so both locally and as deployed to Render, every state-changing endpoint (order submission, emergency shutdown/resume, cancel-all-orders, settings mutation, training approvals) is unauthenticated, even though `main.py:79` correctly wires `dependencies=[Depends(require_api_key)]` app-wide. Separately, the intended auth mechanism is broken by design: the frontend reads the key via `NEXT_PUBLIC_API_KEY` (`frontend/src/lib/api.ts:2-9`), and Next.js inlines every `NEXT_PUBLIC_*` value into the public client JS bundle at build time — so even once a key is set, it ships to every browser and is readable from view-source, making it a discovery mechanism rather than a secret. This reopens GitHub issue #58 (API key exposed in frontend bundle, closed 2026-06-25 without the fix landing) and issue #59 (emergency shutdown/resume identity self-asserted, also closed-but-unfixed).

## Acceptance Criteria
- [ ] Real server-side auth middleware is enforced in both dev and prod (a non-empty `API_KEY` is set in `.env` and in Render's env vars, and `require_api_key` fails closed rather than defaulting to open)
- [ ] The API key (or session token) is never shipped to the browser bundle — replace `NEXT_PUBLIC_API_KEY` with a Next.js server-side proxy (route handlers hold the key server-only) or Supabase Auth sessions
- [ ] Emergency shutdown, resume, and cancel-all-orders endpoints require authentication and derive identity from the authenticated principal, not a free-text body field
- [ ] `api_key != settings.api_key` string comparison is replaced with `secrets.compare_digest` (timing-safe)
- [ ] Regression test: unauthenticated request to `/api/execution/order`, `/api/emergency/shutdown`, `/api/emergency/resume`, `/api/emergency/cancel-all-orders` returns 401/403
- [ ] Issues #58 and #59 are reopened on GitHub and linked to this ticket, then closed only once the fix lands in code

## Context & Notes
Source: `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce.md` (Findings 3 and 4, HIGH) and `/home/joe/AUDIT_2026-07-09/special-sprinkle-sauce_opus.md` ("3. API auth entirely disabled — CONFIRMED", "5. Emergency shutdown/resume identity self-asserted — CONFIRMED"). Opus confirms auth *is* wired globally (`main.py:79`) but is neutered by the empty-key fallback in `auth.py:15-16`, and calls this "the linchpin that makes #1 [shutdown bypass], #2 [dual-approval bypass], and #5 [resume self-assertion] remotely exploitable" by any anonymous internet caller against the public Render deployment. `emergency.py:63-73` `/cancel-all-orders` takes no identity field at all, rate-limited only to 10/min.

## Implementation Plan
1. Generate a strong `API_KEY`, set it in `.env` (mode 600) and in Render's dashboard env vars for both environments
2. Make `require_api_key` fail closed: reject requests when `settings.api_key` is unset instead of allowing all traffic
3. Add a Next.js server-side route-handler proxy so the API key never reaches `NEXT_PUBLIC_*` / the client bundle; update `frontend/src/lib/api.ts` to call the proxy instead of the backend directly
4. Derive `initiated_by`/`approved_by` on shutdown/resume from the authenticated identity, not request-body fields
5. Swap the API key comparison to `secrets.compare_digest`
6. Add auth-required regression tests for all state-changing routes; reopen and then re-close issues #58/#59 referencing the merged fix

## Retrospective
_Fill in when moving to done/: what went well, what didn't, what we'd do differently._
