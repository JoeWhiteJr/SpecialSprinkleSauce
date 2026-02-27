-- Migration 014b: Add RLS policy to price_history table
-- Fixes missing RLS from original migration 014

ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to price_history" ON price_history FOR SELECT USING (true);
