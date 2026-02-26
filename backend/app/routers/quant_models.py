"""Quant models API — scores, status, and agreement metrics."""

from fastapi import APIRouter

from app.config import settings
from app.mock.generators import generate_quant_scores_mock, generate_quant_status_mock

router = APIRouter(prefix="/api/quant-models", tags=["quant-models"])


@router.get("/scores/{ticker}")
async def get_ticker_scores(ticker: str):
    """Get quant model scores for a single ticker."""
    if settings.use_mock_data:
        return generate_quant_scores_mock(ticker)

    from src.intelligence.quant_models import QuantModelOrchestrator

    orchestrator = QuantModelOrchestrator(
        use_mock=False,
        finnhub_api_key=settings.finnhub_api_key,
        newsapi_api_key=settings.newsapi_api_key,
    )
    return orchestrator.score_ticker(ticker)


@router.get("/scores")
async def get_all_scores():
    """Get quant model scores for all pilot tickers."""
    if settings.use_mock_data:
        from src.intelligence.quant_models.mock_scores import PILOT_TICKERS
        return {t: generate_quant_scores_mock(t) for t in PILOT_TICKERS}

    from src.intelligence.quant_models import QuantModelOrchestrator, PILOT_TICKERS

    orchestrator = QuantModelOrchestrator(
        use_mock=False,
        finnhub_api_key=settings.finnhub_api_key,
        newsapi_api_key=settings.newsapi_api_key,
    )
    return orchestrator.score_multiple(PILOT_TICKERS)


@router.get("/status")
async def get_model_status():
    """Get model versions, training status, and manifests."""
    if settings.use_mock_data:
        return generate_quant_status_mock()

    from src.intelligence.quant_models import QuantModelOrchestrator

    orchestrator = QuantModelOrchestrator(use_mock=False)
    return {
        "models": orchestrator.get_all_manifests(),
        "use_mock_data": settings.use_mock_data,
    }


@router.get("/agreement")
async def get_agreement_metrics():
    """Get model agreement metrics across all pilot tickers."""
    if settings.use_mock_data:
        from src.intelligence.quant_models import QuantModelOrchestrator
        orchestrator = QuantModelOrchestrator(use_mock=True)
        return orchestrator.get_agreement_metrics()

    from src.intelligence.quant_models import QuantModelOrchestrator

    orchestrator = QuantModelOrchestrator(
        use_mock=False,
        finnhub_api_key=settings.finnhub_api_key,
        newsapi_api_key=settings.newsapi_api_key,
    )
    return orchestrator.get_agreement_metrics()
