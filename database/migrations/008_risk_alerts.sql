-- 008_risk_alerts.sql
-- System-generated risk alerts with severity levels
-- Supports acknowledgment tracking for audit trail

CREATE TABLE risk_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  alert_type TEXT NOT NULL,
  severity TEXT CHECK (severity IN ('info', 'warning', 'critical')) NOT NULL,
  message TEXT NOT NULL,
  ticker TEXT,
  details JSONB,
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_by TEXT,
  acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_severity ON risk_alerts(severity);
CREATE INDEX idx_alerts_acknowledged ON risk_alerts(acknowledged);
