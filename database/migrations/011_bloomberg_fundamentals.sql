-- 011_bloomberg_fundamentals.sql
-- Fundamental data pulled from Bloomberg terminal
-- Unique per ticker+date, includes freshness grading and error tracking

CREATE TABLE bloomberg_fundamentals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  pull_date DATE NOT NULL,
  price FLOAT,
  market_cap FLOAT,
  trailing_pe FLOAT,
  forward_pe FLOAT,
  eps FLOAT,
  peg_ratio FLOAT,
  fcf FLOAT,
  fcf_yield FLOAT,
  ebitda_margin FLOAT,
  roe FLOAT,
  roc FLOAT,
  gross_margin FLOAT,
  operating_margin FLOAT,
  net_margin FLOAT,
  current_ratio FLOAT,
  quick_ratio FLOAT,
  debt_to_equity FLOAT,
  revenue_growth FLOAT,
  ebitda_interest_coverage FLOAT,
  ccc FLOAT,
  short_interest FLOAT,
  freshness_grade TEXT CHECK (freshness_grade IN ('FRESH', 'RECENT', 'STALE', 'EXPIRED')) DEFAULT 'FRESH',
  is_adr BOOLEAN DEFAULT FALSE,
  is_error BOOLEAN DEFAULT FALSE,
  error_fields JSONB,
  UNIQUE(ticker, pull_date)
);

CREATE INDEX idx_bloomberg_ticker ON bloomberg_fundamentals(ticker);
CREATE INDEX idx_bloomberg_date ON bloomberg_fundamentals(pull_date DESC);

COMMENT ON TABLE bloomberg_fundamentals IS 'Bloomberg terminal fundamental data snapshots per ticker';
