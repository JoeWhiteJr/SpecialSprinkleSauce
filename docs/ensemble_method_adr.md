# Architecture Decision Record: Ensemble Method for Trading Decisions

> **Status:** Accepted
> **Date:** February 26, 2026
> **Authors:** Joe White, Jared Wasden
> **Stakeholders:** Cary Wasden (advisor), Dr. Wyatt Miller (neural network models)
> **References:** PROJECT_STANDARDS_v2.md (Sections 2, 8), KNOWLEDGE_BASE_v2.md (Sections 2, 5, 6, 11, 13), CLAUDE_v2.md

---

## Context

Wasden Watch is an automated trading system that must make daily BUY, SELL, or HOLD decisions across a screened universe of approximately 8 candidate stocks. Trading decisions carry real financial consequences, and the system manages actual capital after a paper-trading validation phase.

No single model, no single human, and no single AI agent can reliably outperform the market across all regimes. Individual models suffer from overfitting, regime sensitivity, and blind spots. Single-agent AI systems exhibit confirmation bias, hallucination risk, and inability to self-critique. Human judgment is slow, emotional, and inconsistent under pressure.

The system requires an architecture that:

1. **Aggregates diverse signal types** -- quantitative scores, qualitative investment philosophy (Wasden's 30+ years of expertise), fundamental analysis, macro awareness, technical signals, and risk assessment.
2. **Surfaces genuine disagreement** rather than papering over it with simple averaging.
3. **Preserves human oversight** at critical decision points, particularly when the system cannot reach conviction.
4. **Produces a complete audit trail** that explains every decision in human-readable terms.
5. **Degrades gracefully** when individual components fail or disagree.
6. **Prevents any single model or agent from dominating** the decision unfairly.

This ADR documents the multi-layer ensemble architecture chosen to meet these requirements.

---

## Decision

### Architecture Overview

The system uses a **5-layer ensemble pipeline** that progresses from quantitative scoring through qualitative debate to jury adjudication, with risk filtering and human escalation gates at each critical juncture. The pipeline is implemented as a 10-node directed graph (`DecisionPipeline` in `src/pipeline/decision_pipeline.py`) with conditional edges.

```
                         +-------------------+
                         |  Quant Ensemble   |
                         |  (4 models)       |
                         +--------+----------+
                                  |
                                  v
                         +-------------------+
                         |  Wasden Watch RAG |
                         |  (APPROVE/NEUTRAL |
                         |   /VETO)          |
                         +--------+----------+
                                  |
                       VETO ------+------- APPROVE/NEUTRAL
                         |                      |
                         v               +------+------+
                      BLOCKED            |             |
                                         v             v
                                  +-----------+  +-----------+
                                  |   Bull    |  |   Bear    |
                                  | Researcher|  | Researcher|
                                  |  (Claude) |  |  (Gemini) |
                                  +-----+-----+  +-----+-----+
                                        |              |
                                        v              v
                                  +------------------------+
                                  |   Structured Debate    |
                                  |   (up to 3 rounds)     |
                                  +-----------+------------+
                                              |
                              AGREEMENT ------+------ DISAGREEMENT
                                  |                       |
                                  v                       v
                          +---------------+     +-------------------+
                          | Risk Check    |     | 10-Agent Jury     |
                          | (7 checks)    |     | (parallel spawn)  |
                          +-------+-------+     +--------+----------+
                                  |                      |
                                  |              5-5 ----+---- 6+ majority
                                  |              tie     |
                                  |               |      v
                                  |               v   +---------------+
                                  |          ESCALATED| Risk Check    |
                                  |          (human)  | (7 checks)    |
                                  |                   +-------+-------+
                                  |                           |
                                  v                           v
                          +---------------+           +---------------+
                          | Pre-Trade     |           | Pre-Trade     |
                          | Validation    |           | Validation    |
                          +-------+-------+           +-------+-------+
                                  |                           |
                                  v                           v
                          +------------------------------------------+
                          |          Decision Arbiter                |
                          |  (priority rules + position sizing)     |
                          +------------------------------------------+
```

### Layer 1: Quantitative Ensemble (4 Tier-1 Models)

The `QuantModelOrchestrator` (`src/intelligence/quant_models/orchestrator.py`) coordinates four independent quantitative models that each produce a directional probability score between 0.0 (strong sell) and 1.0 (strong buy):

| Model | Type | Primary Signal | Implementation |
|-------|------|---------------|----------------|
| XGBoost | Gradient-boosted tree classifier | 5-day forward return direction | `xgboost_model.py` |
| ElasticNet | Regularized regression | Second directional signal with L1/L2 | `elastic_net_model.py` |
| ARIMA | Time series forecast | Price trajectory extrapolation | `arima_model.py` |
| Sentiment | NLP-derived score | Market mood via Finnhub + NewsAPI | `sentiment_model.py` |

**Composite scoring:** The four individual scores are combined via arithmetic mean to produce a single `composite` score. This is deliberately simple -- the composite is an input to the debate, not the final decision.

**Model disagreement detection:** The standard deviation of the four individual scores is computed. When `std_dev > 0.50` (the `HIGH_MODEL_DISAGREEMENT_THRESHOLD` constant from `backend/app/services/risk/constants.py`), a `high_disagreement_flag` is raised. This flag has two downstream effects:

1. It reduces position sizing by 50% in the DecisionArbiter.
2. It provides critical context to the debate and jury agents -- they see the disagreement explicitly.

The threshold value of 0.50 is a PROTECTED constant that requires written approval from both Joe and Jared to change.

**Tier 2 models (future):** Dr. Miller's neural networks (DowSmall1a and DowLarger1a), GARCH volatility modeling, HMM regime detection, and Monte Carlo simulations are planned additions. These will be validated on holdout data before inclusion in the ensemble.

### Layer 2: Wasden Watch RAG Verdict

Before any debate begins, the system queries the Wasden Watch Retrieval-Augmented Generation system. This system embeds and retrieves from approximately 30 of Cary Wasden's "Weekender" newsletters (June 2022 to present), applying Wasden's investment philosophy to the candidate stock.

The Wasden Watch produces a structured verdict:

- **APPROVE** -- Wasden's philosophy supports this trade.
- **NEUTRAL** -- Insufficient coverage or mixed signals in the corpus.
- **VETO** -- Wasden's philosophy actively opposes this trade.

Each verdict includes a confidence score (0.0 to 1.0), reasoning text, and a mode flag (`direct_coverage` when Wasden explicitly discussed the stock/sector, `framework_application` when applying his principles to uncovered territory).

**Veto power:** Wasden Watch VETO is the highest authority in the system. A VETO immediately short-circuits the pipeline -- no debate, no jury, no risk check. The trade is BLOCKED. This is implemented in `DecisionArbiter.decide()` as Rule 1, the first check evaluated.

**Override mechanism:** Humans (specifically Jared) can override a VETO. Every override is logged as a separate `VetoOverrideRecord` with the overrider's identity, reasoning, and timestamp. All overrides are reviewed in the weekly bias monitoring report.

### Layer 3: Adversarial Debate (Bull vs. Bear)

If the Wasden verdict is APPROVE or NEUTRAL, the system initiates a structured adversarial debate between two different large language models. The use of different LLM providers is a deliberate architectural choice -- different training data and architectures produce genuinely different reasoning patterns, unlike a single model arguing with itself.

| Role | LLM Provider | Fallback |
|------|-------------|----------|
| Bull Researcher | Claude (Anthropic) | None -- bull call fails if Claude is unavailable |
| Bear Researcher | Gemini (Google) | None -- bear call fails if Gemini is unavailable |
| Agreement Judge | Claude, Gemini fallback | Falls back from Claude to Gemini |

**No cross-fallback:** The bull researcher never uses Gemini, and the bear researcher never uses Claude. This is enforced in `DebateLLMClient` (`src/pipeline/debate/debate_llm_client.py`). If either provider is down, the debate cannot proceed -- the system does not substitute one model for the other because doing so would undermine the architectural independence of the opposing cases.

**Debate structure (`DebateEngine` in `src/pipeline/debate/debate_engine.py`):**

1. **Round 1 (Initial arguments):** Both researchers receive identical context -- the quant composite score, individual model scores, Wasden verdict with confidence and reasoning, and any available fundamental data. Each builds a 3-5 paragraph case.
2. **Rounds 2-3 (Rebuttals):** Up to 2 rebuttal rounds (configurable via `MAX_REBUTTAL_ROUNDS`). Each researcher sees the opponent's previous argument and must directly address their strongest objections while advancing their own thesis. Maximum total: 3 rounds.
3. **Agreement detection:** A neutral LLM judge (Claude with Gemini fallback) evaluates the final arguments from both sides and determines whether they have converged on the same direction (AGREEMENT) or still fundamentally disagree (DISAGREEMENT). The judge returns structured JSON with `outcome`, `agreed_action`, and `reasoning`.

**If AGREEMENT:** The debate has resolved the question. The pipeline skips the jury and proceeds directly to risk checking. The agreed-upon action is mapped to BUY, SELL, or HOLD based on the quant composite score (composite > 0.6 = BUY, < 0.4 = SELL, else HOLD).

**If DISAGREEMENT:** The jury is spawned.

### Layer 4: 10-Agent Jury

The jury system (`src/pipeline/jury/`) is spawned only when the bull/bear debate ends in disagreement. This is a cost-optimization design -- the 10 additional LLM calls are only incurred when the system genuinely cannot resolve the question through simpler means.

**Jury composition** (`jury_prompts.py`, PROTECTED -- requires human approval to modify):

| Agent ID | Focus Area | Specialization |
|----------|-----------|----------------|
| 1 | Fundamentals | Valuation metrics (P/E, P/B, PEG, EV/EBITDA, DCF) |
| 2 | Fundamentals | Cash flow quality (FCF generation, coverage, leverage) |
| 3 | Fundamentals | Growth and profitability (revenue growth, margins, ROE, ROIC) |
| 4 | Macro | Fed policy, interest rates, credit conditions |
| 5 | Macro | Sector rotation, industry dynamics, capital flows |
| 6 | Risk | Downside and tail risk (regulatory, litigation, black swan) |
| 7 | Risk | Risk-reward asymmetry (probability-weighted upside vs. downside) |
| 8 | Technical | Trend and price action (moving averages, support/resistance, momentum) |
| 9 | Technical | Volume and sentiment indicators (accumulation/distribution, short interest, options flow) |
| 10 | Wasden Framework | Wasden 5-bucket framework application (the only agent with deep Wasden context) |

The 3-2-2-2-1 distribution is designed to ensure that fundamentals and ratio analysis -- the core of Wasden's philosophy -- carry the most weight, while no single perspective dominates.

**Execution model (`JurySpawner` in `jury_spawn.py`):**

- All 10 agents are spawned in parallel via `asyncio.gather()`.
- Each agent receives the full debate transcript (all rounds), quant scores, Wasden verdict with confidence, and any available fundamental data.
- Each agent returns a structured JSON vote: `{"vote": "BUY" | "SELL" | "HOLD", "reasoning": "2-3 sentence explanation"}`.
- Failed agents get one retry. If both attempts fail, the agent casts a default HOLD vote with error reasoning.
- Invalid vote values are coerced to HOLD with a logged explanation.

**Aggregation rules (`JuryAggregator` in `jury_aggregate.py`):**

- **6+ votes for one action = decisive.** The majority action (BUY, SELL, or HOLD) becomes the jury's decision.
- **5-5 tie (any two-way exact split) = ESCALATED to human.** This is an absolute, non-negotiable rule. A 5-5 tie is NEVER auto-resolved. The system sets `escalated_to_human = True` and the trade requires manual decision by Jared.
- **No clear majority (e.g., 4-3-3 three-way split) = HOLD.** The system defaults to inaction when conviction is insufficient.

The 5-5 escalation rule is enforced at multiple levels:
- In code: `JuryAggregator.aggregate()` checks for exact 5-5 splits before evaluating majority.
- In the DecisionArbiter: Rule 2 checks `jury_escalated` before any other action resolution.
- In project standards: CLAUDE.md Critical Rule 4, PROJECT_STANDARDS_v2.md Section 2, CLAUDE_v2.md "Never Do" list.
- In CI: Review agent checklist verifies this behavior on every PR touching jury or arbiter code.

### Layer 5: DecisionArbiter and Position Sizing

The `DecisionArbiter` (`src/pipeline/arbiter/decision_arbiter.py`) is the final arbitration layer. It reads pre-computed results from all prior nodes via the `TradingState` object and applies a strict priority-ordered rule set:

**Priority rules (evaluated in order, first match wins):**

| Priority | Condition | Action | Position Size |
|----------|-----------|--------|---------------|
| 1 | `wasden_vetoed == True` | BLOCKED | 0.0 |
| 2 | `jury_escalated == True` | ESCALATED (human decides) | 0.0 |
| 3 | `risk_passed == False` | BLOCKED | 0.0 |
| 4 | `pre_trade_passed == False` | BLOCKED | 0.0 |
| 5 | `high_disagreement_flag == True` | Proceed but halve position | Calculated, then halved |
| 6 | All checks pass | BUY/SELL/HOLD per jury or debate | Calculated |

**Position sizing formula:**

```
recommended_position_size = MAX_POSITION_PCT * wasden_confidence * (1 - quant_std_dev)
```

Where:
- `MAX_POSITION_PCT` = 0.12 (12% of portfolio, PROTECTED constant)
- `wasden_confidence` = Wasden Watch confidence score, clamped to [0.0, 1.0]
- `quant_std_dev` = standard deviation of the 4 quant model scores

If the `high_disagreement_flag` is set (`quant_std_dev > 0.50`), the calculated position size is additionally halved:

```
if high_disagreement_flag:
    recommended_position_size *= 0.50
```

The result is always capped at `MAX_POSITION_PCT` (0.12). This formula ensures that:
- Higher Wasden confidence increases position size.
- Higher model disagreement decreases position size.
- The two effects multiply, providing double attenuation when confidence is low AND disagreement is high.

**Separation of concerns:** The DecisionArbiter does NOT import `risk_engine.py` or `pre_trade_validation.py`. It reads pre-computed results from `TradingState`. The risk engine and pre-trade validation are completely separate code paths with zero cross-imports, enforced by test.

### Risk Engine (7 Sequential Checks)

Before the DecisionArbiter makes its final call, the trade must pass through 7 sequential risk checks (implemented in `backend/app/services/risk/risk_engine.py`):

| Order | Check | Threshold | Behavior |
|-------|-------|-----------|----------|
| 1 | Position size | MAX_POSITION_PCT = 0.12 | Block if proposed size exceeds 12% |
| 2 | Cash reserve | MIN_CASH_RESERVE_PCT = 0.10 | Block if cash would drop below 10% |
| 3 | Correlation | CORRELATION_THRESHOLD = 0.70 | Block if >3 positions with 30-day correlation >0.70 |
| 4 | Stress correlation | STRESS_CORRELATION_THRESHOLD = 0.80 | Block if stress-tested correlation (worst 10 market days) >0.80 |
| 5 | Sector concentration | 40% sector limit | Block if sector exposure exceeds limit |
| 6 | Gap risk | Event-based score | Block if gap risk score too high (earnings, FDA, etc.) |
| 7 | Model disagreement | HIGH_MODEL_DISAGREEMENT_THRESHOLD = 0.50 | Block if std_dev exceeds threshold (redundant check) |

### Pre-Trade Validation (4 Independent Checks)

A completely separate validation layer (implemented in `backend/app/services/risk/pre_trade_validation.py`) runs 4 additional checks with ZERO imports from the risk engine:

1. **Quantity sanity** -- order size within reasonable bounds.
2. **Duplicate detection** -- same ticker submitted within 60 seconds.
3. **Portfolio impact** -- projected portfolio impact within limits.
4. **Dollar sanity** -- dollar value of order within bounds.

### Pipeline State and Audit Trail

Every pipeline run produces a `TradingState` object (`src/pipeline/state.py`) that carries the complete decision context through all 10 nodes. At completion, the state is serialized to a `DecisionJournalEntry`-compatible dictionary containing:

- All 4 individual quant scores, composite, std_dev, and disagreement flag.
- Wasden verdict, confidence, reasoning, and operating mode.
- Bull and bear case text.
- Debate outcome and round count.
- Full jury vote breakdown (all 10 votes with reasoning and focus areas) when spawned.
- Risk check and pre-trade validation results with specific failed checks listed.
- Final action, reason, recommended position size, and human approval status.
- Node-by-node execution journal with timestamps.

---

## Consequences

### Benefits

1. **No single point of failure.** A quantitative model failure does not silence the qualitative layer. An LLM hallucination is challenged by an opposing LLM. A jury deadlock escalates to a human rather than generating a bad trade.

2. **Explainability.** Every trade decision can be traced back through quantitative scores, a Wasden verdict with reasoning, a full debate transcript, and individual jury votes with per-agent reasoning. This is critical for the weekly bias monitoring report and for learning from mistakes.

3. **Bias diversification.** The quant models are trained on historical price data. Wasden's philosophy comes from 30 years of live experience. The bull and bear researchers use different LLM providers with different training corpora. The jury agents apply 5 distinct analytical perspectives. These diverse biases partially cancel rather than compound.

4. **Graceful degradation under uncertainty.** When the system is uncertain, it does not guess -- it either reduces position size (model disagreement), defaults to HOLD (no jury majority), or escalates to a human (5-5 tie). Capital preservation under ambiguity is a feature, not a bug.

5. **Cost efficiency.** The jury is only spawned on debate disagreement. For the estimated 8 daily candidates, the debate resolves many without jury involvement. At Haiku pricing, even full jury runs cost under $1/day.

6. **Regulatory readiness.** The complete audit trail, human escalation points, and explainable decision chain position the system favorably for any future compliance requirements.

### Risks and Trade-offs

1. **Latency.** A full pipeline run with jury involves 10+ LLM calls, each with network latency. For a daily recommendation system this is acceptable; for intraday trading it would not be.

2. **Correlated LLM failures.** If both Claude and Gemini are simultaneously unavailable, the debate cannot proceed. The system halts rather than degrading to quant-only decisions -- this is a deliberate conservatism.

3. **Wasden temporal bias.** The RAG corpus covers a specific market regime (post-COVID 2022-present). Wasden's cautionary language from a bear-to-recovery period may incorrectly veto valid bull trades in a different regime. Mitigation: planned regime detection logic (design ticket required).

4. **Jury prompt sensitivity.** The 10 jury agent prompts are PROTECTED for good reason -- small prompt changes can systematically shift vote distributions. This means the jury composition is deliberately rigid and cannot be easily tuned.

5. **Position sizing compression.** The multiplicative formula `MAX_POSITION_PCT * wasden_confidence * (1 - quant_std_dev)` can produce very small positions when both confidence is moderate and disagreement is nonzero. For example, 0.12 * 0.60 * 0.70 = 0.0504 (5.04%), further halved to 2.52% if the disagreement flag triggers. This extreme conservatism is intentional but limits upside participation.

6. **Selection bias in screening.** By the time a stock reaches the debate, it has already passed through a quantitative screening funnel (market cap > $5B, PEG < 2.0, FCF yield > 3%, Piotroski >= 5). Wasden Watch only evaluates what the quant models already like. This is monitored via the weekly bias report.

---

## Alternatives Considered

### Alternative 1: Simple Majority Voting Across All Models

**Approach:** Each quant model, Wasden Watch, and a single LLM agent each cast a BUY/SELL/HOLD vote. Simple majority wins.

**Why rejected:** Treats all signals as equally reliable, which they are not. The Wasden Watch represents 30 years of institutional expertise and should have veto power, not just one vote among many. Simple voting also loses all nuance -- a model that barely signals BUY counts the same as one with high conviction. Most critically, simple voting produces no explainable reasoning chain.

### Alternative 2: Single LLM Agent with All Context

**Approach:** Feed all quantitative scores, Wasden corpus, fundamentals, and market data into a single Claude prompt and ask for a trading decision.

**Why rejected:** Single-model systems exhibit confirmation bias (the model agrees with itself), hallucination risk (no adversarial challenge), and catastrophic failure modes (one bad model update affects all decisions). The adversarial debate between Claude and Gemini surfaces disagreements that a single model would paper over. Additionally, a single model cannot genuinely argue against its own conclusion.

### Alternative 3: Weighted Score Averaging Without Debate

**Approach:** Assign static weights to each model and Wasden Watch, compute a weighted average, and use thresholds to map to BUY/SELL/HOLD.

**Why rejected:** Loses the qualitative reasoning that makes decisions explainable and auditable. Weight tuning becomes a black box -- how do you weight Wasden vs. XGBoost vs. ARIMA? Static weights cannot adapt to regime changes without retuning, and retuning weights is explicitly prohibited by the autotune guardrails (jury weights are excluded from autotune scope). The debate + jury architecture produces the same effect as dynamic weighting but through transparent, logged reasoning.

### Alternative 4: Jury Without Debate (Direct Jury on Every Trade)

**Approach:** Skip the bull/bear debate and spawn the 10-agent jury for every candidate.

**Why rejected:** Cost inefficiency (10 LLM calls per candidate per day = 80 calls minimum), and the jury would lack the structured arguments that make their evaluation meaningful. The debate produces the "case brief" that jury agents evaluate. Without it, each jury agent would need to independently research the bull and bear cases, leading to inconsistent and lower-quality reasoning. The staged approach (debate first, jury only on disagreement) is both cheaper and produces better jury decisions because the agents evaluate argument quality rather than raw data.

### Alternative 5: Human-in-the-Loop for Every Trade

**Approach:** Present all data to Jared and Joe for every trade decision, with the system as advisory only.

**Why rejected:** Does not scale. With 8 candidates daily, each requiring review of quant scores, fundamentals, Wasden analysis, and market context, the human time requirement is 2-4 hours per day. The system is designed to handle the 90% of decisions where conviction is clear, escalating only the genuinely ambiguous cases (5-5 ties, high disagreement, veto overrides) to human judgment. This preserves human attention for where it adds the most value.

---

## Related Decisions

- **Jury agent prompt design:** Prompts are PROTECTED and documented in `src/pipeline/jury/jury_prompts.py`. Changes require written approval from both Jared and Joe.
- **Risk constants:** All 13 constants in `backend/app/services/risk/constants.py` are PROTECTED. The position sizing formula references `MAX_POSITION_PCT` and `HIGH_MODEL_DISAGREEMENT_THRESHOLD` from this file.
- **Decision journal schema:** Defined in PROJECT_STANDARDS_v2.md Section 4. Every field in the schema maps to a specific pipeline node output.
- **Pre-trade validation separation:** The pre-trade validation layer must remain a completely separate code path from the risk engine and DecisionArbiter. Zero cross-imports, enforced by test.
- **TRADING_MODE enforcement:** The entire pipeline operates under the TRADING_MODE environment variable. No defaults. System halts if unset.

---

## Implementation References

| Component | File | Key Class/Function |
|-----------|------|-------------------|
| Pipeline orchestrator | `src/pipeline/decision_pipeline.py` | `DecisionPipeline` |
| Pipeline state | `src/pipeline/state.py` | `TradingState` |
| Quant ensemble | `src/intelligence/quant_models/orchestrator.py` | `QuantModelOrchestrator` |
| Debate engine | `src/pipeline/debate/debate_engine.py` | `DebateEngine` |
| Bull researcher | `src/pipeline/debate/bull_researcher.py` | `BullResearcher` |
| Bear researcher | `src/pipeline/debate/bear_researcher.py` | `BearResearcher` |
| Agreement detector | `src/pipeline/debate/agreement_detector.py` | `AgreementDetector` |
| Debate LLM client | `src/pipeline/debate/debate_llm_client.py` | `DebateLLMClient` |
| Debate prompts | `src/pipeline/debate/prompts.py` | System/user prompt templates |
| Jury spawner | `src/pipeline/jury/jury_spawn.py` | `JurySpawner` |
| Jury aggregator | `src/pipeline/jury/jury_aggregate.py` | `JuryAggregator` |
| Jury prompts (PROTECTED) | `src/pipeline/jury/jury_prompts.py` | `JURY_AGENTS`, `JURY_USER_PROMPT` |
| Decision arbiter | `src/pipeline/arbiter/decision_arbiter.py` | `DecisionArbiter` |
| Risk constants (PROTECTED) | `backend/app/services/risk/constants.py` | 13 named constants |
