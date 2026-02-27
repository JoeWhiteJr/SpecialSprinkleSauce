-- 005_jury_votes.sql
-- Individual jury agent votes for pipeline runs that trigger jury deliberation
-- Each agent (1-10) casts a vote with reasoning and confidence

CREATE TABLE jury_votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  pipeline_run_id UUID NOT NULL,
  ticker TEXT NOT NULL,
  agent_id INT NOT NULL CHECK (agent_id BETWEEN 1 AND 10),
  agent_perspective TEXT NOT NULL,
  vote TEXT CHECK (vote IN ('BUY', 'SELL', 'HOLD')) NOT NULL,
  reasoning TEXT NOT NULL,
  confidence FLOAT
);

CREATE INDEX idx_jury_pipeline ON jury_votes(pipeline_run_id);

COMMENT ON TABLE jury_votes IS 'Individual agent votes from 10-agent jury sessions';
