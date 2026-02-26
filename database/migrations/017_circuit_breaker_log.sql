-- 017_circuit_breaker_log.sql
-- Circuit breaker event log for regime detection.

CREATE TABLE circuit_breaker_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  spy_5day_return NUMERIC(8,6),
  actions JSONB DEFAULT '[]',
  resolved_at TIMESTAMPTZ,
  resolved_by TEXT
);

CREATE INDEX idx_circuit_breaker_triggered ON circuit_breaker_log(triggered_at DESC);
