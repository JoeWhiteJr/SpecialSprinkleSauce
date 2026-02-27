-- Migration 023: Report cache table
-- Week 10: Reports service persistence

CREATE TABLE IF NOT EXISTS report_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type TEXT NOT NULL CHECK (report_type IN ('daily', 'weekly', 'monthly')),
    period TEXT NOT NULL,
    report_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (report_type, period)
);

CREATE INDEX IF NOT EXISTS idx_report_cache_type_period ON report_cache(report_type, period);
CREATE INDEX IF NOT EXISTS idx_report_cache_created_at ON report_cache(created_at DESC);

ALTER TABLE report_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to report_cache" ON report_cache FOR SELECT USING (true);

COMMENT ON TABLE report_cache IS 'Cached generated reports by type and period';
