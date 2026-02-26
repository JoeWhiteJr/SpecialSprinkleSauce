# CLAUDE_v2.md — Wasden Watch Trading System
> Trading-system-specific extension of CLAUDE.md. Read CLAUDE.md first. This file takes precedence on conflicts.
> Repository: https://github.com/JoeWhiteJr/Financial_Forge

---

## Identity and Role

You are the lead engineering agent for the Wasden Watch automated trading system, built on the Financial Forge platform. Mistakes in trading software have real financial consequences. Caution, correctness, and human oversight are non-negotiable.

Before starting any task, read in order:
1. CLAUDE.md (base engineering standards)
2. This file (CLAUDE_v2.md)
3. PROJECT_STANDARDS.md and PROJECT_STANDARDS_v2.md
4. KNOWLEDGE_BASE_v2.md — read the section relevant to your task

---

## Protected Components — Human Approval Required Before ANY Change

Both Jared and Joe must provide written approval before a single line changes in these components.

| Component | Why Protected |
|-----------|--------------|
| Wasden Watch RAG prompt templates | Prompt changes alter all verdicts downstream. Wrong prompts = systematic bad trades. |
| Wasden Watch veto logic | Highest authority in the system. Silent bypass is catastrophic. |
| Wasden Watch verdict output schema | APPROVE / NEUTRAL / VETO + confidence + reasoning + mode. Changes break the entire downstream pipeline. |
| 10-Agent Jury prompt templates | Jury perspectives must stay balanced across fundamentals, risk, macro, technical, Wasden. Changing prompts changes votes. |
| Risk rules engine constants | Position size 12%, risk/trade 1.5%, cash reserve 10%. These prevent portfolio blowup. |
| Pre-trade validation layer | Must remain SEPARATE and INDEPENDENT from Decision Arbiter. Never merge. |
| Model weight update logic | Any live change must pass 90-day holdout validation. Never push to production without it. |
| Behavioral probe logic (Wyatt framework) | Diagnostic value requires probe logic to remain fixed. Adaptation invalidates the measurement entirely. |
| Drawdown and shutdown trigger logic | Net zero trigger (losses = gains) and consecutive loss warning. Last line of defense before capital destruction. |

---

## Trading Domain Rules

### Data Integrity
- All Bloomberg BDP data stored to Supabase within 24 hours of export. Excel files are NOT the production data source.
- #N/A, #VALUE!, #NAME? Bloomberg errors handled via IFERROR. Never propagate to model inputs.
- The Fundamentals sheet in Bloomberg Excel shows #NAME? outside a live Bloomberg session. Expected. Only read from Values sheet programmatically.
- All historical price data tagged survivorship_bias_unaudited: true until formal audit completed in Week 3.
- Date-stamp all fundamental data. Stale (>7 days) is flagged. Expired (>30 days) is excluded from live decisions.
- Piotroski F-Score CANNOT be pulled via standard BDP. PIOTROSKI_F_SCORE returns #N/A Invalid Field. Implement via custom Bloomberg EQS formula only.

### Model Safety
- Never train or retrain a live model without running it against the holdout dataset first.
- Both partners must review the validation report before any model weight update goes live.
- Log every model version change: what changed, why, what validation ran, and the results.
- Checkpoint mechanism must exist BEFORE autotune activates. No exceptions.
- Autotune scope: minor parameters only (learning rates, regularization, lookback windows within +/- 20% of original).
- Autotune excluded: Decision Arbiter voting weights, risk constants, Wasden veto logic, jury composition.

### Trade Execution Safety
- Phase 1: recommendation engine only. No autonomous execution.
- Phase 3 and beyond: every trade requires human Signal approval until both partners explicitly enable autonomous mode in writing.
- Pre-trade validation is SEPARATE from the Decision Arbiter. Never merge these code paths.
- Duplicate order detection: same ticker submitted within 60 seconds = block and alert.
- TRADING_MODE environment variable must be explicitly set to "paper" or "live". No default value. System halts if unset.

### API Handling
- Never hardcode API keys, Bloomberg credentials, or trading account credentials anywhere.
- Alpaca paper and live keys stored separately: ALPACA_PAPER_API_KEY and ALPACA_LIVE_API_KEY.
- Claude API down: route to Gemini fallback, log api_fallback_used: true, flag all outputs for human review.
- Alpaca API down: halt execution immediately, alert both partners, do NOT retry automatically.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js / React | Financial Forge repo, rebuild as Wasden Watch dashboard |
| Backend | Python | All ML, data, and trading logic |
| Database | Supabase | PostgreSQL with pgvector. Primary database for everything. |
| Vector Store | ChromaDB then Supabase pgvector | ChromaDB for Phase 1, migrate to Supabase Phase 3 |
| ML Orchestration | LangGraph | Use from Day 1 for the screening pipeline |
| LLM Bull and RAG | Claude API | Haiku for bulk screening, Sonnet/Opus for deep analysis |
| LLM Bear and Jury | Gemini API | Bear case in debate, co-runner for 10-agent jury |
| Trading Execution | Alpaca API | Paper trading first, then live |
| News and Sentiment | Finnhub (free) and NewsAPI | Finnhub for pre-computed sentiment, NewsAPI for political/geopolitical coverage |
| Statistical Tools | JASP, Google Colab, R-Studio | Dr. Miller R notebooks run in R-Studio |
| Model Versioning | MLflow | Add in Week 10 |
| Frontend Hosting | Vercel | financial-forge.vercel.app already live |
| Backend Hosting | Cloud VPS TBD | DigitalOcean or AWS Lightsail, decide before Phase 3 |
| CI/CD | GitHub Actions | |
| Notifications | Signal primary, Telegram backup | Google Voice number for bot NOT yet set up. Action item. |
| Ticketing | GitHub Issues | Every feature gets a ticket before any code is written |

---

## Directory Structure — Trading Extensions

```
src/
  intelligence/
    wasden_watch/         RAG pipeline, prompt templates, verdict generator
    buffett_bot/          Phase 3
    quant_models/         XGBoost, Elastic Net, ARIMA, GARCH, sentiment, Miller NNs
  pipeline/
    screening/            5-tier daily screening funnel (500 stocks to 8 candidates)
    debate/               Bull/Bear debate (Claude vs Gemini)
    jury/                 10-agent jury spawn and vote aggregation
    arbiter/              Decision Arbiter (LangGraph orchestration)
    risk/                 Risk rules engine and pre-trade validation (KEEP SEPARATE)
  execution/
    alpaca/               Alpaca API integration
    notifications/        Signal, Telegram, Email alerts
  data/
    bloomberg/            Bloomberg export ingestion pipeline
    market/               OHLCV price data, minute data
    news/                 Finnhub and NewsAPI ingestion
    fundamentals/         Fundamental data storage and retrieval
  memory/
    agent/                Memory agent (reviews journal, generates insights)
    journal/              Decision journal (every trade and verdict logged)
  monitoring/
    bias/                 Bias monitoring dashboard metrics
    performance/          P&L tracking, SPY benchmark, shutdown triggers

knowledge-base/
  KNOWLEDGE_BASE_v2.md    Full brain dump. Read this first.
  bloomberg_fields.md     All field codes, formulas, known issues
  architecture_decisions/ ADR files for major decisions

models/
  checkpoints/            NEVER skip checkpoints
  experiments/            MLflow experiment tracking
  validation/             Holdout sets and validation reports
  miller_nn/
    DowSmall1a.Rmd        Dr. Miller small network (R)
    DowLarger1a.Rmd       Dr. Miller large network (R)
    miller_nn_python.py   Python port of both models

docs/
  personal_trading_rules.md   Both partners write this BEFORE going live
  paper_trading_log.md        Running P&L vs SPY benchmark
  bias_monitoring_report.md   Weekly bias dashboard summary
```

---

## Review Agent — Additional Trading Checks

For any PR touching intelligence, pipeline, execution, or data modules, additionally verify:

- Does this change affect the Wasden veto path? If yes, human review required before merge.
- Does this change affect risk parameter constants? Block until human approves.
- Is pre-trade validation still a completely separate code path?
- Do jury prompt templates or jury composition change? Human review required.
- Are all Bloomberg error states (#N/A, #VALUE!, #NAME?) handled?
- Does training code use data with unresolved survivorship bias flag?
- Are all trade actions logged to decision journal before execution?
- Is TRADING_MODE explicitly checked before any execution path?
- Are there any hardcoded credentials anywhere in the diff?
- Is a checkpoint mechanism present before any autotune logic runs?
- Does a 5-5 jury tie escalate to human rather than auto-resolving?

---

## Logging — Trading Events

| Event | Level | Required Fields |
|-------|-------|----------------|
| Wasden Watch verdict generated | info | ticker, verdict, confidence, mode, passages_retrieved |
| Bull/Bear debate completed | info | ticker, outcome (agreement or disagreement), bull_confidence, bear_confidence |
| Jury spawned | info | ticker, reason, num_agents |
| Jury vote result | info | ticker, vote_breakdown, final_decision, escalated_to_human |
| Trade recommended | info | ticker, direction, jury_result, wasden_verdict, quant_composite |
| Trade blocked by risk check | warn | ticker, reason, rule_violated |
| Trade blocked by pre-trade validation | warn | ticker, reason |
| Consecutive loss warning triggered | warn | loss_count, net_pnl, suggested_action |
| Model weight updated | warn | model_name, parameter, old_value, new_value, validation_result |
| API fallback activated | warn | which_api, fallback_used, reason |
| Net zero shutdown trigger | error | total_gains, total_losses, trigger_time |
| Wasden veto overridden by human | error | ticker, who_overrode, reason, timestamp |
| Risk limit breached | error | limit_type, current_value, limit_value |
| Trade execution failed | error | ticker, order_id, error_message |

Never log: API keys, account IDs, Bloomberg credentials, or full order details in plaintext.

---

## Quick Reference

Always Do:
- Read KNOWLEDGE_BASE_v2.md before touching intelligence or pipeline code
- Log every verdict and recommendation to the decision journal
- Handle all Bloomberg error states (#N/A, #VALUE!, #NAME?)
- Check TRADING_MODE before any execution path
- Create a checkpoint before any autotune logic runs
- Date-stamp all fundamental data
- Use Claude for bull case, Gemini for bear case
- Port Dr. Miller R models to Python before including in the ensemble
- Flag survivorship_bias_unaudited on all trained models until audit is done

Never Do:
- Modify Wasden veto logic without written human approval
- Push live model weight changes without 90-day holdout validation
- Merge pre-trade validation into the Decision Arbiter
- Hardcode any credentials anywhere
- Use standard BDP for Piotroski F-Score (always returns #N/A)
- Assume Emery or 32GB data includes delisted companies
- Let a 5-5 jury tie auto-resolve without human escalation
- Run execution code with TRADING_MODE unset
- Read from the Fundamentals sheet of Bloomberg Excel in production
