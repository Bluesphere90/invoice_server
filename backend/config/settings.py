"""
Configuration management - loads from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings:
    """Application settings loaded from environment."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://invoice_user:password@localhost:5432/invoice_db"
    )

    # Tax Portal
    TAX_USERNAME: str = os.getenv("TAX_USERNAME", "")
    TAX_PASSWORD: str = os.getenv("TAX_PASSWORD", "")

    # Collector
    COLLECTOR_INTERVAL_HOURS: int = int(os.getenv("COLLECTOR_INTERVAL_HOURS", "6"))

    # API Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "change_me_in_production")

    # JWT Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

    # Environment
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


# Singleton instance
settings = Settings()
