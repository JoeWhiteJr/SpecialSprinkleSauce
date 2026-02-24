-- 009_consecutive_loss_tracker.sql
-- Tracks consecutive losing trades for circuit-breaker logic
-- Single-row table updated after each closed position

CREATE TABLE consecutive_loss_tracker (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  current_streak INT DEFAULT 0,
  max_streak INT DEFAULT 0,
  net_pnl FLOAT DEFAULT 0,
  status TEXT CHECK (status IN ('active', 'warning', 'halted')) DEFAULT 'active',
  last_loss_ticker TEXT,
  last_loss_date TIMESTAMPTZ,
  resumed_by TEXT,
  resumed_at TIMESTAMPTZ
);
