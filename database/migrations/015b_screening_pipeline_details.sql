-- 015_screening_pipeline_details.sql
-- Per-ticker tier results for screening pipeline + additional columns on screening_runs.

-- Tier-level results for each ticker in each screening run
CREATE TABLE screening_tier_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES screening_runs(id) ON DELETE CASCADE,
  tier INT NOT NULL CHECK (tier BETWEEN 1 AND 5),
  ticker TEXT NOT NULL,
  passed BOOLEAN NOT NULL DEFAULT FALSE,
  fail_reasons TEXT[] DEFAULT '{}',
  metrics JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_screening_tier_run ON screening_tier_results(run_id);
CREATE INDEX idx_screening_tier_ticker ON screening_tier_results(ticker);

-- Add detail columns to screening_runs
ALTER TABLE screening_runs
  ADD COLUMN IF NOT EXISTS final_candidates TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS model_used TEXT DEFAULT 'claude-haiku',
  ADD COLUMN IF NOT EXISTS data_freshness_summary JSONB DEFAULT '{}';

COMMENT ON TABLE screening_tier_results IS 'Per-ticker tier pass/fail results for each screening pipeline run';
