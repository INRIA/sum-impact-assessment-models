"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from ..__version__ import __version__


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

    # Application configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

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
