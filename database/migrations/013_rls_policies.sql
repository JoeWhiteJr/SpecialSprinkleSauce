-- 013_rls_policies.sql
-- Row Level Security policies for Supabase
-- Authenticated users get read access to all tables
-- Insert/update limited to action tables (recommendations, overrides, alerts, settings)
-- Service role bypasses RLS automatically in Supabase

-- Enable RLS on all tables
ALTER TABLE decision_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_daily_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE jury_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE veto_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE consecutive_loss_tracker ENABLE ROW LEVEL SECURITY;
ALTER TABLE bias_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE bloomberg_fundamentals ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read all
CREATE POLICY "Authenticated users can read" ON decision_journal FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON trade_recommendations FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON portfolio_positions FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON portfolio_daily_snapshot FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON jury_votes FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON debate_transcripts FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON veto_overrides FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON risk_alerts FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON consecutive_loss_tracker FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON bias_metrics FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON bloomberg_fundamentals FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON watchlist FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON screening_runs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read" ON system_settings FOR SELECT TO authenticated USING (true);

-- Authenticated users can insert/update for action tables
CREATE POLICY "Authenticated users can insert" ON trade_recommendations FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update" ON trade_recommendations FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can insert" ON veto_overrides FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update" ON veto_overrides FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can update" ON risk_alerts FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can update" ON system_settings FOR UPDATE TO authenticated USING (true);

-- Service role bypasses RLS automatically in Supabase
