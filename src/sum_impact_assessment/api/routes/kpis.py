"""
KPI API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ...database.connection import get_db
from ...repositories.kpi_repository import KPIRepository
from ...utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        Status message indicating the API is healthy.
    """
    logger.debug("Health check endpoint called")
    return {
        "status": "healthy",
        "service": "SUM Impact Assessment API"
    }


@router.get("/kpis")
def get_kpis(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Retrieve all KPI definitions from the database.
    
    Args:
        db: Database session (injected by FastAPI)
        
    Returns:
        List of all KPI definitions from the kpi_definitions table.
    """
    logger.debug("GET /kpis endpoint called")
    
    try:
        repository = KPIRepository(db)
        repository.check_db_connection()
        kpis = repository.get_all_kpis()
        
        logger.debug(
            "Successfully returned KPIs",
            extra={"kpi_count": len(kpis)}
        )
        return kpis
    except Exception as e:
        logger.error(
            "Error in GET /kpis endpoint",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True
        )
        raise
