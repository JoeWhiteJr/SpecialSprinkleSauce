# Wasden Investment Philosophy -- Comprehensive Reference

> Structured documentation of Cary Wasden's investment framework as implemented in the Wasden Watch trading system. Sourced from the Wasden Weekender newsletter corpus, the Emery meeting transcript, `KNOWLEDGE_BASE_v2.md` Sections 3, 7, 8, and the RAG pipeline codebase.
>
> Version: 2.0 | Last Updated: February 26, 2026

---

## 1. Overview: What Is the Wasden Watch?

The Wasden Watch is the qualitative intelligence layer of the Wasden Watch trading system -- a Retrieval-Augmented Generation (RAG) pipeline that applies Cary Wasden's investment philosophy to evaluate stock candidates. It occupies **Node 2** of the 10-node decision pipeline and holds the **highest authority** in the system: a Wasden Watch VETO immediately blocks a trade, short-circuiting all subsequent pipeline stages (debate, jury, risk check, pre-trade validation).

### 1.1 Role in the System

The Wasden Watch serves three distinct functions:

1. **Qualitative filter:** Evaluates whether a stock candidate aligns with Wasden's investment principles before any debate or jury deliberation occurs.
2. **Veto authority:** Can unilaterally block trades that contradict Wasden's philosophy, regardless of quantitative model scores.
3. **Confidence input:** The Wasden confidence score directly influences position sizing via the DecisionArbiter formula: `MAX_POSITION_PCT * wasden_confidence * (1 - quant_std_dev)`.

### 1.2 Why This Approach

The system is anchored in Cary Wasden's methodology because:

- Wasden was ranked the #1 financial analyst in the US, with particular dominance in the energy sector
- He managed money for large institutional clients including Sir John Templeton (founder of Templeton Funds)
- His 5-bucket framework was created specifically for Templeton to systematize portfolio management
- His process has been "remarkably consistent" since founding Caspian Securities in 1996
- The AI system is designed to codify *how Wasden thinks*, not just *what he said*

> *"The numbers tell stories."* -- Cary Wasden
> *"Markets can remain irrational longer than you can remain liquid."* -- Cary Wasden

---

## 2. The 5-Bucket Analysis Framework

This is the most important framework in the entire system. Created for Sir John Templeton. The framework organizes all investment analysis into five hierarchical categories, ordered by their contribution to returns and reliability.

**Return distribution:** Buckets 1-3 account for 94% of returns. Buckets 4-5 are where "adult size money" is made but with higher volatility.

### 2.1 Bucket 1: Instruments

**Core question:** What type of asset should we own -- equities or fixed income?

**Categories:**
- Equities: large value, growth, and other styles
- Fixed income: sovereign (government bonds), corporate investment grade, municipal, non-investment grade

**Trigger mechanism:** Risk-adjusted yield comparison. The US government bond yield (risk-free rate) is the benchmark. Every additional risk taken must be compensated. If it is not, that is a signal.

**Example:** US government bond at 4.8% vs. equity FCF yield of 3% = get out of stocks on a risk-adjusted basis.

**System implementation:** The Bucket 1 Instrument Signal compares equity FCF yield (via Bloomberg `FREE_CASH_FLOW_YIELD`) to the US 10-year Treasury yield. When the bond yield exceeds the equity FCF yield, the system surfaces a portfolio-level alert recommending reduced equity exposure. This signal is logged in the decision journal and displayed on the dashboard.

**Real-world data point (Oct 2025 newsletter):** S&P 500 free cash flow yield at 2.6% vs. 10-year government bond yield at 4.0% -- bond yield excess over stock yield at historic highs, a classic Bucket 1 warning signal.

### 2.2 Bucket 2: Countries

**Core question:** Which country's markets should we be in?

**Primary markets:** United States, China/Hong Kong (two different markets, both viable), Brazil, Israel, most of Europe, Japan, South Korea.

**Selection criteria -- must be right on all three:**
1. Interest rates
2. Inflation
3. Currencies

**Requirements:** Deep capital markets (gauge by trading volume as % of GDP), rule of law, clear property rights, independent judiciary. Small/niche markets (Vietnam, Cambodia, Argentina) do not work well -- the smaller the market, the less reliable the pricing signals.

**Key insight from the Emery transcript:** Simply knowing which country to be in and choosing the two broadest indices gives dramatic outperformance. There are times when switching is appropriate -- China was the best-performing stock market 3 years prior to the transcript date. The US-China divergence has been enormous.

**System relevance:** The current system focuses on US equities (S&P 500 universe). Country-level analysis is surfaced through the Wasden Watch RAG when newsletter passages discuss international market dynamics. The newsletters frequently cover Hong Kong/China performance and international comparisons.

### 2.3 Bucket 3: Sectors

**Core question:** Which sectors should receive allocation?

**Framework:** The 11 GICS sectors are the same across every economy worldwide. Analysis at the sub-sector level is phenomenal; at the industry group level, information value degrades.

**Method:** Use FCF yield plus quality and growth fundamentals to determine sector allocation. Compare sectors within the same economy and across economies.

**System implementation:** The screening pipeline tracks sector exposure in recommendations. The risk engine enforces a 40% maximum sector concentration limit. Sector rotation signals come through the Wasden Watch RAG when newsletter passages discuss sector dynamics.

### 2.4 Bucket 4: Themes (Long-Term Structural)

**Core question:** What secular trends will drive returns regardless of short-term market cycles?

**Current themes identified in the corpus:**
- Artificial intelligence and technology infrastructure
- Aging populations (particularly China -- called "one of the more devastating economic events to happen in your generation")
- Renewable energy and electric vehicles
- Infrastructure spending

**Key characteristic:** These are NOT cyclical. They are structural. They will not be materially affected by whether we hit a recession. Long-term trades, but with more certainty than special situations.

**System implementation:** Theme analysis is implicit in the RAG pipeline. When the Wasden Watch retrieves passages discussing AI, demographics, or energy transition, these themes influence the verdict.

### 2.5 Bucket 5: Special Occasions / Special Situations

**Core question:** Is the market dramatically wrong about something right now?

This is the highest-volatility, highest-return bucket. Special situations "present themselves" -- you cannot go searching for them easily. When they appear, they are obvious to those paying attention.

**Characteristics:**
- Requires long staying power OR very clear catalyst identification
- Must have a confidence interval on conviction -- big money only on high-confidence situations
- Can be wrong 99 of 100 times; if sized correctly, the one right call is transformational
- Key question always: "What is the catalyst? How do I get out? What happens for the market to return to normalcy?"

**Example from Emery transcript:** Crude oil at -$47/barrel during COVID. You knew it could not stay there more than a month because we consume oil every day and run out every month. Take as many positions as possible. Enormous winner once it returned to zero.

**Example from corpus:** Costco at 55x earnings vs. historical ~20x, growing slower than historically. Excess liquidity-driven mispricing. The question is: what is the catalyst (the "Minsky moment") that brings it back?

**What Wasden wants from AI:**
> "What I would like AI to do, especially here, is to find more that aren't obvious... if you can use AI to say I found 50 points or scenarios where the market may be very significantly misjudging prices."

The AI is not just implementing existing rules -- it is finding mispricings Wasden could not find manually. Special situations at scale.

---

## 3. Coverage Modes

The Wasden Watch operates in two distinct modes, determined automatically by analyzing whether the stock ticker appears in retrieved newsletter passages.

### 3.1 Direct Coverage Mode

**Trigger:** The ticker appears in 3 or more of the top retrieved passages (configurable via `direct_coverage_min_passages` in `WasdenWatchSettings`).

**Meaning:** Wasden has explicitly discussed this stock, sector, or closely related topic in the newsletter corpus. The system can draw on specific commentary and context.

**Confidence bounds:** 0.75 to 0.95. Direct coverage allows higher confidence because the verdict is grounded in Wasden's actual analysis rather than inferred principles.

**Example from mock data:** NVDA (direct semiconductor thesis alignment), AAPL (consistent Wasden favorite -- ecosystem strength), MSFT (AI infrastructure play directly referenced), AMD (semiconductor thesis alignment).

### 3.2 Framework Application Mode

**Trigger:** The ticker appears in fewer than 3 retrieved passages (or not at all).

**Meaning:** Wasden has not directly covered this stock. The system applies his 5-bucket framework, ratio analysis principles, and macro/sector views from the corpus to evaluate an unfamiliar ticker.

**Confidence bounds:** 0.50 to 0.75. Framework application carries lower confidence because the system is extrapolating principles rather than citing specific analysis.

**Example from mock data:** PYPL (fintech growth thesis applied from framework), NFLX (framework suggests caution on valuation), TSM (geopolitical risk factors from framework).

### 3.3 Fallback Mode

**Trigger:** The primary LLM (Claude) fails and the system falls back to Gemini for verdict generation.

**Confidence cap:** 0.60 maximum. When using the fallback LLM, confidence is capped lower because the secondary model may not replicate the primary model's interpretation quality.

### 3.4 Mode Prompt Instructions

The prompt adjusts based on mode (from `prompt_templates.py`):

- **Direct coverage:** "This ticker appears directly in {n} retrieved passages. Analyze the specific commentary and context from the newsletters."
- **Framework application:** "This ticker does not appear directly in the newsletter corpus. Apply the Wasden Weekender's 5-bucket analytical framework to evaluate it based on the macro, sector, and market context from the retrieved passages."

---

## 4. Verdict Taxonomy

### 4.1 APPROVE

**Meaning:** The weight of evidence across the 5 buckets supports a positive investment thesis. Most buckets are favorable, and risks are manageable.

**Confidence range:** Typically 0.70-0.95 (direct coverage) or 0.50-0.75 (framework application).

**Pipeline effect:** Trade proceeds to the bull/bear debate. Wasden confidence influences position sizing.

### 4.2 NEUTRAL

**Meaning:** Mixed signals across buckets. Some positive, some negative. Insufficient conviction to take a strong position. Wait for more clarity.

**Confidence range:** Typically 0.40-0.70.

**Pipeline effect:** Trade proceeds to debate, but the lower confidence reduces position sizing. In the screening pipeline (Tier 4), NEUTRAL is treated as a pass -- the trade is not blocked.

### 4.3 VETO

**Meaning:** Significant red flags in multiple buckets. Unfavorable risk/reward. Active reasons to avoid or exit the position.

**Minimum confidence requirement:** 0.85. If the LLM returns a VETO verdict with confidence below 0.85, the system automatically downgrades it to NEUTRAL. This prevents low-conviction vetoes from blocking trades.

**Pipeline effect:** Immediate short-circuit. The trade is BLOCKED. No debate, no jury, no risk check. The VETO is logged with full reasoning.

**Override mechanism:** Humans (specifically Jared) can override a VETO. Every override is logged as a separate `VetoOverrideRecord` with the overrider's identity, reasoning, and timestamp. All overrides are reviewed in the weekly bias monitoring report.

### 4.4 Confidence Calibration Guidelines

The LLM is instructed to calibrate confidence as follows (from `prompt_templates.py`):

| Confidence Range | Meaning |
|-----------------|---------|
| 0.90-0.95 | Very high confidence, strong evidence across most buckets |
| 0.75-0.89 | High confidence, clear directional signal with minor uncertainties |
| 0.60-0.74 | Moderate confidence, some conflicting signals |
| 0.50-0.59 | Low confidence, limited direct evidence, relying on framework extrapolation |

### 4.5 Decision Journal Schema

Every verdict is recorded in the decision journal with the following structure (from `PROJECT_STANDARDS_v2.md` Section 4):

```json
{
  "wasden_verdict": {
    "verdict": "APPROVE | NEUTRAL | VETO",
    "confidence": 0.85,
    "reasoning": "2-4 paragraph analysis covering relevant buckets",
    "mode": "direct_coverage | framework_application",
    "passages_retrieved": 10
  }
}
```

---

## 5. Corpus Summary: The Wasden Weekender Newsletters

### 5.1 Overview

The corpus consists of **28 PDF newsletters** published under the "Wasden Weekender" brand by various imprints of Cary Wasden's analytical practice. The newsletters are in native text format (text is selectable/copyable), typically 4-12 pages each, and include charts and images.

Permission to use the newsletters has been confirmed.

### 5.2 Date Range and Distribution

- **Earliest:** June 12, 2022 ("Finding the Bogeyman")
- **Latest:** January 31, 2026 ("All That Glitters")
- **Gap:** No newsletters from July 2022 to August 2024 (approximately 25 months). Video sessions from this period exist but have not been processed.

| Year | Count | Date Range |
|------|-------|-----------|
| 2022 | 5 | June 12 - July 17 |
| 2024 | 5 | August 18 - November 23 |
| 2025 | 16 | February 18 - November 16 |
| 2026 | 2 | January 10 - January 31 |

### 5.3 Author/Imprint Variations

The newsletters appear under several related imprints:

| Author/Imprint | Count | Notes |
|----------------|-------|-------|
| Archimedes Insights and Analytics | 10 | Original imprint |
| KT Insights and Analytics | 10 | Primary 2025 imprint |
| Wasden Weekender | 2 | Feb 2025 issues |
| Black Box Insights and Analytics | 1 | Nov 2024 |
| Archimedes Black Box | 1 | Oct 2024 |
| Investor Solutions | 1 | Nov 2024 |

All are authored by Cary Wasden and represent the same analytical framework.

### 5.4 Topic Coverage

Based on the `newsletter_metadata.json` tags across all 28 newsletters, the most frequently covered topics are:

| Topic | Frequency (of 28) | Notes |
|-------|--------------------|-------|
| Federal Reserve policy / Monetary policy | 27 | Near-universal; central to macro analysis |
| Inflation | 25 | Core concern throughout corpus period |
| Consumer spending | 23 | Key economic indicator Wasden tracks |
| Earnings season | 21 | Quarterly recurring topic |
| Labor market | 18 | Employment data as economic signal |
| Tariffs | 12 | Dominant in 2025 issues |
| Fixed income / Bonds | 17 | Bucket 1 instrument analysis |
| AI / Technology | 13 | Recurring theme, especially 2024-2025 |
| Recession risk | 14 | Persistent concern |
| Geopolitics | 10 | Including election, trade wars, Middle East |
| Valuation | 8 | Market-wide and individual stock |
| Stagflation | 4 | Raised in bear market periods |
| Cryptocurrency / Bitcoin | 3 | Mentioned but not core focus |

### 5.5 Sector Coverage

| Sector | Frequency | Notes |
|--------|-----------|-------|
| US Equities | 28 | Every issue |
| Fixed Income | 22 | Bond market analysis |
| Technology | 21 | Including semiconductors, AI |
| Consumer / Retail | 18 | Spending trends |
| International / Emerging Markets | 13 | China, Hong Kong, Brazil |
| Energy | 8 | Wasden's #1 sector expertise |
| Financials | 7 | Bank earnings, credit conditions |
| Real Estate | 6 | Mortgage rates, construction |
| Commodities | 5 | Gold, oil, copper |
| Utilities | 4 | Defensive positioning |
| Healthcare | 2 | Limited coverage |
| Communications | 2 | Limited coverage |

### 5.6 Market Regime Coverage

The corpus spans three distinct market regimes:

1. **2022 Bear Market (June-July 2022):** 5 issues covering the inflation shock, aggressive Fed tightening, S&P 500 decline of -22.9% YTD. CPI peaked at 9.1%. Consumer sentiment hit all-time lows.

2. **2024 Recovery/Bull (August-November 2024):** 5 issues covering the S&P 500 recovery to all-time highs, AI enthusiasm, election impact, rate cut expectations, Bitcoin resurgence.

3. **2025-2026 Tariff/Uncertainty (February 2025-January 2026):** 18 issues covering tariff volatility (-18.9% peak-to-trough Feb-Apr 2025), stagflation concerns, consumer debt at record levels, AI capex boom, and gradual recovery.

### 5.7 Key Recurring Data Points

The newsletters frequently reference these metrics (useful for understanding what data Wasden considers most important):

- S&P 500 year-to-date return and PE ratio
- 10-year Treasury yield
- CPI and PPI (headline and core)
- Consumer sentiment (University of Michigan)
- Monthly job creation figures
- Magnificent Seven market share and performance
- Individual stock valuations (Costco, NVDA, TSLA frequently cited)

---

## 6. Time-Decay Weighting

### 6.1 Mechanism

The vector store applies exponential time-decay weighting to retrieved passages. More recent newsletters receive higher weight, reflecting the principle that recent market analysis is more relevant than older analysis.

### 6.2 Formula

```python
time_decay_weight = 0.5 ** (days_old / half_life)
final_score = relevance_score * time_decay_weight
```

Where:
- `days_old` = number of days between the newsletter date and today
- `half_life` = 365 days (configurable via `time_decay_half_life_days` in `WasdenWatchSettings`)
- `relevance_score` = cosine similarity from ChromaDB (converted from distance: `1.0 - distance`)

### 6.3 Practical Effect

| Newsletter Age | Time Decay Weight | Effect |
|---------------|------------------|--------|
| Today | 1.000 | Full weight |
| 6 months (183 days) | 0.707 | ~71% weight |
| 1 year (365 days) | 0.500 | 50% weight |
| 2 years (730 days) | 0.250 | 25% weight |
| 3 years (1095 days) | 0.125 | 12.5% weight |

This means the June 2022 newsletters (approximately 3.7 years old at current date) receive roughly 10% of their relevance weight, while January 2026 newsletters receive nearly full weight.

### 6.4 Over-Retrieval and Re-Ranking

The search retrieves 3x the requested `top_k` passages from ChromaDB, applies time-decay weighting, re-ranks by `final_score`, and returns only the top `top_k` results. This ensures that a highly relevant but older passage can still surface if its content relevance score is high enough to overcome the time decay.

---

## 7. RAG Pipeline Architecture

### 7.1 Pipeline Flow

```
PDF Corpus -> Text Extraction -> Chunking -> Embedding -> ChromaDB Storage
                                                              |
Search Query -> Embedding -> Vector Similarity -> Time-Decay Re-ranking
                                                              |
Retrieved Passages -> Prompt Construction -> LLM (Claude/Gemini) -> Verdict
                                                              |
                                              Verdict Logging -> Supabase
```

### 7.2 PDF Processing (`pdf_processor.py`)

1. **Input:** PDF files from `data/wasden_corpus/` directory
2. **Metadata:** Loaded from `data/wasden_corpus/newsletter_metadata.json` (date, title, author, topics, sectors per file)
3. **Text extraction:** PyMuPDF (`fitz`) extracts text from each page. Pages are joined with double newlines.
4. **Chunking:** Text is tokenized using `tiktoken` (`cl100k_base` encoding) and split into chunks of ~600 tokens with 100-token overlap.
5. **Output:** List of `CorpusDocument` objects and flat list of `TextChunk` objects ready for embedding.

### 7.3 Chart/Image Processing (`chart_describer.py`)

When Wasden writes "as you can see from the chart below," the text extraction captures the sentence but loses the chart. The `ChartDescriber` class handles this:

1. Extracts images from PDFs using PyMuPDF
2. Filters out small images (< 5KB, likely icons/logos)
3. Sends each image to Claude Vision API for description
4. Returns text descriptions of financial charts and data visualizations

This is a one-time cost per PDF and enriches the corpus with visual data context.

### 7.4 Vector Store (`vector_store.py`)

- **Backend:** ChromaDB with persistent storage (local directory at `local/chroma_wasden_watch/`)
- **Embedding model:** `all-MiniLM-L6-v2` via SentenceTransformers (384-dimensional embeddings)
- **Distance metric:** Cosine similarity (`hnsw:space = cosine`)
- **Collection name:** `wasden_weekender`
- **Batch ingestion:** Processes chunks in batches of 500 to stay within ChromaDB limits
- **Deduplication:** If the collection already has >= the expected chunk count, ingestion is skipped

### 7.5 LLM Client (`llm_client.py`)

- **Primary:** Claude Sonnet (currently `claude-sonnet-4-20250514`)
- **Fallback:** Gemini Flash (currently `gemini-2.5-flash`)
- **Key rotation:** Round-robin across up to 2 API keys per provider
- **Response parsing:** Handles raw JSON, markdown-wrapped JSON, and brace-extracted JSON
- **Temperature:** 0.3 (low for consistency)
- **Max tokens:** 2048

### 7.6 Verdict Generation (`verdict_generator.py`)

The `VerdictGenerator` orchestrates the full pipeline:

1. **Ensure ingestion:** Check if vector store is populated; ingest PDFs if not.
2. **Search:** Query vector store with `"{ticker} {company_name} {sector}"`.
3. **Determine mode:** Count direct ticker mentions in retrieved passages. If >= 3 mentions: `direct_coverage`. Otherwise: `framework_application`.
4. **Build prompt:** Assemble system prompt (5-bucket framework + verdict guidelines) and user prompt (ticker info, fundamentals, retrieved passages, mode instruction).
5. **Call LLM:** Claude primary, Gemini fallback.
6. **Clamp confidence:** Apply mode-specific confidence bounds.
7. **Enforce VETO threshold:** If verdict is VETO but confidence < 0.85, downgrade to NEUTRAL.
8. **Log verdict:** Write to Supabase `wasden_verdicts` table (optional, never crashes caller).
9. **Return:** `VerdictResponse` with verdict, confidence, reasoning, mode, passages, model used, corpus stats.

---

## 8. Integration Points in the Decision Pipeline

### 8.1 Position in the 10-Node Pipeline

```
Node 1: Quant Scoring (4 models)
Node 2: WASDEN WATCH <-- HERE
  |
  +-- VETO --> Skip to Node 10 (BLOCKED)
  +-- APPROVE/NEUTRAL --> Continue to debate
  |
Node 3: Bull Researcher (Claude)
Node 4: Bear Researcher (Gemini)
Node 5: Structured Debate (up to 3 rounds)
Node 6: Jury Spawn (if disagreement)
Node 7: Jury Aggregate (if jury spawned)
Node 8: Risk Check (7 checks)
Node 9: Pre-Trade Validation (4 checks, SEPARATE from risk)
Node 10: Decision Arbiter (priority rules + position sizing)
```

### 8.2 VETO Short-Circuit Behavior

When the Wasden Watch returns a VETO verdict:

1. `state.wasden_vetoed` is set to `True`
2. The pipeline immediately jumps to Node 10 (DecisionArbiter)
3. DecisionArbiter Rule 1 fires: `final_action = "BLOCKED"`, `recommended_position_size = 0.0`
4. No debate, no jury, no risk check, no pre-trade validation is executed
5. The decision journal records the VETO with full reasoning

This short-circuit saves LLM API calls and prevents the system from wasting resources debating a fundamentally flawed trade.

### 8.3 Screening Pipeline Integration (Tier 4)

In the 5-tier screening pipeline (`screening_engine.py`), the Wasden Watch appears as Tier 4:

- **Tier 1:** Liquidity (market cap > $5B)
- **Tier 2:** Sprinkle Sauce (PEG < 2.0, FCF yield > 3%, Piotroski >= 5)
- **Tier 3:** Quant Models (composite > 0.55, no high disagreement)
- **Tier 4:** Wasden Watch (VETO = fail, APPROVE/NEUTRAL = pass)
- **Tier 5:** Final Selection (top 5 by `composite_quant * wasden_confidence`)

### 8.4 Position Sizing Influence

The Wasden confidence score directly influences position sizing in the DecisionArbiter:

```python
position_size = MAX_POSITION_PCT * wasden_confidence * (1 - quant_std_dev)
```

Where `MAX_POSITION_PCT = 0.12` (12% of portfolio, PROTECTED constant).

Example calculations:
- High confidence (0.85) + low disagreement (0.10): `0.12 * 0.85 * 0.90 = 0.0918` (9.18%)
- Moderate confidence (0.60) + moderate disagreement (0.30): `0.12 * 0.60 * 0.70 = 0.0504` (5.04%)
- Low confidence (0.50) + high disagreement (0.55): `0.12 * 0.50 * 0.45 = 0.0270`, then halved = 1.35%

### 8.5 Jury Agent #10

One of the 10 jury agents (Agent #10) is specifically dedicated to the Wasden 5-bucket framework. This agent receives the full debate transcript and evaluates arguments through Wasden's analytical lens. It is the only jury agent with deep Wasden context.

---

## 9. Core Philosophical Principles

These principles are extracted from the Wasden Weekender corpus, the Emery meeting transcript, and `KNOWLEDGE_BASE_v2.md` Section 7.

### 9.1 Cash Flow Over Earnings

FCF is Wasden's #1 favorite metric. Earnings can be misrepresented; cash flow is harder to manipulate. The system implements this through:
- FCF yield as a Tier 2 screening criterion (> 3%)
- FCF yield vs. bond yield as the Bucket 1 instrument signal
- FCF-to-Net Income ratio (> 1.0 = strong cash generation)

### 9.2 The "Blood Test" Approach to Ratios

Ratios are like a blood test -- they tell you something is wrong, but they do not diagnose. When a ratio is abnormal, you must go into the story to understand why. The 5 categories that tell "99% of the story":

1. **Valuation** (PE, PEG, Price/Cash Flow)
2. **Profitability** (ROE, ROC, margins)
3. **Liquidity** (Current ratio, Quick ratio)
4. **Leverage** (Debt/Equity)
5. **Efficiency** (CCC, Asset turnover)

### 9.3 Discipline Over Brilliance

- "Don't have to be brilliant, just be thoughtful"
- Know when you get out BEFORE you get in -- have a sell discipline
- Emotions ruin trading; discipline eliminates emotion
- Never make a decision until you have about 80% of the information needed

### 9.4 Morning Portfolio Review

Every morning, look at your portfolio. Ask: "If I had to buy today, would I still want to buy?" If not: examine short vs. long-term gain differences, check if they surpass or drop below your threshold, check PE earnings now and next year.

### 9.5 Three Things to Focus On

1. **Unit growth** -- are they selling more stuff?
2. **Pricing power** -- need a competitive environment
3. **Balance sheet matters** -- how quickly a company can go from non-existence to success

### 9.6 Technical Analysis Role

Technical trading determines WHEN to trade, NOT WHAT to trade. Fundamentals tell you what to buy; technicals tell you when to buy it. Bollinger Bands + RSI should be used together -- wait for both to align before acting. Never use one alone.

### 9.7 Contrarian Thinking

- Buy when people are fearful, sell when people are greedy
- Every time you see something positive, ask why -- then try to prove it wrong
- Always ask "why" repeatedly until you reach the root cause
- Markets move on expectations: meeting, missing, or exceeding them

### 9.8 Cash Reserves

Always have cash. Wait for the moment when you want to buy. There WILL be a time in the near future. Keep cash so you can buy opportunities AND absorb losses.

### 9.9 On Analyst Recommendations

Useful for insights, NOT good for decision making. Analysts' firms meet with the companies they cover and have incentives to make stocks look good.

### 9.10 Standard Deviation Re-evaluation

Any time an evaluation moves or is off by a standard deviation, re-evaluate purchases. Volatility allows you to get in and out to reset over and over.

### 9.11 Temporal Horizon

Do not look past 2 years into the future. Precision of language -- talk in numbers. Is it cheaper or expensive? Always return to this question.

---

## 10. Known Limitations

### 10.1 Temporal Coverage Gap

The corpus has a 25-month gap between July 2022 and August 2024. This means the system lacks direct newsletter coverage of:
- The 2023 regional banking crisis (Silicon Valley Bank, First Republic)
- The 2023 AI boom inception (ChatGPT launch and initial market reaction)
- The 2023-2024 Fed pause period
- The start of the 2024 rate cut cycle

Video sessions from this period exist but have not been processed. This is a pending action item.

### 10.2 Single Regime Risk

The corpus is built on newsletters from a specific set of market regimes: post-COVID inflation, aggressive Fed tightening, recovery, and tariff-driven volatility. Bear-market caution language from 2022 may incorrectly veto valid bull-market trades in a different regime.

**Mitigation (planned):** Regime detection logic that contextualizes Wasden's caution passages against current conditions. Design ticket required.

### 10.3 Sector Coverage Bias

Wasden's expertise is strongest in energy. The corpus has heavy coverage of macro/Fed policy and technology but lighter coverage of healthcare, industrials, and utilities. Framework application mode is used more frequently for sectors with thin corpus coverage, resulting in lower confidence scores for those sectors.

### 10.4 Chart Loss During Extraction

When Wasden references visual data ("as you can see from the chart below"), the text extraction captures the reference but loses the chart. The `ChartDescriber` module addresses this with Claude Vision processing, but this is an optional enrichment step that adds cost and latency.

### 10.5 Confidence Clamping May Suppress Signal

The confidence bounds (direct_coverage: 0.75-0.95; framework_application: 0.50-0.75) mean the LLM's raw confidence is always clamped. A highly confident framework-application verdict is capped at 0.75, which reduces position sizing even when the signal may be strong. This is a deliberate conservatism.

### 10.6 VETO Confidence Floor

The 0.85 minimum confidence for VETO means weak vetoes are downgraded to NEUTRAL. While this prevents spurious blocks, it could also allow problematic trades through if the LLM is uncertain about its negative assessment. All downgraded vetoes are logged for monitoring.

### 10.7 Corpus Size

28 newsletters over 3.7 years is a modest corpus. The vector store may have limited coverage for niche topics. Planned expansion includes requesting pre-June 2022 newsletters from Wasden and processing the video sessions.

### 10.8 No Live Market Data in RAG

The RAG pipeline retrieves from a static corpus. It does not have access to live market data, current prices, or real-time news. Current market context must be provided to the LLM via the `fundamentals` field in `VerdictRequest` and through the prompt construction in `verdict_generator.py`.

---

## 11. API and CLI Access

### 11.1 REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/wasden-watch/verdict` | POST | Generate a verdict for a ticker (accepts `VerdictRequest` body) |
| `/api/wasden-watch/corpus/stats` | GET | Return vector store statistics (chunk count, date range) |
| `/api/wasden-watch/corpus/search` | GET | Debug search endpoint (`?query=...&top_k=5`) |

### 11.2 CLI Commands

```bash
# Ingest PDF corpus into vector store
python -m app.cli.wasden_cli ingest [--force]

# Generate a verdict for a single ticker
python -m app.cli.wasden_cli verdict NVDA --company "NVIDIA" --sector "Technology"

# Show vector store statistics
python -m app.cli.wasden_cli stats

# Search the corpus directly
python -m app.cli.wasden_cli search "inflation Federal Reserve" --top-k 5

# Run verdicts for all 11 pilot tickers
python -m app.cli.wasden_cli pilot [--top-k 10]
```

---

## 12. Data Model and Storage

### 12.1 Supabase Table: `wasden_verdicts` (Migration 015)

```sql
CREATE TABLE wasden_verdicts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ticker TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('APPROVE', 'NEUTRAL', 'VETO')),
  confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  reasoning TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('direct_coverage', 'framework_application', 'fallback')),
  model_used TEXT NOT NULL,
  passages_retrieved INT NOT NULL DEFAULT 0,
  generated_at TIMESTAMPTZ NOT NULL
);
```

### 12.2 Key Pydantic Models (from `src/intelligence/wasden_watch/models.py`)

- **`VerdictRequest`**: Input -- ticker, company_name, sector, fundamentals dict, top_k
- **`WasdenVerdict`**: Output -- verdict (APPROVE/NEUTRAL/VETO), confidence, reasoning, mode, passages_retrieved, key_passages
- **`VerdictResponse`**: Wrapper -- ticker, verdict, generated_at, model_used, corpus_stats
- **`CorpusDocument`**: PDF metadata -- filename, date, title, author, topics, sectors, full_text, chunks
- **`TextChunk`**: Embedding unit -- chunk_id, text, source_filename, source_date, source_title, token_count
- **`RetrievedPassage`**: Search result -- text, source info, relevance_score, time_decay_weight, final_score

---

## 13. Configuration Reference

All configuration lives in `src/intelligence/wasden_watch/config.py` via `WasdenWatchSettings` (pydantic-settings, loaded from `.env`):

| Setting | Default | Description |
|---------|---------|-------------|
| `pdf_corpus_path` | `data/wasden_corpus` | Path to PDF files |
| `metadata_path` | `data/wasden_corpus/newsletter_metadata.json` | Newsletter metadata file |
| `chroma_persist_dir` | `local/chroma_wasden_watch` | ChromaDB storage directory |
| `chunk_size_tokens` | 600 | Target chunk size (500-800 range) |
| `chunk_overlap_tokens` | 100 | Overlap between consecutive chunks |
| `default_top_k` | 10 | Default number of passages to retrieve |
| `time_decay_half_life_days` | 365 | Half-life for time-decay weighting |
| `claude_model` | `claude-sonnet-4-20250514` | Primary LLM model |
| `gemini_model` | `gemini-2.5-flash` | Fallback LLM model |
| `max_tokens` | 2048 | Max response tokens from LLM |
| `temperature` | 0.3 | LLM temperature (low for consistency) |
| `direct_coverage_confidence_min` | 0.75 | Min confidence for direct coverage mode |
| `direct_coverage_confidence_max` | 0.95 | Max confidence for direct coverage mode |
| `framework_confidence_min` | 0.50 | Min confidence for framework application mode |
| `framework_confidence_max` | 0.75 | Max confidence for framework application mode |
| `veto_min_confidence` | 0.85 | Minimum confidence required for VETO |
| `fallback_max_confidence` | 0.60 | Max confidence when using Gemini fallback |
| `direct_coverage_min_passages` | 3 | Minimum ticker mentions for direct coverage mode |

---

## 14. Background: Cary Wasden

Cary Wasden founded Caspian Securities in 1996. He managed money for large institutional clients including Sir John Templeton, the founder of Templeton Funds. In 2006, Templeton personally invited Wasden to manage his private wealth. Wasden would travel regularly to Nassau, Bahamas to meet with Templeton. The 5-bucket system was created specifically for Templeton to systematize money management.

Wasden is considered one of the top financial analysts in the US, particularly dominant in the energy sector. His process has been "remarkably consistent" for three decades.

### 14.1 Long-Term Vision

Wasden and the team discussed using conjoint/contract analysis (Sawtooth software methodology) to quantize Wasden's decision-making process -- essentially building an AI that replicates how he makes decisions, not just what decisions he makes. Combined with statistical models, the goal is a merged AI system that can train itself based on heuristics from multiple decision-making processes.

### 14.2 Wasden's Life Principles (from KNOWLEDGE_BASE)

- "Don't have to be brilliant, just be thoughtful"
- Discipline yourself to let the numbers tell the story
- Precision of language -- talk in numbers
- Always ask why, repeatedly
- Volatility is opportunity, not danger
