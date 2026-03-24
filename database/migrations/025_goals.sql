-- 025_goals.sql — Goal runs and goal trades for task-based trading
-- Tracks goal orchestrator runs and individual trades within each goal.

CREATE TABLE IF NOT EXISTS goal_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capital NUMERIC NOT NULL,
    target_return_pct NUMERIC NOT NULL,
    timeframe_days INTEGER NOT NULL,
    max_loss_pct NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    candidates TEXT[] DEFAULT '{}',
    portfolio_allocations JSONB DEFAULT '[]',
    trade_plan JSONB DEFAULT '[]',
    cumulative_pnl NUMERIC DEFAULT 0,
    cumulative_pnl_pct NUMERIC DEFAULT 0,
    remaining_target_pct NUMERIC DEFAULT 0,
    portfolio_debate_outcome TEXT,
    portfolio_bull_case TEXT,
    portfolio_bear_case TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE goal_runs IS 'Goal orchestrator runs — task-based trading with defined financial targets';

CREATE TABLE IF NOT EXISTS goal_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES goal_runs(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    action TEXT NOT NULL,
    shares INTEGER NOT NULL,
    entry_price_est NUMERIC,
    entry_price_actual NUMERIC,
    exit_price NUMERIC,
    stop_loss_price NUMERIC,
    target_exit_price NUMERIC,
    contribution_target_pct NUMERIC,
    position_dollar NUMERIC,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    status TEXT NOT NULL DEFAULT 'planned',
    day_target INTEGER DEFAULT 1,
    pipeline_run_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    executed_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

COMMENT ON TABLE goal_trades IS 'Individual trades within a goal orchestrator run';

CREATE INDEX IF NOT EXISTS idx_goal_trades_goal_id ON goal_trades(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_runs_status ON goal_runs(status);
CREATE INDEX IF NOT EXISTS idx_goal_runs_created_at ON goal_runs(created_at DESC);
