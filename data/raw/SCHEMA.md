# Dow Jones Historical Data Schema

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
