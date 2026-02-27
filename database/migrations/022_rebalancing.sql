-- Migration 022: Rebalancing tables
-- Week 10: Rebalancing service persistence

CREATE TABLE IF NOT EXISTS rebalance_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL UNIQUE,
    target_weight NUMERIC(5,2) NOT NULL CHECK (target_weight >= 0 AND target_weight <= 100),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rebalance_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'failed')),
    trades JSONB NOT NULL DEFAULT '[]'::jsonb,
    trade_count INTEGER NOT NULL DEFAULT 0,
    drift_summary TEXT,
    trading_mode TEXT NOT NULL DEFAULT 'paper',
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rebalance_targets_ticker ON rebalance_targets(ticker);
CREATE INDEX IF NOT EXISTS idx_rebalance_executions_status ON rebalance_executions(status);
CREATE INDEX IF NOT EXISTS idx_rebalance_executions_created_at ON rebalance_executions(created_at DESC);

ALTER TABLE rebalance_targets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to rebalance_targets" ON rebalance_targets FOR SELECT USING (true);

ALTER TABLE rebalance_executions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to rebalance_executions" ON rebalance_executions FOR SELECT USING (true);

COMMENT ON TABLE rebalance_targets IS 'Target portfolio weights per ticker for rebalancing';
COMMENT ON TABLE rebalance_executions IS 'History of rebalancing execution runs';
