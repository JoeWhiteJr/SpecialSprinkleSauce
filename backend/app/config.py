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
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
