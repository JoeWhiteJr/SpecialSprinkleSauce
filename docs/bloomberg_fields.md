# Bloomberg Field Reference — Wasden Watch

> Structured reference for all 25 Bloomberg BDP fields used in the system.
> Key data points filled from KNOWLEDGE_BASE_v2.md. Detail TBD by Joe/Jared.

---

## Field Codes

### Valuation Ratios

| # | Metric | Bloomberg Code | DB Column | Description |
|---|--------|---------------|-----------|-------------|
| 1 | Current Price | PX_LAST | price | Last trade price |
| 2 | Market Cap | CUR_MKT_CAP | market_cap | Market capitalization |
| 3 | P/E Ratio (Trailing) | PE_RATIO | trailing_pe | Trailing 12-month P/E |
| 4 | P/E Ratio (Forward) | BEST_PE_RATIO | forward_pe | Forward P/E estimate |
| 5 | EPS (Current) | IS_EPS | eps | Current earnings per share |
| 6 | PEG Ratio | PEG_RATIO | peg_ratio | Price/Earnings to Growth. Below 1 = cheap. |

### Cash Flow Ratios (Wasden's Favorites)

| # | Metric | Bloomberg Code | DB Column | Description |
|---|--------|---------------|-----------|-------------|
| 7 | Free Cash Flow | CF_FREE_CASH_FLOW | fcf | Wasden's #1 favorite metric |
| 8 | FCF Yield | FREE_CASH_FLOW_YIELD | fcf_yield | FCF / Market Cap. Compared to bond yields for Bucket 1 instrument signal. |
| 9 | EBITDA Margin | EBITDA_MARGIN | ebitda_margin | Better than earnings — harder to misrepresent |

### Profitability Ratios

| # | Metric | Bloomberg Code | DB Column | Description |
|---|--------|---------------|-----------|-------------|
| 10 | ROE | RETURN_COM_EQY | roe | Return on equity. Should not exceed ROC. |
| 11 | ROC | RETURN_ON_CAP | roc | Return on capital. Should be > ROE. |
| 12 | Gross Margin | GROSS_MARGIN | gross_margin | Compare over time and vs. peers |
| 13 | Operating Margin | OPER_MARGIN | operating_margin | Compare over time and vs. peers |
| 14 | Net Margin | PROF_MARGIN | net_margin | Compare over time and vs. peers |

### Liquidity & Leverage

| # | Metric | Bloomberg Code | DB Column | Description |
|---|--------|---------------|-----------|-------------|
| 15 | Current Ratio | CUR_RATIO | current_ratio | Current assets / current liabilities |
| 16 | Quick Ratio | QUICK_RATIO | quick_ratio | Quick ratio |
| 17 | Debt to Equity | TOT_DEBT_TO_TOT_EQY | debt_to_equity | Compare by industry. More reliable the industry, more debt OK. |
| 18 | Interest Coverage | INTEREST_COVERAGE_RATIO | ebitda_interest_coverage | EBITDA / Interest expense |

### Growth & Efficiency

| # | Metric | Bloomberg Code | DB Column | Description |
|---|--------|---------------|-----------|-------------|
| 19 | Revenue Growth YoY | SALES_GROWTH | revenue_growth | If below inflation, concern |
| 20 | Cash Conversion Cycle | CASH_CONVERSION_CYCLE | ccc | DIO + DSO - DPO. Negative = competitive advantage (e.g., AAPL at -72.4). |
| 21 | Short Interest | SHORT_INT_RATIO | short_interest | Sentiment signal |

### Not in Standard BDP

| # | Metric | Bloomberg Code | DB Column | Notes |
|---|--------|---------------|-----------|-------|
| 22 | Piotroski F-Score | PIOTROSKI_F_SCORE | — | Returns #N/A Invalid Field. Requires custom EQS formula. Score 0-9. |
| 23 | EPS Forward Est | BEST_EPS | — | In Excel but not in bloomberg_fundamentals table |
| 24 | Long-term Growth Est | BEST_EST_LONG_TERM_GROWTH | — | Used for PEG calculation fallback |

---

## Known Bloomberg Errors

| Error String | Typed Code | Meaning | Handling |
|-------------|-----------|---------|----------|
| `#N/A Invalid Field` | N/A_INVALID_FIELD | Field not available for ticker | Store as error, don't propagate |
| `#N/A Field Not Applicable` | N/A_NOT_APPLICABLE | ADR or security type issue | Use BEST_PE_RATIO instead of PE_RATIO for ADRs |
| `#N/A N/A` | N/A_NA | Data not available | Store as null |
| `#VALUE!` | VALUE_ERROR | Calculation error (e.g., PEG with no growth) | Store as error |
| `#NAME?` | NAME_ERROR | Formula error outside Bloomberg session | Only read from Values sheet — never Fundamentals |

---

## ADR Notes

- **TSM (TSMC):** Trailing PE via PE_RATIO returns `#N/A Field Not Applicable` — expected. Use BEST_PE_RATIO as primary.
- **AAPL:** ROC (RETURN_ON_CAP) returns `#N/A N/A` — known issue.
- All ADR tickers flagged with `is_adr: true` in bloomberg_fundamentals table.

---

## Data Freshness Rules

| Grade | Age | Weight | Action |
|-------|-----|--------|--------|
| FRESH | < 24 hours | Full weight | — |
| RECENT | 1-7 days | Full weight | Flagged in logs |
| STALE | 7-30 days | Weight reduced 50% | Downweighted in Decision Arbiter |
| EXPIRED | > 30 days | Excluded | Excluded from live decisions |

**Recommended cadence:** Daily upload after market close using `JMWFM_Bloomberg_YYYY-MM-DD.xlsx`.

---

## Calculation Notes

| Formula | Expression | Notes |
|---------|-----------|-------|
| PEG | BEST_PE_RATIO / BEST_EST_LONG_TERM_GROWTH | Fallback to manual if PEG_RATIO returns #VALUE! |
| CCC | DIO + DSO - DPO | Match fiscal periods |
| FCF Yield | CF_FREE_CASH_FLOW / CUR_MKT_CAP | Also used in Bucket 1 instrument signal |
| FCF to Net Income | CF_FREE_CASH_FLOW / IS_NET_INCOME | Over 1.0 = strong cash generation |
| Instrument Signal | FCF Yield vs 10yr Treasury | Bond yield > equity FCF yield = reduce equity exposure |

---

## TODO (Joe/Jared)
- [ ] Document Piotroski F-Score custom EQS formula
- [ ] Add per-ticker ADR handling rules
- [ ] Document Bloomberg fallback chain field mappings (Yahoo Finance, Finnhub)
- [ ] Add sector-specific ratio benchmarks
