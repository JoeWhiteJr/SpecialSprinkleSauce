"""Quantitative models for Wasden Watch — 4-model ensemble scoring + Tier 2 models."""

from .arima_model import ARIMAModel
from .elastic_net_model import ElasticNetDirectionModel
from .manifests import generate_initial_manifests
from .miller_nn import DowLarger1aModel, MillerNNSmall
from .mlflow_tracking import ModelTracker
from .mock_scores import MOCK_QUANT_SCORES, PILOT_TICKERS, get_mock_scores
from .model_comparison import ModelComparison
from .orchestrator import QuantModelOrchestrator
from .sentiment_model import SentimentModel
from .train_pipeline import TrainingPipeline
from .validation import (
    TimeSeriesCrossValidator,
    WalkForwardValidator,
    calculate_metrics,
    generate_validation_report,
)
from .xgboost_model import XGBoostDirectionModel

__all__ = [
    "QuantModelOrchestrator",
    "XGBoostDirectionModel",
    "ElasticNetDirectionModel",
    "ARIMAModel",
    "SentimentModel",
    "MillerNNSmall",
    "DowLarger1aModel",
    "MOCK_QUANT_SCORES",
    "PILOT_TICKERS",
    "get_mock_scores",
    "generate_initial_manifests",
    "ModelTracker",
    "WalkForwardValidator",
    "TimeSeriesCrossValidator",
    "calculate_metrics",
    "generate_validation_report",
    "TrainingPipeline",
    "ModelComparison",
]
