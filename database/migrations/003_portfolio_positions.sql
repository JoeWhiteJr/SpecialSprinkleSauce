-- 003_portfolio_positions.sql
-- Tracks all open and closed portfolio positions
-- Used for P&L tracking and position management

CREATE TABLE portfolio_positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  direction TEXT CHECK (direction IN ('long', 'short')),
  entry_price FLOAT NOT NULL,
  entry_date TIMESTAMPTZ NOT NULL,
  current_price FLOAT,
  exit_price FLOAT,
  exit_date TIMESTAMPTZ,
  shares INT NOT NULL,
  status TEXT CHECK (status IN ('open', 'closed')) DEFAULT 'open',
  pnl FLOAT,
  pnl_pct FLOAT,
  pipeline_run_id UUID
);

CREATE INDEX idx_positions_status ON portfolio_positions(status);
CREATE INDEX idx_positions_ticker ON portfolio_positions(ticker);
