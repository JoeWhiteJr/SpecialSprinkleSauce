-- Migration 026: Training Lab
-- Experiment tracking, parameter sweeps, model snapshots, and dual-approval change proposals

-- ============================================================
-- 1. Experiments
-- ============================================================
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_name TEXT NOT NULL CHECK (user_name IN ('joe', 'jared')),
    experiment_type TEXT NOT NULL CHECK (experiment_type IN (
        'hyperparameter_sweep', 'weight_tuning', 'threshold_optimization',
        'stress_test', 'goal_calibration', 'baseline', 'paper_validation'
    )),
    name TEXT NOT NULL,
    description TEXT,
    parameters JSONB NOT NULL DEFAULT '{}',
    results JSONB NOT NULL DEFAULT '{}',
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'cancelled'
    )),
    phase TEXT CHECK (phase IN (
        'pre_server', 'server_setup', 'weight_tuning',
        'stress_test', 'goal_calibration', 'paper_trading'
    )),
    data_source TEXT CHECK (data_source IN ('mock', 'emery', 'dow_jones', 'custom')),
    mlflow_run_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_experiments_user_name ON experiments(user_name);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_created_at ON experiments(created_at DESC);
CREATE INDEX idx_experiments_phase ON experiments(phase);

-- ============================================================
-- 2. Parameter Sweeps
-- ============================================================
CREATE TABLE IF NOT EXISTS parameter_sweeps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    parameter_name TEXT NOT NULL,
    parameter_category TEXT NOT NULL CHECK (parameter_category IN (
        'model_hyperparam', 'ensemble_weight', 'screening_threshold',
        'risk_constant', 'sentiment_weight', 'goal_param'
    )),
    min_value NUMERIC NOT NULL,
    max_value NUMERIC NOT NULL,
    step_size NUMERIC,
    values_tested JSONB NOT NULL DEFAULT '[]',
    results_per_value JSONB NOT NULL DEFAULT '[]',
    best_value NUMERIC,
    best_metric_name TEXT,
    best_metric_value NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_parameter_sweeps_experiment_id ON parameter_sweeps(experiment_id);

-- ============================================================
-- 3. Model Snapshots
-- ============================================================
CREATE TABLE IF NOT EXISTS model_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}',
    parameters JSONB NOT NULL DEFAULT '{}',
    artifact_path TEXT,
    is_baseline BOOLEAN NOT NULL DEFAULT FALSE,
    data_source TEXT,
    data_range TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_model_snapshots_experiment_id ON model_snapshots(experiment_id);
CREATE INDEX idx_model_snapshots_is_baseline ON model_snapshots(is_baseline) WHERE is_baseline = TRUE;

-- ============================================================
-- 4. Parameter Change Proposals (dual-approval gate)
-- ============================================================
CREATE TABLE IF NOT EXISTS parameter_change_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    parameter_name TEXT NOT NULL,
    parameter_category TEXT NOT NULL CHECK (parameter_category IN (
        'model_hyperparam', 'ensemble_weight', 'screening_threshold',
        'risk_constant', 'sentiment_weight', 'goal_param'
    )),
    current_value NUMERIC NOT NULL,
    proposed_value NUMERIC NOT NULL,
    metric_before JSONB NOT NULL DEFAULT '{}',
    metric_after JSONB NOT NULL DEFAULT '{}',
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'joe_approved', 'jared_approved', 'applied', 'rejected', 'rolled_back'
    )),
    joe_approved_at TIMESTAMPTZ,
    jared_approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_proposals_status ON parameter_change_proposals(status);
CREATE INDEX idx_proposals_experiment_id ON parameter_change_proposals(experiment_id);

-- ============================================================
-- 5. Parameter History (rollback trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS parameter_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES parameter_change_proposals(id),
    parameter_name TEXT NOT NULL,
    old_value NUMERIC NOT NULL,
    new_value NUMERIC NOT NULL,
    applied_by TEXT NOT NULL,
    metric_before JSONB NOT NULL DEFAULT '{}',
    metric_after JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_parameter_history_proposal_id ON parameter_history(proposal_id);
CREATE INDEX idx_parameter_history_parameter_name ON parameter_history(parameter_name);

-- ============================================================
-- Enable RLS (matches project pattern)
-- ============================================================
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE parameter_sweeps ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE parameter_change_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE parameter_history ENABLE ROW LEVEL SECURITY;
