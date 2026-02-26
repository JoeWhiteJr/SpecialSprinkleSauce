# Sprinkle Sauce — Screening Pipeline Specification

> Version 1.0 | Week 3 Implementation

## Overview

The Sprinkle Sauce is the 5-tier screening funnel that reduces the S&P 500 universe (~500 stocks) down to 5 final candidates for the full Decision Arbiter pipeline.

## Tier Definitions

### Tier 1: Liquidity Filter
- **Criteria:** Market cap > $5B
- **ADV check:** Optional (attempt via fallback data sources if available)
- **Purpose:** Ensure sufficient liquidity for entry/exit without excessive slippage
- **Expected pass rate:** ~60-70% of S&P 500

### Tier 2: Sprinkle Sauce (Fundamental Screen)
- **PEG Ratio:** < 2.0 (positive values only; negative PEG = negative earnings growth, excluded)
- **FCF Yield:** > 3.0% (stored as percentage in DB: 3.0 = 3%, not 0.03)
- **Piotroski F-Score:** >= 5/9 (proportional: `score / max_possible >= 5/9`)
- **Purpose:** Filter for fundamentally sound, undervalued companies
- **Expected pass rate:** ~30-40% of Tier 1 survivors

### Tier 3: Quant Model Filter (STUB — Week 5)
- **Criteria:** Composite score > 0.55, low model disagreement
- **Models:** XGBoost, Elastic Net, ARIMA, Sentiment ensemble
- **Purpose:** Apply quantitative signals

### Tier 4: Wasden Watch Verdict (STUB — Week 7)
- **Criteria:** Wasden verdict != VETO
- **Purpose:** Apply Peter Wasden's investment framework via RAG
- **Integration:** Wired after Week 4 RAG system is complete

### Tier 5: Final Selection (STUB — Week 7)
- **Criteria:** Top 5 by composite × Wasden confidence
- **Purpose:** Rank and select the best candidates

## Piotroski F-Score Details

### 9 Binary Signals
1. **ROA Positive** — Net income > 0 (proxy: EPS > 0)
2. **Operating Cash Flow Positive** — OCF > 0 (proxy: FCF > 0)
3. **ROA Improving** — ROA higher than prior year (requires 2 snapshots)
4. **Accrual Quality** — OCF > Net Income (proxy: FCF > 0 AND operating margin > 0)
5. **Leverage Decreasing** — D/E ratio lower than prior year
6. **Current Ratio Improving** — Current ratio higher than prior year
7. **No Dilution** — No new share issuance (requires shares outstanding data)
8. **Gross Margin Improving** — Gross margin higher than prior year
9. **Asset Turnover Improving** — Revenue growth > 0

### Single Snapshot Mode
With only one Bloomberg snapshot (typical for daily pipeline), signals 3, 5, 6, 7, 8 require prior period data and score as "unavailable." The proportional threshold adjusts: `score / max_possible >= 5/9`.

Example: If only 4 signals are computable and 3 pass: 3/4 = 0.75 > 0.556 → PASSES.

## Data Source Fallback Chain

Per PROJECT_STANDARDS_v2.md Section 5:
1. **Supabase** (cached Bloomberg data from daily Excel uploads)
2. **Finnhub** (free API, confirmed access)
3. **Yahoo Finance** (free, via yfinance library)

If all sources fail for a critical field, the ticker is flagged but NOT automatically failed — it proceeds with reduced confidence.

## FCF Yield Convention

FCF yield is stored as a **percentage** in the database:
- `14.05` means 14.05%
- Threshold is `3.0` (not `0.03`)
- Formula: `CF_FREE_CASH_FLOW / CUR_MKT_CAP × 100`
