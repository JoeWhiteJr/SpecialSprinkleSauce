-- 007_veto_overrides.sql
-- Tracks when a human overrides a Wasden VETO
-- Includes outcome tracking to measure override quality over time

CREATE TABLE veto_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ticker TEXT NOT NULL,
  original_verdict TEXT DEFAULT 'VETO',
  override_reason TEXT NOT NULL,
  overridden_by TEXT NOT NULL,
  pipeline_run_id UUID,
  status TEXT CHECK (status IN ('pending', 'approved', 'rejected', 'completed')) DEFAULT 'pending',
  outcome_tracked BOOLEAN DEFAULT FALSE,
  outcome_note TEXT,
  outcome_pnl FLOAT
);

CREATE INDEX idx_overrides_status ON veto_overrides(status);

COMMENT ON TABLE veto_overrides IS 'Human overrides of Wasden VETO verdicts with outcome tracking';
