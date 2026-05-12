"""
KPI Measures Analysis Job - Executes impact analysis using KPIImpactAnalyzer.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict
from ..repositories.job_repository import JobRepository
from .analysis_data_service import AnalysisDataService
from .jobs.base import BaseJob
from ..models.impact_analysis.kpi_impact_analysis import KPIImpactAnalyzer
from ..schemas.job import JobStatusEnum
from ..utils.logger import get_logger
from ..utils.modal_split import expand_modal_split_groups
from ..utils.time import utc_now

# Initialize logger
logger = get_logger(__name__)


class KpiMeasuresAnalysisJob(BaseJob):
    """
    Job that executes KPI measures impact analysis.

    This job:
    1. Fetches data from the database (KPIs, measures, groups, living labs)
    2. Transforms raw data into Pydantic schemas
    3. Instantiates KPIImpactAnalyzer
    4. Runs the analysis
    5. Logs results and updates job status
    """

    @classmethod
    def _execute(cls, job_id: str, db: Session, params: Optional[Dict], job_repo: JobRepository) -> None:
        """Domain logic for KPI measures impact analysis."""
        # Run KPI impact analysis using shared function
        kpi_group_filter = params.get("kpi_group_type") if params else None
        logger.info("Running impact analysis")

        input_data_snapshot, successful_results, error_results = KpiMeasuresAnalysisJob.run_kpi_impact_analysis(
            db=db,
            kpi_group_filter=kpi_group_filter
        )

        # Save input data snapshot
        job_repo.update_job_data(
            job_id=job_id, input_data=input_data_snapshot)
        logger.info("Input data snapshot saved")

        # Serialize and save output data snapshot
        output_data_snapshot = {
            "success": successful_results,
            "errors": error_results,
            "timestamp": utc_now().isoformat()
        }
        job_repo.update_job_data(
            job_id=job_id, output_data=output_data_snapshot)
        logger.info("Output data snapshot saved")

        # Log results
        logger.info(
            "Analysis completed successfully",
            extra={
                "groups_analyzed": len(successful_results),
                "groups_failed": len(error_results)
            }
        )

        # Update status to SUCCESS
        success_count = len(successful_results)
        total_count = len(successful_results) + len(error_results)
        analyzed_groups = ', '.join(
            [r['group_name'] for r in successful_results])
        failed_groups = ', '.join(
            [r['group_name'] for r in error_results]) if error_results else None

        success_message = (
            f"Analysis completed for {success_count}/{total_count} KPI groups. "
            f"Analyzed: ({analyzed_groups})"
        )
        if failed_groups:
            success_message += f" | Failed: ({failed_groups})"
        job_repo.update_job_status(
            job_id=job_id,
            status=JobStatusEnum.SUCCESS,
            message=success_message,
            completed_at=utc_now()
        )
        logger.info(
            f"KPI measures analysis job completed successfully: {job_id}")

    @staticmethod
    def run_kpi_impact_analysis(db: Session, kpi_group_filter: Optional[str] = None):
        """
        Run KPI impact analysis and return results.

        This function retrieves data, runs the analysis, and returns results.
        It can be used by both KpiMeasuresAnalysisJob and McdaQuantitativeJob.

        Args:
            db: Database session for fetching data
            kpi_group_filter: Optional filter for specific KPI group

        Returns:
            tuple: (input_data_snapshot, successful_results, error_results)
        """
        # Fetch and transform data using service
        data_service = AnalysisDataService(db)
        kpis, measures, kpi_groups, living_labs = data_service.get_analysis_input_data(
            kpi_group_filter=kpi_group_filter
        )

        # Expand Modal Split group by transport mode for KPI impact analysis only.
        # MCDA analysis keeps original groups (no transport mode split considered).
        if kpi_group_filter != "MCDA_GOALS":
            kpi_groups = expand_modal_split_groups(kpi_groups, living_labs)

        # Create input data snapshot
        input_data_snapshot = {
            "kpis": [kpi.model_dump() for kpi in kpis],
            "measures": [measure.model_dump() for measure in measures],
            "kpi_groups": [group.model_dump() for group in kpi_groups],
            "living_labs": [lab.model_dump() for lab in living_labs],
            "kpi_group_filter": kpi_group_filter,
            "timestamp": utc_now().isoformat()
        }

        # Instantiate KPIImpactAnalyzer
        analyzer = KPIImpactAnalyzer(
            living_labs=living_labs,
            measures=measures,
            kpis=kpis,
            kpi_groups=kpi_groups
        )

        # Run the analysis - track successful results and errors separately
        successful_results = []
        error_results = []

        for group in kpi_groups:
            try:
                logger.debug(
                    f"Analyzing KPI group: {group.name} (ID: {group.id})")
                group_results = analyzer.run_analysis_group(group)

                # Store full KPIGroupImpactOutput
                successful_results.append({
                    "group_id": group.id,
                    "group_name": group.name,
                    "results": group_results.model_dump()
                })

            except Exception as e:
                error_message = str(e)
                logger.warning(
                    f"Failed to analyze KPI group {group.id}: {error_message}",
                    exc_info=True
                )

                # Store error information
                error_results.append({
                    "group_id": group.id,
                    "group_name": group.name,
                    "error": error_message
                })
                continue

        return input_data_snapshot, successful_results, error_results
