# Bloomberg Field Reference -- Wasden Watch

> Comprehensive reference for all Bloomberg BDP fields, error handling, and data pipeline behavior in the Wasden Watch trading system.
> Based on code in `backend/app/services/bloomberg_pipeline.py`, `data/bloomberg/SCHEMA.md`, `KNOWLEDGE_BASE_v2.md` Section 18-19, and `PROJECT_STANDARDS_v2.md` Section 5.
>
> Version: 2.0 | Last Updated: February 26, 2026

---

## 1. Field Code Reference

The system uses 25 Bloomberg BDP (Bloomberg Data Point) fields exported via the Bloomberg Excel Add-In. All fields are pulled as snapshot (current period) values from the **Values** sheet of the `JMWFM_Bloomberg_YYYY-MM-DD.xlsx` workbook.

### 1.1 Valuation Ratios

| # | Metric | Bloomberg Code | DB Column | Type | Description | System Usage |
|---|--------|---------------|-----------|------|-------------|-------------|
| 1 | Current Price | `PX_LAST` | `price` | Float | Last trade price | Baseline for all calculations; screening, position sizing |
| 2 | Market Cap | `CUR_MKT_CAP` | `market_cap` | Float | Market capitalization (shares x price) | Tier 1 screening filter (> $5B), FCF yield denominator |
| 3 | P/E Ratio (Trailing) | `PE_RATIO` | `trailing_pe` | Float | Trailing 12-month price-to-earnings | Valuation comparison; returns `#N/A Field Not Applicable` for ADRs (e.g., TSM) |
| 4 | P/E Ratio (Forward) | `BEST_PE_RATIO` | `forward_pe` | Float | Consensus forward P/E estimate | Primary PE for ADRs; PEG fallback numerator |
| 5 | EPS (Current) | `IS_EPS` | `eps` | Float | Current earnings per share | Piotroski signal 1 (ROA proxy), valuation |
| 6 | PEG Ratio | `PEG_RATIO` | `peg_ratio` | Float | Price/Earnings to Growth ratio | Tier 2 screening (< 2.0); below 1 = undervalued |

### 1.2 Cash Flow Ratios (Wasden's Favorites)

| # | Metric | Bloomberg Code | DB Column | Type | Description | System Usage |
|---|--------|---------------|-----------|------|-------------|-------------|
| 7 | Free Cash Flow | `CF_FREE_CASH_FLOW` | `fcf` | Float | Free cash flow (dollars) | Wasden's #1 metric; Piotroski signal 2; FCF-to-NI ratio |
| 8 | FCF Yield | `FREE_CASH_FLOW_YIELD` | `fcf_yield` | Float | FCF / Market Cap (stored as %) | Tier 2 screening (> 3%); Bucket 1 instrument signal |
| 9 | EBITDA Margin | `EBITDA_MARGIN` | `ebitda_margin` | Float | EBITDA as % of revenue | Profitability assessment; harder to manipulate than earnings |

### 1.3 Profitability Ratios

| # | Metric | Bloomberg Code | DB Column | Type | Description | System Usage |
|---|--------|---------------|-----------|------|-------------|-------------|
| 10 | ROE | `RETURN_COM_EQY` | `roe` | Float | Return on common equity | Profitability; should not exceed ROC |
| 11 | ROC | `RETURN_ON_CAP` | `roc` | Float | Return on capital | Should be > ROE; returns `#N/A N/A` for AAPL |
| 12 | Gross Margin | `GROSS_MARGIN` | `gross_margin` | Float | Gross margin % | Piotroski signal 8 (improving YoY); peer comparison |
| 13 | Operating Margin | `OPER_MARGIN` | `operating_margin` | Float | Operating margin % | Piotroski signal 4 (accrual quality proxy) |
| 14 | Net Margin | `PROF_MARGIN` | `net_margin` | Float | Net profit margin % | Bottom-line profitability |

### 1.4 Liquidity and Leverage

| # | Metric | Bloomberg Code | DB Column | Type | Description | System Usage |
|---|--------|---------------|-----------|------|-------------|-------------|
| 15 | Current Ratio | `CUR_RATIO` | `current_ratio` | Float | Current assets / current liabilities | Piotroski signal 6 (improving YoY); Sprinkle Sauce filter |
| 16 | Quick Ratio | `QUICK_RATIO` | `quick_ratio` | Float | (Current assets - inventory) / current liabilities | Stricter liquidity measure |
| 17 | Debt to Equity | `TOT_DEBT_TO_TOT_EQY` | `debt_to_equity` | Float | Total debt / total equity | Piotroski signal 5 (leverage decreasing); industry-relative |
| 18 | Interest Coverage | `INTEREST_COVERAGE_RATIO` | `ebitda_interest_coverage` | Float | EBITDA / interest expense | Sprinkle Sauce filter; solvency signal |

### 1.5 Growth and Efficiency

| # | Metric | Bloomberg Code | DB Column | Type | Description | System Usage |
|---|--------|---------------|-----------|------|-------------|-------------|
| 19 | Revenue Growth YoY | `SALES_GROWTH` | `revenue_growth` | Float | Year-over-year revenue growth % | Piotroski signal 9 (asset turnover proxy); Sprinkle Sauce |
| 20 | Cash Conversion Cycle | `CASH_CONVERSION_CYCLE` | `ccc` | Float | DIO + DSO - DPO (days) | Efficiency signal; negative = competitive advantage (AAPL at -72.4) |
| 21 | Short Interest | `SHORT_INT_RATIO` | `short_interest` | Float | Short interest ratio | Sentiment signal; contrarian indicator |

### 1.6 Fields Not in Standard BDP

These fields are referenced in the system but cannot be retrieved through standard Bloomberg BDP queries.

| # | Metric | Bloomberg Code | Status | Notes |
|---|--------|---------------|--------|-------|
| 22 | Piotroski F-Score | `PIOTROSKI_F_SCORE` | Returns `#N/A Invalid Field` | Requires custom EQS formula or manual calculation (see Section 5) |
| 23 | EPS Forward Estimate | `BEST_EPS` | Available in Excel | Present in Bloomberg export but not stored in `bloomberg_fundamentals` table |
| 24 | Long-term Growth Est | `BEST_EST_LONG_TERM_GROWTH` | Available in Excel | Used for PEG calculation fallback when `PEG_RATIO` returns `#VALUE!` |
| 25 | VWAP | `EQY_WEIGHTED_AVG_PX` | Not currently used | Referenced in project planning but not implemented in pipeline |

---

## 2. Known Error Codes

Bloomberg returns several error strings in cell values. The pipeline in `bloomberg_pipeline.py` classifies these into typed error codes using regex pattern matching. Errors are stored as structured data, never raw strings (per `PROJECT_STANDARDS_v2.md` Section 1).

### 2.1 Error Classification Table

| Bloomberg Error String | Typed Code | Regex Pattern | Meaning | Frequency |
|----------------------|-----------|---------------|---------|-----------|
| `#N/A Invalid Field` | `N/A_INVALID_FIELD` | `#N/A Invalid Field` | Field is not available for this security type via standard BDP | Common for Piotroski F-Score |
| `#N/A Field Not Applicable` | `N/A_NOT_APPLICABLE` | `#N/A Field Not Applicable` | Field exists but does not apply to this security (ADR, ETF, etc.) | Common for ADR trailing P/E |
| `#N/A N/A` | `N/A_NA` | `#N/A N/A` | Data is genuinely not available from Bloomberg for this ticker | Sporadic (AAPL ROC) |
| `#N/A` (generic) | `N/A_GENERIC` | `#N/A` | Catch-all for unclassified N/A variants | Rare |
| `#VALUE!` | `VALUE_ERROR` | `#VALUE!` | Calculation error (e.g., division by zero in PEG when growth rate is 0) | PEG for PYPL, NFLX, TSLA |
| `#NAME?` | `NAME_ERROR` | `#NAME\?` | Excel formula error occurring outside Bloomberg session | Fundamentals sheet only |
| (unparseable string) | `PARSE_ERROR` | N/A | Value could not be parsed as a float | Pipeline-generated, not Bloomberg |

### 2.2 Pattern Matching Order

The `classify_error()` function in `bloomberg_pipeline.py` checks patterns from most specific to least specific. This ordering is critical because `#N/A Invalid Field` would also match the generic `#N/A` pattern:

1. `#N/A Invalid Field` (most specific N/A variant)
2. `#N/A Field Not Applicable`
3. `#N/A N/A`
4. `#N/A` (generic catch-all)
5. `#VALUE!`
6. `#NAME?`

---

## 3. Error Handling Strategy

### 3.1 Pipeline Behavior by Error Type

| Error Code | Value Stored | `is_error` Flag | Downstream Behavior |
|-----------|-------------|----------------|-------------------|
| `N/A_INVALID_FIELD` | `NULL` | `true` | Field excluded from calculations; Piotroski computed manually |
| `N/A_NOT_APPLICABLE` | `NULL` | `true` | Fallback field used (e.g., `BEST_PE_RATIO` instead of `PE_RATIO` for ADRs) |
| `N/A_NA` | `NULL` | `true` | Stored as null; field skipped in downstream calculations |
| `N/A_GENERIC` | `NULL` | `true` | Treated same as `N/A_NA` |
| `VALUE_ERROR` | `NULL` | `true` | Manual calculation attempted (e.g., PEG via `BEST_PE_RATIO / BEST_EST_LONG_TERM_GROWTH`) |
| `NAME_ERROR` | `NULL` | `true` | Should never appear -- pipeline only reads Values sheet, not Fundamentals |
| `PARSE_ERROR` | `NULL` | `true` | Logged as warning; value excluded |

### 3.2 Per-Record Error Tracking

Each ticker row in the `bloomberg_fundamentals` table includes:

- **`is_error`** (boolean): `true` if any field in the row had an error
- **`error_fields`** (JSONB): Array of error objects, each with `field_name`, `raw_value`, and `error_type`

Example `error_fields` value:
```json
[
  {"field_name": "trailing_pe", "raw_value": "#N/A Field Not Applicable", "error_type": "N/A_NOT_APPLICABLE"},
  {"field_name": "roc", "raw_value": "#N/A N/A", "error_type": "N/A_NA"}
]
```

### 3.3 Validation Report

The `run_bloomberg_pipeline()` function produces a validation report for every import:

- Total tickers parsed
- Successful tickers (zero errors) vs. failed tickers (one or more errors)
- Per-ticker breakdown: fields parsed, fields errored, specific error details
- Upload status (whether data was written to Supabase)

### 3.4 Core Principles

1. **Never silently drop data.** Every error is stored with its typed code and the original raw value.
2. **Never propagate raw error strings.** Bloomberg errors are always classified into typed codes before storage.
3. **Flag, do not filter.** Tickers with partial errors are still stored; the `is_error` flag and `error_fields` column enable downstream logic to handle them appropriately.
4. **Only read from the Values sheet.** The Fundamentals sheet shows `#NAME?` errors when opened outside a Bloomberg session. This is expected behavior, not a bug.

---

## 4. Data Freshness

### 4.1 Freshness Grades

Data freshness is computed by `backend/app/services/freshness.py` (shared module) based on the age of the `pull_date` relative to the current date. The `bloomberg_pipeline.py` module delegates to this shared implementation.

| Grade | Age | Weight in Decision Arbiter | Action |
|-------|-----|---------------------------|--------|
| `FRESH` | < 24 hours (< 1 calendar day) | 1.0 (full weight) | No action needed |
| `RECENT` | 1-7 days | 1.0 (full weight) | Flagged in logs for visibility |
| `STALE` | 7-30 days | 0.5 (50% weight reduction) | Downweighted in Decision Arbiter; flagged in dashboard |
| `EXPIRED` | > 30 days | 0.0 (excluded) | Excluded from live trading decisions entirely |

### 4.2 Weight Application

The `freshness_weight()` function in `freshness.py` returns the multiplier:

```python
FRESH  -> 1.0
RECENT -> 1.0
STALE  -> 0.5
EXPIRED -> 0.0
```

The `apply_freshness_filter()` function can be used to filter record lists, optionally excluding expired data and enriching each record with its freshness grade and weight.

### 4.3 Freshness in the Bloomberg Pipeline

- Each row in `bloomberg_fundamentals` has a `freshness_grade` column (`CHECK` constraint: `FRESH`, `RECENT`, `STALE`, `EXPIRED`)
- Freshness is computed at parse time and stored with the data
- The `get_freshness_report()` endpoint queries the latest pull date per ticker and recomputes freshness grades against the current date
- Recommended cadence: daily upload after market close using `JMWFM_Bloomberg_YYYY-MM-DD.xlsx`

### 4.4 Freshness in the Data Source Chain

When the data source fallback chain (`data_source_chain.py`) fetches from Supabase (cached Bloomberg), it returns the most recent record by `pull_date`. Freshness is not checked at the chain level -- the consuming code (screening engine, risk engine) applies freshness weights.

---

## 5. Piotroski F-Score Workaround

The standard Bloomberg BDP field `PIOTROSKI_F_SCORE` returns `#N/A Invalid Field` for all security types. The system implements a manual Piotroski calculator in `backend/app/services/piotroski.py`.

### 5.1 The 9 Standard Piotroski Signals

| Signal # | Name | Standard Definition | Bloomberg Data Used | Available from Snapshot? |
|----------|------|--------------------|--------------------|------------------------|
| 1 | `roa_positive` | Net income > 0 | `IS_EPS` (EPS as proxy) | Yes |
| 2 | `operating_cash_flow_positive` | Operating cash flow > 0 | `CF_FREE_CASH_FLOW` (FCF as proxy) | Yes |
| 3 | `roa_improving` | ROA increased vs. prior year | `IS_EPS` (current vs. prior) | Only with prior period data |
| 4 | `accrual_quality` | Operating CF > Net Income | `CF_FREE_CASH_FLOW` + `OPER_MARGIN` | Yes (proxy: FCF > 0 AND operating margin > 0) |
| 5 | `leverage_decreasing` | Long-term debt decreased | `TOT_DEBT_TO_TOT_EQY` (current vs. prior) | Only with prior period data |
| 6 | `current_ratio_improving` | Current ratio increased | `CUR_RATIO` (current vs. prior) | Only with prior period data |
| 7 | `no_dilution` | Shares outstanding did not increase | Not available in Bloomberg snapshot | Never (no shares outstanding field) |
| 8 | `gross_margin_improving` | Gross margin increased | `GROSS_MARGIN` (current vs. prior) | Only with prior period data |
| 9 | `asset_turnover_improving` | Revenue / Total Assets improved | `SALES_GROWTH` (revenue growth as proxy) | Yes (proxy: revenue growth > 0) |

### 5.2 Single-Snapshot Limitations

With only a single Bloomberg export (no prior period), only 3-4 of the 9 signals are computable:

- Signal 1 (ROA positive): computable from current EPS
- Signal 2 (Operating CF positive): computable from current FCF
- Signal 4 (Accrual quality): computable from current FCF + operating margin
- Signal 9 (Asset turnover improving): computable from revenue growth

Signals 3, 5, 6, 7, and 8 require prior-period comparison data.

### 5.3 Proportional Threshold

Because the number of computable signals varies, the system uses a proportional threshold rather than a fixed score:

```
passes_threshold = (score / max_possible) >= 5/9
```

For example, if only 4 signals are computable and the ticker scores 3/4, the ratio is 0.75 which exceeds 5/9 (0.556), so it passes. This prevents penalizing tickers where Bloomberg data gaps make signals uncomputable.

### 5.4 Proxy Mappings

Several signals use Bloomberg fields as proxies for data the Piotroski score traditionally requires:

| Traditional Piotroski Input | Bloomberg Proxy | Rationale |
|---------------------------|----------------|-----------|
| Net Income | `IS_EPS` (EPS) | EPS > 0 implies positive net income |
| Operating Cash Flow | `CF_FREE_CASH_FLOW` (FCF) | FCF is operating CF minus capex; positive FCF implies positive operating CF |
| Total Assets | Not used directly | Revenue growth (`SALES_GROWTH`) used as proxy for asset turnover improvement |
| Shares Outstanding | Not available | Signal 7 (`no_dilution`) is always marked as `data_available=False` |

---

## 6. Field Availability by Security Type

### 6.1 US Equities (Standard)

All 21 stored fields are expected to be available for standard US equities (e.g., NVDA, MSFT, AMZN). Exceptions are documented per-ticker below.

### 6.2 ADR Securities

American Depositary Receipts have known field limitations:

| Ticker | Company | Known Errors | Handling |
|--------|---------|-------------|---------|
| TSM | TSMC | `PE_RATIO` returns `#N/A Field Not Applicable`; `fcf_yield` may be `N/A` | Use `BEST_PE_RATIO` as primary P/E; `is_adr: true` flag |

All ADR tickers are flagged with `is_adr: true` in both the pipeline (`ADR_TICKERS = {"TSM"}`) and the `bloomberg_fundamentals` table.

**ADR-specific rules:**
- Trailing P/E (`PE_RATIO`) is expected to fail for ADRs. Use forward P/E (`BEST_PE_RATIO`) as the primary valuation metric.
- All ADR tickers must have `is_adr: true` metadata for downstream logic.

### 6.3 Known Per-Ticker Issues (Feb 21, 2026 Snapshot)

| Ticker | Field | Error | Notes |
|--------|-------|-------|-------|
| TSM | `trailing_pe` (`PE_RATIO`) | `N/A_NOT_APPLICABLE` | ADR characteristic; use `BEST_PE_RATIO` (23.6x) |
| TSM | `eps` (`IS_EPS`) | `N/A` | ADR; forward EPS (`BEST_EPS`) available |
| TSM | `fcf_yield` (`FREE_CASH_FLOW_YIELD`) | `N/A` | Compute manually: `CF_FREE_CASH_FLOW / CUR_MKT_CAP` |
| AAPL | `roc` (`RETURN_ON_CAP`) | `N/A_NA` | Known Bloomberg issue for AAPL |
| AAPL | `ebitda_interest_coverage` | `N/A` | Not available |
| PYPL | `peg_ratio` (`PEG_RATIO`) | `VALUE_ERROR` | No growth estimate; compute manually |
| PYPL | `ccc` | `N/A` | Cash conversion cycle not applicable for financial services |
| NFLX | `peg_ratio` (`PEG_RATIO`) | `VALUE_ERROR` | Compute via `BEST_PE_RATIO / BEST_EST_LONG_TERM_GROWTH` |
| NFLX | `ccc` | `N/A` | Not applicable for streaming services |
| TSLA | `peg_ratio` (`PEG_RATIO`) | `VALUE_ERROR` | Negative growth makes PEG meaningless |

### 6.4 ETFs and Indices

The current system is designed for **equities only**. The 10-ticker pilot watchlist and S&P 500 universe are all individual stocks. Bloomberg field availability for ETFs (e.g., SPY) and indices differs significantly:

- Most fundamental ratios (`PE_RATIO`, `CF_FREE_CASH_FLOW`, `GROSS_MARGIN`, etc.) are not applicable to ETFs or indices
- Price fields (`PX_LAST`, `CUR_MKT_CAP`) are available
- The risk engine uses SPY price data for circuit breaker calculations but sources this from Alpaca/Yahoo, not Bloomberg BDP

---

## 7. Snapshot vs. Time-Series Queries

### 7.1 Current Architecture: Snapshot Only

The Bloomberg pipeline uses **snapshot (BDP)** queries exclusively. Each export captures a single point-in-time view of 25 metrics for the pilot tickers. This is because:

1. Bloomberg Terminal access is through a university license with limited hours
2. Data is exported via the Bloomberg Excel Add-In, not a live API
3. The system stores one row per ticker per pull date in `bloomberg_fundamentals`

### 7.2 When Snapshot Is Appropriate

- Current fundamental ratios (P/E, margins, FCF yield, etc.)
- Current price and market cap
- Current debt and liquidity metrics
- Screening and filtering (all 5 tiers use snapshot data)

### 7.3 When Time-Series Would Be Needed

| Use Case | Data Required | Current Source |
|----------|--------------|---------------|
| Piotroski signals 3, 5, 6, 8 (YoY comparisons) | Prior-period fundamentals | Multiple Bloomberg snapshots over time |
| OHLCV price history for quant models | Daily open/high/low/close/volume | `price_history` table (Dow Jones CSV, Emery CSV) |
| Correlation calculations (risk engine) | 30+ days of daily returns | Alpaca API or Yahoo Finance |
| SPY circuit breaker (5-day rolling) | 5 days of SPY prices | Alpaca API |
| Moving averages and technical indicators | 50-200 days of prices | Alpaca API or Yahoo Finance |

### 7.4 Historical Price Data (Non-Bloomberg)

OHLCV price history is stored in the `price_history` table (migration 014) and comes from two CSV sources, not Bloomberg:

| Source | Date Range | Granularity | Columns |
|--------|-----------|-------------|---------|
| Dow Jones | 1928-2009 | Daily | Open, High, Low, Close, Volume, Adjusted Close |
| Emery S&P 500 | ~2015-2025 | 1-minute bars | ticker, open, high, low, close, volume, window_start, transactions |

### 7.5 Building a Time-Series from Snapshots

As Bloomberg snapshots accumulate over weeks, the system will build a time-series of fundamental data. Each snapshot becomes a row in `bloomberg_fundamentals` with its `pull_date`. This enables:

- Piotroski YoY comparisons (once 12+ months of data exist)
- Fundamental trend analysis (margin expansion/contraction over time)
- Freshness tracking (older snapshots grade from FRESH to EXPIRED)

---

## 8. Calculation Formulas

These formulas use Bloomberg fields and are documented in `PROJECT_STANDARDS_v2.md` Section 3.

| Formula | Expression | Bloomberg Fields | Notes |
|---------|-----------|-----------------|-------|
| PEG Ratio (manual) | `BEST_PE_RATIO / BEST_EST_LONG_TERM_GROWTH` | Forward PE, LT Growth | Fallback when `PEG_RATIO` returns `#VALUE!` |
| Cash Conversion Cycle | `DIO + DSO - DPO` | `CASH_CONVERSION_CYCLE` (direct) | Match fiscal periods; negative = competitive advantage |
| FCF Yield (manual) | `CF_FREE_CASH_FLOW / CUR_MKT_CAP * 100` | FCF, Market Cap | Stored as percentage (3.0 = 3%); threshold is 3.0 |
| FCF to Net Income | `CF_FREE_CASH_FLOW / IS_NET_INCOME` | FCF, Net Income | > 1.0 indicates strong cash generation |
| Instrument Signal | FCF Yield vs. 10yr Treasury | `FREE_CASH_FLOW_YIELD` | Wasden Bucket 1: bond yield > equity FCF yield = reduce equity exposure |

---

## 9. Data Source Fallback Chain

When Bloomberg data is unavailable (terminal not accessed, field errors, or eventual license expiration in Spring 2027), the system uses a fallback chain implemented in `backend/app/services/data_source_chain.py`.

### 9.1 Chain Order

```
Supabase (cached Bloomberg) -> Finnhub API -> Yahoo Finance -> halt and alert
```

### 9.2 Field Mapping: Bloomberg to Finnhub

| DB Column | Bloomberg Code | Finnhub Metric Key | Notes |
|-----------|---------------|-------------------|-------|
| `market_cap` | `CUR_MKT_CAP` | `marketCapitalization` | Finnhub returns in millions; multiplied by 1,000,000 |
| `trailing_pe` | `PE_RATIO` | `peNormalizedAnnual` | |
| `forward_pe` | `BEST_PE_RATIO` | `forwardPE` | |
| `eps` | `IS_EPS` | `epsNormalizedAnnual` | |
| `peg_ratio` | `PEG_RATIO` | `pegRatio` | |
| `roe` | `RETURN_COM_EQY` | `roeTTM` | |
| `gross_margin` | `GROSS_MARGIN` | `grossMarginTTM` | |
| `operating_margin` | `OPER_MARGIN` | `operatingMarginTTM` | |
| `net_margin` | `PROF_MARGIN` | `netProfitMarginTTM` | |
| `current_ratio` | `CUR_RATIO` | `currentRatioQuarterly` | |
| `debt_to_equity` | `TOT_DEBT_TO_TOT_EQY` | `totalDebtToEquityQuarterly` | |
| `revenue_growth` | `SALES_GROWTH` | `revenueGrowthQuarterlyYoy` | |

**Not available on Finnhub:** `price`, `fcf`, `fcf_yield`, `ebitda_margin`, `roc`, `quick_ratio`, `ebitda_interest_coverage`, `ccc`, `short_interest`

### 9.3 Field Mapping: Bloomberg to Yahoo Finance

| DB Column | Bloomberg Code | Yahoo Finance Key | Notes |
|-----------|---------------|------------------|-------|
| `price` | `PX_LAST` | `currentPrice` | |
| `market_cap` | `CUR_MKT_CAP` | `marketCap` | |
| `trailing_pe` | `PE_RATIO` | `trailingPE` | |
| `forward_pe` | `BEST_PE_RATIO` | `forwardPE` | |
| `eps` | `IS_EPS` | `trailingEps` | |
| `peg_ratio` | `PEG_RATIO` | `pegRatio` | |
| `fcf` | `CF_FREE_CASH_FLOW` | `freeCashflow` | |
| `fcf_yield` | `FREE_CASH_FLOW_YIELD` | Computed | `freeCashflow / marketCap * 100` |
| `roe` | `RETURN_COM_EQY` | `returnOnEquity` | Yahoo returns as decimal (0.45); multiplied by 100 |
| `gross_margin` | `GROSS_MARGIN` | `grossMargins` | Yahoo returns as decimal; multiplied by 100 |
| `operating_margin` | `OPER_MARGIN` | `operatingMargins` | Yahoo returns as decimal; multiplied by 100 |
| `net_margin` | `PROF_MARGIN` | `profitMargins` | Yahoo returns as decimal; multiplied by 100 |
| `current_ratio` | `CUR_RATIO` | `currentRatio` | |
| `debt_to_equity` | `TOT_DEBT_TO_TOT_EQY` | `debtToEquity` | |
| `revenue_growth` | `SALES_GROWTH` | `revenueGrowth` | Yahoo returns as decimal; multiplied by 100 |

**Not available on Yahoo Finance:** `roc`, `ebitda_margin`, `quick_ratio`, `ebitda_interest_coverage`, `ccc`, `short_interest`

---

## 10. Database Schema

The `bloomberg_fundamentals` table (migration 011) stores all Bloomberg data:

```sql
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
  freshness_grade TEXT CHECK (freshness_grade IN ('FRESH', 'RECENT', 'STALE', 'EXPIRED')),
  is_adr BOOLEAN DEFAULT FALSE,
  is_error BOOLEAN DEFAULT FALSE,
  error_fields JSONB,
  UNIQUE(ticker, pull_date)
);
```

Key design decisions:
- **Unique on (ticker, pull_date):** One row per ticker per export date. Upsert on conflict.
- **All metric columns are nullable:** A `NULL` value means "data not available" (Bloomberg error or field not in export).
- **`error_fields` is JSONB:** Stores structured error detail without requiring separate error tables.
- **`freshness_grade` is a CHECK constraint:** Database enforces valid values.

---

## 11. Export Pipeline

### 11.1 File Format

- **Filename pattern:** `JMWFM_Bloomberg_YYYY-MM-DD.xlsx`
- **Storage location:** `data/raw/bloomberg/` (not committed to git)
- **Sheet to read:** Values sheet only (Fundamentals sheet shows `#NAME?` outside terminal)
- **Recommended cadence:** Daily after market close
- **Upload to Supabase:** Within 24 hours of export

### 11.2 Pipeline Steps

```
1. Parse Excel (Values sheet) via openpyxl
2. Extract pull date from filename
3. Map Excel column headers to DB columns via COLUMN_MAP
4. Parse each cell: numeric values extracted, errors classified
5. Flag ADR tickers (currently: TSM)
6. Compute freshness grade for each row
7. Build validation report
8. Upsert to Supabase bloomberg_fundamentals table
9. Return validation report
```

### 11.3 CLI Access

```bash
# Run the Bloomberg pipeline
cd backend && python -m app.cli.pipeline_cli bloomberg data/raw/bloomberg/JMWFM_Bloomberg_2026-02-21.xlsx

# Check data freshness
cd backend && python -m app.cli.pipeline_cli freshness
```

---

## 12. Bloomberg Terminal Commands Reference

For manual data verification and exploration in the Bloomberg Terminal:

| Command | Description | Usage |
|---------|-------------|-------|
| `DES` | Security Description | Overview of a ticker |
| `FA` | Financial Analysis | Ratios, cash flow, profitability |
| `EE` | Estimates | P/E, forward P/E, EPS, PEG |
| `EM` | Earnings & Revenue | Earnings trajectory |
| `RV` | Relative Value | Peer comparison |
| `EQRV` | Equity Relative Value | Multiples vs. comparables |
| `ANR` | Analyst Recommendations | Consensus ratings |
| `GP` | Price Chart | Historical price chart |
| `OWN` | Ownership | Institutional ownership |
| `SURP` | Earnings Surprise | Beat/miss history |
| `SPLC` | Suppliers & Customers | Supply chain analysis |

---

## 13. Pilot Watchlist (10 Tickers)

All fields are sourced from the Feb 21, 2026 Bloomberg snapshot stored in `KNOWLEDGE_BASE_v2.md` Section 19.

| Ticker | Company | Bloomberg ID | Sector | is_adr | Key Notes |
|--------|---------|-------------|--------|--------|-----------|
| NVDA | NVIDIA | NVDA US Equity | Technology | No | PEG 0.54, ROE 107%, rev growth 114% |
| PYPL | PayPal | PYPL US Equity | Technology | No | FCF Yield 14%, PEG = VALUE_ERROR |
| NFLX | Netflix | NFLX US Equity | Communication | No | PEG = VALUE_ERROR |
| TSM | TSMC | TSM US Equity | Technology | Yes | PE_RATIO = N/A_NOT_APPLICABLE |
| XOM | Exxon Mobil | XOM US Equity | Energy | No | PEG 2.85 (fails Tier 2) |
| AAPL | Apple | AAPL US Equity | Technology | No | CCC -72.4, ROC = N/A_NA |
| MSFT | Microsoft | MSFT US Equity | Technology | No | PEG 1.58, clean data |
| AMZN | Amazon | AMZN US Equity | Consumer | No | CCC -41.0, FCF yield 0.34% |
| TSLA | Tesla | TSLA US Equity | Consumer | No | PE 341.8, PEG = VALUE_ERROR |
| AMD | AMD | AMD US Equity | Technology | No | PEG 0.61, CCC 162.3 days |
