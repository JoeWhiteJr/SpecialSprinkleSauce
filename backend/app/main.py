import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    health,
    portfolio,
    recommendations,
    journal,
    debates,
    jury,
    overrides,
    alerts,
    bias,
    screening,
    settings as settings_router,
    data_pipeline,
    wasden_watch as wasden_watch_router,
    risk,
    execution,
)

logger = logging.getLogger("wasden_watch")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log critical configuration on startup."""
    logger.info("=" * 60)
    logger.info("Wasden Watch Trading Dashboard — Backend Starting")
    logger.info("=" * 60)
    logger.info(f"TRADING_MODE  = {settings.trading_mode}")
    logger.info(f"USE_MOCK_DATA = {settings.use_mock_data}")
    logger.info(f"CORS_ORIGINS  = {settings.cors_origins}")
    if settings.use_mock_data:
        logger.info("Running with MOCK DATA. Supabase will not be queried.")
    else:
        logger.info(f"Supabase URL  = {settings.supabase_url[:30]}..." if settings.supabase_url else "Supabase URL  = NOT SET")
    logger.info("=" * 60)

    # TRADING_MODE hardening — halt if invalid
    if settings.trading_mode not in ("paper", "live"):
        logger.critical(
            f"FATAL: TRADING_MODE='{settings.trading_mode}' is invalid. "
            "Must be 'paper' or 'live'. Shutting down."
        )
        sys.exit(1)

    yield
    logger.info("Wasden Watch backend shutting down.")


app = FastAPI(
    title="Wasden Watch Trading Dashboard API",
    description="Backend API for the Wasden Watch automated trading system dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow frontend origin(s)
origins = list(settings.cors_origins)
if settings.frontend_url:
    origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all 15 routers
app.include_router(health.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
app.include_router(journal.router)
app.include_router(debates.router)
app.include_router(jury.router)
app.include_router(overrides.router)
app.include_router(alerts.router)
app.include_router(bias.router)
app.include_router(screening.router)
app.include_router(settings_router.router)
app.include_router(data_pipeline.router)
app.include_router(wasden_watch_router.router)
app.include_router(risk.router)
app.include_router(execution.router)
