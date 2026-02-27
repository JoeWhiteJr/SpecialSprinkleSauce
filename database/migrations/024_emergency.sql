-- Migration 024: Emergency events table
-- Week 10: Emergency service persistence

CREATE TABLE IF NOT EXISTS emergency_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN ('shutdown', 'resume', 'cancel_orders', 'force_paper')),
    initiated_by TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emergency_events_type ON emergency_events(event_type);
CREATE INDEX IF NOT EXISTS idx_emergency_events_created_at ON emergency_events(created_at DESC);

ALTER TABLE emergency_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to emergency_events" ON emergency_events FOR SELECT USING (true);

COMMENT ON TABLE emergency_events IS 'Audit log of emergency actions (shutdown, resume, cancel orders, force paper mode)';
