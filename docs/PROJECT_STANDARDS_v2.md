# PROJECT_STANDARDS_v2.md — Wasden Watch Trading System
> Trading-system-specific extension of PROJECT_STANDARDS.md. Read that file first. This file adds only trading-specific rules. When there is a conflict, this file takes precedence.
> Version: 2.0 | Last Updated: February 23, 2026

---

## 1. Trading Data Standards

### Price Data
- All historical price data uses adjusted prices (split and dividend adjusted) unless explicitly stated otherwise
- Corporate actions (splits, reverse splits, spinoffs, ticker changes, delistings) are logged immediately and affected historical data flagged for re-adjustment
- Delisted tickers preserved in Supabase with delisted_date and delisted_reason fields. Never deleted.
- All data from 32GB minute dataset and Emery 10-year dataset tagged survivorship_bias_unaudited: true until Week 3 audit sets survivorship_bias_audited: true

### Fundamental Data
- All Bloomberg fundamental data includes: ticker, pull_date, bloomberg_field_code, value, is_error (bool), error_type
- Stale (over 7 days): flagged stale: true, downweighted in Decision Arbiter
- Expired (over 30 days): excluded from live decisions
- #N/A, #VALUE!, #NAME? stored as typed errors, not raw strings

### Data Freshness Grades
FRESH (under 24 hours): full weight
RECENT (1-7 days): full weight, flagged in logs
STALE (7-30 days): weight reduced by 50%
EXPIRED (over 30 days): excluded from live decisions

### Ticker Format
Bloomberg format: TICKER US Equity for US stocks. ADR status in metadata as is_adr: bool.

### Data Asset Formats
Dow Jones (1928-2009): OHLCV plus adjusted close, daily CSV, delivered midnight. Variable name in R: dowjones1.
Emery S&P 500 (last 10 years): OHLCV, all US stocks, CSV.
Both stored in data/raw/ with date-stamped filenames.

---

## 2. Model Development Standards

### Model Manifest (Required at Every Export)

```json
{
  "model_name": "xgboost_direction_classifier",
  "version": "v1.0.0",
  "trained_date": "2026-02-21",
  "training_data_range": "2020-01-01 to 2025-12-31",
  "survivorship_bias_audited": false,
  "holdout_period": "2025-10-01 to 2025-12-31",
  "validation_results": {
    "accuracy": 0.0,
    "sharpe_on_holdout": 0.0,
    "max_drawdown_on_holdout": 0.0,
    "win_rate": 0.0
  },
  "parameters": {},
  "notes": ""
}
```

### Dr. Miller Neural Networks

DowSmall1a (R): 5 inputs (Open_Lag0 through Open_Lag4), hidden [5, 3], predicts today's close.
DowLarger1a (R): 6 inputs (adds Close_Lag1), hidden [10, 8, 6], threshold 0.001. More precise.

Integration plan:
1. Store R notebooks as-is in models/miller_nn/
2. Port both to Python (TensorFlow or PyTorch) as miller_nn_python.py
3. Retrain Python versions on Emery 10-year OHLCV dataset for modern conditions
4. Convert close price prediction to directional signal: predicted_close > current_price = bullish
5. Validate before adding to ensemble
6. Tier 2 models — not used in Phase 1

### 10-Agent Jury Configuration

Triggered when bull/bear debate reaches disagreement. 10 agents review full debate transcript and vote BUY, SELL, or HOLD.

Recommended composition:
- 3 agents: fundamentals and ratio analysis focus
- 2 agents: macro and sector environment focus
- 2 agents: risk and downside scenario focus
- 2 agents: technical signal interpretation focus
- 1 agent: Wasden 5-bucket framework application focus

Decision rules:
- 6 or more votes in one direction = decisive
- 5-5 split = escalate to human (Jared decides). NEVER auto-resolve.
- Full vote breakdown and reasoning logged for every jury session

### Ensemble Voting (Quant Layer)
4 Tier 1 models (XGBoost, Elastic Net, ARIMA, Sentiment) produce a composite score that feeds the Bull/Bear debate as context. Track standard deviation of model scores. std_dev above 0.5 = high disagreement flag, reduce position sizing automatically.

### Continuous Learning Guardrails
- Checkpoint mechanism must exist before autotune activates
- Autotune allowed: minor parameters (learning rates, regularization, lookback within 20%)
- Autotune prohibited: jury weights, risk constants, Wasden veto, ensemble composition
- Every autotune run: log changes, run 90-day holdout, written human sign-off before going live
- Net zero performance triggers shutdown warning automatically

---

## 3. Financial Calculation Standards

| Ratio | Formula | Notes |
|-------|---------|-------|
| PEG | BEST_PE_RATIO / BEST_EST_LONG_TERM_GROWTH | Fallback to manual if PEG_RATIO returns #VALUE! |
| CCC | DIO + DSO - DPO | Match fiscal periods |
| FCF Yield | CF_FREE_CASH_FLOW / CUR_MKT_CAP | Also used in Bucket 1 instrument signal |
| FCF to Net Income | CF_FREE_CASH_FLOW / IS_NET_INCOME | Over 1.0 = strong cash generation |
| Instrument Signal | FCF Yield vs 10yr Treasury | Wasden Bucket 1 portfolio-level signal |

Piotroski F-Score: standard BDP field returns #N/A Invalid Field. Implement via custom Bloomberg EQS formula documented in KNOWLEDGE_BASE_v2.md Section 9. Score 0-9. Required for Sprinkle Sauce screening.

Bucket 1 Instrument Signal: compare equity FCF yield to US government 10-year bond yield. Bond yield exceeding equity FCF yield = signal to reduce equity exposure. Surface in dashboard and decision journal as portfolio-level alert.

ADR tickers: trailing PE via PE_RATIO returns #N/A Field Not Applicable — expected. Use BEST_PE_RATIO as primary. Flag all ADRs with is_adr: true.

All data stored and displayed in USD unless explicitly tagged otherwise.

---

## 4. Decision Audit Trail

Every trade recommendation, veto, jury vote, override, and execution is logged. The decision journal is the single source of truth.

### Decision Journal Schema

```python
{
  "timestamp": "ISO-8601",
  "ticker": "NVDA US Equity",
  "pipeline_run_id": "uuid",
  "quant_scores": {
    "xgboost": float, "elastic_net": float, "arima": float, "sentiment": float,
    "composite": float, "std_dev": float, "high_disagreement_flag": bool
  },
  "wasden_verdict": {
    "verdict": "APPROVE or NEUTRAL or VETO",
    "confidence": float, "reasoning": str,
    "mode": "direct_coverage or framework_application",
    "passages_retrieved": int
  },
  "bull_case": str,
  "bear_case": str,
  "debate_result": {"outcome": "agreement or disagreement", "rounds": int},
  "jury": {
    "spawned": bool, "reason": str,
    "votes": [{"agent_id": int, "vote": "BUY or SELL or HOLD", "reasoning": str}],
    "final_count": {"buy": int, "sell": int, "hold": int},
    "decision": "BUY or SELL or HOLD or ESCALATED",
    "escalated_to_human": bool
  },
  "risk_check": {"passed": bool, "checks_failed": []},
  "pre_trade_validation": {"passed": bool, "checks_failed": []},
  "final_decision": {
    "action": "BUY or SELL or HOLD or BLOCKED",
    "reason": str, "recommended_position_size": float,
    "human_approval_required": bool, "human_approved": bool,
    "approved_by": str, "approved_at": str
  },
  "execution": {
    "executed": bool, "order_id": str, "fill_price": float, "slippage": float
  }
}
```

### Veto Override Record (Separate Log Entry)

```python
{
  "timestamp": "ISO-8601", "ticker": str,
  "original_verdict": "VETO", "override_reason": str,
  "overridden_by": str, "pipeline_run_id": str, "outcome_tracked": bool
}
```

All veto overrides reviewed in the weekly bias monitoring report.

---

## 5. Bloomberg Data Handling

Export pipeline:
1. Export Values sheet only (never Fundamentals sheet)
2. Run validation script: check for #N/A, #VALUE!, #NAME?, empty fields, out-of-range
3. Store to Supabase with full provenance
4. Flag invalid fields — never silently drop

Date-stamp filename format: JMWFM_Bloomberg_YYYY-MM-DD.xlsx. Store in data/raw/bloomberg/.
Store to Supabase within 24 hours of export.

Bloomberg fallback chain (for when terminal access expires Spring 2027):
- Primary: Bloomberg Terminal
- Fallback 1: Yahoo Finance (free)
- Fallback 2: Finnhub (free API, confirmed)
- Fallback 3: Fidelity Active Trader Pro
- Future: paid Bloomberg if system is profitable

All data fetch functions accept a data_source parameter and route accordingly.

---

## 6. API and External Service Standards

Required .env keys:
CLAUDE_API_KEY, GEMINI_API_KEY, ALPACA_PAPER_API_KEY, ALPACA_PAPER_SECRET_KEY,
ALPACA_LIVE_API_KEY, ALPACA_LIVE_SECRET_KEY, SUPABASE_URL, SUPABASE_ANON_KEY,
SUPABASE_SERVICE_KEY, NEWSAPI_KEY, FINNHUB_API_KEY, TRADING_MODE, SIGNAL_NUMBER

API fallback chains:
- LLM: Claude → Gemini fallback → halt and alert
- Market data: Bloomberg → Yahoo Finance → Finnhub → halt and alert
- Trade execution: Alpaca → halt immediately, alert, do NOT retry

Rate limiting: exponential backoff on all external API calls. Daily spend cap is hard, not soft.

LLM model selection by task:
- 500 stock bulk screening: Claude Haiku
- Top 8 Wasden Watch verdicts: Claude Sonnet
- Deep analysis edge cases: Claude Opus

---

## 7. Paper vs. Live Trading Standards

### TRADING_MODE Requirement

```python
TRADING_MODE = os.getenv("TRADING_MODE")
assert TRADING_MODE in ("paper", "live"), "TRADING_MODE must be explicitly set"
```

No default. System halts with clear error if unset. Primary safeguard against accidental live trading.

### Slippage Model
Order above 1% of average daily volume: model 0.1% slippage per 1% of ADV. Paper results without slippage are misleadingly optimistic.

### Live Trading Transition Checklist (Both Partners Sign Off)
- Minimum paper trading period completed (both partners define this number before going live)
- 60-80% win rate validated on backtesting
- Personal trading rules document written and signed
- Override and drawdown rules documented
- Live API keys confirmed and tested in paper mode first
- Maximum starting capital agreed (start small)
- Emergency shutdown procedure documented and tested
- Google Voice or prepaid Signal number set up

### Capital Cycling Rule
Once capital doubles in live trading, pull out and reallocate. Cycle the doubling.

---

## 8. Risk System Standards

### Risk Parameter Constants

```python
MAX_POSITION_PCT = 0.12
RISK_PER_TRADE_PCT = 0.015
MIN_CASH_RESERVE_PCT = 0.10
MAX_CORRELATED_POSITIONS = 3
CORRELATION_THRESHOLD = 0.70
STRESS_CORRELATION_THRESHOLD = 0.80
REGIME_CIRCUIT_BREAKER_SPY_DROP = 0.05
DEFENSIVE_POSITION_REDUCTION = 0.50
DEFENSIVE_CASH_TARGET = 0.40
HIGH_MODEL_DISAGREEMENT_THRESHOLD = 0.50
SLIPPAGE_ADV_THRESHOLD = 0.01
SLIPPAGE_PER_ADV_PCT = 0.001
```

Changes to any constant require human approval and a decision journal entry.

### Shutdown Triggers
Consecutive loss warning: triggered after N consecutive losses (N defined by both partners before going live). System explains what it is doing, why, and suggests possible shutdown.
Net zero trigger: cumulative losses equal cumulative gains (net PnL at or below 0). System halts new entries and alerts both partners. Requires written human approval to restart.

### Risk Check Order
1. Position size check
2. Cash reserve check
3. Correlation check (30-day rolling)
4. Stress correlation check (worst 10 market days in last year)
5. Sector concentration check
6. Gap risk score check
7. Model disagreement check

### Regime Circuit Breaker
SPY drops more than 5% in rolling 5-day window: cut all positions by 50%, increase cash to 40%, halt new entries, log regime_circuit_breaker_active: true, alert both partners.

---

## 9. Testing Standards

Unit tests: every ratio calculation has a test. All Bloomberg error states tested. Slippage model tested. Risk constants cannot be accidentally changed.

Integration tests: full pipeline run on test ticker produces deterministic output. Wasden Watch verdict tested against 10 known stocks. Jury tested with simulated debate transcripts. Pre-trade validation covers all 4 checks.

Stress tests (required before going live): COVID crash Feb-Mar 2020, 2022 bear market, regional banking crisis March 2023, major Fed pivot moments, Dow Jones 1928-2009 crash scenarios.

Paper trading regression: after changes to intelligence, pipeline, or risk modules, run 30-day simulation on historical data. If max drawdown increases more than 15% relative vs. pre-change baseline, flag for human review before merging.

---

## 10. Required Documentation

| Document | Location | When |
|----------|----------|------|
| KNOWLEDGE_BASE_v2.md | knowledge-base/ | Maintained continuously |
| bloomberg_fields.md | knowledge-base/ | Before any Bloomberg field goes into code |
| personal_trading_rules.md | docs/ | Both partners write this BEFORE going live |
| paper_trading_log.md | docs/ | Weekly once paper trading starts |
| bias_monitoring_report.md | docs/ | Weekly once system generates recommendations |
| model manifests | models/ | One JSON per trained model at export |

ADRs required for: jury agent prompt design, quant ensemble method, decision journal schema, vector store migration plan, regime detection method, position sizing method, any change to Wasden veto logic.

### Weekly Report Contents (Once System Is Running)
- Wasden APPROVE/NEUTRAL/VETO distribution
- Model agreement rate (how often std_dev is under 0.5)
- Sector concentration in recommendations
- Paper trading P&L vs. SPY
- API cost actual vs. budget (target under $150/month)
- Consecutive loss count vs. warning threshold
- Capital cycle status (distance from doubling target)
