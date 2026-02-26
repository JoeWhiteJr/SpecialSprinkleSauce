import os
from pydantic_settings import BaseSettings

TRADING_MODE = os.getenv("TRADING_MODE")
assert TRADING_MODE in ("paper", "live"), (
    "TRADING_MODE must be explicitly set to 'paper' or 'live'. "
    "System halts if unset. Set via environment variable or .env file. "
    "This is the primary safeguard against accidental live trading."
)


class Settings(BaseSettings):
    trading_mode: str = TRADING_MODE
    use_mock_data: bool = True
    supabase_url: str = ""
    supabase_service_key: str = ""
    frontend_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    # Alpaca API keys (never hardcode — loaded from .env)
    alpaca_paper_api_key: str = ""
    alpaca_paper_secret_key: str = ""
    alpaca_live_api_key: str = ""
    alpaca_live_secret_key: str = ""

    # Finnhub API key
    finnhub_api_key: str = ""

    # NewsAPI key
    newsapi_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
