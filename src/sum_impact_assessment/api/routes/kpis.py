"""
KPI API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ...database.connection import get_db
from ...repositories.kpi_repository import KPIRepository

router = APIRouter()


@router.get("/health")
def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        Status message indicating the API is healthy.
    """
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
    repository = KPIRepository(db)
    repository.check_db_connection()
    kpis = repository.get_all_kpis()
    return kpis
