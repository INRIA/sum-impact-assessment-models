"""
Repository for fetching data required for KPI impact analysis.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from ..utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class AnalysisDataRepository:
    """
    Repository for fetching all data required for KPI impact analysis.
    """

    def __init__(self, session: Session):
        """
        Initialize the analysis data repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def get_kpi_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all KPI definitions from the database.

        Returns:
            List of dictionaries containing KPI definition data
        """
        logger.debug("Fetching KPI definitions from database")

        query = text("SELECT * FROM kpidefinitions k")
        result = self.session.execute(query)

        columns = result.keys()
        kpi_definitions = [dict(zip(columns, row))
                           for row in result.fetchall()]

        logger.debug(f"Fetched {len(kpi_definitions)} KPI definitions")
        return kpi_definitions

    def get_measures(self) -> List[Dict[str, Any]]:
        """
        Get all measures (projects) from the database.

        Returns:
            List of dictionaries containing measure data
        """
        logger.debug("Fetching measures from database")

        query = text("SELECT * FROM projects p")
        result = self.session.execute(query)

        columns = result.keys()
        measures = [dict(zip(columns, row)) for row in result.fetchall()]

        logger.debug(f"Fetched {len(measures)} measures")
        return measures

    def get_kpi_groups(self, category_type: str = 'KPI_SIEF') -> List[Dict[str, Any]]:
        """
        Get KPI groups with their associated KPI IDs.

        Returns:
            List of dictionaries containing KPI group data with kpi_ids
        """
        logger.debug("Fetching KPI groups from database")

        query = text("""
            SELECT 
                c.id,
                c.name,
                kc.kpidefinition_id,
                k.name as kpidefinition_name,
                k.progression_target as kpidefinition_progression_target,
                k.min_value as kpidefinition_min_value,
                k.max_value as kpidefinition_max_value,
                k.metric as kpidefinition_metric
            FROM categories c
            INNER JOIN kpidefinitions_category kc ON c.id = kc.category_id
            INNER JOIN kpidefinitions k ON kc.kpidefinition_id = k.id
            WHERE c.`type` = :category_type
        """)
        result = self.session.execute(query, {'category_type': category_type})

        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]

        # Group KPI IDs by category
        distinct_group_id = set()
        for row in rows:
            distinct_group_id.add(row['id'])
        logger.debug(
            f"Fetched {len(rows)} kpis for {len(distinct_group_id)} KPI groups")
        return rows

    def get_living_labs(self) -> List[Dict[str, Any]]:
        """
        Get all living labs from the database.

        Returns:
            List of dictionaries containing living lab data
        """
        logger.debug("Fetching living labs from database")

        query = text("SELECT l.id, l.name FROM labs l")
        result = self.session.execute(query)

        columns = result.keys()
        living_labs = [dict(zip(columns, row))
                       for row in result.fetchall()]

        logger.debug(f"Fetched {len(living_labs)} living labs")
        return living_labs

    def get_living_lab_measures(self) -> List[Dict[str, Any]]:
        """
        Get living lab implementations with their measures (projects).

        Returns:
            List of dictionaries containing living lab and measure associations
        """
        logger.debug("Fetching living lab measures from database")

        query = text("""
            SELECT llpi.living_lab_id as lab_id, l.name as lab_name, llpi.project_id, p.name as project_name
            FROM living_lab_projects_implementation llpi
            INNER JOIN labs l ON llpi.living_lab_id = l.id
            INNER JOIN projects p ON p.id  = llpi.project_id 
        """)
        result = self.session.execute(query)

        columns = result.keys()
        living_lab_measures = [dict(zip(columns, row))
                               for row in result.fetchall()]

        logger.debug(
            f"Fetched {len(living_lab_measures)} living lab measure associations")
        return living_lab_measures

    def get_living_lab_kpi_results(self) -> List[Dict[str, Any]]:
        """
        Get living lab KPI results with before and after values.

        Returns:
            List of dictionaries containing KPI results with before/after values
        """
        logger.debug("Fetching living lab KPI results from database")

        query = text("""
            SELECT 
                b4.kpidefinition_id,
                b4.transport_mode_id,
                tm.name as transport_mode_name,
                b4.living_lab_id,
                b4.value as value_before,
                b4.date as date_before,
                after.value as value_after,
                after.date as date_after,
                k.name,
                k.progression_target,
                k.min_value,
                k.max_value,
                k.metric
            FROM kpiresults b4
            INNER JOIN kpiresults after
                ON b4.living_lab_id = after.living_lab_id 
                AND b4.kpidefinition_id = after.kpidefinition_id
                AND ((b4.transport_mode_id IS NULL AND after.transport_mode_id IS NULL) OR (b4.transport_mode_id = after.transport_mode_id))
                AND b4.date < after.date
            INNER JOIN kpidefinitions k
                ON b4.kpidefinition_id = k.id
            LEFT JOIN transport_mode tm ON tm.id = b4.transport_mode_id
            INNER JOIN (
                SELECT 
                    living_lab_id,
                    kpidefinition_id,
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM kpiresults
                GROUP BY living_lab_id, kpidefinition_id
            ) bounds
                ON b4.living_lab_id = bounds.living_lab_id
                AND b4.kpidefinition_id = bounds.kpidefinition_id
                AND b4.date = bounds.min_date
                AND after.date = bounds.max_date
        """)
        result = self.session.execute(query)

        columns = result.keys()
        kpi_results = [dict(zip(columns, row)) for row in result.fetchall()]

        logger.debug(f"Fetched {len(kpi_results)} living lab KPI results")
        return kpi_results
