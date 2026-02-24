export interface PortfolioPosition {
  id: string
  ticker: string
  direction: "long" | "short"
  entry_price: number
  entry_date: string
  current_price: number
  exit_price: number | null
  exit_date: string | null
  shares: number
  status: "open" | "closed"
  pnl: number
  pnl_pct: number
}

export interface DailySnapshot {
  date: string
  total_value: number
  daily_pnl: number
  cumulative_pnl: number
  spy_daily_return: number
  spy_cumulative_return: number
  cash_balance: number
  positions_count: number
}

export interface PortfolioSummary {
  total_value: number
  daily_pnl: number
  daily_pnl_pct: number
  total_pnl: number
  total_pnl_pct: number
  win_rate: number
  open_positions: number
  closed_positions: number
  cash_balance: number
}

export interface TradeRecommendation {
  id: string
  created_at: string
  ticker: string
  direction: "BUY" | "SELL"
  confidence: number
  reasoning: string
  quant_composite: number
  wasden_verdict: string
  pipeline_run_id: string
  status: "pending" | "approved" | "rejected"
  reviewed_by: string | null
  reviewed_at: string | null
  review_note: string | null
}

export interface QuantScores {
  xgboost: number
  elastic_net: number
  arima: number
  sentiment: number
  composite: number
  std_dev: number
  high_disagreement_flag: boolean
}

export interface WasdenVerdict {
  verdict: "APPROVE" | "NEUTRAL" | "VETO"
  confidence: number
  reasoning: string
  mode: "direct_coverage" | "framework_application"
  passages_retrieved: number
}

export interface JuryVote {
  agent_id: number
  agent_perspective: string
  vote: "BUY" | "SELL" | "HOLD"
  reasoning: string
  confidence: number
}

export interface JuryResult {
  spawned: boolean
  reason: string
  votes: JuryVote[]
  final_count: { buy: number; sell: number; hold: number }
  decision: "BUY" | "SELL" | "HOLD" | "ESCALATED"
  escalated_to_human: boolean
}

export interface DecisionJournalEntry {
  id: string
  created_at: string
  ticker: string
  pipeline_run_id: string
  quant_scores: QuantScores
  wasden_verdict: WasdenVerdict
  bull_case: string
  bear_case: string
  debate_outcome: "agreement" | "disagreement"
  debate_rounds: number
  jury: JuryResult | null
  risk_check: { passed: boolean; checks_failed: string[] }
  pre_trade_validation: { passed: boolean; checks_failed: string[] }
  final_action: "BUY" | "SELL" | "HOLD" | "BLOCKED"
  final_reason: string
  recommended_position_size: number
  human_approval_required: boolean
  human_approved: boolean | null
  executed: boolean
  fill_price: number | null
  slippage: number | null
}

export interface DebateTranscript {
  id: string
  created_at: string
  pipeline_run_id: string
  ticker: string
  rounds: DebateRound[]
  outcome: "agreement" | "disagreement"
}

export interface DebateRound {
  round_number: number
  bull_argument: string
  bull_confidence: number
  bear_argument: string
  bear_confidence: number
}

export interface VetoOverride {
  id: string
  created_at: string
  ticker: string
  original_verdict: string
  override_reason: string
  overridden_by: string
  pipeline_run_id: string
  status: "pending" | "approved" | "rejected" | "completed"
  outcome_tracked: boolean
  outcome_note: string | null
  outcome_pnl: number | null
}

export interface RiskAlert {
  id: string
  created_at: string
  alert_type: string
  severity: "info" | "warning" | "critical"
  message: string
  ticker: string | null
  details: Record<string, unknown>
  acknowledged: boolean
  acknowledged_by: string | null
  acknowledged_at: string | null
}

export interface ConsecutiveLossTracker {
  current_streak: number
  max_streak: number
  net_pnl: number
  status: "active" | "warning" | "halted"
  last_loss_ticker: string | null
  last_loss_date: string | null
}

export interface BiasMetric {
  id: string
  week_start: string
  week_end: string
  approve_count: number
  neutral_count: number
  veto_count: number
  total_recommendations: number
  sector_distribution: Record<string, number>
  model_agreement_rate: number
  avg_confidence: number
  override_count: number
}

export interface ScreeningRun {
  id: string
  run_date: string
  tier1_count: number
  tier2_count: number
  tier3_count: number
  tier4_count: number
  tier5_count: number
  final_recommendations: number
  duration_seconds: number
}

export interface SystemSetting {
  key: string
  value: string
  description: string
  updated_at: string
}

export interface HealthStatus {
  status: string
  trading_mode: string
  db_connected: boolean
  timestamp: string
  use_mock_data: boolean
}

export interface JuryStats {
  total_sessions: number
  total_votes: number
  buy_votes: number
  sell_votes: number
  hold_votes: number
  agreement_rate: number
  escalation_count: number
}

export interface BloombergFundamental {
  ticker: string
  pull_date: string
  price: number
  market_cap: number
  trailing_pe: number | null
  forward_pe: number
  eps: number | null
  peg_ratio: number | null
  fcf: number
  fcf_yield: number | null
  ebitda_margin: number
  roe: number
  roc: number
  gross_margin: number
  operating_margin: number
  net_margin: number
  current_ratio: number
  quick_ratio: number
  debt_to_equity: number
  revenue_growth: number
  freshness_grade: "FRESH" | "RECENT" | "STALE" | "EXPIRED"
  is_adr: boolean
}
