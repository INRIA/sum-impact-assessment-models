"""
Analysis Data Service - Shared service for fetching and transforming analysis data.

This service centralizes data fetching and transformation logic used by multiple jobs.
"""
from sqlalchemy.orm import Session
from typing import Tuple, List, Optional
from ..repositories.analysis_data_repository import AnalysisDataRepository
from .analysis_data_transformer import AnalysisDataTransformer
from ..schemas.core import KPI, Measure, KPIGroup, LivingLab
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisDataService:
    """
    Service for fetching and transforming data required for impact and MCDA analysis.

    Provides centralized data access with consistent transformation logic.
    """

    def __init__(self, db: Session):
        """
        Initialize the service with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.analysis_repo = AnalysisDataRepository(db)
        self.transformer = AnalysisDataTransformer()

    def get_analysis_input_data(
        self,
        kpi_group_filter: Optional[str] = None
    ) -> Tuple[List[KPI], List[Measure], List[KPIGroup], List[LivingLab]]:
        """
        Fetch and transform all data needed for analysis.

        Args:
            kpi_group_filter: Optional group type filter (e.g., "MCDA_GOALS")

        Returns:
            Tuple containing:
            - List of KPI definitions
            - List of measures
            - List of KPI groups (filtered if specified)
            - List of living labs with measures and KPI results
        """
        logger.info(
            "Fetching analysis input data",
            extra={"kpi_group_filter": kpi_group_filter}
        )

        # Step 1: Fetch raw data from database
        raw_kpi_definitions = self.analysis_repo.get_kpi_definitions()
        raw_measures = self.analysis_repo.get_measures()

        # Fetch KPI groups with optional filter
        if kpi_group_filter:
            raw_kpi_groups = self.analysis_repo.get_kpi_groups(
                kpi_group_filter)
        else:
            raw_kpi_groups = self.analysis_repo.get_kpi_groups("KPI_SIEF")

        raw_lab_measures = self.analysis_repo.get_living_lab_measures()
        raw_lab_kpi_results = self.analysis_repo.get_living_lab_kpi_results()
        raw_living_labs = self.analysis_repo.get_living_labs()

        logger.info(
            "Raw data fetched successfully",
            extra={
                "kpi_definitions": len(raw_kpi_definitions),
                "measures": len(raw_measures),
                "kpi_groups": len(raw_kpi_groups),
                "living_labs": len(raw_living_labs),
                "lab_measures": len(raw_lab_measures),
                "kpi_results": len(raw_lab_kpi_results),
            }
        )

        # Step 2: Transform to Pydantic schemas
        logger.info("Transforming data to Pydantic schemas")

        kpis = self.transformer.transform_kpis(raw_kpi_definitions)
        measures = self.transformer.transform_measures(raw_measures)
        kpi_groups = self.transformer.transform_kpi_groups(raw_kpi_groups)
        living_labs = self.transformer.transform_living_labs(
            raw_living_labs,
            raw_lab_measures,
            raw_lab_kpi_results
        )

        logger.info(
            "Data transformation completed",
            extra={
                "kpis": len(kpis),
                "measures": len(measures),
                "kpi_groups": len(kpi_groups),
                "living_labs": len(living_labs)
            }
        )

        return kpis, measures, kpi_groups, living_labs

    def get_kpi_group_by_id(self, group_id: str) -> Optional[KPIGroup]:
        """
        Get a specific KPI group by ID.

        Args:
            group_id: The group ID to fetch

        Returns:
            KPIGroup if found, None otherwise
        """
        raw_groups = self.analysis_repo.get_kpi_groups(group_id)
        if not raw_groups:
            return None

        groups = self.transformer.transform_kpi_groups(raw_groups)
        return groups[0] if groups else None
