# SCHEDULE_v1.md — Wasden Watch Week-by-Week Development Schedule
> **Version:** 1.1 | **Last Updated:** February 25, 2026
> **Target:** Operable (paper trading, 60–80% backtested win rate) by end of May 2026
> **Note:** Weekly sync required. Daily check-in recommended.

> **Server Timeline:** Building and developing locally for Weeks 2–4. A dedicated 4TB server is being set up separately and will be integrated in Week 5+ for large dataset storage, model training, and heavy compute workloads.

---

## Timeline Overview

| Phase | Weeks | Focus |
|-------|-------|-------|
| Foundation | 1–3 | Environment, data pipeline, schemas |
| Intelligence | 4–6 | Wasden Watch RAG, quant models, debate |
| Pipeline | 7 | Decision pipeline, jury, LangGraph integration |
| Risk & Execution | 8 | Risk engine, Alpaca, pre-trade validation |
| Polish & Testing | 9 | Stress tests, prompt calibration, bias review |
| Dashboard & Launch | 10 | Financial Forge interface, paper trading live |

---

## WEEK 1 — Project Foundation
**Goal:** Environment up, repo organized, all data assets confirmed, team fully aligned

- [x] Set up Notion workspace and project board (tickets, weekly milestones, sprint view)
- [x] Create Notion ticket template (description, acceptance criteria, owner, week target)
- [x] Audit all 4 project documents — confirm accuracy before any code is written
- [x] Set up backend hosting (Render — replaced AWS EC2)
- [x] Set up Supabase project — configure PostgreSQL + pgvector extension
- [x] Set up all required API accounts: Alpaca (paper), Finnhub, NewsAPI
- [x] Configure `.env.example` with all required key placeholders — never commit `.env`
- [x] Clone Financial Forge repo — confirm local dev environment running
- [x] Pull Bloomberg data for full watchlist (all 11 tickers, all 25 metrics) — update Feb 21 snapshot
- [x] Export Bloomberg data to CSV — store in `data/bloomberg/` with date-stamp filename
- [x] Verify Emery's 10-year OHLCV dataset — confirm format, row count, date range, ticker coverage
- [x] Confirm Dow Jones 1928–2009 CSV loads correctly — verify OHLCV + adjusted close columns
- [x] Inventory all Wasden Weekender PDFs — consistent naming convention, confirm total count
- [x] Review Financial Forge GitHub repo — document what to keep vs. rebuild
- [x] Set up GitHub Actions CI/CD baseline (lint + test on push to main)
- [x] Read both `DowSmall1a.Rmd` and `DowLarger1a.Rmd` — understand architecture before porting
- [x] Set up Google Voice number for Signal bot notifications
- [x] Weekly sync: review all documents, agree on Week 1 completion definition

### Week 1 Completion Notes (Feb 25, 2026)

**Deviations from original plan:**
- **AWS EC2 replaced by Render** for backend hosting — simpler auto-deploy from GitHub, free tier sufficient for development phase
- **Vercel added for frontend hosting** — auto-deploys on push to `main`, zero-config for Next.js
- **Supabase migrations and seed data** created and applied — database schema operational with initial seed data

**What was deployed:**
- Frontend live at `https://special-sprinkle-sauce.vercel.app`
- Backend live at `https://specialsprinklesauce.onrender.com`
- Supabase PostgreSQL configured and seeded
- GitHub repo structured with `frontend/`, `backend/`, `database/` directories
- `.env.example` configured with all required placeholders
- CI/CD: pushes to `main` auto-deploy to both Vercel (frontend) and Render (backend)

**Deferred to later weeks:**
- 4TB dedicated server setup — targeting Week 5+ for large dataset storage and model training
- Large training datasets will remain local until server is online

---

## WEEK 2 — Data Pipeline & Database Schema
**Goal:** All data sources flowing into Supabase, schemas defined, Bloomberg export automated

- [ ] Implement fundamental data schema in Supabase
- [ ] Build Bloomberg export pipeline: CSV → validate → Supabase with provenance metadata
- [ ] Load Dow Jones historical CSV into Supabase (`data/market/`)
- [ ] Load Emery 10-year OHLCV dataset into Supabase (`data/market/`)
- [ ] Build `TRADING_MODE` env var check — halt immediately if unset or invalid
- [ ] Audit both datasets for survivorship bias scope — document findings in Notion
- [ ] Document all Bloomberg known issues: Piotroski `#N/A`, TSM trailing P/E, AAPL ROC
- [ ] Tag all Wasden Weekender PDFs with metadata (date, topics, sectors covered)
- [ ] Begin `wasden_philosophy.md` — document 5 buckets, key principles, ratio theory in full
- [ ] Weekly sync: confirm all datasets accessible in Supabase, schema validated against `PROJECT_STANDARDS_v2.md`

---

## WEEK 3 — Screening Pipeline & Sprinkle Sauce
**Goal:** 5-tier screening funnel operational. S&P 500 narrows to top candidates end-to-end.

- [ ] Document full Sprinkle Sauce filter criteria — which fields, which thresholds
- [ ] Define Tier 1–5 funnel rules in Notion (complete spec before building)
- [ ] Implement Tier 1 screening (price, volume, market cap filters)
- [ ] Implement Tier 2 screening (Sprinkle Sauce fundamentals using Supabase data)
- [ ] Research and document custom Piotroski F-Score EQS implementation formula
- [ ] Build manual Piotroski F-Score calculation from component Bloomberg fields
- [ ] Implement data freshness grades (FRESH / RECENT / STALE / EXPIRED) on all reads
- [ ] Build `BloombergFieldError` error class and `#N/A` handling on all field reads
- [ ] Implement fallback data source chain: Bloomberg → Yahoo Finance → Finnhub
- [ ] Write survivorship bias audit plan — which datasets need audit, priority order
- [ ] Weekly sync: run screening funnel on all 11 pilot tickers, review and validate outputs

---

## WEEK 4 — Wasden Watch RAG — Build
**Goal:** RAG system ingesting Weekenders, generating structured APPROVE / NEUTRAL / VETO verdicts

- [ ] Process all Wasden Weekender PDFs — extract text, identify charts, prepare corpus
- [ ] Submit charts to Claude Vision — generate descriptions, insert into corpus as context
- [ ] Set up ChromaDB vector store — ingest all processed Weekenders as embeddings
- [ ] Implement time-decay weighting (recent Weekenders weighted higher in retrieval)
- [ ] Write Wasden Watch prompt template for verdict generation
- [ ] Build `wasden_watch/verdict_generator.py` — takes ticker + fundamentals, returns verdict JSON
- [ ] Calibrate verdict schema: APPROVE / NEUTRAL / VETO with confidence and mode flag
- [ ] Define "direct coverage" vs. "framework application" mode criteria
- [ ] Implement `WasdenWatchError` with Gemini fallback and `wasden_mode: fallback` flag
- [ ] Implement verdict logging to decision journal (passages cited, confidence, mode, timestamp)
- [ ] Weekly sync: run Wasden Watch on all 11 pilot tickers, review verdicts, recalibrate prompts

---

## WEEK 5 — Quantitative Models — Build
**Goal:** XGBoost, Elastic Net, ARIMA, sentiment model operational. Model agreement metric live.

- [ ] Agree on feature set for quant models before training begins
- [ ] Port `DowSmall1a.Rmd` to Python — validate output matches R version on same input
- [ ] Port `DowLarger1a.Rmd` to Python — validate output matches R version on same input
- [ ] Train XGBoost model (5-day forward return direction) on Emery dataset
- [ ] Train Elastic Net model on Emery dataset
- [ ] Implement ARIMA time-series model
- [ ] Build basic sentiment model (Finnhub scores + NewsAPI)
- [ ] Implement model agreement metric (`std_dev` of all model scores per ticker)
- [ ] Tag all trained models with version manifest per `PROJECT_STANDARDS_v2.md`
- [ ] Finalize `ensemble_method_adr.md` — document 10-agent jury architecture as decision record
- [ ] Weekly sync: review all model outputs on pilot watchlist, agree on HIGH_DISAGREEMENT threshold behavior

---

## WEEK 6 — Agent Debate System — Build
**Goal:** Bull (Claude) vs. Bear (Gemini) debate pipeline live with 10-agent jury resolution

- [ ] Build `debate/bull_researcher.py` — Claude bull case generator
- [ ] Build `debate/bear_researcher.py` — Gemini bear case generator
- [ ] Implement 1–2 rebuttal round logic
- [ ] Write jury agent perspective prompts for all 10 roles: 3 fundamental, 2 macro/sector, 2 risk, 2 technical, 1 Wasden framework
- [ ] Build `jury/jury_spawn.py` — spawns exactly 10 agents with distributed perspective prompts
- [ ] Build `jury/jury_aggregate.py` — collects votes, returns decisive result or escalation flag
- [ ] Implement 5-5 split Signal escalation
- [ ] Define quantitative agreement threshold (what confidence level skips jury?)
- [ ] Log full debate transcript + all jury votes to decision journal
- [ ] Weekly sync: run full debate on 3 tickers, evaluate quality and jury outcomes, recalibrate prompts

---

## WEEK 7 — LangGraph Pipeline Integration
**Goal:** Full decision pipeline end-to-end in LangGraph. Every node connected and logging.

- [ ] Build `StateGraph` with all nodes: `quant_scoring`, `wasden_watch`, `bull_researcher`, `bear_researcher`, `debate`, `jury_spawn`, `jury_aggregate`, `risk_check`, `pre_trade_validation`, `decision`
- [ ] Wire all conditional edges (veto branch, agreement/disagreement, jury path)
- [ ] Enforce pipeline determinism (same input → same output, all random seeds set)
- [ ] Generate `pipeline_run_id` for every run and attach to all journal entries
- [ ] Write acceptance test scenarios for each path: Veto, Agreement, Jury, 5-5 escalation
- [ ] Verify decision journal schema completeness — every node must produce a structured entry
- [ ] Integration test: full pipeline on 10 known tickers, validate all outcomes against expected
- [ ] Weekly sync: run full pipeline end-to-end on pilot watchlist, review all outputs

---

## WEEK 8 — Risk Engine & Alpaca Execution
**Goal:** All 8 risk categories implemented. Pre-trade validation independent. Alpaca paper trading connected.

- [ ] Implement all 8 risk category check functions
- [ ] Implement all named constants in `risk/constants.py`
- [ ] Build regime circuit breaker (SPY -5% rolling 5-day → cut 50% positions, 40% cash, halt entries)
- [ ] Build consecutive loss counter with 7-loss Signal alert + entry pause + await human decision
- [ ] Build pre-trade validation module — FULLY INDEPENDENT from risk check module
- [ ] Connect Alpaca paper trading API
- [ ] Build order management state machine: Submitted → Pending → Filled / Partial / Rejected / Expired
- [ ] Build slippage model for paper trading accuracy
- [ ] Review and confirm all risk constants before implementation
- [ ] Write stress test scenarios for all 5 historical crash periods
- [ ] Design `paper_trading_log.md` structure for tracking P&L vs. SPY from Day 1
- [ ] Weekly sync: run full pipeline including risk and Alpaca paper, confirm all 8 risk checks fire correctly

---

## WEEK 9 — Stress Testing, Calibration & Hardening
**Goal:** All historical backtests complete. Prompts calibrated. Bias monitoring running. System secure.

- [ ] Run backtests: COVID crash (Feb–March 2020), 2022 bear market, regional banking (March 2023)
- [ ] Run Dow Jones historical stress tests — key events: 1929, WWII, 1987, dot-com, 2008
- [ ] Deploy bias monitoring to `monitoring/bias/` — generate weekly report output
- [ ] Review bias monitoring baseline — % VETO vs. APPROVE, quant/Wasden agreement rate, sector concentration
- [ ] Prompt calibration pass — review 20+ Wasden verdicts, adjust until outputs are accurate
- [ ] Run 30-day paper simulation regression test — flag if drawdown increases > 15% relative
- [ ] Implement `ConsecutiveLossAlert` full behavior: pattern analysis, pause, await human response
- [ ] Complete unit test suite: ratio calculations, Bloomberg error handling, risk constants, TRADING_MODE
- [ ] Complete integration test suite: determinism, 10-known-stock verdicts, pre-trade validation
- [ ] Set up MLflow for model versioning and experiment tracking
- [ ] OWASP security review pass
- [ ] Weekly sync: review full stress test results — Go/No-Go decision for Week 10 launch

---

## WEEK 10 — Financial Forge Dashboard & Paper Trading Launch
**Goal:** Dashboard live on Vercel. Paper trading live on Alpaca. System is operable.

- [ ] Build Financial Forge dashboard:
  - Portfolio monitoring (P&L vs. SPY, open positions, win/loss history)
  - Daily recommendation feed with full reasoning and confidence scores
  - Decision journal viewer (filterable by ticker, date, outcome)
  - Debate transcript viewer (full bull vs. bear argument)
  - Jury vote breakdown (all 10 agent votes and reasoning)
  - Override controls (approve / reject / escalate)
  - Consecutive loss warning panel (7-loss alert display)
  - Bias monitoring section (weekly metrics)
- [ ] Connect LangGraph streaming to dashboard for live pipeline view
- [ ] Deploy backend to AWS
- [ ] Confirm Vercel frontend connected to AWS backend
- [ ] Complete `bloomberg_fields.md` — all field codes, known errors, ADR notes, Piotroski workaround
- [ ] Complete `wasden_philosophy.md` — final version, full 5-bucket detail
- [ ] Request pre-June 2022 Weekenders from Wasden directly
- [ ] Set up `paper_trading_log.md` — begin tracking from Day 1
- [ ] LAUNCH: first full day of paper trading
- [ ] Weekly sync: review Day 1 results, confirm system behaving as expected

---

## Post-Week 10 — Paper Trading Phase (Ongoing)

### Ongoing Cadence
| Cadence | Tasks |
|---------|-------|
| Daily | Review recommendation feed, approve/reject, monitor system health and API costs |
| Weekly | Bias monitoring report, performance vs. SPY, prompt review if verdicts drifting |
| Monthly | Full system review in Notion — what's working, model retraining assessment |

### Live Trading Readiness Checklist
Both partners must agree before real money goes in:
- [ ] 60–80% win rate validated across minimum 60 days of paper trading
- [ ] 7-consecutive-loss scenario handled correctly at least once
- [ ] Override conditions agreed in writing by both partners
- [ ] Signal notifications fully operational
- [ ] Maximum initial live capital agreed by both partners
- [ ] Emergency shutdown procedure documented

---

## Future Phases (Not May Scope)

| Feature | Earliest |
|---------|---------|
| Buffett Bot | Phase 3 — Summer 2026 |
| Memory agent (continuous learning) | Phase 3 — Summer 2026 |
| ChromaDB → Supabase pgvector migration | Phase 3 |
| ANM/dHSIC causal analysis | Phase 4 |
| MCP inter-agent communication | Phase 5 |
| Conjoint/Sawtooth decision modeling | Phase 5 |
| Advanced neural architectures | Only if Tier 1–2 prove insufficient |
| Live money | After 60-day paper validation + live readiness checklist |

---

*End of SCHEDULE_v1.md*
*Last Updated: February 23, 2026*
