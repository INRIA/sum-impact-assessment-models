"""
Run the FastAPI application server.

Usage:
    python run_api.py
"""
import uvicorn
from src.sum_impact_assessment.config.settings import settings
from src.sum_impact_assessment.api.main import app


if __name__ == "__main__":
    uvicorn.run(
        "__main__:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENV == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
