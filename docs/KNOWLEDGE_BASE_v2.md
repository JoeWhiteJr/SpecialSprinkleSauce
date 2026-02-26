# Wasden Watch — Project Knowledge Base
> **Version:** 2.0 | **Last Updated:** February 23, 2026
> **Purpose:** Complete institutional memory of the Wasden Watch trading system. Every AI agent, developer, and contributor reads this before touching anything. Nothing is summarized out of existence.

---

## Table of Contents

1. [Project Vision & Goals](#1-project-vision--goals)
2. [System Architecture & Decision Pipeline](#2-system-architecture--decision-pipeline)
3. [Intelligence Layer 1 — The Wasden Watch RAG](#3-intelligence-layer-1--the-wasden-watch-rag)
4. [Intelligence Layer 2 — The Buffett Bot](#4-intelligence-layer-2--the-buffett-bot)
5. [Intelligence Layer 3 — Quantitative & Statistical Models](#5-intelligence-layer-3--quantitative--statistical-models)
6. [The 10-Agent Jury Ensemble System](#6-the-10-agent-jury-ensemble-system)
7. [Cary Wasden's Investment Philosophy](#7-cary-wasdens-investment-philosophy)
8. [Wasden's 5-Bucket Analysis Framework](#8-wasdens-5-bucket-analysis-framework)
9. [Fundamental Analysis Reference](#9-fundamental-analysis-reference)
10. [Technical Analysis Reference](#10-technical-analysis-reference)
11. [Agent Debate Pattern — Bull vs. Bear](#11-agent-debate-pattern--bull-vs-bear)
12. [Memory Agent & Continuous Learning](#12-memory-agent--continuous-learning)
13. [Risk Management Framework](#13-risk-management-framework)
14. [Bias Protection System](#14-bias-protection-system)
15. [API & Data Ecosystem](#15-api--data-ecosystem)
16. [Data Assets Inventory](#16-data-assets-inventory)
17. [Neural Network Models — Dr. Miller's Framework](#17-neural-network-models--dr-millers-framework)
18. [Bloomberg Terminal Reference](#18-bloomberg-terminal-reference)
19. [Bloomberg Fundamental Data — Feb 21, 2026 Snapshot](#19-bloomberg-fundamental-data--feb-21-2026-snapshot)
20. [Stock Universe & Screening Funnel](#20-stock-universe--screening-funnel)
21. [MCP / LangGraph Orchestration](#21-mcp--langgraph-orchestration)
22. [Dashboard & Financial Forge Interface](#22-dashboard--financial-forge-interface)
23. [Wyatt's Behavioral Environment Framework](#23-wyatts-behavioral-environment-framework)
24. [Causal Analysis & Noise Modeling](#24-causal-analysis--noise-modeling)
25. [Day Trading Notes (Jeff Singer Method)](#25-day-trading-notes-jeff-singer-method)
26. [Market Observations & Macro Notes](#26-market-observations--macro-notes)
27. [Stock Debates — Documented Sessions](#27-stock-debates--documented-sessions)
28. [Wasden Meeting Transcript — Emery Session](#28-wasden-meeting-transcript--emery-session)
29. [Design Decisions Log](#29-design-decisions-log)
30. [Critical Problems & Resolutions](#30-critical-problems--resolutions)
31. [Development Phases & Schedule](#31-development-phases--schedule)
32. [Team Structure](#32-team-structure)
33. [Infrastructure & Tooling](#33-infrastructure--tooling)
34. [Feedback from Collaborators](#34-feedback-from-collaborators)
35. [Joe's Goals & Vision](#35-joes-goals--vision)
36. [Cary Wasden's Life Wisdom](#36-cary-wasdens-life-wisdom)
37. [Book Recommendations & Reading List](#37-book-recommendations--reading-list)
38. [People & References](#38-people--references)
39. [Stocks & Tickers to Watch](#39-stocks--tickers-to-watch)
40. [Miscellaneous Ideas & Loose Notes](#40-miscellaneous-ideas--loose-notes)
41. [Open Questions & Things to Investigate](#41-open-questions--things-to-investigate)

---

## 1. Project Vision & Goals

### What We're Building
An automated trading system that blends Wasden's qualitative investment wisdom with quantitative models, orchestrated by AI agents, with human oversight. More than a trading bot — it functions as a full portfolio manager that researches, debates, debates again with a jury of agents, decides, and learns.

**Working Names:** "Wasden's Weekender" / "The Wasden Watch" / "Wasden Watch"

**Repository:** https://github.com/JoeWhiteJr/Financial_Forge
**Live Site:** https://financial-forge.vercel.app

### Core Philosophy
The system is anchored in Cary Wasden's investment methodology. Wasden was the #1 financial analyst in the US, created the 5-bucket framework for Sir John Templeton personally, and has been managing large institutional and private wealth since 1996. His approach is fundamentals-driven, ratio-based, and long-term thinking applied with disciplined entry/exit rules. The system tries to codify how Wasden thinks, not just what he said.

> *"The numbers tell stories."* — Cary Wasden
> *"Markets can remain irrational longer than you can remain liquid."* — Cary Wasden

### Primary Performance Target
**40% return weekly.** Both partners agree. This is the target.

Secondary metrics:
- 60–80% accuracy (win rate) on backtesting before going live
- Real money makes money 60–80% of the time
- Keep losses less than wins

### Definition of "Operable"
The system is operable when:
1. Sufficient backtesting has been completed
2. Win rate is validated at 60–80% on historical data
3. System is generating paper trade recommendations with full reasoning
4. Human approves every trade before execution

### Drawdown / Shutdown Rules
- **Warning trigger:** 7 consecutive losses during paper OR live trading — system must explain what it's doing, why, and suggest a possible shutdown
- **Hard shutdown trigger:** Human decision after 7-loss warning is triggered — system flags, notifies via Signal, and waits for human response
- **Capital cycling:** Once capital doubles in live trading, pull out and reallocate. Cycle the doubling.

### Autonomy Progression
Start as recommendation engine → paper trade validation → 60–80% win rate confirmed → live money → when capital doubles, reallocate.

---

## 2. System Architecture & Decision Pipeline

### Full Decision Flow
```
Quant scores → Wasden Watch →
  BULL CASE (Claude): "Here's why this trade should proceed..."
  BEAR CASE (Gemini): "Here's why this trade should NOT proceed..."
  → DEBATE (1–2 rounds of rebuttal) →
  → [IF DISAGREEMENT] → 10-AGENT JURY VOTE →
  → Risk filtering → Pre-trade validation → Decision
```

### Voting Power Hierarchy
1. **Wasden Watch** — highest authority, veto power over any trade
2. **10-Agent Jury** — resolves Bull/Bear disagreement (aggregate vote wins)
3. **Quant/Statistical models** — feeds the debate, informs agents
4. **Buffett Bot** — advisory only, no vote

### Key Rules
- Wasden has veto power over any trade. Period.
- If contrarian argues convincingly against Wasden's veto: Flag for human review — Jared decides manually.
- Escalation threshold: if bull case confidence ≥ 0.80 after jury vote, escalate to human via Signal.
- Buffett Bot does NOT sway voting — advisory section only.
- When jury is inconclusive: human decides.

### LangGraph State Object
```python
class TradingState(TypedDict):
    ticker: str
    quant_scores: dict
    wasden_verdict: dict
    bull_case: str
    bear_case: str
    debate_result: dict
    jury_votes: list[dict]      # 10 agent votes with reasoning
    jury_decision: dict          # aggregate result
    risk_check: dict
    final_decision: dict
```

### Pipeline Nodes (LangGraph)
```
quant_scoring
  → wasden_watch
    → [VETO] → decision (blocked)
    → [continue] → bull_researcher (Claude)
                 → bear_researcher (Gemini)
                 → debate
                   → [AGREEMENT] → risk_check
                   → [DISAGREEMENT] → jury_spawn (10 agents)
                                    → jury_aggregate
                                    → risk_check
                 → pre_trade_validation
                 → decision
```

---

## 3. Intelligence Layer 1 — The Wasden Watch RAG

### About Cary Wasden
Wasden founded Caspian Securities in 1996, managing money for large institutional clients including Sir John Templeton (founder of Templeton Funds). In 2006, Templeton personally invited Wasden to manage his private wealth directly. Wasden would travel to Nassau, Bahamas regularly. The 5-bucket system was created specifically for Templeton to systematize money management. Wasden is considered one of the top financial analysts in the US, particularly dominant in energy.

### About the Weekenders
Cary releases a weekly newsletter called "The Weekender." We have approximately 30 PDFs covering June 2022 onward. Format: native text (can select/copy text), 4–12 pages each, charts and images included. Permission to use confirmed.

**Status:** Videos of earlier sessions exist but extraction is harder — have not yet asked Wasden for pre-June 2022 weekenders directly. This is a pending action item.

### What the Weekenders Cover
- Mix of broad market (macro, Fed, cross-sector) and specific sectors
- Heavy emphasis on energy sector (Wasden was #1 in energy)
- Talks extensively about news, politics, geopolitics
- Charts with Wasden's commentary referencing visual data

### Chart/Image Processing Challenge
When Wasden writes "as you can see from the chart below, the yield curve has inverted" — text extraction gets the sentence but the chart disappears. The RAG will have references to visual evidence it can't see.

**Solution:** Use Claude Vision to describe charts. Extract images from PDFs → send to Claude Vision → auto-generate descriptions → insert into corpus. One-time cost per PDF.

### RAG Architecture
- **Storage:** ChromaDB (Phase 1) → migrate to Supabase pgvector (Phase 3)
- **Retrieval:** Time-decay weighting (more recent Weekenders weighted higher)
- **Verdict output:** APPROVE / NEUTRAL / VETO + confidence + reasoning + mode flag

### Two Operating Modes
- **Direct Coverage Mode:** Wasden explicitly discussed this sector/stock. High confidence.
- **Framework Application Mode:** Applying Wasden's ratios, principles, and methodology to stocks he hasn't directly covered. Lower confidence — must be flagged in output.

### Critical Limitation: Single Regime Risk
The RAG is built on ~30 PDFs from a specific regime: post-COVID inflation, aggressive Fed tightening, then recovery (2022–present). Bear-market caution may incorrectly veto valid bull-market trades.

**Mitigation:** Regime detection logic needed to contextualize Wasden's caution passages against current conditions. Design ticket required.

### What Wasden Wants From AI (from Emery transcript)
> "What I would like AI to do, especially here, is to find more that aren't obvious... if you can use AI to say I found 50 points or scenarios where the market may be very significantly misjudging prices."

The AI isn't just implementing Wasden's existing rules — it's finding mispricings he couldn't find manually. Special situations at scale.

### Long-Term Vision: Replicating Wasden's Decision-Making
Wasden and the team discussed using conjoint/contract analysis (Sawtooth software methodology) to quantize Wasden's decision-making process — essentially building an AI that replicates how he makes decisions, not just what decisions he makes. Combined with statistical models (Vasu's approach), the goal is a merged AI that can train itself based on heuristics from multiple decision-making processes.

---

## 4. Intelligence Layer 2 — The Buffett Bot

### Source Material
Warren Buffett's annual shareholder letters. Not yet sourced — planned Phase 3.

**To make it more Buffett-like:** Annual meeting Q&A transcripts, interviews, "The Essays of Warren Buffett," SEC filings from Berkshire's actual trades.

### Role
Advisory section only at the end of each analysis: "what would Buffett think about this?" Does NOT vote. Does NOT sway the decision pipeline.

### Key Consideration
Buffett's approach is long-term value investing with very infrequent trades. For a daily system, Buffett will often say "do nothing." This is a feature — it serves as a conservative counterweight that may flag when the system is overtrading.

### Tax Efficiency
The Buffett Bot considers tax efficiency in sell decisions — tracking holding periods and wash sale risk.

---

## 5. Intelligence Layer 3 — Quantitative & Statistical Models

### Tier 1 (Build First)
- **XGBoost** — 5-day forward return direction classification
- **Elastic Net** — regularized regression, second signal
- **ARIMA** — time series forecasting
- **Basic Sentiment Model** — using Finnhub pre-computed scores + NewsAPI

### Tier 2 (Add Later)
- **Dr. Miller's Neural Networks** (R → port to Python) — Dow Jones closing price prediction using lagged open prices. Two architectures: small [5,3] and large [10,8,6]. See Section 17.
- **GARCH** — volatility modeling
- **HMM Regime Detection** — Hidden Markov Model for market regime identification
- **Monte Carlo** — risk simulations

### Tier 3 (Much Later — Only If Needed)
- **ANM/dHSIC Causal Analysis** — PhD-level complexity, Phase 4 experiment
- Advanced neural architectures beyond Dr. Miller's framework

### Model Agreement Metric
Track std dev of model scores as a separate signal. `std_dev > 0.5` = high disagreement flag. High disagreement reduces position sizing or triggers jury escalation.

### Continuous Learning Rules
- Checkpoint mechanism required before autotune is activated
- Minor parameter autotune: automated
- Major changes: human approval required
- Any live weight update must pass 90-day holdout validation first

### Survivorship Bias Warning
The 32GB minute-level data and Emery's 10-year dataset likely don't include delisted/bankrupt companies. Must audit before training. All models trained on this data are tagged `survivorship_bias_unaudited` until audit complete.

---

## 6. The 10-Agent Jury Ensemble System

### Concept
This is the core decision arbitration mechanism. After the initial bull/bear debate between Claude (bull) and Gemini (bear), if they disagree, 10 additional LLM agents are spawned to review the debate arguments and vote.

### How It Works
1. Bull researcher (Claude) builds bull case
2. Bear researcher (Gemini) builds bear case
3. 1–2 rounds of rebuttal
4. **If agreement:** Proceed to risk check
5. **If disagreement:** Spawn 10 additional agents
   - Each agent reviews the full debate transcript
   - Each agent votes: BUY / SELL / HOLD
   - Each agent provides brief reasoning
   - Aggregate vote count determines the decision
   - Majority wins (6+ of 10 = decisive; 5-5 = escalate to human)

### Why This Architecture Works
- Prevents any single model from dominating unfairly
- The jury agents can be prompted with different perspectives (fundamentals-focused, risk-focused, macro-focused, sector-focused, etc.)
- The vote is based on the ARGUMENTS, not raw data — the jury evaluates the quality of the reasoning
- Fundamentals and ratios are the primary lens agents use to evaluate arguments

### Jury Agent Prompt Perspectives (suggested distribution)
- 3 agents: fundamentals and ratio analysis focus
- 2 agents: macro/sector environment focus
- 2 agents: risk and downside focus
- 2 agents: technical signal interpretation focus
- 1 agent: Wasden framework application focus

### Escalation
- 6+ of 10 votes in one direction = decisive
- 5-5 split = escalate to human (Jared decides)
- Human override is always available

### Cost Estimate
10 extra Claude/Gemini API calls per candidate. For 8 top candidates per day, that's up to 80 extra calls. At Haiku pricing, this is negligible — under $1/day. Worth every penny for explainability and reduced single-model bias.

---

## 7. Cary Wasden's Investment Philosophy

### Background
Wasden founded Caspian Securities in 1996. Managed money for large institutional clients, including Sir John Templeton. In 2006, Templeton invited him to manage his personal funds directly. Templeton taught Wasden poker. The 5-bucket system was created for Templeton's personal money management. Wasden's process has been "remarkably consistent" since then.

### Core Disciplines

**1. Morning Portfolio Review**
Every morning, look at your portfolio. Ask: "If I had to buy today, would I still want to buy?" Must be willing to buy every day. If not: look at difference of short and long-term gains; if it surpasses or drops below your threshold, sell; check PE earnings now and next year.

**2. Have a Sell Discipline**
Know when you get out BEFORE you get in. "I get out when it reaches X." Emotions ruin trading — discipline eliminates emotion.

**3. Be Thoughtful**
Don't have to be brilliant, just be thoughtful.

**4. Always Have Cash**
Wait for the moment when you want to buy. THERE WILL BE A TIME IN THE NEAR FUTURE. Keep cash so you can buy opportunities AND absorb losses.

**5. Markets Move on Expectations**
Meeting, missing, or exceeding expectations drives price. If you are a trader: go where the tail is fat. If you are an investor: go where the tail is thin.

**6. Re-evaluate at Standard Deviations**
Any time an evaluation moves or is off by a standard deviation, re-evaluate purchases.

### Key Principles
- Use technical trading to determine WHEN to trade — NOT for what to trade or buy
- Discipline yourself to let the numbers tell the story
- Precision of language — talk in numbers
- Is it cheaper or expensive? (always return to this question)
- Don't look past 2 years in the future
- Ratios are like a blood test — they tell you something is wrong, but don't diagnose. Go into the story.
- Buy when people are fearful, sell when people are greedy
- Every time you see something positive, ask why — then try to prove it wrong
- Always ask why why why why why why why
- Look into the current CEO's track record
- Volatility allows you to get in and out to reset over and over
- Never make a decision until you have about 80% of the information needed

### Three Things to Focus On
1. **Unit growth** — are they selling more stuff?
2. **Pricing power** — need a competitive environment
3. **Balance sheet matters** — how quickly a company can go from non-existence to success

### On Special Situations (from Emery transcript)
> "These are situations where the market is just absolutely wrong. They happen more often than you think. But what you really want are ones that are so obvious that when it comes around, you just put all your money on red and you let it go. You mortgage your house, whatever else to get that to happen."

Example: Crude oil at -$47/barrel during COVID. You knew it couldn't stay there more than a month because we consume oil every day and run out of oil every month. You take as many positions as you can. Enormous winner once it gets back to zero.

### On Market Mispricing (from Emery transcript)
Costco currently trades at 55× earnings vs. historical ~20×, and growing slower than historically. That's a situation where something is clearly out of whack — driven by excess liquidity. The question is: what's the catalyst that brings it back? Markets require a "Minsky moment" — when people suddenly say "this is dumb, I'm not doing this anymore." Same as the internet era, same as the credit crisis.

### On Analyst Recommendations
Useful insights, NOT good for decision making. Analysts' firms meet with the companies they cover. They have incentives to make stocks look good.

---

## 8. Wasden's 5-Bucket Analysis Framework

This is the MOST IMPORTANT framework in the system. Created for Sir John Templeton. 94% of returns come from the first 3 buckets. The last 2 are where real alpha lives.

### The 5 Buckets (in order)
1. **Instruments**
2. **Countries**
3. **Sectors**
4. **Themes**
5. **Special Occasions (Special Situations)**

### Return Distribution
- **Buckets 1–3** (Instruments, Countries, Sectors): 94% of returns. Predictable, repeatable, useful.
- **Buckets 4–5** (Themes, Special Situations): Higher volatility, but where "adult size money" is made. You can be wrong 99 out of 100 times on Special Situations — if you're right once and sized correctly, it's transformational.

### Bucket 1: Instruments
- Equities (large value, growth, etc.)
- Fixed income — sovereign (government bonds), corporate investment grade, municipal, non-investment grade
- Triggers: Risk-adjusted yield comparisons. Example: US government bond at 4.8% vs. equity FCF yield of 3% = get out of stocks on risk-adjusted basis. Simple metrics that work reliably.
- The risk-free rate (US government bond) is the benchmark. Every additional risk taken should be compensated. If it's not, that's a trigger signal.

### Bucket 2: Countries
- United States
- China / Hong Kong (two totally different markets — both work)
- Brazil (phenomenal)
- Israel (great)
- Most of Europe
- Japan, Korea

**Country selection criteria — must be right on all three:**
1. Interest rates
2. Inflation
3. Currencies

**Deep capital markets requirement:** Can gauge by capital market trading volume as % of GDP. Small/niche markets don't work well: Vietnam, Cambodia, Argentina, etc. The smaller the market, the less reliable the pricing signals.

**Key observation (from Emery transcript):** US stock market vs. China has shown incredible divergence — China largely flat, US up dramatically. Simply knowing which country to be in, and choosing the two broadest indices in those countries, gives dramatic outperformance. There are times when you want to switch — China was the best performing stock market 3 years prior.

### Bucket 3: Sectors
- 11 sectors (same across every economy worldwide — GICS standard)
- Inside sectors: sub-sectors and industry groups
- Phenomenal information at sub-sector level; information value degrades at the industry group level
- 11 sectors to focus on; use FCF yield + quality and growth fundamentals to determine which sectors to be in
- Paying farther into the weeds (beyond sub-sector) doesn't tend to yield valuable information

### Bucket 4: Themes (Long-Term Structural)
- AI
- Aging populations
- Renewable energy / electric vehicles
- Key characteristic: NOT cyclical — structural. Won't be materially affected by whether we hit a recession. Long-term trades but more certain.
- Aging of China specifically called out as "one of the more devastating economic events to happen in your generation" — major theme.
- The US benefited from immigration (adds to working population) but that dynamic may be changing.

### Bucket 5: Special Occasions / Special Situations
The highest volatility, highest return bucket. These "present themselves" — you can't go searching for them easily. When they appear, they're obvious to those paying attention. The market is just absolutely wrong.

**Characteristics:**
- Requires long staying power OR a very clear catalyst identification
- Must have confidence interval on your conviction — put big money only on high-confidence situations
- Can be wrong 99 of 100 times, but the one time you're right with proper sizing is transformational
- Key question always: "What is the catalyst? How do I get out? What happens for the market to return to normalcy?"

**Examples:**
- Crude oil at -$47/barrel during COVID (couldn't last >1 month — easy catalyst)
- Costco at 55× earnings vs. historical 20× — excess liquidity driven mispricing
- Internet era bubble — "five hookers shouldn't be able to have five houses each"

**AI's role in Special Situations:** Use AI to find 50+ scenarios where the market may be very significantly misjudging prices. The AI can surface what a human analyst would need years of experience to notice.

---

## 9. Fundamental Analysis Reference

### Key Ratios — The "Blood Test" Metrics

All ratios must be compared:
1. **Historically** — over time for the same company
2. **By peer** — against companies in the same sector/industry

#### Valuation Ratios
| Metric | Bloomberg Code | Notes |
|--------|---------------|-------|
| Current Price | PX_LAST | Baseline |
| P/E Ratio (Trailing) | PE_RATIO | Wasden Core |
| P/E Ratio (Forward) | BEST_PE_RATIO | Wasden Core |
| EPS (Current) | IS_EPS | Core |
| EPS (Next Year Est) | BEST_EPS | Core |
| PEG Ratio | PEG_RATIO | Wasden Core — PEG > 1 overpriced, < 1 underpriced |

**P/E Theory:** To find Price: `PE × EPS`. Get PE from historical or comparable stocks.
**Forward PE Rule:** If Forward PE is lower than growth rate, or equivalent, that's good.
**PEG Rule:** `BEST_PE_RATIO / BEST_EST_LONG_TERM_GROWTH`. Below 1 = cheap.

#### Cash Flow Ratios (Wasden's Favorites)
| Metric | Bloomberg Code | Notes |
|--------|---------------|-------|
| Free Cash Flow | CF_FREE_CASH_FLOW | Wasden's #1 favorite metric |
| FCF Yield | FREE_CASH_FLOW_YIELD | FCF / Market Cap — also used in Bucket 1/2 instrument selection |
| EBITDA Margin | EBITDA_MARGIN | Better than earnings — harder to misrepresent |
| FCF to Net Income | Calculated | If > 1, strong cash generation |

**Why FCF > Earnings:** Earnings can be misrepresented. Cash flow analysis is better. FCF is harder to manipulate. FCF yield is also directly compared to bond yields for instrument selection (Bucket 1).

#### Profitability Ratios
| Metric | Bloomberg Code | Notes |
|--------|---------------|-------|
| ROE | RETURN_COM_EQY | Should not be > ROC |
| ROC | RETURN_ON_CAP | Should be > ROE |
| Gross Margin | GROSS_MARGIN | Compare over time and vs. peers |
| Operating Margin | OPER_MARGIN | Compare over time and vs. peers |
| Net Margin | PROF_MARGIN | Compare over time and vs. peers |

#### Liquidity & Leverage
| Metric | Bloomberg Code | Notes |
|--------|---------------|-------|
| Current Ratio | CUR_RATIO | Sprinkle Sauce filter |
| Quick Ratio | QUICK_RATIO | |
| Debt to Equity | TOT_DEBT_TO_TOT_EQY | Compare by industry |
| Interest Coverage | INTEREST_COVERAGE_RATIO | Sprinkle Sauce |

**Debt to Equity rule:** More reliable the industry, the more debt they can carry.

#### Growth & Efficiency
| Metric | Bloomberg Code | Notes |
|--------|---------------|-------|
| Revenue Growth YoY | SALES_GROWTH | If below inflation, concern |
| Cash Conversion Cycle | CASH_CONVERSION_CYCLE | DIO + DSO - DPO |
| Market Cap | CUR_MKT_CAP | $ per share × # shares |
| Short Interest | SHORT_INT_RATIO | Sentiment signal |

#### Piotroski F-Score
**Cannot use standard BDP field** — `PIOTROSKI_F_SCORE` returns `#N/A Invalid Field`. Must implement via custom Bloomberg EQS formula or calculate manually from component fields.

### The 5 Categories of Ratios (Wasden: "99% of the story")
1. Valuation (P/E, PEG, Price/Cash Flow)
2. Profitability (ROE, ROC, margins)
3. Liquidity (Current, Quick)
4. Leverage (Debt/Equity)
5. Efficiency (CCC, Asset turnover)

### CEO Analysis
Always look into the current CEO. Track record, influence on the company over the years. Management quality matters enormously.

### Common Template
Wasden recommended a common Excel template that auto-calculates ratios when importing Bloomberg data. Reduces time on basic work, frees time for analytical work. The JMWFM Bloomberg file is the beginning of this. Compare companies to each other.

---

## 10. Technical Analysis Reference

### Bollinger Bands + RSI (Use Together)
- Top band: overbought (over-buyers)
- Bottom band: oversold (over-sellers)
- RSI: frequency of moves (30 = oversold, 70 = overbought)
- **Critical rule:** Wait for BOTH to line up before stepping in. Never use one alone.

### Other Technical Indicators
| Indicator | Description |
|-----------|-------------|
| SMI | Stochastic Momentum Index — measures momentum (in-between on ask/bid) — good for predicting |
| EMA | Exponential Moving Average |
| MACD | Standard momentum indicator |
| Zone exit re-entry | Entry/exit zone strategy |

### Technical vs. Fundamental Split (CRITICAL)
**USE technical trading to determine WHEN to trade.**
**DO NOT use technical trading to determine WHAT to trade.**

Fundamentals tell you WHAT. Technicals tell you WHEN.

---

## 11. Agent Debate Pattern — Bull vs. Bear

### Why Two Different LLMs
- **Claude:** Bull case
- **Gemini:** Bear case
Structurally important — different training data, different architectures, genuinely different reasoning. Not one model arguing with itself.

### Debate Structure
1. Bull researcher (Claude) builds case using positive quant signals, Wasden APPROVE passages, sector momentum
2. Bear researcher (Gemini) builds case using risk factors, macro headwinds, Wasden caution passages, correlation
3. 1–2 rounds of rebuttal
4. Agreement → proceed to risk check
5. Disagreement → 10-Agent Jury (see Section 6)

### What Gets Logged
Full debate transcript is logged in decision journal. Every trade is explainable — you can read exactly why the system was bullish or bearish.

---

## 12. Memory Agent & Continuous Learning

### What the Memory Agent Stores (Examples)
```
"When VIX crosses above 25 while AAPL shows bullish momentum, the
 momentum signal has been wrong 4 out of 5 times."

"Wasden vetoed TSLA entries 3 times in Q3. All 3 vetoes were correct.
 Weight Wasden higher on TSLA-related decisions."

"XGBoost underperforms in the first week after Fed meetings. Reduce
 its weight during these periods."

"Our best Sharpe periods coincide with high model agreement (std dev
 < 0.2). When models agree, size up."
```

### Architecture
- Stored as embeddings in Supabase pgvector alongside Wasden Watch corpus
- Queries both Wasden Watch AND memory store for each evaluation
- Includes confidence score, date learned, number of supporting examples
- Runs weekly after enough paper trading data accumulates — Phase 3

### Guardrails
- Checkpoint mechanism before autotune goes live
- 90-day holdout validation before any live weight update
- Human intervention trigger: consecutive losses OR net zero performance (see Section 1)

---

## 13. Risk Management Framework

### Core Parameters
- Maximum position size: 12%
- Risk per trade: 1.5%
- Minimum cash reserve: 10%
- Max correlation between positions: 0.7 (normal), 0.8 (stress-tested)
- Max 3 stocks with correlation > 0.7

### The 8 Categories of Trade Risk

#### 1. Gap Risk
Closes at $150, stop at $145, opens at $130 after overnight news. Stop fires at $130.
**Build:** Gap risk score per position. Higher score for upcoming catalysts (earnings, FDA, court) = reduced max position size.

#### 2. Liquidity Risk
Large order moves price. Alpaca paper fills are instant — live fills aren't.
**Build:** Slippage model. Order > 1% of ADV → model 0.1% slippage per 1% of ADV.

#### 3. Correlation Blowup Risk
In crashes, correlations go to 1.0. "Diversified" positions all drop together.
**Build:** Stress-test correlation check using worst 10 market days in last year. Flag if stress correlation > 0.8.

#### 4. Whipsaw Risk
Stock dips to stop, you sell, then it recovers. Tight stops in volatile markets.
**Build:** ATR-adaptive stops + re-entry logic. If stock recovers above stop within 2 trading days and quant models still signal positive, flag for potential re-entry (not automatic).

#### 5. Regime Change Risk
All models trained on historical data. When regime changes, all models can fail simultaneously.
**Build:** Circuit breaker — if SPY drops > 5% in rolling 5-day window: cut all positions by 50%, increase cash to 40%, halt new entries.

#### 6. Execution Risk
Market orders fill at whatever price is available.
**Build:** Order management state machine: Submitted → Pending → Filled / Partially Filled / Rejected / Expired. Each state has defined behavior.

#### 7. Fat Finger / System Error Risk
Bugs in position sizing, double submissions.
**Build:** Pre-trade validation as SEPARATE, INDEPENDENT code path: order quantity sanity, duplicate detection, portfolio impact, dollar sanity.

#### 8. Model Disagreement Risk
2-2 split with asymmetric signal strengths looks like consensus but isn't.
**Build:** Track model agreement std dev. > 0.5 = high disagreement flag → reduce position or skip trade → trigger jury if in debate context.

### PDT Rule
Swing trading as primary mode. $25K account or ≤3 trades/week. Cash account: no PDT limit, 1-day settlement wait.

### Historical Stress Tests Required
- COVID crash (Feb–March 2020)
- 2022 bear market
- Regional banking crisis (March 2023)
- Major Fed pivot moments
- Dow Jones historical data: Great Depression, WWII, Black Monday 1987, dot-com bubble, 2008 financial crisis

---

## 14. Bias Protection System

### Four Types of Bias Risk

**1. Wasden Temporal Bias** — RAG from June 2022 (specific bear-to-recovery regime). Bear-era caution may fire on valid bull trades.

**2. Quant Model Overfitting Bias** — Models trained on 2020–2025 may have learned pandemic-era patterns, not durable market dynamics.

**3. Confirmation Bias in Arbiter** — If quant models and Wasden Watch are trained on overlapping time periods, they may agree not because they're independent but because they're responding to the same pattern. Two "independent" signals that aren't actually independent.

**4. Selection Bias in Screening Funnel** — Funnel narrows 500 to 8 before Wasden sees them. Wasden only evaluates what quant models already like.

### Bias Monitoring Dashboard (Weekly)
- % of Wasden verdicts that are VETO vs. APPROVE vs. NEUTRAL
- Whether quant models and Wasden agree more than expected by chance
- Sector concentration in recommendations
- "What if we ignored Wasden?" backtest comparison

---

## 15. API & Data Ecosystem

### LLM Layer
| API | Primary Role | Cost |
|-----|-------------|------|
| Claude API | Wasden Watch RAG, bull case, screening (Haiku), report generation, chart vision | $20–50/month |
| Gemini API | Bear case, contrarian check, second-opinion sentiment, backup | Free tier |

### Claude vs. Gemini Task Split
```
CLAUDE:                          GEMINI:
────────────────────             ────────────────────
Wasden Watch RAG                 Bear case in debate
Bull case in debate              Contrarian check
Screening (Haiku for bulk)       Second-opinion sentiment
Report generation                Daily market summary
Buffett checklist                Backup for Wasden Watch
Chart description (Vision)       Backup report generation
```

### Trading Execution
- **Alpaca API** — Paper trading, real-time and historical price data. Free tier. Confirmed by Vasu.

### Data & News
- **Finnhub** — Free API. Pre-computed sentiment scores, insider sentiment (MSPR), SEC filing sentiment, fundamentals backup. Use as Tier 1 sentiment.
- **NewsAPI** — Catches political/geopolitical stories Wasden reacts to. Financial-only APIs miss this.
- **Bloomberg Terminal** — University access. Export to own database. Cannot run 24/7 (licensing). Expires at graduation (Spring 2027).
- **Wall Street Journal subscription** — Available for deep-dive.
- **Fidelity Active Trader Pro** — Fallback after Bloomberg expires.

### Notifications
- **Signal** — Primary. Google Voice or prepaid number for bot (NOT yet set up — action item).
- **Telegram** — Backup if Signal breaks. Has first-class Bot API.
- Escalation threshold: confidence ≥ 0.80 after jury vote → Signal notification to Jared.

### Monthly Budget
$50–$150/month (Emery estimated $300 at full scale).

---

## 16. Data Assets Inventory

| Asset | Description | Format | Source | Status |
|-------|-------------|--------|--------|--------|
| 32GB Minute Data | 5 years, all US equities, every minute | CSV | Local + hard drive | Available |
| Wasden Weekenders | ~30 PDFs, June 2022–present | PDF (native text) | Local | Available |
| Dow Jones Historical | OHLCV + adjusted close, 1928–2009, daily | CSV, daily at midnight | Joe | Available |
| Emery S&P 500 Data | OHLCV, last 10 years, every US stock | CSV | Emery | Available |
| Bloomberg Snapshot | 10 tickers, 25 metrics, Feb 21, 2026 | Excel (JMWFM file) | Project | Available |
| Dr. Miller NN (Small) | R notebook, 5-feature, hidden [5,3] | .Rmd | Uploaded | Available |
| Dr. Miller NN (Large) | R notebook, 6-feature, hidden [10,8,6] | .Rmd | Uploaded | Available |

### 32GB Minute Data
- 5 years, all US equity tickers, every minute
- CSV format, fairly clean with some missing data
- Covers pretty much all US equities
- **Survivorship bias warning:** Likely missing delisted/bankrupt companies. Audit before training.

### Dow Jones Historical (1928–2009)
- Columns: Open, High, Low, Close, Volume, Adjusted Close
- Daily frequency, delivered at midnight (12am)
- 20,000+ rows covering: Great Depression, WWII, post-war expansion, 1970s stagflation, 1980s bull market, Black Monday 1987, dot-com bubble, 2008 financial crisis
- Extremely valuable for regime identification and stress testing
- Used as input to Dr. Miller's neural network models (`dowjones1` variable)

### Emery's S&P 500 Data
- OHLCV, last 10 years, every stock on the US Stock Exchange
- Much broader than the 32GB dataset in ticker coverage
- More recent — covers 2015–2025 approximately
- Survivorship bias likely applies here too — audit needed

### Wasden Weekenders
- ~30 PDFs, June 2022–present
- Video sessions exist for earlier content but haven't been requested from Wasden yet
- Permission to use confirmed
- Native text — can select/copy
- Charts/images present — require Claude Vision processing

---

## 17. Neural Network Models — Dr. Miller's Framework

Both models were built by Dr. Wyatt Miller (professor). Written in R-Studio using the `neuralnet` package. Input data: `dowjones1` CSV dataset (Dow Jones 1928–2009 historical data).

### DowSmall1a — Simple Architecture

**Purpose:** Predict Dow Jones closing price from lagged opening prices.

**Features (5 inputs):**
- `Open_Lag0` — Today's opening price
- `Open_Lag1` — Yesterday's opening price
- `Open_Lag2` — 2 days ago open
- `Open_Lag3` — 3 days ago open
- `Open_Lag4` — 4 days ago open

**Target:** Today's `Close` price.

**Architecture:** `neuralnet(hidden = c(5, 3), linear.output = TRUE, threshold = 0.01)`
- Layer 1: 5 nodes
- Layer 2: 3 nodes
- Output: Linear (regression, not classification)

**Data processing:**
- Min-max normalization using min/max of Open_Lag0 and Close only
- 80/20 train/test split, `set.seed(123)`

**Performance metrics:** RMSE (typical error in dollars), MAPE-based accuracy (100 - MAPE%).

**Prediction function:** Takes 5 opening prices as numeric vector, returns predicted closing price.

**R Dependencies:** `neuralnet`, `dplyr`, `readr`

### DowLarger1a — Deeper Architecture

**Purpose:** Same as DowSmall, but richer features and deeper network.

**Features (6 inputs):**
- `Open_Lag0` through `Open_Lag4` (same as DowSmall)
- `Close_Lag1` — Previous day's closing price (ADDED vs. DowSmall)

**Architecture:** `neuralnet(hidden = c(10, 8, 6), linear.output = TRUE, threshold = 0.001, stepmax = 1e7)`
- Layer 1: 10 nodes
- Layer 2: 8 nodes
- Layer 3: 6 nodes (one layer deeper than DowSmall)
- Much finer threshold (0.001 vs 0.01) — more precise training

**Data processing:**
- More sophisticated normalization: `max_val <- max(data_prepared %>% select(-Date))` — normalizes across ALL numeric columns together, not just Open/Close
- 80/20 train/test split, same seed

**Key difference from DowSmall:** Adding `Close_Lag1` as a feature gives the model information about where the previous day ended, not just where days opened. This is theoretically more informative.

### Integration Plan
1. Port both R models to Python using `tensorflow` or `pytorch`
2. Retrain on Emery's 10-year OHLCV dataset for modern market conditions
3. Use as Tier 2 models initially — validate before including in live ensemble
4. The architecture insight (lagged opens + previous close → predict today's close) can be extended to individual stocks in the S&P 500 universe

### Important Notes
- Both models are trained on Dow Jones index-level data (1928–2009) — significant regime differences from today
- The `dowjones1` variable must be loaded before running either script
- These are close price predictors, not directional classifiers — output needs to be converted to BUY/SELL/HOLD signal by comparing predicted close to current price

---

## 18. Bloomberg Terminal Reference

### Access
- Through university. Available daily.
- Realistic: 3–4× per week minimum.
- Must export to own database — cannot run 24/7 (licensing restriction).
- Expires at graduation (Spring 2027). Fallback: Yahoo Finance, Fidelity, eventually pay for access.

### Key Commands
| Command | Description |
|---------|-------------|
| DES | Description |
| GP | Price Chart |
| FA | Financial Analysis (Ratios, Cash Flow, Profitability) |
| EE | Estimates (P/E, Forward P/E, EPS, PEG) |
| EM | Earnings & Revenue |
| RV | Relative Value (Peer Comparison) |
| EQRV | Equity Relative Value (Multiples vs Comps) |
| ANR | Analyst Recommendations |
| PT | Price Targets |
| BRC | Broker Research |
| SURP | Earnings Surprise |
| BI | Bloomberg Intelligence |
| ERN | Earnings Analysis |
| OWN | Ownership |
| HDS | Top Holders |
| OMON | Options Monitor |
| SPLC | Suppliers and Customers |
| MGMT | Management |
| DVD | Dividend |
| GE | General |

### Bloomberg BDP Field Codes
```
PX_LAST                    -- Current Price
CUR_MKT_CAP                -- Market Cap
PE_RATIO                   -- Trailing P/E
BEST_PE_RATIO              -- Forward P/E
IS_EPS                     -- Current EPS
BEST_EPS                   -- Forward EPS Estimate
BEST_EST_LONG_TERM_GROWTH  -- Long-term growth estimate
PEG_RATIO                  -- PEG Ratio
CF_FREE_CASH_FLOW          -- Free Cash Flow
FREE_CASH_FLOW_YIELD       -- FCF Yield
EBITDA_MARGIN              -- EBITDA Margin
RETURN_COM_EQY             -- ROE
RETURN_ON_CAP              -- ROC
GROSS_MARGIN               -- Gross Margin
OPER_MARGIN                -- Operating Margin
PROF_MARGIN                -- Net Margin
CUR_RATIO                  -- Current Ratio
QUICK_RATIO                -- Quick Ratio
TOT_DEBT_TO_TOT_EQY        -- Debt to Equity
SALES_GROWTH               -- Revenue Growth YoY
INTEREST_COVERAGE_RATIO    -- EBITDA/Interest
CASH_CONVERSION_CYCLE      -- CCC
SHORT_INT_RATIO            -- Short Interest
PIOTROSKI_F_SCORE          -- REQUIRES CUSTOM EQS (standard BDP returns #N/A)
```

### Known Bloomberg Issues
- `PIOTROSKI_F_SCORE` — not accessible via standard BDP. Requires custom EQS screen formula.
- TSM trailing P/E (`PE_RATIO`) — returns `#N/A Field Not Applicable` (ADR characteristic). Expected, not an error. Use `BEST_PE_RATIO`.
- AAPL ROC (`RETURN_ON_CAP`) — returns `#N/A N/A`. Known issue.
- PEG Ratio — sometimes returns `#VALUE!` if growth rate unavailable. Use `IFERROR` fallback.
- `Fundamentals` sheet in Excel shows `#NAME?` when opened outside Bloomberg session. This is expected. Only read from `Values` sheet programmatically.

---

## 19. Bloomberg Fundamental Data — Feb 21, 2026 Snapshot

Data pulled via Bloomberg Excel Add-In (BDP) on February 21, 2026. 10 tickers, 25 metrics.

| Ticker | Price | Mkt Cap ($B) | Trail P/E | Fwd P/E | EPS | PEG | FCF ($M) | FCF Yield% | EBITDA Margin% | ROE% | ROC% | Gross Margin% | Op Margin% | Net Margin% | Cur Ratio | Quick Ratio | D/E | Rev Growth% | EBITDA/Int | CCC | Short Int |
|--------|-------|-------------|----------|--------|-----|-----|----------|-----------|---------------|------|------|--------------|-----------|-----------|----------|------------|-----|------------|-----------|-----|---------|
| NVDA | 189.82 | 4,612.6 | 48.0 | 26.8 | 2.97 | 0.54 | 60,853 | 1.67 | 60.5 | 107.4 | 96.6 | 75.0 | 62.4 | 55.8 | 4.44 | 3.67 | 12.9 | 114.2 | 329.8 | 88.0 | 1.57 |
| PYPL | 41.65 | 38.3 | 7.9 | 7.8 | 5.46 | ERR | 5,564 | 14.05 | 21.7 | 25.7 | 18.1 | 51.8 | 18.3 | 15.8 | 1.29 | 0.24 | 52.8 | 4.3 | 13.8 | N/A | 2.82 |
| NFLX | 78.67 | 332.2 | 31.0 | 25.0 | 2.58 | ERR | 9,461 | 2.83 | 30.2 | 42.8 | 27.0 | 48.5 | 29.5 | 24.3 | 1.19 | 1.01 | 63.8 | 15.9 | 17.2 | N/A | 1.24 |
| TSM | 370.54 | 1,921.8 | N/A | 23.6 | N/A | 0.67 | 1,086,331 | N/A | 68.9 | 35.4 | 28.7 | 59.9 | 50.8 | 45.1 | 2.62 | 2.30 | 18.2 | 31.6 | 97.8 | 76.4 | 1.37 |
| XOM | 147.28 | 613.7 | 21.8 | 22.0 | 6.70 | 2.85 | 23,612 | 3.72 | 18.4 | 11.0 | 9.5 | 14.2 | 10.4 | 8.9 | 1.15 | 0.76 | 18.9 | -4.5 | 55.6 | 35.5 | 2.59 |
| AAPL | 264.58 | 3,884.3 | 33.4 | 30.6 | 7.49 | 2.30 | 98,767 | 3.14 | 35.1 | 152.0 | N/A | 46.9 | 32.0 | 26.9 | 0.89 | 0.57 | 152.4 | 6.4 | N/A | -72.4 | 2.00 |
| MSFT | 397.23 | 2,949.7 | 26.5 | 22.6 | 13.70 | 1.58 | 71,611 | 2.62 | 62.6 | 34.4 | 26.4 | 68.8 | 45.6 | 36.1 | 1.35 | 1.16 | 32.7 | 14.9 | 53.9 | -17.0 | 1.34 |
| AMZN | 210.11 | 2,255.5 | 30.1 | 22.2 | 7.29 | 1.21 | 7,695 | 0.34 | 22.3 | 22.3 | 15.7 | 50.3 | 11.2 | 10.8 | 1.05 | 0.88 | 41.3 | 12.4 | 35.2 | -41.0 | 1.77 |
| TSLA | 411.82 | 1,545.3 | 341.8 | 208.6 | 1.18 | ERR | 6,220 | 0.47 | 11.1 | 4.9 | 4.4 | 18.0 | 4.6 | 4.0 | 2.16 | 1.53 | 17.8 | -2.9 | 12.9 | 14.2 | 1.04 |
| AMD | 200.15 | 326.3 | 78.7 | 29.5 | 2.67 | 0.61 | 6,735 | 2.07 | 19.3 | 7.2 | 7.0 | 49.5 | 10.7 | 12.5 | 2.85 | 1.78 | 6.1 | 34.3 | 28.2 | 162.3 | 0.88 |

### Initial Analysis Notes
**NVDA:** PEG 0.54 — undervalued relative to growth rate despite 48× trailing P/E. FCF $60.8B, ROE 107%, revenue growth 114%. Extraordinary fundamentals.

**PYPL:** FCF Yield 14% — highest on the list by far. Wasden's favorite metric screaming potential undervaluation. Why is the market not giving it credit? Growth quality issue? This is the question to answer.

**TSLA:** P/E 341× with negative revenue growth (-2.9%) and near-zero FCF yield (0.47%). Fails multiple Sprinkle Sauce screens. Likely a Wasden VETO candidate.

**TSM:** ADR — trailing P/E unavailable. Forward P/E 23.6×, PEG 0.67 (undervalued). EBITDA margin 68.9%. Revenue growth 31.6%. Clean fundamentals.

**AAPL:** ROE 152% from massive buybacks. CCC -72.4 = Apple gets paid before paying suppliers (enormous competitive advantage). Current ratio 0.89 (below 1) is optical warning sign but doesn't reflect reality for Apple.

**Piotroski:** All tickers returning `#N/A Invalid Field` — confirmed requires custom EQS formula.

---

## 20. Stock Universe & Screening Funnel

### Universe
S&P 500 (500 stocks) as primary universe. Penny stocks noted by Emery as potential parallel strategy.

### Pilot Watchlist (11 Tickers)
NVDA, PYPL, NFLX, TSM, XOM, AAPL, MSFT, AMZN, TSLA, AMD + Anthropic (pending IPO).

**Note:** Tech-heavy (8 of 11). Planned expansion to healthcare, industrials, utilities.

### 5-Tier Daily Screening Funnel
Narrows 500 → 3–8 recommendations per day.
- Tier 1: Basic quantitative filters (price, volume, market cap)
- Tier 2: Sprinkle Sauce fundamental screens
- Tier 3: Technical signal filters
- Tier 4: Wasden Watch evaluation
- Tier 5: Bull/Bear debate + 10-Agent Jury (for top candidates in disagreement)

### Sprinkle Sauce Filter
Wasden's proprietary screening function. Bloomberg fields tagged "Sprinkle Sauce":
- Market Cap (CUR_MKT_CAP)
- Current Ratio (CUR_RATIO)
- Revenue Growth YoY (SALES_GROWTH)
- EBITDA/Interest Coverage (INTEREST_COVERAGE_RATIO)
- Piotroski F-Score (requires custom implementation)

---

## 21. MCP / LangGraph Orchestration

### Why LangGraph
Direct Python function calls are rigid. LangGraph declares the pipeline as a graph. Easy modification, visual debugging, built-in state management, retry logic, streaming to dashboard.

### Full Pipeline Including Jury
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(TradingState)

workflow.add_node("quant_scoring", run_quant_models)
workflow.add_node("wasden_watch", run_wasden_watch)
workflow.add_node("bull_researcher", run_bull_case)         # Claude
workflow.add_node("bear_researcher", run_bear_case)         # Gemini
workflow.add_node("debate", run_debate_rounds)
workflow.add_node("jury_spawn", spawn_jury_agents)          # 10 agents
workflow.add_node("jury_aggregate", aggregate_jury_votes)
workflow.add_node("risk_check", run_risk_checks)
workflow.add_node("pre_trade_validation", run_pre_trade)
workflow.add_node("decision", make_final_decision)

# Edges
workflow.add_edge("quant_scoring", "wasden_watch")
workflow.add_conditional_edges("wasden_watch",
    lambda state: "blocked" if state["wasden_verdict"]["verdict"] == "VETO"
                  else "continue",
    {"blocked": "decision", "continue": "bull_researcher"})
workflow.add_edge("bull_researcher", "bear_researcher")
workflow.add_edge("bear_researcher", "debate")
workflow.add_conditional_edges("debate",
    lambda state: "jury" if state["debate_result"]["outcome"] == "DISAGREEMENT"
                  else "risk",
    {"jury": "jury_spawn", "risk": "risk_check"})
workflow.add_edge("jury_spawn", "jury_aggregate")
workflow.add_edge("jury_aggregate", "risk_check")
workflow.add_edge("risk_check", "pre_trade_validation")
workflow.add_edge("pre_trade_validation", "decision")
```

### MCP
Phase 5+. Relevant when running agents across multiple containers or scaling to multiple providers. Emery noted MCP server may need its own server — significant performance cost.

---

## 22. Dashboard & Financial Forge Interface

### Repository
- **GitHub:** https://github.com/JoeWhiteJr/Financial_Forge
- **Live:** https://financial-forge.vercel.app
- **Tech:** JavaScript (98.6%), Next.js/React, already has CLAUDE.md and backend/frontend/database structure
- **Existing structure:** `frontend/`, `backend/`, `database/migrations/`, `docs/`, Docker Compose, `.env.example`
- **Plan:** Remake/rebuild this as the Wasden Watch dashboard

### Stack
- Frontend: Next.js / React (existing repo)
- Backend: Python (trading logic) + JavaScript/Node (API layer potentially)
- Database: Supabase (PostgreSQL + pgvector)
- Hosting: Vercel (frontend), AWS (backend)

### Dashboard Priorities (All Equal)
1. Real-time portfolio monitoring and P&L tracking
2. Interactive model testing (change parameters, see results)
3. Wasden Watch deep-dive (read verdicts, passages, override decisions)

### Dashboard Views
- Portfolio view with P&L vs. SPY benchmark
- Daily recommendation feed with full reasoning
- Decision journal viewer (why did that trade happen)
- Debate transcript viewer (full bull/bear argument)
- Jury vote breakdown (which agents voted which way and why)
- Override controls (human-in-the-loop)
- Screening funnel live view (LangGraph streaming)
- Bias monitoring section (weekly metrics)
- Warning/shutdown alerts (consecutive losses, net zero trigger)

---

## 23. Wyatt's Behavioral Environment Framework

### Overview
Dr. Wyatt Miller's deterministic analytical framework for assessing whether market conditions are structurally compatible with a predefined trading behavior. Measures "behavioral survivability" — not price prediction.

### Core Question
*Given the current environment, which behavioral responses are being tolerated, and how persistent is that tolerance likely to be?*

### Behavioral Probes
- Each probe = fixed behavioral response. Entry, exit, timing held constant.
- Differences across probes: sensitivity and tolerance parameters only.
- Probes NOT optimized for performance. Changes in outcomes = changes in environment.
- **Critical invariant:** Behavioral footprint must remain fixed through time. Never adapt probe logic to improve performance — this invalidates the measurement.

### Probe Pairs (Example)
- Account 6: 100-stop tolerance (shallow)
- Account 23: 200-stop tolerance (deep)

Differential performance = measure of environmental elasticity.

### Curve Shape Interpretation
Horizon-indexed probability curve P₁...P₅:
- **Flat high/flat low:** Broad regime alignment or hostility
- **Rising/falling slope:** Strengthening or decaying compatibility
- **Concavity:** Delayed release vs. snapback dynamics
- **Kinks:** Transition pressure between horizons

### Wyatt's "Stutter" Method
Wyatt looks for correlation in the stutter. A stutter that correlates the mimic. "You do not need it to be perfect, you just need it to be often." ALWAYS run the model before making the trade to confirm it still works (causal, not just correlated).

---

## 24. Causal Analysis & Noise Modeling

### Core Question
WHAT IS CAUSING THINGS? Not just correlated — causal.

### Methodology
1. Get all correlations with S&P 500
2. Use noise model to find which are causal (not just correlated)
3. Identify major causal predictors
4. Do NOT use economics as predictors — use it as understanding of traffic

### Additive Noise Model (ANM)
Shows correlation but then explains the cause. Look at correlations, then use ANM to see what's causing fluctuations.

### Central Limit Theorem Application
- Need at least 30 trades for normal distribution
- Sum 100 stocks → normal distribution
- Makes it so you don't know if 1 trade makes money, but 95% will — systematic edge
- Must look at magnitude of wins and losses — if losses cost all the wins, it doesn't work (weighted means)

### Implementation Priority
ANM/dHSIC is PhD-level in noisy financial data. Phase 4 experiment. Do not let it block Phase 1 or 2.

---

## 25. Day Trading Notes (Jeff Singer Method)

**Connection:** Jeff Singer — Renaissance Technologies connection.

**Core rules:**
- Only on open, no futures
- Close all positions every day
- Short and cover on buys
- Stop: just under the highest peak

**Top Gainers Strategy:**
1. stockanalysis.com — Top Gainers
2. Stock price as close to $2 as possible (high leverage)
3. Look for volatility and lots of movement (1-day)
4. Look if it's over-inflated
5. Short everything
6. Find the low/high, find the middle, short there
7. Immediately: buy cover — limit at the middle

**Market Oscillation:** Once something goes one way, it oscillates back in the opposite direction (middle of day). Triple Witching Day: 6/20.

---

## 26. Market Observations & Macro Notes

### Fed & Interest Rates
- Lower interest rates → anything tied to credit in higher demand
- Watch the market — doesn't have to go down just because rates drop
- Look at yield curve on Bloomberg
- Supply and demand of bonds is crucial
- US government bond (4.8%) vs. equity FCF yield (3%) = bonds are providing more yield than stocks on risk-adjusted basis → get out of stocks signal (Wasden Bucket 1 trigger)

### Economy vs. Stock Market
- Stock market good → economy may be bad (investing not spending)
- Economy good → stock may be bad (spending not investing)
- Economy fails → everything fails

### International Markets
- Japan and India: interesting opportunities
- China: aging population is "one of the more devastating economic events of your generation" (theme play)
- China was #1 performing stock market 3 years prior to current US dominance — can switch

### Momentum
- Momentum repeats itself
- Figure out when it breaks (thresholds)

### Sentiment & News
- NYT, WSJ: look at words that describe stocks — if talked about, people bought
- How many people use certain stocks (like Amazon)? Volume of mentions matters.
- How innovative? Idea: innovation index

---

## 27. Stock Debates — Documented Sessions

### Stock Debate 1 (Fundamental Analysis Practice)
- PE = P/EPS; to find P: PE × EPS
- If PE Est < PE, it is growing (good sign)
- Don't look past 2 years in the future
- Ratios = blood test: tells you if something is wrong, not what's wrong
- CRDO — look at this stock
- Bloomberg codes used: GE, GP, FA, DES, OMON

### Stock Debate 2 — TSM (Taiwan Semiconductor)
- ADR — trailing P/E returns N/A (expected for ADRs)
- Trailing vs. Forward PE: If Forward PE ≤ growth rate = good
- PEG = PE / Growth rate; below 1 = cheap
- Cash Conversion Cycle = DIO + DSO - DPO
- Free cash flow yield = Wasden's favorite metric ***
- Must be right on: market health and the economic soft period

### Stock Debate 3 — Leidos (LDOS)
- Missile defense / government contractor
- Current ratio 1.62 = can pay bills
- Compare ratios over time AND to peers
- SPLC Bloomberg code: shows suppliers and customers
- EBITDA: cash flow analysis > earnings analysis
- Debt to equity: compare by industry
- Revenue % increase below inflation = concern
- Bloomberg code used: SPLC

---

## 28. Wasden Meeting Transcript — Emery Session

This is a transcript of an actual Wasden investment group meeting. Key content not found elsewhere.

### Wasden's Background
- Founded Caspian Securities in 1996, managed large institutional clients
- Client: Sir John Templeton (founder of Templeton Funds)
- In 2006, Templeton invited Wasden to manage his personal funds directly
- Wasden traveled regularly to Nassau, Bahamas to work with Templeton
- Templeton taught Wasden poker
- The 5-bucket system was created specifically for Templeton's personal money management
- Process has been "remarkably consistent" since 1996

### Country Selection Deep Dive
- US vs. China: incredible divergence — China largely flat, US dramatically up
- Simply choosing the right country and the two broadest indices gives dramatic outperformance
- Three things you must be right on: **interest rates, inflation, currencies**
- Deep capital markets test: capital market trading volume as % of GDP
- Works: Israel, Brazil, most of Europe, China, Hong Kong
- Doesn't work well: small niche markets (Vietnam, Cambodia, Argentina, etc.)

### Instrument Selection Deep Dive (Bucket 1 Example)
- US government bond = risk-free rate in financial theory (government can't default per Constitution)
- Currently: US gov bond at 4.8%, equity FCF yield at 3% → bonds yield more than stocks despite stocks being more risky → get out of stocks on risk-adjusted basis
- Simple metrics that work really, really well

### Sector Level
- 11 sectors, same across all economies worldwide
- Sub-sector level: "phenomenal information"
- Industry group level: information value degrades quickly
- Use FCF yield + quality/growth fundamentals to determine sectors

### Themes vs. Special Situations
- Themes: structural, not cyclical. AI, aging populations, EVs. Long-term trades, more certain.
- Special Situations: hardest to find, highest return. Can be wrong 99/100 times. When right and sized correctly: transformational.
- Quote: "Once you find something that's out of whack, you put a lot of money on that and let it go, and you can earn alpha."
- 94% of returns from first 3 buckets. The last 2 are where "adult size money" is made.

### AI's Role in the Framework (from Wasden himself)
> "What I would like AI to do, especially here, is to find more that aren't obvious... if you can use AI to say I found 50 points or scenarios where the market may be very significantly misjudging prices."

### The Special Situation Example — Crude Oil -$47
During COVID: Crude oil at -$47/barrel. "The market completely froze up." You knew it couldn't stay there — we consume oil every day and run out every month. "Take as many positions as you can... you're an enormous winner if it gets to zero."

Requires identifying the catalyst: "Markets can remain irrational longer than you can remain liquid. What's the catalyst? How do I get out of this?"

### Costco as Current Example
Costco at 55× earnings vs. historical ~20×, growing slower than historically. Elements that justified the premium (faster growth) aren't there. Driven by excess liquidity. How does excess liquidity unwind? Requires a "Minsky moment" — when people suddenly say "this is dumb, I'm not doing this anymore." Internet era, credit crisis — same pattern.

### Modeling Approach Discussed
- Start with historical date (2008, COVID, AI rise, etc.)
- Model to that point → see what it would have predicted
- Compare to what actually happened → iterate
- Test different dates to find where model is strong vs. weak
- Then: "Given this data, what are we missing? Given that we know these things happened later, what other data would have helped us?"
- Confidence interval system: red/yellow/green on conviction

### Long-Term Vision: Replicating Decision-Making
- Use conjoint analysis (Sawtooth software methodology) to quantize Wasden's decision-making
- Each of the 5 buckets has options; sawtooth creates a global model of preferences
- Result: An AI that replicates Wasden's choices without having to ask him each time
- Then merge with Vasu's statistical model approach
- Goal: "An AI that knows where to go, look, can train itself, make decisions, and go back to the five buckets"
- Timeline estimate: "At least six months, a year, I don't think much longer than that"
- End state: "Set it up with Python... make the trades... I don't have to look at it anymore"

### Quote on Obscurity
> "How do we make sure that we're obscure enough that no one pays attention to us while we do this?"
— Wasden on not drawing attention to a successful systematic strategy

---

## 29. Design Decisions Log

| Decision | Resolution |
|----------|-----------|
| Autonomy level | Start as recommendation engine → autonomous later |
| Stock universe | S&P 500 daily screening |
| Trade frequency | Daily evaluation, swing trading primary mode |
| Wasden vs. quant models | Wasden has veto power |
| Buffett Bot role | Advisory only — no vote |
| LLM for bull case | Claude |
| LLM for bear case | Gemini |
| Ensemble/disagreement resolution | 10-agent jury vote |
| Jury trigger | Disagreement after bull/bear debate |
| Jury composition | 10 agents with different fundamental/risk/macro/technical perspectives |
| Database | Supabase (PostgreSQL + pgvector) |
| Frontend hosting | Vercel |
| Repository | Financial Forge (https://github.com/JoeWhiteJr/Financial_Forge) |
| Performance target | 40% weekly return (both partners agree) |
| Operable definition | 60–80% win rate validated on backtesting |
| Drawdown/shutdown trigger | Net zero (losses = gains) + consecutive loss warning |
| Capital cycling | Pull out when capital doubles, reallocate, repeat |
| PDT rule | Swing trading or $25K account |
| Starting capital | Paper money only |
| Bloomberg fallback | Yahoo Finance, Fidelity, M1 |
| Notification system | Signal (primary), Telegram (backup) |
| Google Voice number | NOT yet set up — action item |
| Truth Social | Not a data source. Never was. |
| Finnhub | Free API — confirmed |
| Dow Jones data format | OHLCV + adjusted close, daily CSV, daily at 12am |
| Emery data format | OHLCV, last 10 years, all US stocks |
| Neural networks | Dr. Miller's two R notebooks — port to Python |
| 5 Buckets order | Instrument, Country, Sector, Theme, Special Occasion |
| ANM/dHSIC causal analysis | Phase 4 experiment — do not block earlier phases |
| Continuous learning guardrail | 90-day holdout + human sign-off |
| Daily check-in | Both partners, daily, time doesn't matter |
| Benchmark | 40% weekly return / 60–80% win rate |

---

## 30. Critical Problems & Resolutions

### Problem 1: Wasden Veto — Single Regime Risk
**Status: WATCH CLOSELY**
RAG built on ~30 PDFs from 2022 bear-to-recovery regime. Build regime detection before Wasden veto is applied.

### Problem 2: Survivorship Bias in All Datasets
**Status: WATCH CLOSELY**
32GB minute data AND Emery's 10-year dataset likely missing delisted companies. Audit Week 3 before training anything.

### Problem 3: Buffett Bot Philosophical Mismatch
**Status: RESOLVED**
Advisory only. No vote.

### Problem 4: Ensemble Method
**Status: RESOLVED**
10-agent jury vote. Agents review debate arguments and vote. Aggregate wins. 5-5 split escalates to human. Agents weighted toward fundamental/ratio analysis.

### Problem 5: Continuous Learning Feedback Loop
**Status: WATCH CLOSELY**
Checkpoint mechanism required before autotune. 90-day holdout validation required. Shutdown trigger: net zero performance.

### Problem 6: Bloomberg Expires at Graduation
**Status: RESOLVED**
Fallback: Yahoo Finance, Fidelity, M1. Design fallback from Day 1.

### Problem 7: No Transaction Cost Model
**Status: NEEDS DISCUSSION**
Design ticket for Week 7. Model: bid-ask spread, short/long capital gains split minimum.

---

## 31. Development Phases & Schedule

See `SCHEDULE_v1.md` for full week-by-week breakdown.

### Phase Overview
- **Weeks 1–3:** Foundation — environment, data pipeline, Bloomberg export, schema
- **Weeks 4–5:** Wasden Watch RAG — PDF processing, embeddings, verdict generator
- **Weeks 5–6:** Quant models — XGBoost, Elastic Net, ARIMA, sentiment
- **Week 7:** Decision pipeline — LangGraph, debate, jury, arbitration
- **Week 8:** Risk engine, pre-trade validation, Alpaca execution
- **Week 9:** Prompt engineering polish, stress testing, OWASP review
- **Week 10:** Dashboard, documentation, paper trading launch

### Features Cut From May Scope
| Feature | When |
|---------|------|
| MCP for inter-agent communication | Phase 5+ |
| Neural Network (Tier 3 beyond Dr. Miller) | If Tier 1–2 insufficient |
| ANM/dHSIC Causal Analysis | Phase 4 |
| Live money trading | After 3+ months paper + 60–80% win rate confirmed |
| Buffett Bot | Phase 3 |

---

## 32. Team Structure

| Person | Notes |
|--------|-------|
| Joe | Co-founder |
| Jared | Co-founder |
| Claude Code | AI agent — Dev, Review, Security, QA |
| Emery | External advisor — data assets, architecture feedback |
| Cary Wasden | Investment mentor — philosophy, Weekenders, 5-bucket framework |
| Dr. Wyatt Miller | Statistical advisor — neural network framework, causal analysis methodology |

### Weekly Cadence
1-hour sync weekly. Review tickets → demo what was built → plan next week. No exceptions.

---

## 33. Infrastructure & Tooling

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js / React (Financial Forge repo) |
| Backend | Python (ML, data, trading logic) |
| Database | Supabase (PostgreSQL + pgvector) |
| Vector Store | ChromaDB (Phase 1) → Supabase pgvector (Phase 3) |
| ML Orchestration | LangGraph |
| LLM — Bull / RAG | Claude API (Haiku bulk, Sonnet/Opus deep) |
| LLM — Bear / Jury | Gemini API |
| Trading Execution | Alpaca API |
| News & Sentiment | Finnhub (free) + NewsAPI |
| Statistical Tools | JASP, Google Colab, R-Studio |
| Model Versioning | MLflow (Week 10) |
| Hosting — Frontend | Vercel |
| Hosting — Backend | AWS |
| Notifications | Signal (primary) + Telegram (backup) |
| CI/CD | GitHub Actions |
| Ticketing | GitHub Issues |

---

## 34. Feedback from Collaborators

### Emery's Key Points
- Wasden #1 in energy specifically — not everything (sector concentration risk in RAG)
- Autotune: checkpoint mechanism is critical or it will break itself
- LLM weighting: 55/45 if switching based on market status. Switching is too biased unless you train separate bear/bull models.
- MCP server needs separate server — significant performance cost
- Memory is critical
- Multiple news data sources if serious; Bloomberg covers most of it
- Budget closer to $300/month at full scale
- Penny stocks: worth exploring as parallel strategy
- Slippage model: yes, build it
- Cash account: no PDT limit, just settlement wait
- He has 10 years of S&P 500 OHLCV data — provided

---

## 35. Joe's Goals & Vision

### Performance Targets
- 40% return weekly
- 60–80% accuracy (win rate)
- Keep losses less than wins
- Net zero = shutdown trigger
- Capital doubles → pull out and reallocate → cycle the doubling

### Wasden Watch Philosophy (Joe's Framing)
- Based on Wasden's reasoning and theory, not just what he said
- 5-bucket analysis is the most important framework
- About driving clarity
- About reading the story of the company through its financials
- "The numbers tell stories"
- Ratios are the blood test — standardize by sector for peer comparison
- Looking at other companies that affect the story

---

## 36. Cary Wasden's Life Wisdom

### #1: NEVER LIVE BEYOND YOUR MEANS
- When you make more money, don't change your lifestyle
- Take the excess and invest it — try for 12–14% return
- Put your weakness into a "fun account"

### #2: HAVE A BLAST, LIFE IS SHORT
"You will either wear yourself out or rust yourself out."

### Decision Making
"Never make a decision until you have about 80% of the information needed."

### Self-Mentorship
"You will be your best mentor."

### On Intelligence
> "There is nobody smarter than you out there doing brilliant things. The vast majority of us are just average." — Cary Wasden

### On Wealth
"Is money really the issue? Is it your end goal? Knowing your objective is 90% of the actual result."

---

## 37. Book Recommendations & Reading List

| Book | Author | Context |
|------|--------|---------|
| Black Swan | Nassim Nicholas Taleb | Risk, rare events |
| Antifragile | Nassim Nicholas Taleb | Systems that gain from disorder |
| A Random Walk Down Wall Street | Burton Malkiel | Market efficiency |
| Al Brooks (3 books) | Al Brooks | Price action trading |
| Fabric of the Cosmos | Brian Greene | Broader thinking |
| End of History and the Last Man | Francis Fukuyama | Geopolitics |
| The End of the World | Peter Zeihan | Demographics, macro |
| The Essays of Warren Buffett | Lawrence Cunningham | Buffett Bot corpus |
| The Age of Extraction by the 23 | TBD | Referenced |

**Regular reading:** Barron's (Saturday), Financial Times, WSJ, Bloomberg News, Tom Keen (Bloomberg mornings).

---

## 38. People & References

| Person | Role |
|--------|------|
| Cary Wasden | Mentor, #1 analyst, 5-bucket framework creator, Weekenders source |
| Sir John Templeton | Templeton Funds founder — Wasden managed his personal funds |
| Warren Buffett | Buffett Bot source material |
| Dr. Wyatt Miller | Professor — behavioral framework, neural network models, causal analysis |
| Jeff Singer | Day trading methodology — Renaissance Technologies connection |
| Emery | Technical advisor — data assets, architecture review |
| Joe (White) | Business partner — technical lead, data assets |
| Harry | Group member — questions during Wasden sessions |
| Vasu | Confirmed Alpaca; statistical model expert mentioned in Emery transcript |
| Jacob Veeter | Referenced — context unclear |
| Tom Keen | Bloomberg News morning anchor — recommended by Wasden |
| Peter Zeihan | Geopolitical analyst / author |
| Al Brooks | Price action trading author |
| Jerome Powell | Fed Chair — macro context |

---

## 39. Stocks & Tickers to Watch

| Ticker | Company | Notes |
|--------|---------|-------|
| NVDA | NVIDIA | Pilot — extraordinary fundamentals |
| PYPL | PayPal | Pilot — high FCF yield potential value |
| NFLX | Netflix | Pilot — Cary presented this one |
| TSM | TSMC | Pilot — Debate 2, ADR |
| XOM | Exxon | Pilot — energy (Wasden's #1 sector) |
| AAPL | Apple | Pilot — unusual capital structure |
| MSFT | Microsoft | Pilot |
| AMZN | Amazon | Pilot |
| TSLA | Tesla | Pilot — likely fails Sprinkle Sauce |
| AMD | AMD | Pilot |
| LDOS | Leidos | Debate 3 — missile defense |
| BRK | Berkshire | Watchlist |
| QQQ | Nasdaq ETF | Reference benchmark |
| CRDO | Credo Technology | "Look at this stock" — Debate 1 |
| Anthropic | Anthropic | Pending IPO |

---

## 40. Miscellaneous Ideas & Loose Notes

- Create sheet tracking all buys/sells: return amount, %, daily average; averages cost basis for multiple entries
- Automate web scrub: previous day vs. 5-day and month, news, ML on news, prediction → email recommendation
- Make weird little projects and games — e.g., find stocks that double your money every year
- Fundamentals and options as a combined strategy
- Innovation index — how innovative is a company?
- Make sure Claude archives old versions (don't rewrite what was already created)
- Dashboard output: bad things, good things, why did bad things happen
- Claude Code agents: two-team workflow (development team → review team)
- "How do we make sure we're obscure enough that no one pays attention to us while we do this?" — Wasden

---

## 41. Open Questions & Things to Investigate

### Active (Needs Decision Before Code Is Written)
- Define what "agreement" means quantitatively in the debate — at what confidence threshold does the system skip the jury entirely?
- What specific Finnhub endpoints to use first (sentiment, insider MSPR, fundamentals backup)?
- Conjoint/contract analysis with Sawtooth software — Phase 2 or Phase 5?

### Longer Term
- Corporate actions pipeline (splits, spinoffs, delistings)
- Regime detection to contextualize Wasden veto (prevent bear-era caution misfiring in bull market)
- Simultaneous signal priority: ROI ranking + human selects from shortlist
- ANM/dHSIC causal analysis (Phase 4)

---

*End of Knowledge Base v2.0*
*Last Updated: February 23, 2026*
*Next review: End of Week 1 of development*
