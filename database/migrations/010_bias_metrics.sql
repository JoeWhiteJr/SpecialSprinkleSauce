-- 010_bias_metrics.sql
-- Weekly aggregated bias metrics for monitoring Wasden model behavior
-- Tracks approval rates, sector distribution, and override frequency

CREATE TABLE bias_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  approve_count INT DEFAULT 0,
  neutral_count INT DEFAULT 0,
  veto_count INT DEFAULT 0,
  total_recommendations INT DEFAULT 0,
  sector_distribution JSONB,
  model_agreement_rate FLOAT,
  avg_confidence FLOAT,
  override_count INT DEFAULT 0
);

CREATE INDEX idx_bias_week ON bias_metrics(week_start DESC);

COMMENT ON TABLE bias_metrics IS 'Weekly bias analysis metrics for model and verdict distribution';
