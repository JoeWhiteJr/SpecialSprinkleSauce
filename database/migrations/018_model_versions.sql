-- Migration 018: Model versions table for quant model tracking
-- Week 5: Quantitative Models

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    trained_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_data_range TEXT,
    holdout_period TEXT,
    survivorship_bias_audited BOOLEAN NOT NULL DEFAULT FALSE,
    validation_results JSONB DEFAULT '{}'::jsonb,
    parameters JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_versions_model_name ON model_versions(model_name);
CREATE INDEX IF NOT EXISTS idx_model_versions_trained_date ON model_versions(trained_date DESC);

COMMENT ON TABLE model_versions IS 'Tracks quant model versions, training metadata, and audit status';
COMMENT ON COLUMN model_versions.survivorship_bias_audited IS 'Must be explicitly set to true after audit — default false';
