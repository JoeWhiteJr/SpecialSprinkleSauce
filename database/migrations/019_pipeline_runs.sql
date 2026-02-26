-- Migration 019: Pipeline runs table for decision pipeline audit trail
-- Week 7: LangGraph Decision Pipeline

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'vetoed')),

    -- Pipeline stage results (JSONB for flexibility)
    quant_scores JSONB DEFAULT '{}'::jsonb,
    wasden_verdict JSONB DEFAULT '{}'::jsonb,
    debate_result JSONB DEFAULT '{}'::jsonb,
    jury_result JSONB DEFAULT '{}'::jsonb,
    risk_check JSONB DEFAULT '{}'::jsonb,
    pre_trade_validation JSONB DEFAULT '{}'::jsonb,
    final_decision JSONB DEFAULT '{}'::jsonb,
    node_journal JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_ticker ON pipeline_runs(ticker);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);

COMMENT ON TABLE pipeline_runs IS 'Full audit trail for each decision pipeline execution';
COMMENT ON COLUMN pipeline_runs.pre_trade_validation IS 'SEPARATE from risk_check — never merge';
