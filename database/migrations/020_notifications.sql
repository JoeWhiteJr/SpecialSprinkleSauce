-- Migration 020: Notification history table
-- Week 10: Notification service persistence

CREATE TABLE IF NOT EXISTS notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    channel TEXT NOT NULL DEFAULT 'log',
    success BOOLEAN NOT NULL DEFAULT true,
    ticker TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_history_severity ON notification_history(severity);
CREATE INDEX IF NOT EXISTS idx_notification_history_channel ON notification_history(channel);
CREATE INDEX IF NOT EXISTS idx_notification_history_created_at ON notification_history(created_at DESC);

ALTER TABLE notification_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to notification_history" ON notification_history FOR SELECT USING (true);

COMMENT ON TABLE notification_history IS 'Audit trail for all notifications sent across channels';
