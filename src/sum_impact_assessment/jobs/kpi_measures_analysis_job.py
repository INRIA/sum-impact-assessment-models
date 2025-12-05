"""
KPI Measures Analysis Job - Executes impact analysis using KPIImpactAnalyzer.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from ..repositories.job_repository import JobRepository
from ..repositories.analysis_data_repository import AnalysisDataRepository
from ..services.analysis_data_transformer import AnalysisDataTransformer
from ..models.impact_analysis.kpi_impact_analysis import KPIImpactAnalyzer
from ..schemas.job import JobStatusEnum
from ..utils.logger import get_logger
from pandas import DataFrame, concat

# Initialize logger
logger = get_logger(__name__)


class KpiMeasuresAnalysisJob:
    """
    Job that executes KPI measures impact analysis.

    This job:
    1. Fetches data from the database (KPIs, measures, groups, living labs)
    2. Transforms raw data into Pydantic schemas
    3. Instantiates KPIImpactAnalyzer
    4. Runs the analysis
    5. Logs results and updates job status
    """
    @staticmethod
    def _get_data_and_transform(db: Session):
        """
        Fetch and transform all required data for the analysis.

        Args:
            db: Database session for data fetching
        Returns:
            Tuple containing lists of KPIs, Measures, KPIGroups, and LivingLabs
        """
        # Step 1: Fetch data from database
        logger.info("Fetching data from database")
        analysis_repo = AnalysisDataRepository(db)

        raw_kpi_definitions = analysis_repo.get_kpi_definitions()
        raw_measures = analysis_repo.get_measures()
        raw_kpi_groups = analysis_repo.get_kpi_groups("MCDA_GOALS")
        raw_lab_measures = analysis_repo.get_living_lab_measures()
        raw_lab_kpi_results = analysis_repo.get_living_lab_kpi_results()
        raw_living_labs = analysis_repo.get_living_labs()

        logger.info(
            "Data fetched successfully",
            extra={
                "kpi_definitions": len(raw_kpi_definitions),
                "measures": len(raw_measures),
                "kpi_groups": len(raw_kpi_groups),
                "living_labs": len(raw_living_labs),
                "lab_measures": len(raw_lab_measures),
                "kpi_results": len(raw_lab_kpi_results),
            }
        )

        # Step 2: Transform data to Pydantic schemas
        logger.info("Transforming data to Pydantic schemas")
        transformer = AnalysisDataTransformer()

        kpis = transformer.transform_kpis(raw_kpi_definitions)
        measures = transformer.transform_measures(raw_measures)
        kpi_groups = transformer.transform_kpi_groups(raw_kpi_groups)
        living_labs = transformer.transform_living_labs(raw_living_labs,
                                                        raw_lab_measures,
                                                        raw_lab_kpi_results,
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

    @staticmethod
    def run(job_id: str, db: Session) -> None:
        """
        Execute the KPI measures analysis job.

        Args:
            job_id: UUID of the job run to track
            db: Database session for updating job status and fetching data
        """
        job_repo = JobRepository(db)

        try:
            # Update status to STARTED
            logger.info(f"Starting KPI measures analysis job: {job_id}")
            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.STARTED,
                started_at=datetime.utcnow()
            )

            # Step 1 & 2: Fetch and transform data
            kpis, measures, kpi_groups, living_labs = KpiMeasuresAnalysisJob._get_data_and_transform(
                db)

            # Step 3: Instantiate KPIImpactAnalyzer
            analyzer = KPIImpactAnalyzer(
                living_labs=living_labs,
                measures=measures,
                kpis=kpis,
                kpi_groups=kpi_groups
            )

            # Step 4: Run the analysis
            logger.info("Running impact analysis")
            # results = analyzer.run_analysis()
            results = DataFrame()
            analyzed_groups_names = ''
            for group in kpi_groups:
                try:
                    logger.debug(
                        f"Analyzing KPI group: {group.name} (ID: {group.id})")
                    group_results = analyzer.run_analysis_group(group)
                    df = DataFrame([coef.model_dump()
                                   for coef in group_results.measure_coefficients])

                    # add df to final_df
                    results = concat([results, df], ignore_index=True)
                    analyzed_groups_names += f"{group.name}, "
                except Exception as e:
                    logger.warning(
                        f"Failed to analyze KPI group {group.id}: {e}")
                    continue

            # # Step 5: Log results
            logger.info(
                "Analysis completed successfully",
                extra={
                    "groups_analyzed": results.size
                }
            )

            # Update status to SUCCESS
            groups_names = ', '.join([group.name for group in kpi_groups])
            success_message = f"Analysis completed successfully for {results.size}/{len(kpi_groups)} KPI groups {groups_names}. Groupes analyzed : ({analyzed_groups_names})"
            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.SUCCESS,
                message=success_message,
                completed_at=datetime.utcnow()
            )
            logger.info(
                f"KPI measures analysis job completed successfully: {job_id}")

        except Exception as e:
            # Update status to FAILURE
            error_message = f"KpiMeasuresAnalysisJob failed: {str(e)}"
            logger.error(
                error_message,
                extra={"job_id": job_id},
                exc_info=True
            )

            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.FAILURE,
                message=error_message,
                completed_at=datetime.utcnow()
            )
