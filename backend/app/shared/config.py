from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    No secrets are hardcoded here.
    """

    APP_NAME: str = "Vuneliq API"
    ENVIRONMENT: str
    DEBUG: bool = True


    # Database
    # Default to SQLite for local development/testing; can be overridden via DATABASE_URL
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # CORS settings: list of origins allowed to talk to this API
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()