-- Audit log: durable sink for all security-sensitive backend actions.
-- Mirrors the stdout log in backend/app/audit.py so events survive
-- container restarts and Render log-retention cutoffs.
--
-- Written by: backend/app/audit.py via Supabase service-role client
-- Read by: Joe/Jared for forensic review of trading actions

CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    action      TEXT        NOT NULL,                    -- e.g. 'emergency_shutdown'
    endpoint    TEXT        NOT NULL,                    -- e.g. '/api/emergency/shutdown'
    principal   TEXT        NOT NULL DEFAULT 'unknown',  -- derived from X-API-Key
    details     TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action     ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_principal  ON audit_log (principal);

-- RLS: service role writes; authenticated users (Joe/Jared) read all entries
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON audit_log
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_read" ON audit_log
    FOR SELECT TO authenticated
    USING (true);
