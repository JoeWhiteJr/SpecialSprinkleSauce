# Wasden Watch — Launch Checklist

> Path from "code complete" to "making live trades." 42 tasks across 9 phases.
> Created: 2026-05-11. Tracks the local-machine build (server is parked indefinitely).
> Tick items as you go. The numbered IDs match the in-session task list.

---

## Phase 1 — API keys & environment (#1–#6)

- [ ] **#1** Create local `.env` from `.env.example`
  - Set `TRADING_MODE=paper`, `USE_MOCK_DATA=true` (flip to false once data loads), `API_KEY=<any-strong-random-string>`
  - Never commit `.env`

- [ ] **#2** Get Claude API key → `CLAUDE_API_KEY` in `.env`
  - https://console.anthropic.com
  - Used by: Wasden Watch RAG, bull researcher, jury agents
  - Code supports dual-key round-robin (doubles rate limits)

- [ ] **#3** Get Gemini API key → `GEMINI_API_KEY` in `.env`
  - https://aistudio.google.com/apikey
  - Used by: bear researcher, jury co-runner, Claude fallback

- [ ] **#4** Get Alpaca paper trading keys → `ALPACA_PAPER_API_KEY` + `ALPACA_PAPER_SECRET_KEY`
  - https://alpaca.markets (Paper trading only — NOT live yet)
  - Live keys (`ALPACA_LIVE_*`) stay empty until task #41

- [ ] **#5** Get Finnhub + NewsAPI keys
  - Finnhub: https://finnhub.io/register (free tier OK) → `FINNHUB_API_KEY`
  - NewsAPI: https://newsapi.org/register (free tier OK) → `NEWSAPI_KEY`

- [ ] **#6** Verify Supabase project is still alive
  - URL is in `docs/PARTNER_SYNC.md`
  - Free tier pauses after 7 days inactivity — un-pause if needed
  - Grab `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` into `.env`
  - Verify migrations 001–028 are applied via the SQL Editor

---

## Phase 2 — Boot it (#7–#8)

- [ ] **#7** Boot backend locally
  - `make dev-backend` (uses `backend/venv/`)
  - Hit `/api/health` — should return 200
  - Run `make test-backend` — all 154 tests should pass

- [ ] **#8** Boot frontend + verify it talks to local backend
  - `cd frontend && npm install && npm run dev`
  - Visit http://localhost:3000
  - All 18 sidebar pages should load
  - Network tab: requests go to localhost:8000 with `X-API-Key` header

---

## Phase 3 — Data ingestion (#9–#13)

- [ ] **#9** Write Emery minute → daily resampler
  - Walk `Historical Data/Emery 5 Year/**/*.csv.gz` (1,256 files, 23 GB)
  - Aggregate each ticker-day minute bars into one daily OHLCV row
  - Open = first regular-session bar (09:30 ET), close = last (16:00 ET), high/low across session, volume = sum
  - Write to `data/market/emery_daily.parquet`
  - Tag every row `survivorship_bias_unaudited=true`

- [ ] **#10** Load Emery daily into Supabase `price_history`
  - Use `backend/app/services/data_loader.py`
  - Batched inserts (~5k rows/chunk)
  - Migration 014 + 014b (RLS) already applied

- [ ] **#11** Load Dow Jones 1928–2009 into Supabase
  - Read `Historical Data/Dow Jones/dowjones1 data.xlsx` (20,205 rows)
  - Insert as `instrument='DJIA'` in price_history (or new `dow_jones_daily` table)
  - Used by: Miller NN training, historical stress tests

- [ ] **#12** Build Bloomberg workbook → Supabase ingestion
  - Read `JMWFM_Bloomberg_Data_Pulling.xlsx`, sheets `Pull` + historical snapshots
  - Write all 51 BDP fields to `bloomberg_fundamentals` (migration 011)
  - Typed errors for `#N/A`/`#VALUE!`/`#NAME?`
  - Apply freshness grades (FRESH/RECENT/STALE/EXPIRED)
  - **NEVER read the Fundamentals sheet — only `Values`**

- [ ] **#13** Survivorship bias audit on Emery
  - Cross-reference 9,250 tickers/day against known-delisted list (SVB, Bed Bath & Beyond, Lehman, etc.)
  - If absent → keep `survivorship_bias_unaudited=true` on all models
  - If present → flip to `audited=true`, unblock live-decision path

---

## Phase 4 — Train the models (#14–#19)

- [ ] **#14** Train XGBoost on Emery daily (5-day forward return direction)
  - `python -m backend.app.cli.train_pipeline --model=xgboost --data=emery`
  - Walk-forward CV, gap-aware time-series splits
  - Holdout = last 90 days
  - Generate model manifest, log to MLflow, save to `models/checkpoints/`

- [ ] **#15** Train Elastic Net on Emery daily
  - Same flow as #14, `--model=elastic_net`
  - Second quant signal

- [ ] **#16** Train ARIMA on Emery daily
  - `arima_model.py` is built (ARIMA(5,1,0))
  - Save fitted model + manifest

- [ ] **#17** Calibrate Sentiment model against Finnhub + NewsAPI
  - Run on 11 pilot tickers
  - Tune weighted-average formula if scores look off

- [ ] **#18** Train Miller NNs (Small + Larger) on Dow Jones
  - PyTorch ports already exist in `miller_nn.py`
  - Validate output matches R neuralnet reference on same input
  - Tier 2 — not in Phase 1 ensemble until validated

- [ ] **#19** 90-day holdout validation for every trained model
  - Required by PROJECT_STANDARDS §2 before any live use
  - Record accuracy / Sharpe / max drawdown / win rate in each manifest
  - Both partners must review before going live

---

## Phase 5 — Wasden Watch (intelligence) (#20–#22)

- [ ] **#20** Verify ChromaDB has 207 Wasden chunks loaded
  - Per Week 4 notes: 28 PDFs → 207 chunks, all-MiniLM-L6-v2, half-life 365d
  - Check the persist dir (ChromaDB is local file storage)
  - If wiped, re-run ingestion CLI from `wasden_watch/`

- [ ] **#21** Run Claude Vision on Wasden chart pages
  - `chart_describer.py` is built but unused
  - Extract images from 28 PDFs → Claude Vision → re-ingest descriptions as enrichment chunks
  - One-time cost ~$1–5

- [ ] **#22** Calibrate Wasden Watch prompts on real watchlist
  - Run `verdict_generator` on Sprinkle Sauce watchlist (43 tickers, from Bloomberg `Details` sheet)
  - Pilot was: 2 APPROVE / 9 NEUTRAL / 0 VETO on 11 tickers
  - Review 20+ verdicts — confidence, mode, reasoning quality
  - **Prompt templates are PROTECTED** — changes require both partners' written approval

---

## Phase 6 — Pipeline live (#23–#25)

- [ ] **#23** Run live bull/bear debate on 3+ tickers
  - Verify: bull (Claude), bear (Gemini), 1–2 rebuttals, agreement_detector classifies right
  - Inspect transcripts

- [ ] **#24** Run live 10-agent jury on a disagreement case
  - Force disagreement or pick a divisive ticker
  - `jury_spawn` fires 10 agents in parallel (asyncio.gather)
  - 3 fundamentals + 2 macro + 2 risk + 2 technical + 1 Wasden
  - 6+ in one direction = decisive; 5-5 = `escalated_to_human=True`
  - **Jury prompts are PROTECTED**

- [ ] **#25** Run full 10-node pipeline E2E on 11 pilot tickers
  - Every node logs to decision journal
  - `pipeline_run_id` unique per run
  - Exercise all 4 paths: Wasden VETO short-circuit / debate agreement / jury decisive / 5-5 ESCALATED

---

## Phase 7 — Trade safety (#26–#30)

- [ ] **#26** Verify Alpaca paper connection + test order
  - Place a single $100 SPY paper buy via execution router
  - `order_state_machine` flows SUBMITTED → PENDING → FILLED
  - Confirm position visible in Alpaca dashboard, then close it

- [ ] **#27** Verify all 7 risk checks fire on real data
  - Force each fail at least once: position size > 12%, cash < 10%, correlation > 0.70, stress correlation > 0.80, sector concentration, gap risk, model disagreement > 0.50
  - Each should block + log
  - Confirm pre-trade validation runs **separately** (test_pre_trade_validation.py enforces zero imports from risk_engine)

- [ ] **#28** Verify regime circuit breaker + consecutive-loss tracker
  - Simulate SPY −5% over 5-day window → 50% position cut, 40% cash, halt entries, alert
  - Simulate 7 consecutive losses → pause entries, alert, await human decision

- [ ] **#29** Set up Signal notification channel
  - Google Voice number already set up (Week 1 ✅)
  - Wire `signal-cli` or signal-bot into `notification_service.py`
  - Test: trigger 5-5 escalation → Signal message arrives within 60s

- [ ] **#30** Flip frontend off mock data + walk all 18 pages
  - Set `USE_MOCK_DATA=false`
  - Pages: portfolio, recommendations, journal, debates, jury, overrides, alerts, bias, screening, settings, pipeline, emergency, backtesting, notifications, rebalancing, reports, training, goals
  - SSE pages (pipeline, goals) should show live updates

---

## Phase 8 — Validate (#31–#34)

- [ ] **#31** Historical stress tests (COVID, 2022 bear, 2023 banking)
  - `stress_test.py` defines 5 scenarios
  - Run `backtest_engine` over each, output equity curve / max DD / Sharpe per scenario

- [ ] **#32** Dow Jones long-history stress tests
  - 1929 crash, WWII, Black Monday 1987, dot-com 2000–02, 2008 GFC
  - Pure price-action test (no fundamentals available for these eras)

- [ ] **#33** Run 30-day paper-trading regression
  - Full pipeline over the last 30 days of paper conditions
  - If max drawdown increases >15% vs baseline → human review before merging
  - Standing regression gate after any intelligence/pipeline/risk module change

- [ ] **#34** Establish baseline bias-monitoring metrics
  - After ~50 pipeline runs, `bias_monitor.py` produces baselines for: veto rate, quant-Wasden agreement, sector concentration, model disagreement trend, jury escalation rate
  - These become the weekly bias monitoring report

---

## Phase 9 — Launch (#35–#42)

- [ ] **#35** Write `personal_trading_rules.md` (both partners)
  - Required by PROJECT_STANDARDS §10 before live capital
  - Cover: max position size, override conditions, manual halt triggers, sell discipline, cash floor, max sector exposure
  - Signed, committed

- [ ] **#36** Decide N for consecutive-loss threshold (both partners)
  - Default = 7. Confirm or update.
  - Encode in `risk/constants.py` as `MAX_CONSECUTIVE_LOSSES`
  - Constants change requires the constants-approval flow

- [ ] **#37** 🚀 **First day of paper trading**
  - Enable daily cron
  - Screening funnel runs (S&P 500 → ~8 candidates)
  - Pipeline produces recommendations
  - Every recommendation needs human Signal approval before Alpaca executes
  - Start tracking in `paper_trading_log.md`
  - Initial paper capital: $100k

- [ ] **#38** Set up daily/weekly/monthly review cadence
  - DAILY: review feed, approve/reject, monitor health + API costs
  - WEEKLY: bias monitoring report, P&L vs SPY, prompt drift review
  - MONTHLY: full system review, model retraining assessment

- [ ] **#39** Validate 60–80% win rate over 60+ paper days
  - Live-trading readiness gate
  - If under 60%, calibrate prompts/models/risk, extend paper period

- [ ] **#40** Emergency shutdown drill
  - Trigger kill switch → all orders cancelled, `TRADING_MODE` forced to paper, emergency_events row inserted, both partners notified
  - Then resume with human approval flow
  - **Confirm before any live money**

- [ ] **#41** Get Alpaca LIVE keys + test in paper mode first
  - `ALPACA_LIVE_API_KEY` + `ALPACA_LIVE_SECRET_KEY`
  - Both partners sign off on max starting live capital BEFORE flipping
  - **Capital starts small**

- [ ] **#42** 🟢 **Flip TRADING_MODE=live** (both partners, written approval)
  - **Final gate.** All checklist items in PROJECT_STANDARDS §7 must be green.
  - Then change one env var. System enforces the rest.

---

## Phase 10 — Security & quality scaffolding (#43–#50)

> Hardening that must land BEFORE feature work resumes. Closes the 6 maintainability gaps from the May-11 audit.

- [x] **#1 (done)** Create local `.env` from `.env.example`
- [ ] **#43** Install pre-commit framework + Layer-1 hooks (gitleaks, ruff, hygiene, lint-staged)
- [ ] **#44** Write `docs/SECURITY_RUNBOOK.md` (secret-rotation procedures per key class)
- [ ] **#45** Add dependency-vulnerability gate to CI (pip-audit + npm audit)
- [ ] **#46** Audit Supabase RLS on sensitive tables (decision_journal, orders, positions, veto_overrides)
- [ ] **#47** Add gitleaks secret-scan job to CI (Layer 2 defense-in-depth)
- [ ] **#48** Add coverage thresholds (pytest `--cov-fail-under=60`, vitest `--coverage`)
- [ ] **#49** Configure branch protection on `main` (require CI + review, block force-push, block direct commits)
- [ ] **#50** Align CI Python version to 3.12 (matches local venv)

- [ ] **#51** Port pipeline code to LangGraph 1.x and bump deps (DEADLINE 2026-05-25)
  - Surfaced by PR #36 dep-vuln triage. langgraph 0.2 → 1.0.10 clears CVE-2026-28277, but the move requires API edits.
  - Cluster bumps in one go: `langgraph` 0.2.0 → 1.0.10, `langchain-core` 0.2.43 → 1.3.3, `langgraph-checkpoint` 1.0.12 → 4.0.0, `langsmith` 0.1.147 → 0.7.31.
  - Step plan:
    1. Read upstream LangGraph 1.x migration guide
    2. Bump the 4 pins in `backend/requirements.txt`
    3. Update `src/pipeline/decision_pipeline.py` to use the new `StateGraph` + node signatures
    4. Update `src/pipeline/streaming_pipeline.py` (depends on decision_pipeline)
    5. Confirm all 9 tests in `backend/tests/test_pipeline.py` still pass
    6. Confirm all 4 tests in `backend/tests/test_pipeline_stream.py` still pass
    7. Manually verify all 4 pipeline paths behave identically: Wasden VETO short-circuit / debate agreement (skip jury) / debate disagreement → jury decisive / 5-5 ESCALATED
    8. Remove the 10 Category D CVE entries from `.github/pip-audit-allowlist.txt`
  - Single dedicated PR. **NEVER** lump with other unrelated changes.
  - If 2026-05-25 arrives without this PR landing, re-triage: extend the deadline with a written reason in `docs/SECURITY_DEP_TRIAGE.md`, OR start the port immediately.

---

## Critical-path dependencies

- Nothing trains (#14–18) until data loads (#9–12)
- Nothing trades (#26+) until Alpaca keys (#4) + risk verified (#27–28)
- Nothing goes live (#42) until 60-day paper validation (#39) + emergency drill (#40) + both partners sign off

## What can run in parallel right now

Without any user input I can do: **#1**, **#7**, **#8**, **#9**.
Keys (#2–#6) can be acquired by you while I work on resampling.

---

*Living document. Update as items complete or new blockers appear.*
