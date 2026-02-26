"""Tests for quant model orchestrator — mock mode."""

import os
import statistics

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from src.intelligence.quant_models import QuantModelOrchestrator  # noqa: E402
from src.intelligence.quant_models.mock_scores import MOCK_QUANT_SCORES  # noqa: E402


def test_orchestrator_mock_mode():
    """All 4 scores are in [0, 1] for all pilot tickers."""
    orchestrator = QuantModelOrchestrator(use_mock=True)

    for ticker in MOCK_QUANT_SCORES:
        scores = orchestrator.score_ticker(ticker)
        assert 0.0 <= scores["xgboost"] <= 1.0, f"{ticker} xgboost out of range"
        assert 0.0 <= scores["elastic_net"] <= 1.0, f"{ticker} elastic_net out of range"
        assert 0.0 <= scores["arima"] <= 1.0, f"{ticker} arima out of range"
        assert 0.0 <= scores["sentiment"] <= 1.0, f"{ticker} sentiment out of range"
        assert 0.0 <= scores["composite"] <= 1.0, f"{ticker} composite out of range"
        assert scores["std_dev"] >= 0.0, f"{ticker} std_dev negative"


def test_composite_calculation():
    """Composite is the mean of the 4 model scores."""
    orchestrator = QuantModelOrchestrator(use_mock=True)
    scores = orchestrator.score_ticker("NVDA")

    expected = statistics.mean([
        scores["xgboost"], scores["elastic_net"],
        scores["arima"], scores["sentiment"],
    ])
    assert abs(scores["composite"] - expected) < 0.001, (
        f"Composite {scores['composite']} != expected mean {expected:.4f}"
    )


def test_std_dev_calculation():
    """std_dev matches statistics.stdev of the 4 scores."""
    orchestrator = QuantModelOrchestrator(use_mock=True)
    scores = orchestrator.score_ticker("NVDA")

    expected = statistics.stdev([
        scores["xgboost"], scores["elastic_net"],
        scores["arima"], scores["sentiment"],
    ])
    assert abs(scores["std_dev"] - expected) < 0.001, (
        f"std_dev {scores['std_dev']} != expected {expected:.4f}"
    )


def test_high_disagreement_flag():
    """Flag triggers when std_dev > 0.5."""
    orchestrator = QuantModelOrchestrator(use_mock=True)

    # TSLA has high disagreement: xgboost=0.85, elastic_net=0.35, arima=0.42, sentiment=0.91
    scores = orchestrator.score_ticker("TSLA")
    all_vals = [scores["xgboost"], scores["elastic_net"], scores["arima"], scores["sentiment"]]
    std = statistics.stdev(all_vals)

    if std > 0.5:
        assert scores["high_disagreement_flag"] is True, "TSLA should have high disagreement"
    else:
        assert scores["high_disagreement_flag"] is False

    # NVDA should NOT have high disagreement (scores are all 0.68-0.88)
    nvda = orchestrator.score_ticker("NVDA")
    assert nvda["high_disagreement_flag"] is False, "NVDA should not have high disagreement"


def test_model_manifest_schema():
    """All manifests have required keys per PROJECT_STANDARDS Section 2."""
    orchestrator = QuantModelOrchestrator(use_mock=True)
    manifests = orchestrator.get_all_manifests()

    required_keys = {"model_name", "version", "model_type", "target", "output_range", "parameters", "trained", "survivorship_bias_audited"}

    for model_name, manifest in manifests.items():
        for key in required_keys:
            assert key in manifest, f"{model_name} manifest missing key: {key}"
        assert manifest["survivorship_bias_audited"] is False, (
            f"{model_name} should not be marked as audited"
        )
        assert isinstance(manifest["output_range"], list), f"{model_name} output_range should be list"
        assert len(manifest["output_range"]) == 2, f"{model_name} output_range should have 2 elements"


def test_score_multiple():
    """score_multiple returns scores for all requested tickers."""
    orchestrator = QuantModelOrchestrator(use_mock=True)
    tickers = ["NVDA", "AAPL", "TSLA"]
    results = orchestrator.score_multiple(tickers)

    assert len(results) == 3
    for ticker in tickers:
        assert ticker in results
        assert "composite" in results[ticker]
        assert "std_dev" in results[ticker]


def test_agreement_metrics():
    """Agreement metrics are calculated correctly."""
    orchestrator = QuantModelOrchestrator(use_mock=True)
    metrics = orchestrator.get_agreement_metrics()

    assert "tickers_analyzed" in metrics
    assert "avg_std_dev" in metrics
    assert "high_disagreement_count" in metrics
    assert metrics["threshold"] == 0.5
    assert metrics["tickers_analyzed"] == 10  # all pilot tickers
