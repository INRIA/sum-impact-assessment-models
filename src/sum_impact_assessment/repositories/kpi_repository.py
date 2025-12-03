"""
Repository for KPI data access.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any


class KPIRepository:
    """
    Repository for accessing KPI definitions from the database.
    Follows the Repository pattern for data access abstraction.
    """
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        
    def check_db_connection(self) -> bool:
        """
        Check if the database connection is alive.
        
        Returns:
            True if the connection is alive, False otherwise.
        """
        try:
            self.session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def get_all_kpis(self) -> List[Dict[str, Any]]:
        """
        Retrieve all KPI definitions from the kpidefinitions table.
        
        Returns:
            List of KPI definitions as dictionaries.
        """
        query = text("SELECT * FROM kpidefinitions")
        result = self.session.execute(query)
        
        # Convert rows to dictionaries
        columns = result.keys()
        kpis = [dict(zip(columns, row)) for row in result.fetchall()]
        
        return kpis
    
    def get_kpi_by_id(self, kpi_id: str) -> Dict[str, Any] | None:
        """
        Retrieve a single KPI definition by ID.
        
        Args:
            kpi_id: The KPI identifier
            
        Returns:
            KPI definition as dictionary, or None if not found.
        """
        query = text("SELECT * FROM kpidefinitions WHERE id = :kpi_id")
        result = self.session.execute(query, {"kpi_id": kpi_id})
        
        row = result.fetchone()
        if row:
            columns = result.keys()
            return dict(zip(columns, row))
        return None
