import type {
  PortfolioPosition,
  DailySnapshot,
  PortfolioSummary,
  TradeRecommendation,
  DecisionJournalEntry,
  DebateTranscript,
  JuryVote,
  JuryStats,
  VetoOverride,
  RiskAlert,
  ConsecutiveLossTracker,
  BiasMetric,
  ScreeningRun,
  SystemSetting,
} from "./types"

const TICKERS = [
  { ticker: "NVDA", price: 189.82 },
  { ticker: "PYPL", price: 41.65 },
  { ticker: "NFLX", price: 78.67 },
  { ticker: "TSM", price: 370.54 },
  { ticker: "XOM", price: 147.28 },
  { ticker: "AAPL", price: 264.58 },
  { ticker: "MSFT", price: 397.23 },
  { ticker: "AMZN", price: 210.11 },
  { ticker: "TSLA", price: 411.82 },
  { ticker: "AMD", price: 200.15 },
]

function uuid() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString()
}

function dateStr(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().split("T")[0]
}

export const mockPositions: PortfolioPosition[] = [
  { id: uuid(), ticker: "NVDA", direction: "long", entry_price: 182.50, entry_date: daysAgo(15), current_price: 189.82, exit_price: null, exit_date: null, shares: 50, status: "open", pnl: 366.0, pnl_pct: 4.01 },
  { id: uuid(), ticker: "AAPL", direction: "long", entry_price: 258.20, entry_date: daysAgo(12), current_price: 264.58, exit_price: null, exit_date: null, shares: 30, status: "open", pnl: 191.40, pnl_pct: 2.47 },
  { id: uuid(), ticker: "MSFT", direction: "long", entry_price: 390.00, entry_date: daysAgo(10), current_price: 397.23, exit_price: null, exit_date: null, shares: 20, status: "open", pnl: 144.60, pnl_pct: 1.85 },
  { id: uuid(), ticker: "AMD", direction: "long", entry_price: 195.30, entry_date: daysAgo(8), current_price: 200.15, exit_price: null, exit_date: null, shares: 40, status: "open", pnl: 194.0, pnl_pct: 2.48 },
  { id: uuid(), ticker: "XOM", direction: "long", entry_price: 150.10, entry_date: daysAgo(5), current_price: 147.28, exit_price: null, exit_date: null, shares: 25, status: "open", pnl: -70.50, pnl_pct: -1.88 },
  { id: uuid(), ticker: "AMZN", direction: "long", entry_price: 198.50, entry_date: daysAgo(20), current_price: 210.11, exit_price: 210.11, exit_date: daysAgo(7), shares: 35, status: "closed", pnl: 406.35, pnl_pct: 5.85 },
  { id: uuid(), ticker: "NFLX", direction: "long", entry_price: 75.20, entry_date: daysAgo(18), current_price: 78.67, exit_price: 78.67, exit_date: daysAgo(9), shares: 60, status: "closed", pnl: 208.20, pnl_pct: 4.61 },
  { id: uuid(), ticker: "TSLA", direction: "long", entry_price: 425.00, entry_date: daysAgo(14), current_price: 411.82, exit_price: 405.30, exit_date: daysAgo(6), shares: 10, status: "closed", pnl: -197.00, pnl_pct: -4.64 },
]

export const mockPnL: DailySnapshot[] = Array.from({ length: 30 }, (_, i) => {
  const day = 29 - i
  const baseValue = 100000
  const dailyChange = (Math.random() - 0.48) * 800
  const cumPnl = (30 - day) * 45 + (Math.random() - 0.5) * 500
  const spyCum = (30 - day) * 30 + (Math.random() - 0.5) * 300
  return {
    date: dateStr(day),
    total_value: baseValue + cumPnl,
    daily_pnl: dailyChange,
    cumulative_pnl: cumPnl,
    spy_daily_return: (Math.random() - 0.48) * 1.5,
    spy_cumulative_return: spyCum / baseValue * 100,
    cash_balance: 15000 + Math.random() * 2000,
    positions_count: 4 + Math.floor(Math.random() * 3),
  }
})

export const mockSummary: PortfolioSummary = {
  total_value: 101243.05,
  daily_pnl: 325.80,
  daily_pnl_pct: 0.32,
  total_pnl: 1243.05,
  total_pnl_pct: 1.24,
  win_rate: 62.5,
  open_positions: 5,
  closed_positions: 3,
  cash_balance: 16450.00,
}

const runIds = Array.from({ length: 6 }, () => uuid())

export const mockRecommendations: TradeRecommendation[] = [
  { id: uuid(), created_at: daysAgo(0), ticker: "PYPL", direction: "BUY", confidence: 0.82, reasoning: "FCF Yield 14% signals deep undervaluation. PEG ratio confirms growth-value disconnect.", quant_composite: 0.78, wasden_verdict: "APPROVE", pipeline_run_id: runIds[0], status: "pending", reviewed_by: null, reviewed_at: null, review_note: null },
  { id: uuid(), created_at: daysAgo(0), ticker: "TSM", direction: "BUY", confidence: 0.75, reasoning: "PEG 0.67 with 31.6% revenue growth. EBITDA margin 68.9% — industry-leading.", quant_composite: 0.71, wasden_verdict: "APPROVE", pipeline_run_id: runIds[1], status: "pending", reviewed_by: null, reviewed_at: null, review_note: null },
  { id: uuid(), created_at: daysAgo(0), ticker: "NVDA", direction: "BUY", confidence: 0.88, reasoning: "PEG 0.54 at 48x P/E. Revenue growth 114%. ROE 107%. Extraordinary fundamentals.", quant_composite: 0.85, wasden_verdict: "APPROVE", pipeline_run_id: runIds[2], status: "pending", reviewed_by: null, reviewed_at: null, review_note: null },
  { id: uuid(), created_at: daysAgo(1), ticker: "AAPL", direction: "BUY", confidence: 0.65, reasoning: "ROE 152% from buyback program. CCC -72.4 days shows massive competitive moat.", quant_composite: 0.62, wasden_verdict: "NEUTRAL", pipeline_run_id: runIds[3], status: "pending", reviewed_by: null, reviewed_at: null, review_note: null },
  { id: uuid(), created_at: daysAgo(1), ticker: "TSLA", direction: "SELL", confidence: 0.71, reasoning: "P/E 341x with -2.9% revenue growth. FCF yield 0.47%. Fails Sprinkle Sauce screens.", quant_composite: 0.35, wasden_verdict: "VETO", pipeline_run_id: runIds[4], status: "pending", reviewed_by: null, reviewed_at: null, review_note: null },
  { id: uuid(), created_at: daysAgo(2), ticker: "AMZN", direction: "BUY", confidence: 0.73, reasoning: "Forward P/E 22.2x with 12.4% revenue growth. PEG 1.21 — reasonably valued.", quant_composite: 0.69, wasden_verdict: "APPROVE", pipeline_run_id: runIds[3], status: "approved", reviewed_by: "Joe", reviewed_at: daysAgo(2), review_note: "Good entry point" },
  { id: uuid(), created_at: daysAgo(3), ticker: "NFLX", direction: "BUY", confidence: 0.68, reasoning: "FCF $9.4B. Revenue growth 15.9%. Wasden presented this — strong franchise value.", quant_composite: 0.66, wasden_verdict: "APPROVE", pipeline_run_id: runIds[4], status: "approved", reviewed_by: "Jared", reviewed_at: daysAgo(3), review_note: "Cary's pick" },
  { id: uuid(), created_at: daysAgo(4), ticker: "XOM", direction: "BUY", confidence: 0.55, reasoning: "Energy sector exposure. Revenue growth -4.5% is concerning but FCF yield 3.72% supports.", quant_composite: 0.52, wasden_verdict: "NEUTRAL", pipeline_run_id: runIds[5], status: "rejected", reviewed_by: "Joe", reviewed_at: daysAgo(3), review_note: "Negative revenue growth, wait for better entry" },
]

export const mockJournalEntries: DecisionJournalEntry[] = [
  {
    id: uuid(), created_at: daysAgo(0), ticker: "NVDA", pipeline_run_id: runIds[2],
    quant_scores: { xgboost: 0.82, elastic_net: 0.79, arima: 0.88, sentiment: 0.91, composite: 0.85, std_dev: 0.05, high_disagreement_flag: false },
    wasden_verdict: { verdict: "APPROVE", confidence: 0.92, reasoning: "NVDA shows extraordinary fundamentals across all five buckets. PEG 0.54 at 48x P/E indicates massive growth underpricing.", mode: "direct_coverage", passages_retrieved: 8 },
    bull_case: "NVIDIA dominates AI compute with 80%+ market share in training GPUs. Revenue growth of 114% YoY with expanding margins. Data center revenue alone exceeds most competitors' total revenue. The PEG ratio of 0.54 suggests the market still hasn't fully priced in the growth trajectory.",
    bear_case: "At 48x trailing P/E, NVDA is priced for perfection. Any slowdown in AI capex spending could cause a significant correction. Customer concentration risk with hyperscalers. Competition from AMD and custom chips (Google TPU, Amazon Trainium) is intensifying.",
    debate_outcome: "disagreement", debate_rounds: 3,
    jury: { spawned: true, reason: "Bull/bear debate reached disagreement after 3 rounds", votes: [], final_count: { buy: 7, sell: 2, hold: 1 }, decision: "BUY", escalated_to_human: false },
    risk_check: { passed: true, checks_failed: [] },
    pre_trade_validation: { passed: true, checks_failed: [] },
    final_action: "BUY", final_reason: "Strong jury consensus (7-2-1) with Wasden APPROVE at 0.92 confidence", recommended_position_size: 0.08,
    human_approval_required: false, human_approved: null, executed: true, fill_price: 189.45, slippage: 0.0002,
  },
  {
    id: uuid(), created_at: daysAgo(1), ticker: "TSLA", pipeline_run_id: runIds[4],
    quant_scores: { xgboost: 0.31, elastic_net: 0.28, arima: 0.45, sentiment: 0.38, composite: 0.35, std_dev: 0.07, high_disagreement_flag: false },
    wasden_verdict: { verdict: "VETO", confidence: 0.88, reasoning: "TSLA fails multiple Sprinkle Sauce screens. P/E 341x with negative revenue growth is incompatible with value-oriented framework.", mode: "framework_application", passages_retrieved: 5 },
    bull_case: "Tesla's robotaxi and energy storage businesses represent massive optionality not captured in current auto-focused valuation.",
    bear_case: "341x P/E with -2.9% revenue growth. FCF yield 0.47%. Autonomous driving timeline keeps slipping. Chinese EV competition intensifying.",
    debate_outcome: "agreement", debate_rounds: 2,
    jury: null,
    risk_check: { passed: true, checks_failed: [] },
    pre_trade_validation: { passed: true, checks_failed: [] },
    final_action: "BLOCKED", final_reason: "Wasden VETO — fails fundamental value screens", recommended_position_size: 0,
    human_approval_required: false, human_approved: null, executed: false, fill_price: null, slippage: null,
  },
  {
    id: uuid(), created_at: daysAgo(2), ticker: "PYPL", pipeline_run_id: runIds[0],
    quant_scores: { xgboost: 0.74, elastic_net: 0.81, arima: 0.72, sentiment: 0.65, composite: 0.78, std_dev: 0.06, high_disagreement_flag: false },
    wasden_verdict: { verdict: "APPROVE", confidence: 0.85, reasoning: "FCF Yield 14% is highest on watchlist. Wasden's favorite metric signals deep undervaluation. Growth quality question needs investigation.", mode: "direct_coverage", passages_retrieved: 6 },
    bull_case: "PayPal's FCF yield of 14% is extraordinary for a tech company. Aggressive buyback program reducing share count. Venmo monetization accelerating.",
    bear_case: "Revenue growth only 4.3% — near stagnation for a 'growth' company. Competition from Apple Pay, Block, and Stripe squeezing margins. Market skepticism around management execution.",
    debate_outcome: "disagreement", debate_rounds: 3,
    jury: { spawned: true, reason: "Growth quality debate unresolved", votes: [], final_count: { buy: 6, sell: 3, hold: 1 }, decision: "BUY", escalated_to_human: false },
    risk_check: { passed: true, checks_failed: [] },
    pre_trade_validation: { passed: true, checks_failed: [] },
    final_action: "BUY", final_reason: "Jury 6-3-1 BUY with strong FCF yield thesis", recommended_position_size: 0.06,
    human_approval_required: true, human_approved: true, executed: true, fill_price: 41.52, slippage: 0.0003,
  },
]

export const mockDebates: DebateTranscript[] = [
  {
    id: uuid(), created_at: daysAgo(0), pipeline_run_id: runIds[2], ticker: "NVDA",
    outcome: "disagreement",
    rounds: [
      { round_number: 1, bull_argument: "NVIDIA's PEG ratio of 0.54 makes it the most undervalued stock relative to growth on our watchlist. Revenue growth of 114% YoY is unprecedented for a company of this size. The data center business alone generated $47.5B in the last year.", bull_confidence: 0.88, bear_argument: "At 48x trailing P/E, the stock requires continued exponential growth just to maintain its current valuation. The AI spending boom is showing signs of maturation — MSFT and GOOG have signaled capex moderation.", bear_confidence: 0.72 },
      { round_number: 2, bull_argument: "Capex moderation signals have been misinterpreted. Total AI infrastructure spending is still in early innings. NVIDIA's CUDA moat and software ecosystem create switching costs that protect margins above 60%.", bull_confidence: 0.85, bear_argument: "Custom silicon from hyperscalers (Google TPU, Amazon Trainium, Microsoft Maia) will erode NVIDIA's dominance over the next 2-3 years. The 75% gross margin is unsustainable in a competitive market.", bear_confidence: 0.68 },
      { round_number: 3, bull_argument: "Custom chips address training, but inference — the larger market — still overwhelmingly runs on NVIDIA GPUs. The Blackwell architecture extends the lead. ROE of 107% proves exceptional capital allocation.", bull_confidence: 0.87, bear_argument: "Concentration risk remains — top 4 customers represent over 40% of revenue. Any single hyperscaler shift could materially impact results. The stock has already tripled in 18 months.", bear_confidence: 0.65 },
    ],
  },
  {
    id: uuid(), created_at: daysAgo(2), pipeline_run_id: runIds[0], ticker: "PYPL",
    outcome: "disagreement",
    rounds: [
      { round_number: 1, bull_argument: "PayPal's FCF yield of 14% is the highest on our entire watchlist. At 7.9x trailing P/E, the market is pricing this like a declining business, but FCF generation is accelerating. Buyback program is reducing shares outstanding at a rapid pace.", bull_confidence: 0.82, bear_argument: "Revenue growth of 4.3% is dangerously close to stagnation. Apple Pay and Google Pay are commoditizing the payment layer. Venmo monetization has consistently disappointed.", bear_confidence: 0.75 },
      { round_number: 2, bull_argument: "The growth narrative misses the transformation underway. New CEO is cutting unprofitable transaction volume and focusing on high-margin branded checkout. Margin expansion is the story, not top-line growth.", bull_confidence: 0.80, bear_argument: "Margin expansion without revenue growth is a classic value trap. The payment processing industry is commoditizing. Block's Cash App and Stripe's embedded payments are winning the next generation of merchants.", bear_confidence: 0.70 },
    ],
  },
]

const perspectives = [
  "Fundamentals & Ratio Analysis",
  "Fundamentals & Balance Sheet",
  "Fundamentals & Cash Flow",
  "Macro & Sector Environment",
  "Macro & Interest Rate Impact",
  "Risk & Downside Scenario",
  "Risk & Tail Risk Assessment",
  "Technical Signal Interpretation",
  "Technical & Momentum",
  "Wasden 5-Bucket Framework",
]

export const mockJuryVotes: JuryVote[] = perspectives.map((perspective, i) => ({
  agent_id: i + 1,
  agent_perspective: perspective,
  vote: i < 7 ? "BUY" : i < 9 ? "SELL" : "HOLD",
  reasoning: `Based on ${perspective.toLowerCase()} analysis, the evidence ${i < 7 ? "supports" : "does not support"} a buy position at current levels.`,
  confidence: 0.6 + Math.random() * 0.3,
}))

export const mockJuryStats: JuryStats = {
  total_sessions: 8,
  total_votes: 80,
  buy_votes: 52,
  sell_votes: 18,
  hold_votes: 10,
  agreement_rate: 0.72,
  escalation_count: 1,
}

export const mockOverrides: VetoOverride[] = [
  { id: uuid(), created_at: daysAgo(1), ticker: "TSLA", original_verdict: "VETO", override_reason: "Short-term momentum play based on robotaxi announcement catalyst", overridden_by: "Jared", pipeline_run_id: runIds[4], status: "pending", outcome_tracked: false, outcome_note: null, outcome_pnl: null },
  { id: uuid(), created_at: daysAgo(5), ticker: "XOM", original_verdict: "VETO", override_reason: "Energy sector rotation thesis supported by macro data", overridden_by: "Joe", pipeline_run_id: runIds[5], status: "approved", outcome_tracked: true, outcome_note: "Position opened, currently -1.88%", outcome_pnl: -70.50 },
  { id: uuid(), created_at: daysAgo(8), ticker: "NFLX", original_verdict: "VETO", override_reason: "Wasden presented bullish case directly", overridden_by: "Jared", pipeline_run_id: runIds[4], status: "rejected", outcome_tracked: false, outcome_note: "Override rejected — Wasden verdict upheld", outcome_pnl: null },
]

export const mockAlerts: RiskAlert[] = [
  { id: uuid(), created_at: daysAgo(0), alert_type: "consecutive_loss", severity: "warning", message: "2 consecutive losing trades detected. Warning threshold approaching.", ticker: null, details: { streak: 2, threshold: 5 }, acknowledged: false, acknowledged_by: null, acknowledged_at: null },
  { id: uuid(), created_at: daysAgo(1), alert_type: "sector_concentration", severity: "warning", message: "Technology sector represents 68% of portfolio. MAX recommended: 40%.", ticker: null, details: { sector: "Technology", pct: 68, max: 40 }, acknowledged: false, acknowledged_by: null, acknowledged_at: null },
  { id: uuid(), created_at: daysAgo(2), alert_type: "model_disagreement", severity: "critical", message: "High model disagreement on TSLA (std_dev: 0.62). Position sizing reduced.", ticker: "TSLA", details: { std_dev: 0.62, threshold: 0.5 }, acknowledged: true, acknowledged_by: "Joe", acknowledged_at: daysAgo(2) },
  { id: uuid(), created_at: daysAgo(3), alert_type: "data_freshness", severity: "info", message: "Bloomberg data for TSM is 5 days old. Grade: RECENT.", ticker: "TSM", details: { days_old: 5, grade: "RECENT" }, acknowledged: true, acknowledged_by: "Joe", acknowledged_at: daysAgo(3) },
  { id: uuid(), created_at: daysAgo(4), alert_type: "cash_reserve", severity: "info", message: "Cash reserve at 16.2%. Above minimum 10% threshold.", ticker: null, details: { current: 16.2, minimum: 10 }, acknowledged: true, acknowledged_by: "Joe", acknowledged_at: daysAgo(4) },
  { id: uuid(), created_at: daysAgo(5), alert_type: "position_size", severity: "info", message: "NVDA position at 9.4% of portfolio. Below 12% maximum.", ticker: "NVDA", details: { current: 9.4, max: 12 }, acknowledged: true, acknowledged_by: "Joe", acknowledged_at: daysAgo(5) },
]

export const mockStreak: ConsecutiveLossTracker = {
  current_streak: 2,
  max_streak: 3,
  net_pnl: 1243.05,
  status: "active",
  last_loss_ticker: "XOM",
  last_loss_date: daysAgo(3),
}

export const mockBiasMetrics: BiasMetric[] = [
  { id: uuid(), week_start: dateStr(7), week_end: dateStr(1), approve_count: 12, neutral_count: 5, veto_count: 3, total_recommendations: 20, sector_distribution: { Technology: 12, Energy: 3, "Communication Services": 2, "Consumer Discretionary": 3 }, model_agreement_rate: 0.78, avg_confidence: 0.72, override_count: 1 },
  { id: uuid(), week_start: dateStr(14), week_end: dateStr(8), approve_count: 10, neutral_count: 6, veto_count: 4, total_recommendations: 20, sector_distribution: { Technology: 10, Energy: 4, "Communication Services": 3, "Consumer Discretionary": 3 }, model_agreement_rate: 0.72, avg_confidence: 0.68, override_count: 2 },
  { id: uuid(), week_start: dateStr(21), week_end: dateStr(15), approve_count: 14, neutral_count: 3, veto_count: 3, total_recommendations: 20, sector_distribution: { Technology: 11, Energy: 3, "Communication Services": 3, "Consumer Discretionary": 3 }, model_agreement_rate: 0.80, avg_confidence: 0.74, override_count: 0 },
  { id: uuid(), week_start: dateStr(28), week_end: dateStr(22), approve_count: 11, neutral_count: 4, veto_count: 5, total_recommendations: 20, sector_distribution: { Technology: 9, Energy: 5, "Communication Services": 3, "Consumer Discretionary": 3 }, model_agreement_rate: 0.68, avg_confidence: 0.66, override_count: 3 },
]

export const mockScreeningRuns: ScreeningRun[] = [
  { id: uuid(), run_date: daysAgo(0), tier1_count: 500, tier2_count: 124, tier3_count: 47, tier4_count: 15, tier5_count: 8, final_recommendations: 5, duration_seconds: 342.5 },
  { id: uuid(), run_date: daysAgo(1), tier1_count: 500, tier2_count: 118, tier3_count: 42, tier4_count: 13, tier5_count: 7, final_recommendations: 4, duration_seconds: 328.1 },
  { id: uuid(), run_date: daysAgo(2), tier1_count: 500, tier2_count: 131, tier3_count: 51, tier4_count: 18, tier5_count: 9, final_recommendations: 6, duration_seconds: 365.2 },
]

export const mockSettings: SystemSetting[] = [
  { key: "TRADING_MODE", value: "paper", description: "Current trading mode (paper or live)", updated_at: daysAgo(0) },
  { key: "USE_MOCK_DATA", value: "true", description: "Use mock data instead of Supabase", updated_at: daysAgo(0) },
  { key: "MAX_POSITION_PCT", value: "0.12", description: "Maximum position size as % of portfolio", updated_at: daysAgo(30) },
  { key: "RISK_PER_TRADE_PCT", value: "0.015", description: "Maximum risk per trade as % of portfolio", updated_at: daysAgo(30) },
  { key: "MIN_CASH_RESERVE_PCT", value: "0.10", description: "Minimum cash reserve as % of portfolio", updated_at: daysAgo(30) },
  { key: "MAX_CORRELATED_POSITIONS", value: "3", description: "Maximum correlated positions allowed", updated_at: daysAgo(30) },
  { key: "CORRELATION_THRESHOLD", value: "0.70", description: "Correlation threshold for position checks", updated_at: daysAgo(30) },
]
