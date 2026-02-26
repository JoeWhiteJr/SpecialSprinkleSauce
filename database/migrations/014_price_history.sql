-- 014_price_history.sql
-- OHLCV price history for historical datasets
-- Supports Dow Jones (1928-2009) and Emery S&P 500 (10yr) data

CREATE TYPE dataset_source_type AS ENUM ('dow_jones', 'emery_sp500');

CREATE TABLE price_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  date DATE NOT NULL,
  open FLOAT,
  high FLOAT,
  low FLOAT,
  close FLOAT,
  volume BIGINT,
  adjusted_close FLOAT,
  dataset_source dataset_source_type NOT NULL,
  survivorship_bias_audited BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Unique constraint: one row per ticker+date+source
ALTER TABLE price_history ADD CONSTRAINT uq_price_history_ticker_date_source
  UNIQUE (ticker, date, dataset_source);

-- Performance index for time-series queries
CREATE INDEX idx_price_history_ticker_date ON price_history (ticker, date DESC);
CREATE INDEX idx_price_history_source ON price_history (dataset_source);
