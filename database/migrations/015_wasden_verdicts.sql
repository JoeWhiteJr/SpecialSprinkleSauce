-- 015_wasden_verdicts.sql
-- Stores Wasden Watch RAG pipeline verdicts for audit trail and analysis
-- Each row is one verdict run: ticker + APPROVE/NEUTRAL/VETO + reasoning

CREATE TABLE wasden_verdicts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ticker TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('APPROVE', 'NEUTRAL', 'VETO')),
  confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  reasoning TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('direct_coverage', 'framework_application', 'fallback')),
  model_used TEXT NOT NULL,
  passages_retrieved INT NOT NULL DEFAULT 0,
  generated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_wasden_verdicts_ticker ON wasden_verdicts(ticker);
CREATE INDEX idx_wasden_verdicts_generated ON wasden_verdicts(generated_at DESC);
CREATE INDEX idx_wasden_verdicts_verdict ON wasden_verdicts(verdict);
