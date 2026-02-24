-- 002_trade_recommendations.sql
-- Pending trade recommendations awaiting human review
-- References decision_journal for full pipeline context

CREATE TABLE trade_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ticker TEXT NOT NULL,
  direction TEXT CHECK (direction IN ('BUY', 'SELL')),
  confidence FLOAT,
  reasoning TEXT,
  quant_composite FLOAT,
  wasden_verdict TEXT,
  pipeline_run_id UUID REFERENCES decision_journal(id),
  status TEXT CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  review_note TEXT
);

CREATE INDEX idx_recommendations_status ON trade_recommendations(status);
CREATE INDEX idx_recommendations_created ON trade_recommendations(created_at DESC);
