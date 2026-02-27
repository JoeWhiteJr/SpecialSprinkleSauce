-- 006_debate_transcripts.sql
-- Full bull vs bear debate transcripts per round
-- Captures arguments, confidence shifts, and round outcomes

CREATE TABLE debate_transcripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  pipeline_run_id UUID NOT NULL,
  ticker TEXT NOT NULL,
  round_number INT NOT NULL,
  bull_argument TEXT NOT NULL,
  bull_confidence FLOAT,
  bear_argument TEXT NOT NULL,
  bear_confidence FLOAT,
  outcome TEXT CHECK (outcome IN ('agreement', 'disagreement'))
);

CREATE INDEX idx_debate_pipeline ON debate_transcripts(pipeline_run_id);
CREATE INDEX idx_debate_ticker ON debate_transcripts(ticker);

COMMENT ON TABLE debate_transcripts IS 'Bull vs bear debate transcripts with round-by-round arguments';
