"""Pre-training model version manifests for all quant models.

These manifests are "pre-training" snapshots aligned with the model_versions
table (migration 018). They will be updated with real training metadata
when models are trained on the server.

Includes Phase 1 (Tier 1) ensemble models and Tier 2 models (Miller NN).
"""

from .arima_model import DEFAULT_ORDER as ARIMA_DEFAULT_ORDER
from .elastic_net_model import DEFAULT_PARAMS as ELASTIC_NET_DEFAULT_PARAMS
from .miller_nn import DEFAULT_PARAMS as MILLER_NN_DEFAULT_PARAMS
from .miller_nn import LARGER_DEFAULT_PARAMS as MILLER_NN_LARGER_PARAMS
from .sentiment_model import FINNHUB_WEIGHT, NEWSAPI_WEIGHT
from .xgboost_model import DEFAULT_PARAMS as XGBOOST_DEFAULT_PARAMS


def generate_initial_manifests() -> list[dict]:
    """Generate pre-training manifests for all quant models.

    Returns manifest dicts matching the model_versions table schema
    (migration 018). All training-related fields are None/empty since
    these models have not yet been trained on real data.

    Returns:
        List of 6 manifest dicts (4 Phase 1 Tier 1 + 2 Tier 2 Miller NN).
    """
    return [
        {
            "model_name": "XGBoostDirectionModel",
            "version": "0.1.0-mock",
            "trained_date": None,
            "training_data_range": None,
            "holdout_period": None,
            "survivorship_bias_audited": False,
            "validation_results": {},
            "parameters": XGBOOST_DEFAULT_PARAMS,
        },
        {
            "model_name": "ElasticNetDirectionModel",
            "version": "0.1.0-mock",
            "trained_date": None,
            "training_data_range": None,
            "holdout_period": None,
            "survivorship_bias_audited": False,
            "validation_results": {},
            "parameters": ELASTIC_NET_DEFAULT_PARAMS,
        },
        {
            "model_name": "ARIMAModel",
            "version": "0.1.0-mock",
            "trained_date": None,
            "training_data_range": None,
            "holdout_period": None,
            "survivorship_bias_audited": False,
            "validation_results": {},
            "parameters": {"order": list(ARIMA_DEFAULT_ORDER)},
        },
        {
            "model_name": "SentimentModel",
            "version": "0.1.0-mock",
            "trained_date": None,
            "training_data_range": None,
            "holdout_period": None,
            "survivorship_bias_audited": False,
            "validation_results": {},
            "parameters": {
                "finnhub_weight": FINNHUB_WEIGHT,
                "newsapi_weight": NEWSAPI_WEIGHT,
                "sources": ["finnhub", "newsapi"],
            },
        },
        # --- Tier 2 models (not in Phase 1 ensemble) ---
        {
            "model_name": "MillerNNSmall_DowSmall1a",
            "version": "0.1.0-mock",
            "trained_date": None,
            "training_data_range": None,
            "holdout_period": None,
            "survivorship_bias_audited": False,
            "validation_results": {},
            "parameters": MILLER_NN_DEFAULT_PARAMS,
            "notes": "Tier 2 — Dr. Miller DowSmall1a, ported from R architecture spec. Not in Phase 1 ensemble.",
        },
        {
            "model_name": "DowLarger1a",
            "version": "0.1.0-mock",
            "trained_date": None,
            "training_data_range": None,
            "holdout_period": None,
            "survivorship_bias_audited": False,
            "validation_results": {},
            "parameters": MILLER_NN_LARGER_PARAMS,
            "notes": "Tier 2 — Dr. Miller DowLarger1a (6 inputs, [10,8,6] hidden). Not in Phase 1 ensemble.",
        },
    ]
