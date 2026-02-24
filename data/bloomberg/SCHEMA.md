# Bloomberg Data Schema

## File Format
- **Type**: CSV
- **Naming**: `YYYY_MM_DD_thru_YYYY_MM_DD.csv` (date range covered)
- **Source**: Bloomberg Terminal BDP export

## Tickers (Pilot Watchlist)
| Ticker | Company |
|--------|---------|
| NVDA US Equity | NVIDIA |
| PYPL US Equity | PayPal |
| NFLX US Equity | Netflix |
| TSM US Equity | TSMC |
| XOM US Equity | Exxon Mobil |
| AAPL US Equity | Apple |
| MSFT US Equity | Microsoft |
| AMZN US Equity | Amazon |
| TSLA US Equity | Tesla |
| AMD US Equity | AMD |

## Columns (25 Metrics)
| Column | Bloomberg Field | Description |
|--------|-----------------|-------------|
| Date | - | Pull date |
| Time | - | Pull time |
| Ticker | - | Bloomberg format (TICKER US Equity) |
| Current Price | PX_LAST | Last trade price |
| Market Cap | CUR_MKT_CAP | Market capitalization |
| P/E Ratio (Trailing) | PE_RATIO | Trailing 12-month P/E |
| P/E Ratio (Forward) | BEST_PE_RATIO | Forward P/E estimate |
| EPS (Current) | IS_EPS | Current earnings per share |
| EPS (Next Year Est) | BEST_EPS | Forward EPS estimate |
| PEG Ratio | PEG_RATIO | Price/Earnings to Growth |
| Free Cash Flow | CF_FREE_CASH_FLOW | Free cash flow |
| FCF Yield | FREE_CASH_FLOW_YIELD | FCF / Market Cap |
| EBITDA Margin | EBITDA_MARGIN | EBITDA margin % |
| ROE | RETURN_COM_EQY | Return on equity |
| ROC | RETURN_ON_CAP | Return on capital |
| Gross Margin | GROSS_MARGIN | Gross margin % |
| Operating Margin | OPER_MARGIN | Operating margin % |
| Net Margin | PROF_MARGIN | Net profit margin % |
| Current Ratio | CUR_RATIO | Current assets / current liabilities |
| Quick Ratio | QUICK_RATIO | Quick ratio |
| Debt to Equity | TOT_DEBT_TO_TOT_EQY | Total debt / equity |
| Revenue Growth YoY | SALES_GROWTH | Year-over-year revenue growth |
| EBITDA/Interest | INTEREST_COVERAGE_RATIO | Interest coverage |
| Piotroski F-Score | PIOTROSKI_F_SCORE | Always returns #N/A - requires custom EQS |
| Cash Conversion Cycle | CASH_CONVERSION_CYCLE | DIO + DSO - DPO |
| Short Interest | SHORT_INT_RATIO | Short interest ratio |

## Known Bloomberg Errors
| Error | Meaning | Handling |
|-------|---------|----------|
| `#N/A Invalid Field` | Field not available for ticker | Store as error, don't propagate |
| `#N/A Field Not Applicable` | ADR or security type issue (e.g., TSM PE_RATIO) | Use BEST_PE_RATIO instead |
| `#N/A N/A` | Data not available | Store as null |
| `#VALUE!` | Calculation error (e.g., PEG with no growth) | Store as error |
| `#NAME?` | Formula error outside Bloomberg session | Only read from Values sheet |

## Data Freshness (per PROJECT_STANDARDS_v2.md)
- **FRESH**: < 24 hours - full weight
- **RECENT**: 1-7 days - full weight, flagged
- **STALE**: 7-30 days - weight reduced 50%
- **EXPIRED**: > 30 days - excluded from live decisions
