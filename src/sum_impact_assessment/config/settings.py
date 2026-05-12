"""
Application configuration settings.
"""
from typing import Any, Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from ..__version__ import __version__
from ..schemas.job import JobNameEnum


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    ENV: str = "development"
    # Database configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "sum_odp"

    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "SUM Impact Assessment API"
    API_VERSION: str = __version__
    INTERNAL_API_KEY: str = ""
    ADMIN_REFRESH_API_KEY: str = ""

    # Application configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    REFRESH_DISPATCH_INTERVAL_SECONDS: float = 1.5
    REFRESH_IDEMPOTENCY_WINDOW_SECONDS: int = 60
    REFRESH_RATE_LIMIT_SECONDS: int = 60
    ADMIN_REFRESH_ALLOWED_IPS: List[str] = ["127.0.0.1", "::1", "localhost", "testclient"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def database_url(self) -> str:
        """
        Construct the database URL for SQLAlchemy.
        """
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


# Global settings instance
settings = Settings()

JOB_RUN_CONFIGURATION: List[Dict[str, Any]] = [
    {
        "job_name": JobNameEnum.KPI_MEASURES_ANALYSIS,
        "kpi_group_type": "KPI_SIEF",
    },
    {
        "job_name": JobNameEnum.MCDA_ANALYSIS_QUANTITATIVE,
        "perspective": "regulatory",
        "kpi_group_type": "MCDA_GOALS",
    },
    {
        "job_name": JobNameEnum.MCDA_ANALYSIS_QUANTITATIVE,
        "perspective": "pto",
        "kpi_group_type": "MCDA_GOALS",
    },
    {
        "job_name": JobNameEnum.MCDA_ANALYSIS_QUANTITATIVE,
        "perspective": "nsm_providers",
        "kpi_group_type": "MCDA_GOALS",
    },
    {
        "job_name": JobNameEnum.MCDA_ANALYSIS_QUALITATIVE,
        "perspective": "regulatory",
    },
    {
        "job_name": JobNameEnum.MCDA_ANALYSIS_QUALITATIVE,
        "perspective": "pto",
    },
    {
        "job_name": JobNameEnum.MCDA_ANALYSIS_QUALITATIVE,
        "perspective": "nsm_providers",
    },
]
