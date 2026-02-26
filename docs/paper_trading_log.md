# Paper Trading Log — Wasden Watch

> **Start Date:** ________ (fill when paper trading begins)
> **Initial Capital:** $100,000 (paper)
> **Benchmark:** SPY (S&P 500 ETF)
> **Trading Mode:** PAPER (enforced via TRADING_MODE env var)
> **Slippage Model:** 0.1% per 1% of ADV (per PROJECT_STANDARDS_v2.md Section 7)

---

## Daily Trade Log

| Date | Ticker | Action | Entry Price | Exit Price | Position Size | P&L % | Cumulative Return | Notes |
|------|--------|--------|-------------|------------|---------------|-------|-------------------|-------|
| | | | | | | | | |
| | | | | | | | | |

---

## Weekly Summary

### Week of ________

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | | |
| Win Rate | | Target: 60-80% (PROJECT_STANDARDS_v2.md Section 7) |
| Sharpe Ratio | | Annualized, risk-free = 5% |
| Sortino Ratio | | Downside-only volatility |
| Max Drawdown | | |
| Max Drawdown Duration | | Trades |
| Profit Factor | | Gross profits / gross losses |
| Cumulative Return | | Since start |
| SPY Return (same period) | | Benchmark comparison |
| Alpha vs SPY | | |
| API Cost | | Target: under $150/month |

**Notable Events:**
- (Circuit breaker triggers, regime changes, unusual market conditions)

**Wasden Watch Distribution:**
- APPROVE: ____ / NEUTRAL: ____ / VETO: ____

**Model Agreement:**
- Mean std_dev across quant models: ____
- High disagreement flags (std_dev > 0.5): ____

---

## Monthly Review

### Month of ________

#### Model Performance Comparison

| Model | Avg Score | Directional Accuracy | Contribution to Composite | Notes |
|-------|-----------|---------------------|---------------------------|-------|
| XGBoost | | | | |
| Elastic Net | | | | |
| ARIMA | | | | |
| Sentiment | | | | |
| **Composite** | | | | |

#### Wasden Watch Analysis

| Metric | Value |
|--------|-------|
| Veto Rate | |
| Veto Rate Alert | Normal / Too Restrictive (>50%) / Too Permissive (<5%) |
| Override Count | |
| Override Win Rate | |
| APPROVE accuracy | |

#### Bias Report

| Metric | Value | Status |
|--------|-------|--------|
| Sector Concentration (max) | | OK / ALERT (>40%) |
| Jury Escalation Rate | | OK / ALERT (>20%) |
| Quant-Wasden Agreement Rate | | |
| Debate Agreement Rate | | |
| Action Distribution (BUY/SELL/HOLD/BLOCKED/ESCALATED) | | |
| Position Size (mean / median) | | |
| Rolling 30-day Win Rate | | OK / ALERT (<50%) |

#### Adjustments Made
- (Any parameter changes, model retraining, prompt updates — with approval status)
- (Risk constant changes require written approval from BOTH Joe and Jared)

---

## Key Metrics Dashboard

> These sections will be filled automatically by `PerformanceTracker.summary_report()` and `BiasMonitor.generate_bias_report()` as data accumulates.

### Returns
- Total Return: ____
- Annualized Return: ____
- Sharpe Ratio: ____
- Sortino Ratio: ____
- Max Drawdown: ____

### Risk
- Current Cash Reserve: ____ (minimum 10% per PROJECT_STANDARDS_v2.md Section 8)
- Circuit Breaker Status: Inactive / Active
- Consecutive Loss Streak: ____ (warning at 7)

### vs Benchmark
- Alpha: ____
- Beta: ____
- Tracking Error: ____
- Information Ratio: ____

---

## Escalation Log

> All 5-5 jury ties, human decisions, and veto overrides are logged here.
> Per CLAUDE.md Critical Rule 4: 5-5 jury ties ALWAYS escalate to human. Never auto-resolve.

| Date | Ticker | Type | Details | Decision By | Outcome |
|------|--------|------|---------|-------------|---------|
| | | 5-5 Tie | | | |
| | | Veto Override | | | |
| | | Human Override | | | |

---

## Consecutive Loss Tracking

> Per PROJECT_STANDARDS_v2.md Section 8: warning at 7 consecutive losses.
> System pauses entries and alerts both partners.

| Date | Streak Count | Status | Tickers | Resolved By | Resolution |
|------|-------------|--------|---------|-------------|------------|
| | | Active / Resolved | | | |

---

## Live Trading Transition Checklist

> Both partners must sign off before transitioning from paper to live.
> From PROJECT_STANDARDS_v2.md Section 7.

- [ ] Minimum paper trading period completed (define duration: ____ days/weeks)
- [ ] 60-80% win rate validated on paper trading
- [ ] Sharpe ratio > ____ (define target)
- [ ] Max drawdown < ____ (define limit)
- [ ] Personal trading rules document written and signed
- [ ] Override and drawdown rules documented
- [ ] Live API keys confirmed and tested in paper mode first
- [ ] Maximum starting capital agreed: $____
- [ ] Emergency shutdown procedure documented and tested
- [ ] Google Voice or prepaid Signal number set up
- [ ] Both partners sign below:

**Joe White:** _________________ Date: _________
**Jared Wasden:** _________________ Date: _________
