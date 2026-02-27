-- Migration 021: Backtest runs table
-- Week 10: Backtesting service persistence

CREATE TABLE IF NOT EXISTS backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    equity_curve JSONB NOT NULL DEFAULT '[]'::jsonb,
    trades JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_ticker ON backtest_runs(ticker);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy ON backtest_runs(strategy);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);

ALTER TABLE backtest_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to backtest_runs" ON backtest_runs FOR SELECT USING (true);

COMMENT ON TABLE backtest_runs IS 'Historical backtest results with metrics, equity curves, and trade logs';
