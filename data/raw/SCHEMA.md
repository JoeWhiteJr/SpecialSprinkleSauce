# Raw Data Schemas

This document describes the raw datasets stored locally (not committed to git).

---

# Emery Intraday OHLCV Dataset

## File Format
- **Type**: CSV (compressed archive, 32GB total)
- **Source**: Emery's 5-year market data extract
- **Granularity**: 1-minute bars
- **Coverage**: ~8,682 tickers (comprehensive US market)
- **Sample File**: `2020-10-15.csv` (one trading day, 77MB, 1.37M rows)

## Columns (8 Fields)
| Column | Type | Description |
|--------|------|-------------|
| ticker | String | Stock symbol (e.g., AAPL, SPY) |
| volume | Integer | Volume traded in this 1-minute window |
| open | Float | Opening price of the minute bar |
| close | Float | Closing price of the minute bar |
| high | Float | High price of the minute bar |
| low | Float | Low price of the minute bar |
| window_start | Integer | Timestamp in nanoseconds (epoch) |
| transactions | Integer | Number of transactions in this window |

## Sample Ticker Coverage
Top tickers by data density (from 2020-10-15 sample):
- NIO, AAPL, SQQQ, SPY, QQQ, FSLY, TSLA, TQQQ, UVXY

## Notes
- Data spans pre-market through after-hours (~16 hours per day)
- Timestamp conversion: `datetime.fromtimestamp(window_start / 1e9)`
- Full dataset not extracted locally due to size (32GB compressed)

---

# Dow Jones Historical Data Schema (Miller NN)

## File Format
- **Type**: CSV
- **Source**: Historical DJIA data (1928-2009)
- **Rows**: 20,204 trading days
- **Date Range**: October 1, 1928 through March 18, 2009

## Purpose
Training data for Dr. Miller's neural network models (DowSmall1a, DowLarger1a) which predict DJIA closing prices based on opening price lag features.

## Columns (7 Fields)
| Column | Type | Description |
|--------|------|-------------|
| Date | Date (YYYY-MM-DD) | Trading day date |
| Open | Float | Opening price (USD) |
| High | Float | Intraday high (USD) |
| Low | Float | Intraday low (USD) |
| Close | Float | Closing price (USD) - **primary prediction target** |
| Volume | Integer | Trading volume |
| Adj Close | Float | Adjusted closing price (accounts for splits/dividends) |

## Neural Network Usage (per DowSmall1a_Architecture.txt)
The models use only `Open` and `Close` columns:
- **Input Features**: 5-day window of opening prices (Open_Lag0 through Open_Lag4)
- **Target Variable**: Current day's Close price
- **Normalization**: Min-Max scaling to [0, 1]

## Data Quality Notes
- First 4 rows are dropped during model training (insufficient lag history)
- Data predates 2009; newer data would be needed for current market conditions
- Volume field available but not currently used by Miller NN models

## Related Files
- `models/miller_nn/DowSmall1a_Architecture.txt` - Model architecture documentation
- `models/miller_nn/DowLarger1a_Architecture.txt` - Extended model documentation
