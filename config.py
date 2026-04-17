"""Application configuration."""
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent
env_path = _PROJECT_ROOT / ".env"
load_dotenv(env_path)


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")

    # Database: prefer DATABASE_URL (Postgres in Docker / production). Else MySQL parts.
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "cashflow_risk")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD)
        database = quote_plus(self.MYSQL_DATABASE)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{database}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Forecast artifact: LightGBM quantile bundle (joblib) or legacy Ridge .pkl
    FORECAST_MODEL_PATH = os.environ.get(
        "FORECAST_MODEL_PATH",
        str(_PROJECT_ROOT / "models" / "forecast_bundle.pkl"),
    )

    # Nightly retrain (APScheduler): set ENABLE_SCHEDULER=1 in production if desired
    ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "0") == "1"
    RETRAIN_CRON_HOUR = int(os.environ.get("RETRAIN_CRON_HOUR", "3"))
    RETRAIN_CRON_MINUTE = int(os.environ.get("RETRAIN_CRON_MINUTE", "0"))

    # ML / holidays (ISO country code for `holidays` library)
    HOLIDAY_COUNTRY = os.environ.get("HOLIDAY_COUNTRY", "IN")

    # LLM — OpenRouter (OpenAI-compatible API: https://openrouter.ai/docs)
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_HTTP_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "")
    OPENROUTER_APP_NAME = os.environ.get("OPENROUTER_APP_NAME", "Cashflow Risk Advisor")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


class TestingConfig(Config):
    """Testing: in-memory SQLite unless TEST_DATABASE_URL is set."""

    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:  # type: ignore[override]
        return os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
