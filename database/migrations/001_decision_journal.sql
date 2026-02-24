-- 001_decision_journal.sql
-- Core table: records every pipeline decision with full audit trail
-- Tracks quant scores, Wasden verdict, debate, jury, risk, and execution details

CREATE TABLE decision_journal (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ticker TEXT NOT NULL,
  pipeline_run_id UUID NOT NULL,
  -- Quant scores
  quant_xgboost FLOAT,
  quant_elastic_net FLOAT,
  quant_arima FLOAT,
  quant_sentiment FLOAT,
  quant_composite FLOAT,
  quant_std_dev FLOAT,
  quant_high_disagreement BOOLEAN DEFAULT FALSE,
  -- Wasden verdict
  wasden_verdict TEXT CHECK (wasden_verdict IN ('APPROVE', 'NEUTRAL', 'VETO')),
  wasden_confidence FLOAT,
  wasden_reasoning TEXT,
  wasden_mode TEXT CHECK (wasden_mode IN ('direct_coverage', 'framework_application')),
  wasden_passages_retrieved INT,
  -- Debate
  bull_case TEXT,
  bear_case TEXT,
  debate_outcome TEXT CHECK (debate_outcome IN ('agreement', 'disagreement')),
  debate_rounds INT,
  -- Jury (SEPARATE from risk_check and pre_trade_validation)
  jury_spawned BOOLEAN DEFAULT FALSE,
  jury_reason TEXT,
  jury_buy_count INT,
  jury_sell_count INT,
  jury_hold_count INT,
  jury_decision TEXT CHECK (jury_decision IN ('BUY', 'SELL', 'HOLD', 'ESCALATED')),
  jury_escalated BOOLEAN DEFAULT FALSE,
  -- Risk check (SEPARATE from pre_trade_validation)
  risk_check_passed BOOLEAN,
  risk_checks_failed TEXT[],
  -- Pre-trade validation (SEPARATE from risk_check)
  pre_trade_passed BOOLEAN,
  pre_trade_checks_failed TEXT[],
  -- Final decision
  final_action TEXT CHECK (final_action IN ('BUY', 'SELL', 'HOLD', 'BLOCKED')),
  final_reason TEXT,
  recommended_position_size FLOAT,
  human_approval_required BOOLEAN DEFAULT FALSE,
  human_approved BOOLEAN,
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  -- Execution
  executed BOOLEAN DEFAULT FALSE,
  order_id TEXT,
  fill_price FLOAT,
  slippage FLOAT
);

CREATE INDEX idx_journal_ticker ON decision_journal(ticker);
CREATE INDEX idx_journal_created ON decision_journal(created_at DESC);
CREATE INDEX idx_journal_pipeline ON decision_journal(pipeline_run_id);
