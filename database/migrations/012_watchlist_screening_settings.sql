-- 012_watchlist_screening_settings.sql
-- Watchlist: tickers under active monitoring
-- Screening runs: logs of each screening pipeline execution
-- System settings: key-value config for the trading system

CREATE TABLE watchlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL UNIQUE,
  company_name TEXT,
  sector TEXT,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  is_pilot BOOLEAN DEFAULT TRUE,
  is_adr BOOLEAN DEFAULT FALSE
);

CREATE TABLE screening_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date TIMESTAMPTZ DEFAULT NOW(),
  tier1_count INT DEFAULT 500,
  tier2_count INT,
  tier3_count INT,
  tier4_count INT,
  tier5_count INT,
  final_recommendations INT,
  duration_seconds FLOAT,
  notes TEXT
);

CREATE INDEX idx_screening_date ON screening_runs(run_date DESC);

CREATE TABLE system_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  description TEXT,
  category TEXT DEFAULT 'system',
  editable BOOLEAN DEFAULT FALSE,
  requires_approval BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT
);
