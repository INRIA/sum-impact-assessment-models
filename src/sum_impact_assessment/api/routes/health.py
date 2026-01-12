"""
KPI API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from ...repositories.kpi_repository import KPIRepository
from ...utils.logger import get_logger
from ...database.connection import get_db

# Initialize logger
logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify the API is running.

    Returns:
        Status message indicating the API is healthy.
    """
    logger.debug("Health check endpoint called")
    status = "healthy"
    try:
        db.execute(select(1))
    except Exception as e:
        logger.error(
            "Database connection failed during health check",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True
        )
        status = "unhealthy"
    return {
        "status": status,
        "service": "SUM Impact Assessment API"
    }
