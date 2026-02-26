"""
PROTECTED risk constants — copied verbatim from PROJECT_STANDARDS_v2.md Section 8.

╔═══════════════════════════════════════════════════════════════════╗
║  DO NOT MODIFY WITHOUT WRITTEN APPROVAL FROM BOTH JOE & JARED  ║
╚═══════════════════════════════════════════════════════════════════╝

Changes to any constant require human approval and a decision journal entry.
"""

# --- Position Sizing ---
MAX_POSITION_PCT = 0.12
RISK_PER_TRADE_PCT = 0.015
MIN_CASH_RESERVE_PCT = 0.10

# --- Correlation ---
MAX_CORRELATED_POSITIONS = 3
CORRELATION_THRESHOLD = 0.70
STRESS_CORRELATION_THRESHOLD = 0.80

# --- Regime Circuit Breaker ---
REGIME_CIRCUIT_BREAKER_SPY_DROP = 0.05
DEFENSIVE_POSITION_REDUCTION = 0.50
DEFENSIVE_CASH_TARGET = 0.40

# --- Model Disagreement ---
HIGH_MODEL_DISAGREEMENT_THRESHOLD = 0.50

# --- Slippage ---
SLIPPAGE_ADV_THRESHOLD = 0.01
SLIPPAGE_PER_ADV_PCT = 0.001

# --- Consecutive Loss ---
CONSECUTIVE_LOSS_WARNING = 7
