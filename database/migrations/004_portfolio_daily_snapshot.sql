-- 004_portfolio_daily_snapshot.sql
-- Daily portfolio value snapshots for equity curve and benchmark comparison
-- One row per trading day

CREATE TABLE portfolio_daily_snapshot (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL UNIQUE,
  total_value FLOAT NOT NULL,
  daily_pnl FLOAT,
  cumulative_pnl FLOAT,
  spy_daily_return FLOAT,
  spy_cumulative_return FLOAT,
  cash_balance FLOAT,
  positions_count INT
);

CREATE INDEX idx_snapshot_date ON portfolio_daily_snapshot(date DESC);

COMMENT ON TABLE portfolio_daily_snapshot IS 'Daily portfolio value snapshots for P&L tracking';
