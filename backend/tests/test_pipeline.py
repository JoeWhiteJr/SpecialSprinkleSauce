"""Tests for decision pipeline — mock mode, all paths."""

import inspect
import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from src.pipeline.decision_pipeline import DecisionPipeline  # noqa: E402
from src.pipeline.mock_pipeline import MockDecisionPipeline  # noqa: E402


def test_pipeline_veto_path():
    """Wasden VETO skips debate/jury, produces BLOCKED."""
    pipeline = DecisionPipeline(use_mock=True)
    # XOM is vetoed in mock data
    result = pipeline.run("XOM", price=147.28)

    assert result["final_decision"]["action"] == "BLOCKED"
    assert "VETO" in result["final_decision"]["reason"]
    # Debate should be skipped (no rounds or minimal)
    assert result["jury"]["spawned"] is False


def test_pipeline_agreement_path():
    """Debate agreement skips jury, proceeds to risk/decision."""
    pipeline = DecisionPipeline(use_mock=True)
    # NVDA reaches agreement in mock
    result = pipeline.run("NVDA", price=189.82)

    assert result["debate_result"]["outcome"] == "agreement"
    assert result["jury"]["spawned"] is False
    # Should not be blocked (NVDA passes everything)
    assert result["final_decision"]["action"] in ("BUY", "HOLD", "SELL")


def test_pipeline_jury_path():
    """Disagreement triggers jury, produces decisive vote."""
    pipeline = DecisionPipeline(use_mock=True)
    # NFLX has disagreement + jury with 6 HOLD votes in mock
    result = pipeline.run("NFLX", price=78.67)

    assert result["debate_result"]["outcome"] == "disagreement"
    assert result["jury"]["spawned"] is True
    assert result["jury"]["escalated_to_human"] is False


def test_pipeline_escalation_path():
    """5-5 jury tie produces ESCALATED — never auto-resolve."""
    pipeline = DecisionPipeline(use_mock=True)
    # TSM has 5 BUY, 5 SELL in mock → escalation
    result = pipeline.run("TSM", price=370.54)

    assert result["final_decision"]["action"] == "ESCALATED"
    assert result["final_decision"]["human_approval_required"] is True
    assert result["jury"]["escalated_to_human"] is True


def test_pipeline_risk_block_path():
    """Risk check failure produces BLOCKED."""
    pipeline = DecisionPipeline(use_mock=True)
    # AAPL fails risk check (sector_concentration) in mock
    result = pipeline.run("AAPL", price=264.58)

    assert result["final_decision"]["action"] == "BLOCKED"
    assert "sector_concentration" in result["risk_check"]["checks_failed"]


def test_pipeline_determinism():
    """Same input produces same output (fixed seed)."""
    pipeline = DecisionPipeline(use_mock=True, random_seed=42)

    result1 = pipeline.run("NVDA", price=189.82)
    result2 = pipeline.run("NVDA", price=189.82)

    # Core decision fields should match
    assert result1["final_decision"]["action"] == result2["final_decision"]["action"]
    assert result1["quant_scores"]["composite"] == result2["quant_scores"]["composite"]
    assert result1["wasden_verdict"]["verdict"] == result2["wasden_verdict"]["verdict"]


def test_decision_arbiter_separation():
    """DecisionArbiter has zero imports from pre_trade_validation or risk_engine."""
    from src.pipeline.arbiter import decision_arbiter

    source = inspect.getsource(decision_arbiter)
    # Extract only actual import lines (not docstrings or comments)
    import_lines = [
        line.strip() for line in source.split("\n")
        if line.strip().startswith(("import ", "from "))
    ]
    import_text = "\n".join(import_lines)

    assert "risk_engine" not in import_text, (
        "DecisionArbiter must not import risk_engine"
    )
    assert "pre_trade_validation" not in import_text, (
        "DecisionArbiter must not import pre_trade_validation"
    )


def test_mock_pipeline_matches():
    """MockDecisionPipeline produces same structure as DecisionPipeline."""
    full = DecisionPipeline(use_mock=True)
    mock = MockDecisionPipeline()

    full_result = full.run("NVDA", price=189.82)
    mock_result = mock.run("NVDA", price=189.82)

    # Same top-level keys
    expected_keys = {
        "id", "timestamp", "ticker", "pipeline_run_id",
        "quant_scores", "wasden_verdict", "bull_case", "bear_case",
        "debate_result", "jury", "risk_check", "pre_trade_validation",
        "final_decision", "execution",
    }
    for key in expected_keys:
        assert key in full_result, f"Full pipeline missing key: {key}"
        assert key in mock_result, f"Mock pipeline missing key: {key}"

    # Same action (deterministic)
    assert full_result["final_decision"]["action"] == mock_result["final_decision"]["action"]


def test_pipeline_veto_bypasses_debate():
    """Wasden VETO should result in no debate/jury activity."""
    pipeline = DecisionPipeline(use_mock=True)
    result = pipeline.run("XOM", price=147.28)

    # No bull/bear cases generated for vetoed tickers
    assert result["bull_case"] == ""
    assert result["bear_case"] == ""
    assert result["debate_result"]["rounds"] == 0
    assert result["jury"]["spawned"] is False
