# Quant Feature Set Agreement

> Agreed feature definitions for all Phase 1 quant models.
> Version: 1.0 | Last Updated: February 26, 2026

---

## 1. Feature Engineering Pipeline

All features are built by `FeatureEngineer.build_features()` in
`src/intelligence/quant_models/feature_engineer.py`. Input is an OHLCV DataFrame
with columns: `date`, `open`, `high`, `low`, `close`, `volume`. Data must be
sorted ascending by date before feature construction.

### 1.1 Complete Feature List

| # | Feature | Category | Calculation | Lookback |
|---|---------|----------|-------------|----------|
| 1 | `sma_5_20_cross` | SMA crossover | (SMA(5) - SMA(20)) / SMA(20) | 20 days |
| 2 | `sma_20_50_cross` | SMA crossover | (SMA(20) - SMA(50)) / SMA(50) | 50 days |
| 3 | `rsi_14` | Momentum | Wilder RSI with 14-day rolling mean of gains/losses | 14 days |
| 4 | `macd` | Momentum | EMA(12) - EMA(26) | 26 days |
| 5 | `macd_signal` | Momentum | EMA(9) of MACD line | 26+9 days |
| 6 | `macd_histogram` | Momentum | MACD - MACD signal | 26+9 days |
| 7 | `bb_position` | Volatility band | (close - BB_mid) / (2 * BB_std), BB period=20, width=2 | 20 days |
| 8 | `return_1d` | Returns | 1-day percent change of close | 1 day |
| 9 | `return_5d` | Returns | 5-day percent change of close | 5 days |
| 10 | `return_20d` | Returns | 20-day percent change of close | 20 days |
| 11 | `volatility_20d` | Volatility | 20-day rolling std of `return_1d` | 20 days |
| 12 | `volume_ratio` | Volume | volume / SMA(volume, 20) | 20 days |

**Total: 12 engineered features.**

Intermediate columns (`sma_5`, `sma_20`, `sma_50`, `bb_upper`, `bb_lower`) are
computed during feature engineering but are **not** included in the final feature
set. Rows with NaN values from rolling window warm-up are dropped.

### 1.2 Feature Details

**SMA Crossovers** -- Normalized difference between fast and slow simple moving
averages. Positive values indicate bullish momentum (fast above slow). The
normalization by the slow SMA makes the signal comparable across price levels.

**RSI-14** -- Relative Strength Index using Wilder's smoothing (14-day rolling
mean). Ranges from 0-100. Values above 70 indicate overbought; below 30
indicates oversold. Division-by-zero when loss is 0 is handled by replacing 0
with NaN.

**MACD (12, 26, 9)** -- Three components: the MACD line (fast EMA minus slow
EMA), the signal line (9-day EMA of MACD), and the histogram (MACD minus
signal). All use `adjust=False` exponential moving averages.

**Bollinger Band Position** -- Position of the close price relative to the
20-day Bollinger Bands (2 standard deviations). Values near +1 indicate price
at the upper band; values near -1 indicate price at the lower band; 0 is the
midpoint.

**Returns** -- Simple percent changes at 1-day, 5-day, and 20-day horizons.
Used directly as features (not log returns).

**Volatility** -- 20-day rolling standard deviation of daily returns. Measures
recent realized volatility.

**Volume Ratio** -- Current volume divided by 20-day average volume. Values
above 1.0 indicate above-average volume activity. Uses lognormal distribution
in mock mode to reflect the typical right-skewed nature of volume data.

---

## 2. Feature Usage by Model

| Feature | XGBoost | Elastic Net | ARIMA | Sentiment |
|---------|:-------:|:-----------:|:-----:|:---------:|
| `sma_5_20_cross` | Y | Y | -- | -- |
| `sma_20_50_cross` | Y | Y | -- | -- |
| `rsi_14` | Y | Y | -- | -- |
| `macd` | Y | Y | -- | -- |
| `macd_signal` | Y | Y | -- | -- |
| `macd_histogram` | Y | Y | -- | -- |
| `bb_position` | Y | Y | -- | -- |
| `return_1d` | Y | Y | -- | -- |
| `return_5d` | Y | Y | -- | -- |
| `return_20d` | Y | Y | -- | -- |
| `volatility_20d` | Y | Y | -- | -- |
| `volume_ratio` | Y | Y | -- | -- |
| Close price series | -- | -- | Y | -- |
| Finnhub news headlines | -- | -- | -- | Y |
| NewsAPI headlines | -- | -- | -- | Y |

**XGBoost** (`XGBoostDirectionModel`) -- Uses all 12 engineered features. Input
is a dict of feature name to value, or a 1D numpy array. Produces bullish
probability [0, 1] via `predict_proba`.

**Elastic Net** (`ElasticNetDirectionModel`) -- Uses all 12 engineered features.
Same input format as XGBoost. Raw regression output is passed through a sigmoid
function to produce [0, 1] probability.

**ARIMA** (`ARIMAModel`) -- Does NOT use engineered features. Operates directly
on the raw close price series (minimum 30 data points). Fits ARIMA(5,1,0) and
forecasts 5 days ahead. The predicted price is converted to directional
confidence [0, 1] via a sigmoid-like scaling where +-5% maps to roughly
[0.25, 0.75].

**Sentiment** (`SentimentModel`) -- Does NOT use engineered features. Fetches
recent news headlines (7-day window) from Finnhub (weight=0.6) and NewsAPI
(weight=0.4). Headlines are scored via keyword matching against positive/negative
word lists. Produces weighted-average sentiment [0, 1].

---

## 3. Label Definition

**Target variable:** 5-day forward return direction (binary).

```python
forward_return = close[t+5] / close[t] - 1
label = 1 if forward_return > 0 else 0
```

- `1` = price went up over the next 5 trading days (bullish)
- `0` = price went down or stayed flat over the next 5 trading days (bearish)

Built by `FeatureEngineer.build_labels(ohlcv_df, forward_days=5)`.

The last 5 rows of any dataset will have NaN labels and must be excluded during
training.

---

## 4. Train/Test Split Methodology

**Method:** Fixed-date holdout split (not random split).

```python
holdout_start = "2025-10-01"  # default
```

- **Training set:** All rows where `date < holdout_start`
- **Validation set:** All rows where `date >= holdout_start`

This approach avoids look-ahead bias that random splits would introduce in
time-series data. The date column is excluded from the feature matrix before
training.

The holdout period aligns with PROJECT_STANDARDS_v2.md Section 2 model manifest
schema: `"holdout_period": "2025-10-01 to 2025-12-31"`.

---

## 5. Feature Normalization Approach

**Current state: No normalization is applied.**

- XGBoost is tree-based and inherently invariant to feature scaling.
- Elastic Net (sklearn `ElasticNet`) would benefit from standardization, but the
  current implementation does not apply any scaler. This is a known limitation
  (see Section 8).
- ARIMA operates on raw price levels.
- Sentiment operates on keyword-scored headlines (already bounded [0, 1]).

---

## 6. Mock Feature Generation

For mock mode and testing, `FeatureEngineer.generate_mock_features()` produces
synthetic feature data.

| Parameter | Value |
|-----------|-------|
| Default rows | 200 |
| Random seed | 42 (deterministic) |
| Date range | 200 business days ending 2026-02-21 |
| RNG | `numpy.random.default_rng(seed)` |

**Mock feature distributions:**

| Feature | Distribution | Parameters |
|---------|-------------|------------|
| `sma_5_20_cross` | Normal | mean=0.01, std=0.03 |
| `sma_20_50_cross` | Normal | mean=0.005, std=0.02 |
| `rsi_14` | Uniform | low=20, high=80 |
| `macd` | Normal | mean=0, std=2 |
| `macd_signal` | Normal | mean=0, std=1.5 |
| `macd_histogram` | Normal | mean=0, std=0.5 |
| `bb_position` | Normal | mean=0, std=0.5 |
| `return_1d` | Normal | mean=0.001, std=0.02 |
| `return_5d` | Normal | mean=0.005, std=0.04 |
| `return_20d` | Normal | mean=0.02, std=0.08 |
| `volatility_20d` | Uniform | low=0.01, high=0.05 |
| `volume_ratio` | Lognormal | mean=0, sigma=0.3 |

Mock scores for the 10 pilot tickers are separately defined in `mock_scores.py`
and are NOT generated from feature data. They are fixed values per ticker per
model.

---

## 7. Ensemble Composition

Per PROJECT_STANDARDS_v2.md Section 2 (Ensemble Voting):

- 4 Tier 1 models: XGBoost, Elastic Net, ARIMA, Sentiment
- **Composite score:** Equal-weighted arithmetic mean of all 4 model scores
- **Disagreement metric:** Standard deviation of the 4 scores
- **High disagreement flag:** `std_dev > 0.50` (from `risk/constants.py`)
- High disagreement triggers automatic position sizing reduction

The composite score feeds the Bull/Bear debate as quant context. It does NOT
directly trigger trades.

---

## 8. Known Limitations

1. **No feature normalization for Elastic Net.** The `ElasticNet` regularization
   penalizes coefficients based on magnitude, so features with larger scales
   (e.g., `rsi_14` ranging 20-80) will dominate over smaller-scale features
   (e.g., `return_1d` ranging -0.05 to 0.05). A `StandardScaler` should be
   added before Elastic Net training.

2. **Survivorship bias.** All training data is tagged
   `survivorship_bias_audited: false` until a formal audit is completed. See
   `docs/survivorship_bias_audit.md` and `docs/survivorship_bias_audit_plan.md`.
   Delisted tickers must be included in training data per PROJECT_STANDARDS_v2.md
   Section 1.

3. **ARIMA model independence.** ARIMA does not use the shared feature set. Its
   predictions are based solely on the close price series with a fixed
   ARIMA(5,1,0) order. No automatic order selection (e.g., auto-ARIMA) is
   implemented.

4. **Sentiment keyword list coverage.** The keyword-based headline scoring is a
   baseline approach. It does not handle negation ("not bullish"), sarcasm, or
   domain-specific jargon. Finnhub weight (0.6) is higher than NewsAPI (0.4) but
   this weighting has not been empirically validated.

5. **Forward label leakage risk.** The `build_labels()` method uses
   `shift(-forward_days)`, which creates NaN labels for the last `forward_days`
   rows. These must be properly excluded during alignment with features. The
   current split logic uses date-based alignment, but care is needed when
   joining features and labels manually.

6. **Mock features are not calibrated to real market statistics.** The synthetic
   distributions approximate realistic ranges but are independently generated
   (no cross-feature correlations). Real market features exhibit significant
   correlations (e.g., returns and volatility).

7. **Equal weighting.** The ensemble uses equal weights for all 4 models. No
   performance-based weighting or stacking is implemented. Autotune of ensemble
   weights is prohibited per PROJECT_STANDARDS_v2.md Section 2.

8. **Minimum data requirements.** Feature engineering requires 50 trading days
   of OHLCV data (driven by the 50-day SMA). ARIMA requires a minimum of 30
   data points. Tickers with insufficient history will fail feature construction.
