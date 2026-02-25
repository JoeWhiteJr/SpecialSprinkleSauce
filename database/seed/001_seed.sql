-- 001_seed.sql
-- Seed data for Wasden Watch trading dashboard
-- Pilot watchlist, Bloomberg fundamentals snapshot, and system settings

-- ============================================================
-- 1. WATCHLIST - 10 pilot tickers
-- ============================================================

INSERT INTO watchlist (ticker, company_name, sector, is_pilot, is_adr) VALUES
  ('NVDA', 'NVIDIA', 'Technology', TRUE, FALSE),
  ('PYPL', 'PayPal', 'Technology', TRUE, FALSE),
  ('NFLX', 'Netflix', 'Communication Services', TRUE, FALSE),
  ('TSM', 'TSMC', 'Technology', TRUE, TRUE),
  ('XOM', 'Exxon Mobil', 'Energy', TRUE, FALSE),
  ('AAPL', 'Apple', 'Technology', TRUE, FALSE),
  ('MSFT', 'Microsoft', 'Technology', TRUE, FALSE),
  ('AMZN', 'Amazon', 'Consumer Discretionary', TRUE, FALSE),
  ('TSLA', 'Tesla', 'Consumer Discretionary', TRUE, FALSE),
  ('AMD', 'AMD', 'Technology', TRUE, FALSE);

-- ============================================================
-- 2. BLOOMBERG FUNDAMENTALS - Feb 21 2026 snapshot
-- ============================================================

INSERT INTO bloomberg_fundamentals (
  ticker, pull_date, price, market_cap, trailing_pe, forward_pe, eps, peg_ratio,
  fcf, fcf_yield, ebitda_margin, roe, roc, gross_margin, operating_margin,
  net_margin, current_ratio, quick_ratio, debt_to_equity, revenue_growth,
  ebitda_interest_coverage, ccc, short_interest, freshness_grade, is_adr, is_error
) VALUES
  -- NVDA
  ('NVDA', '2026-02-21', 130.28, 3190000000000, 50.5, 28.3, 2.58, 0.95,
   60700000000, 0.019, 0.651, 1.15, 0.82, 0.749, 0.622,
   0.558, 4.17, 3.85, 0.17, 0.78,
   132.5, -28.0, 0.011, 'FRESH', FALSE, FALSE),

  -- PYPL
  ('PYPL', '2026-02-21', 72.50, 74500000000, 17.8, 13.9, 4.07, 1.10,
   5400000000, 0.072, 0.224, 0.225, 0.153, 0.408, 0.176,
   0.143, 1.29, 1.29, 0.52, 0.07,
   18.3, -12.0, 0.022, 'FRESH', FALSE, FALSE),

  -- NFLX
  ('NFLX', '2026-02-21', 1050.72, 452000000000, 52.1, 38.7, 20.17, 1.65,
   8200000000, 0.018, 0.283, 0.345, 0.204, 0.454, 0.267,
   0.220, 1.18, 1.18, 0.68, 0.16,
   22.1, -8.0, 0.015, 'FRESH', FALSE, FALSE),

  -- TSM
  ('TSM', '2026-02-21', 203.50, 1053000000000, 28.4, 21.5, 7.17, 0.85,
   33500000000, 0.032, 0.542, 0.303, 0.225, 0.578, 0.475,
   0.398, 2.01, 1.78, 0.24, 0.33,
   45.2, 52.0, 0.008, 'FRESH', TRUE, FALSE),

  -- XOM
  ('XOM', '2026-02-21', 108.25, 464000000000, 14.2, 13.1, 7.62, 2.84,
   36100000000, 0.078, 0.168, 0.177, 0.108, 0.333, 0.135,
   0.099, 1.36, 1.02, 0.21, -0.05,
   25.8, 72.0, 0.009, 'FRESH', FALSE, FALSE),

  -- AAPL
  ('AAPL', '2026-02-21', 245.55, 3720000000000, 33.6, 30.1, 7.31, 1.88,
   110300000000, 0.030, 0.358, 1.47, 0.68, 0.467, 0.335,
   0.267, 0.95, 0.82, 1.87, 0.05,
   47.5, -52.0, 0.007, 'FRESH', FALSE, FALSE),

  -- MSFT
  ('MSFT', '2026-02-21', 411.22, 3058000000000, 34.2, 29.8, 12.02, 1.95,
   74200000000, 0.024, 0.498, 0.368, 0.262, 0.695, 0.453,
   0.358, 1.27, 1.22, 0.29, 0.16,
   52.3, -38.0, 0.006, 'FRESH', FALSE, FALSE),

  -- AMZN
  ('AMZN', '2026-02-21', 228.68, 2410000000000, 40.1, 30.5, 5.70, 1.32,
   52800000000, 0.022, 0.117, 0.228, 0.128, 0.488, 0.107,
   0.085, 1.06, 0.86, 0.55, 0.11,
   28.7, -22.0, 0.008, 'FRESH', FALSE, FALSE),

  -- TSLA
  ('TSLA', '2026-02-21', 362.72, 1165000000000, 172.5, 95.2, 2.10, 4.82,
   3600000000, 0.003, 0.129, 0.098, 0.072, 0.183, 0.078,
   0.071, 1.84, 1.45, 0.11, 0.02,
   8.5, -15.0, 0.028, 'FRESH', FALSE, FALSE),

  -- AMD
  ('AMD', '2026-02-21', 118.42, 192000000000, 42.3, 25.8, 2.80, 0.88,
   5300000000, 0.028, 0.222, 0.045, 0.038, 0.528, 0.218,
   0.068, 2.62, 2.18, 0.04, 0.48,
   35.1, 48.0, 0.024, 'FRESH', FALSE, FALSE);

-- ============================================================
-- 3. SYSTEM SETTINGS
-- ============================================================

INSERT INTO system_settings (key, value, description, category, editable, requires_approval) VALUES
  ('TRADING_MODE', 'paper', 'Current trading mode: paper or live', 'system', FALSE, FALSE),
  ('MAX_POSITION_PCT', '0.12', 'Maximum portfolio allocation per position (12%)', 'risk', FALSE, TRUE),
  ('RISK_PER_TRADE_PCT', '0.015', 'Maximum risk per trade as pct of portfolio (1.5%)', 'risk', FALSE, TRUE),
  ('MIN_CASH_RESERVE_PCT', '0.10', 'Minimum cash reserve as pct of portfolio (10%)', 'risk', FALSE, TRUE),
  ('MAX_CORRELATED_POSITIONS', '3', 'Maximum number of correlated positions allowed', 'risk', FALSE, TRUE),
  ('CORRELATION_THRESHOLD', '0.70', 'Correlation coefficient threshold for position grouping', 'risk', FALSE, TRUE),
  ('USE_MOCK_DATA', 'true', 'Whether to use mock data instead of live feeds', 'system', FALSE, FALSE);

-- ============================================================
-- 4. CONSECUTIVE LOSS TRACKER - Initialize single row
-- ============================================================

INSERT INTO consecutive_loss_tracker (current_streak, max_streak, net_pnl, status)
VALUES (0, 0, 0, 'active');
