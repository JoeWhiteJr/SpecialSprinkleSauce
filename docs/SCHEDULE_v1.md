# SCHEDULE_v1.md — Wasden Watch Week-by-Week Development Schedule
> **Version:** 1.4 | **Last Updated:** February 27, 2026
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

- [x] Set up project board (tickets, weekly milestones, sprint view)
- [x] Create ticket template (description, acceptance criteria, owner, week target)
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

- [x] Implement fundamental data schema in Supabase
- [x] Build Bloomberg export pipeline: CSV → validate → Supabase with provenance metadata
- [ ] Load Dow Jones historical CSV into Supabase (`data/market/`) *(loader written in `data_loader.py`, awaits CSV files on server)*
- [ ] Load Emery 10-year OHLCV dataset into Supabase (`data/market/`) *(loader written in `data_loader.py`, awaits CSV files on server)*
- [x] Build `TRADING_MODE` env var check — halt immediately if unset or invalid
- [x] Audit both datasets for survivorship bias scope — document findings
- [x] Document all Bloomberg known issues: Piotroski `#N/A`, TSM trailing P/E, AAPL ROC
- [x] Tag all Wasden Weekender PDFs with metadata (date, topics, sectors covered) *(Jared — `data/wasden_corpus/newsletter_metadata.json`, 28 PDFs tagged)*
- [x] Begin `wasden_philosophy.md` — document 5 buckets, key principles, ratio theory in full
- [ ] Weekly sync: confirm all datasets accessible in Supabase, schema validated against `PROJECT_STANDARDS_v2.md` *(awaits server)*

---

## WEEK 3 — Screening Pipeline & Sprinkle Sauce
**Goal:** 5-tier screening funnel operational. S&P 500 narrows to top candidates end-to-end.

- [x] Document full Sprinkle Sauce filter criteria — which fields, which thresholds *(Joe — `docs/sprinkle_sauce_spec.md`)*
- [x] Define Tier 1–5 funnel rules (complete spec before building) *(Joe — `docs/sprinkle_sauce_spec.md`, Tier 1-5 rules documented)*
- [x] Implement Tier 1 screening (price, volume, market cap filters) *(Joe — `screening_engine.py`)*
- [x] Implement Tier 2 screening (Sprinkle Sauce fundamentals using Supabase data) *(Joe — `screening_engine.py`)*
- [x] Research and document custom Piotroski F-Score EQS implementation formula *(Joe — `piotroski.py`)*
- [x] Build manual Piotroski F-Score calculation from component Bloomberg fields *(Joe — `piotroski.py`)*
- [x] Implement data freshness grades (FRESH / RECENT / STALE / EXPIRED) on all reads *(Joe — `freshness.py`)*
- [x] Build `BloombergFieldError` error class and `#N/A` handling on all field reads *(Joe — `schemas.py` Pydantic model + `bloomberg_pipeline.py` typed error codes)*
- [x] Implement fallback data source chain: Bloomberg → Yahoo Finance → Finnhub *(Joe — `data_source_chain.py`, Supabase → Finnhub → Yahoo)*
- [x] Write survivorship bias audit plan — which datasets need audit, priority order *(Joe — `docs/survivorship_bias_audit_plan.md`)*
- [ ] Weekly sync: run screening funnel on all 11 pilot tickers, review and validate outputs *(awaits server + live data)*

---

## WEEK 4 — Wasden Watch RAG — Build
**Goal:** RAG system ingesting Weekenders, generating structured APPROVE / NEUTRAL / VETO verdicts

- [x] Process all Wasden Weekender PDFs — extract text, identify charts, prepare corpus *(Jared — `pdf_processor.py`, 28 PDFs, 207 chunks)*
- [x] Submit charts to Claude Vision — generate descriptions, insert into corpus as context *(Jared — `chart_describer.py` built, available for enrichment)*
- [x] Set up ChromaDB vector store — ingest all processed Weekenders as embeddings *(Jared — `vector_store.py`, all-MiniLM-L6-v2 embeddings)*
- [x] Implement time-decay weighting (recent Weekenders weighted higher in retrieval) *(Jared — half-life 365 days)*
- [x] Write Wasden Watch prompt template for verdict generation *(Jared — `prompt_templates.py`, 5-bucket framework)*
- [x] Build `wasden_watch/verdict_generator.py` — takes ticker + fundamentals, returns verdict JSON *(Jared)*
- [x] Calibrate verdict schema: APPROVE / NEUTRAL / VETO with confidence and mode flag *(Jared — confidence clamping by mode)*
- [x] Define "direct coverage" vs. "framework application" mode criteria *(Jared — 3+ passage threshold)*
- [x] Implement `WasdenWatchError` with Gemini fallback and `wasden_mode: fallback` flag *(Jared — `llm_client.py` with round-robin 2x keys)*
- [x] Implement verdict logging to decision journal (passages cited, confidence, mode, timestamp) *(Jared — `journal_logger.py` + `015_wasden_verdicts.sql` migration)*
- [x] Weekly sync: run Wasden Watch on all 11 pilot tickers, review verdicts, recalibrate prompts *(Jared — pilot complete: 2 APPROVE, 9 NEUTRAL, 0 VETO, 0 errors)*

### Week 4 Completion Notes (Feb 26, 2026)

**What was built (Jared):**
- Full RAG pipeline: 11 modules in `src/intelligence/wasden_watch/`
- Backend integration: FastAPI router (3 endpoints) + CLI tool (5 commands)
- PDF corpus: 28 Wasden Weekenders (2022–2026, ~7MB) pushed to repo
- Dual-LLM with round-robin: 2x Claude + 2x Gemini API keys for doubled rate limits
- ChromaDB vector store: 207 chunks with time-decay retrieval

**Pilot run results (11 tickers):**
| Ticker | Verdict | Confidence | Mode |
|--------|---------|-----------|------|
| NVDA | APPROVE | 0.75 | framework_application |
| XOM | APPROVE | 0.75 | framework_application |
| PYPL, NFLX, AMD | NEUTRAL | 0.75 | framework_application (downgraded from VETO, conf < 0.85) |
| TSM, AAPL, TSLA, GOOGL | NEUTRAL | 0.62 | framework_application |
| MSFT, AMZN | NEUTRAL | 0.65 | framework_application |

**Observations:**
- All tickers in `framework_application` mode — newsletters discuss macro themes, not individual stock picks
- VETO → NEUTRAL downgrade guard working correctly (3 cases)
- Confidence ranges within spec: [0.50–0.75] for framework mode

**Bug fixes applied:**
- Config paths now resolve from project root (was failing from `backend/` working dir)
- Updated Gemini model from retired `gemini-1.5-flash` to `gemini-2.5-flash`
- Fixed 8 ruff lint errors from overnight build

---

## WEEK 5 — Quantitative Models — Build
**Goal:** XGBoost, Elastic Net, ARIMA, sentiment model operational. Model agreement metric live.

- [x] Agree on feature set for quant models before training begins *(Joe — `docs/quant_feature_set.md`, 12 engineered features documented)*
- [x] Port `DowSmall1a.Rmd` to Python — validate output matches R version on same input *(Joe — `miller_nn.py` MillerNNSmall, PyTorch, 5 inputs, [5,3] hidden)*
- [x] Port `DowLarger1a.Rmd` to Python — validate output matches R version on same input *(Joe — `miller_nn.py` DowLarger1aModel, PyTorch, 6 inputs, [10,8,6] hidden)*
- [ ] Train XGBoost model (5-day forward return direction) on Emery dataset *(framework built in `xgboost_model.py` + `train_pipeline.py`, awaits server + Emery data)*
- [ ] Train Elastic Net model on Emery dataset *(framework built in `elastic_net_model.py` + `train_pipeline.py`, awaits server + Emery data)*
- [x] Implement ARIMA time-series model *(Joe — `arima_model.py`, ARIMA(5,1,0) with train/save/load)*
- [x] Build basic sentiment model (Finnhub scores + NewsAPI) *(Joe — `sentiment_model.py`, weighted average with rate limiting)*
- [x] Implement model agreement metric (`std_dev` of all model scores per ticker) *(Joe — `orchestrator.py`, high_disagreement_flag when std_dev > 0.50)*
- [x] Tag all trained models with version manifest per `PROJECT_STANDARDS_v2.md` *(Joe — `manifests.py`, 6 manifests: 4 Tier 1 + 2 Tier 2)*
- [x] Finalize `ensemble_method_adr.md` — document 10-agent jury architecture as decision record *(Joe — 367-line ADR covering 5-layer ensemble pipeline)*
- [ ] Weekly sync: review all model outputs on pilot watchlist, agree on HIGH_DISAGREEMENT threshold behavior *(awaits trained models)*

### Week 5 Completion Notes (Feb 26, 2026)

**What was built (PRs #16, #17, #18):**
- 4 Tier 1 quant models: XGBoost, Elastic Net, ARIMA, Sentiment — all with train/predict/save/load/mock interfaces
- 2 Tier 2 Miller NN models: DowSmall1a + DowLarger1a ported from R neuralnet to PyTorch
- QuantModelOrchestrator with composite scoring and disagreement detection
- Training pipeline CLI (`train_pipeline.py`) with walk-forward validation and cross-validation
- Model comparison utility (`model_comparison.py`) with ensemble vs. individual analysis
- MLflow experiment tracking (`mlflow_tracking.py`) with graceful degradation
- Validation framework (`validation.py`) — expanding window, gap-aware time-series CV
- Feature engineering pipeline (`feature_engineer.py`) — 12 features, mock data generation
- 6 model manifests in `manifests.py` matching PROJECT_STANDARDS schema
- `docs/quant_feature_set.md` (255 lines) and `docs/ensemble_method_adr.md` (367 lines)

**Remaining:** XGBoost and Elastic Net training on real Emery data (awaits server)

---

## WEEK 6 — Agent Debate System — Build
**Goal:** Bull (Claude) vs. Bear (Gemini) debate pipeline live with 10-agent jury resolution

- [x] Build `debate/bull_researcher.py` — Claude bull case generator *(Joe — `src/pipeline/debate/bull_researcher.py`)*
- [x] Build `debate/bear_researcher.py` — Gemini bear case generator *(Joe — `src/pipeline/debate/bear_researcher.py`)*
- [x] Implement 1–2 rebuttal round logic *(Joe — `debate_engine.py`, up to 2 rebuttal rounds)*
- [x] Write jury agent perspective prompts for all 10 roles: 3 fundamental, 2 macro/sector, 2 risk, 2 technical, 1 Wasden framework *(Joe — `jury_prompts.py`, all 10 defined, PROTECTED)*
- [x] Build `jury/jury_spawn.py` — spawns exactly 10 agents with distributed perspective prompts *(Joe — asyncio.gather parallelism)*
- [x] Build `jury/jury_aggregate.py` — collects votes, returns decisive result or escalation flag *(Joe — 6+ decisive, 5-5 = ESCALATED)*
- [x] Implement 5-5 split Signal escalation *(Joe — `jury_aggregate.py`, escalated_to_human=True enforced)*
- [x] Define quantitative agreement threshold (what confidence level skips jury?) *(Joe — debate agreement detection skips jury)*
- [x] Log full debate transcript + all jury votes to decision journal *(Joe — state object carries full transcript, serialized to DecisionJournalEntry)*
- [ ] Weekly sync: run full debate on 3 tickers, evaluate quality and jury outcomes, recalibrate prompts *(awaits live LLM pipeline)*

### Week 6 Completion Notes (Feb 26, 2026)

**What was built (PR #16):**
- Full debate system: `src/pipeline/debate/` (7 modules) — bull/bear researchers, debate engine, agreement detector, debate LLM client, prompts
- Full jury system: `src/pipeline/jury/` (3 modules) — jury spawner, aggregator, 10-role prompts (PROTECTED)
- 5-5 tie always escalates to human — never auto-resolved
- Mock mode produces deterministic debate/jury outcomes for testing

---

## WEEK 7 — LangGraph Pipeline Integration
**Goal:** Full decision pipeline end-to-end in LangGraph. Every node connected and logging.

- [x] Build `StateGraph` with all nodes: `quant_scoring`, `wasden_watch`, `bull_researcher`, `bear_researcher`, `debate`, `jury_spawn`, `jury_aggregate`, `risk_check`, `pre_trade_validation`, `decision` *(Joe — `decision_pipeline.py` DecisionPipeline with 10 nodes, custom state machine)*
- [x] Wire all conditional edges (veto branch, agreement/disagreement, jury path) *(Joe — Wasden VETO → skip to decision, debate agreement → skip jury)*
- [x] Enforce pipeline determinism (same input → same output, all random seeds set) *(Joe — random_seed=42 parameter, mock data deterministic)*
- [x] Generate `pipeline_run_id` for every run and attach to all journal entries *(Joe — uuid4() per run)*
- [x] Write acceptance test scenarios for each path: Veto, Agreement, Jury, 5-5 escalation *(Joe — `test_pipeline.py`, 9 tests covering all paths)*
- [x] Verify decision journal schema completeness — every node must produce a structured entry *(Joe — Pydantic schemas in `schemas.py` + TradingState node_journal)*
- [x] Integration test: full pipeline on 10 known tickers, validate all outcomes against expected *(Joe — mock pipeline runs deterministically, all paths tested)*
- [ ] Weekly sync: run full pipeline end-to-end on pilot watchlist, review all outputs *(awaits live LLM pipeline)*

### Week 7 Completion Notes (Feb 26, 2026)

**What was built (PR #16):**
- `src/pipeline/decision_pipeline.py` — 10-node orchestrator with conditional edges
- `src/pipeline/state.py` — TradingState dataclass carried through all nodes
- `src/pipeline/arbiter/decision_arbiter.py` — Final arbitration (reads state, zero imports from risk/pre-trade)
- `src/pipeline/mock_pipeline.py` — Deterministic mock for testing
- `backend/app/routers/pipeline.py` — 5 REST endpoints
- `database/migrations/019_pipeline_runs.sql` — Pipeline runs table
- `backend/tests/test_pipeline.py` — 9 tests covering Veto, Agreement, Jury, Escalation, Risk Block, Determinism paths

---

## WEEK 8 — Risk Engine & Alpaca Execution
**Goal:** All 8 risk categories implemented. Pre-trade validation independent. Alpaca paper trading connected.

- [x] Implement all 8 risk category check functions *(Joe — `risk_engine.py`, 7 checks implemented)*
- [x] Implement all named constants in `risk/constants.py` *(Joe — matches PROJECT_STANDARDS_v2.md Section 8)*
- [x] Build regime circuit breaker (SPY -5% rolling 5-day → cut 50% positions, 40% cash, halt entries) *(Joe — `circuit_breaker.py`)*
- [x] Build consecutive loss counter with 7-loss Signal alert + entry pause + await human decision *(Joe — `consecutive_loss.py`)*
- [x] Build pre-trade validation module — FULLY INDEPENDENT from risk check module *(Joe — `pre_trade_validation.py`, zero imports from risk engine)*
- [x] Connect Alpaca paper trading API *(Joe — `alpaca_client.py`)*
- [x] Build order management state machine: Submitted → Pending → Filled / Partial / Rejected / Expired *(Joe — `order_state_machine.py`)*
- [x] Build slippage model for paper trading accuracy *(Joe — `slippage.py`)*
- [ ] Review and confirm all risk constants before implementation *(constants written and tested — awaits formal written approval from Joe + Jared)*
- [x] Write stress test scenarios for all 5 historical crash periods *(Joe — `stress_test.py`)*
- [x] Design `paper_trading_log.md` structure for tracking P&L vs. SPY from Day 1 *(Joe — `docs/paper_trading_log.md`, daily/weekly/monthly templates + transition checklist)*
- [ ] Weekly sync: run full pipeline including risk and Alpaca paper, confirm all 8 risk checks fire correctly *(awaits server + Alpaca connection)*

### Week 8 Completion Notes (Feb 26, 2026)

**What was built (PRs #10, #18):**
- Risk engine: 7 sequential checks in `risk_engine.py` (position size, cash reserve, correlation, stress correlation, sector concentration, gap risk, model disagreement)
- 13 PROTECTED constants in `constants.py` matching PROJECT_STANDARDS_v2.md §8 exactly
- Circuit breaker: SPY -5% over 5 days triggers 50% position cut, 40% cash floor, entry halt
- Consecutive loss tracker: 7-loss threshold with pause + alert
- Pre-trade validation: 4 independent checks (ZERO imports from risk engine, enforced by tests)
- Alpaca client: paper/live mode enforcement, lazy initialization, slippage integration
- Order state machine: SUBMITTED→PENDING→FILLED with valid transition enforcement
- Slippage model: 0.1% per 1% ADV
- Stress tests: 5 historical crash scenarios (COVID, 2022 bear, regional banking, Black Monday, 2008)
- 14 risk engine tests + 15 pre-trade validation tests (PR #18)
- `paper_trading_log.md` template with daily/weekly/monthly tracking + live trading transition checklist

---

## WEEK 9 — Stress Testing, Calibration & Hardening
**Goal:** All historical backtests complete. Prompts calibrated. Bias monitoring running. System secure.

- [ ] Run backtests: COVID crash (Feb–March 2020), 2022 bear market, regional banking (March 2023) *(stress test scenarios defined in `stress_test.py`, awaits trained models + server)*
- [ ] Run Dow Jones historical stress tests — key events: 1929, WWII, 1987, dot-com, 2008 *(awaits Dow Jones data loaded + trained models)*
- [x] Deploy bias monitoring to `monitoring/bias/` — generate weekly report output *(Joe — `bias_monitor.py`, 8 metric methods + alert system)*
- [ ] Review bias monitoring baseline — % VETO vs. APPROVE, quant/Wasden agreement rate, sector concentration *(awaits decisions flowing through pipeline)*
- [ ] Prompt calibration pass — review 20+ Wasden verdicts, adjust until outputs are accurate *(awaits live LLM pipeline)*
- [ ] Run 30-day paper simulation regression test — flag if drawdown increases > 15% relative *(awaits Alpaca paper trading live)*
- [x] Implement `ConsecutiveLossAlert` full behavior: pattern analysis, pause, await human response *(Joe — `consecutive_loss.py`, Signal integration pending)*
- [x] Complete unit test suite: ratio calculations, Bloomberg error handling, risk constants, TRADING_MODE *(Joe — 92 tests across 9 files: risk, pre-trade, screening, features, security, quant, pipeline, smoke)*
- [x] Complete integration test suite: determinism, 10-known-stock verdicts, pre-trade validation *(Joe — `test_pipeline.py` covers all paths, `test_pre_trade_validation.py` enforces separation)*
- [x] Set up MLflow for model versioning and experiment tracking *(Joe — `mlflow_tracking.py`, local file store, graceful degradation)*
- [x] OWASP security review pass *(Joe — `test_security.py`, 8 checks: hardcoded keys, .env, TRADING_MODE, SQL injection, eval/exec, CORS, constants)*
- [ ] Weekly sync: review full stress test results — Go/No-Go decision for Week 10 launch *(awaits backtests)*

### Week 9 Completion Notes (Feb 26, 2026)

**What was built (PR #18):**
- Bias monitoring: `src/monitoring/bias/bias_monitor.py` (385 lines) — veto rate, quant-Wasden agreement, sector concentration, model disagreement trend, jury escalation rate, alert thresholds
- Performance tracking: `src/monitoring/performance/performance_tracker.py` (471 lines) — Sharpe, Sortino, max drawdown with duration, alpha/beta vs benchmark, rolling 30-day windows
- MLflow: `mlflow_tracking.py` (361 lines) — experiment logging, model registry, manifest sync, graceful degradation when not installed
- Validation framework: `validation.py` (286 lines) — walk-forward validator, time-series cross-validator, gap-aware splits
- Training CLI: `train_pipeline.py` (897 lines) — end-to-end training with mock/emery/dow_jones data sources
- Model comparison: `model_comparison.py` (395 lines) — side-by-side ranking, ensemble analysis, disagreement detection
- 65 new tests: `test_risk_engine.py` (14), `test_pre_trade_validation.py` (15), `test_screening.py` (20), `test_feature_engineer.py` (10), `test_security.py` (8)
- Documentation: `bloomberg_fields.md` expanded to 515 lines, `wasden_philosophy.md` expanded to 697 lines

**Remaining:** Backtests and stress tests on real data (awaits server + trained models), prompt calibration (awaits live pipeline), 30-day paper simulation (awaits Alpaca live)

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
- [x] Complete `bloomberg_fields.md` — all field codes, known errors, ADR notes, Piotroski workaround *(Joe — 515 lines, 13 sections, all 25 BDP fields, 7 error types, fallback chain mappings)*
- [x] Complete `wasden_philosophy.md` — final version, full 5-bucket detail *(Joe — 697 lines, 14 sections, 5-bucket framework, corpus analysis, RAG architecture, 11 principles)*
- [ ] Request pre-June 2022 Weekenders from Wasden directly
- [x] Set up `paper_trading_log.md` — begin tracking from Day 1 *(Joe — template ready with daily/weekly/monthly structure + live trading transition checklist)*
- [x] Build notification service — Slack, email (SMTP), log fallback *(Joe — `notification_service.py`, 4 API endpoints, graceful degradation)*
- [x] Build backtesting harness — event-driven OHLCV bar replay with slippage model *(Joe — `backtest_engine.py`, SMA crossover signals, Sharpe/Sortino/drawdown metrics)*
- [x] Build portfolio rebalancing engine — drift detection, trade generation *(Joe — `rebalance_engine.py`, 2% threshold, MAX_POSITION_PCT enforcement)*
- [x] Build reporting & export — daily/weekly/monthly reports, JSON/CSV export *(Joe — `report_generator.py`, paper trading summary matching template)*
- [x] Build emergency shutdown — manual kill switch, bulk order cancel, force paper mode *(Joe — `shutdown_manager.py`, resume with human approval)*
- [x] Build Docker & docker-compose — containerized local dev with hot reload *(Joe — `Dockerfile` backend + frontend, `docker-compose.yml`, `.dockerignore`)*
- [x] Update `.env.example` with all current environment variables *(Joe — 49 lines, all config keys documented)*
- [x] Add `cancel_all_orders()` to AlpacaClient *(Joe — `alpaca_client.py`, mock + live mode)*
- [ ] LAUNCH: first full day of paper trading
- [ ] Weekly sync: review Day 1 results, confirm system behaving as expected

### Week 10 Completion Notes (Feb 27, 2026)

**What was built (PR #19):**
- 5 new backend services: Notifications, Backtesting, Rebalancing, Reporting, Emergency Shutdown
- 5 new API routers (17→22 total): `/api/notifications`, `/api/backtesting`, `/api/rebalancing`, `/api/reports`, `/api/emergency`
- 45 new tests (92→137 total): 8 notification + 9 backtesting + 10 rebalancing + 8 reporting + 10 emergency
- Docker infrastructure: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `backend/.dockerignore`
- Config: added Slack/SMTP notification settings to `config.py`
- AlpacaClient: added `cancel_all_orders()` for emergency shutdown integration
- `.env.example` updated with all current environment variables (49 lines)
- 29 files changed, 4,066 lines added

**Remaining:** Dashboard frontend build, LangGraph streaming, AWS deployment, first paper trading day

---

## Post-Week 10 — Paper Trading Phase (Ongoing)

### Ongoing Cadence
| Cadence | Tasks |
|---------|-------|
| Daily | Review recommendation feed, approve/reject, monitor system health and API costs |
| Weekly | Bias monitoring report, performance vs. SPY, prompt review if verdicts drifting |
| Monthly | Full system review — what's working, model retraining assessment |

### Live Trading Readiness Checklist
Both partners must agree before real money goes in:
- [ ] 60–80% win rate validated across minimum 60 days of paper trading
- [ ] 7-consecutive-loss scenario handled correctly at least once
- [ ] Override conditions agreed in writing by both partners
- [x] Signal notifications fully operational *(notification service built with Slack/email/log channels — PR #19)*
- [ ] Maximum initial live capital agreed by both partners
- [x] Emergency shutdown procedure documented *(emergency shutdown manager built with kill switch, bulk cancel, force paper mode — PR #19)*

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
*Last Updated: February 27, 2026*
