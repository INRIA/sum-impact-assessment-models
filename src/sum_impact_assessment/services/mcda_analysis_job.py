"""
MCDA Analysis Job - Executes KPI impact analysis followed by PROMETHEE-GAIA MCDA.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict
from ..repositories.job_repository import JobRepository
from .kpi_measures_analysis_job import KpiMeasuresAnalysisJob
from ..models.mcda_analysis.promethee_gaia_analysis import PrometheeGaiaAnalyzer
from ..schemas.job import JobStatusEnum
from ..schemas.mcda import Goal, Alternative
from ..schemas.core import Measure
from ..utils.logger import get_logger
from ..utils.data_loaders import get_goal_weights_for_perspective

# Initialize logger
logger = get_logger(__name__)


class MCDAAnalysisJob:
    """
    Job that executes KPI impact analysis followed by PROMETHEE-GAIA MCDA.

    This job:
    1. Fetches data from the database (KPIs, measures, groups, living labs)
    2. Runs KPI impact analysis to get measure coefficients
    3. Builds Goals and Alternatives from analysis results
    4. Runs PROMETHEE-GAIA multi-criteria decision analysis
    5. Saves structured MCDA output with standardized keys
    """

    @staticmethod
    def run(job_id: str, db: Session, params: Optional[Dict] = None) -> None:
        """
        Execute the MCDA analysis job.

        Args:
            job_id: UUID of the job run to track
            db: Database session for updating job status and fetching data
            params: Optional job parameters. Supported keys:
                    - kpi_group_type: Filter to specific KPI group (e.g., "MCDA_GOALS")
                    - perspective: Stakeholder perspective for goal weighting (e.g., "regulatory", "pto")
        """
        job_repo = JobRepository(db)

        try:
            # Update status to STARTED
            logger.info(f"Starting MCDA analysis job: {job_id}")
            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.STARTED,
                started_at=datetime.utcnow()
            )

            # Extract optional parameters
            kpi_group_filter = params.get("kpi_group_type") if params else None
            perspective = params.get("perspective") if params else None
            logger.debug(
                f"MCDA analysis parameters",
                extra={
                    "kpi_group_filter": kpi_group_filter,
                    "perspective": perspective
                }
            )

            # PHASE 1 & 2: Run KPI impact analysis using shared function
            logger.info("Phase 1-2: Running KPI impact analysis")

            input_data_snapshot, kpi_impact_results, error_results = KpiMeasuresAnalysisJob.run_kpi_impact_analysis(
                db=db,
                kpi_group_filter=kpi_group_filter
            )

            # Save input data snapshot
            job_repo.update_job_data(
                job_id=job_id, input_data=input_data_snapshot)
            logger.debug("Input data snapshot saved")

            # Check if we have enough successful results to proceed
            if not kpi_impact_results:
                raise Exception(
                    "No KPI groups were successfully analyzed. Cannot proceed with MCDA.")

            logger.debug(
                f"KPI impact analysis completed for {len(kpi_impact_results)} groups")

            # PHASE 3: Build Goals and Alternatives from impact results
            logger.debug("Phase 3: Building Goals and Alternatives for MCDA")

            # Get measures from input data
            measures = [Measure(**m) for m in input_data_snapshot['measures']]

            # Build Goals from KPI groups with perspective-based weights
            # Load weights from perspective if provided, otherwise use equal weights
            if perspective:
                try:
                    goal_weights = get_goal_weights_for_perspective(
                        perspective)
                    logger.info(
                        f"Using goal weights for perspective: {perspective}")
                except ValueError as e:
                    logger.warning(
                        f"Failed to load perspective weights: {e}. Using equal weights.")
                    goal_weights = None
            else:
                goal_weights = None
                logger.info("No perspective specified, using equal weights")

            # Default to equal weights if no perspective provided
            default_weight = 1.0 / len(kpi_impact_results)

            goals = []
            for result in kpi_impact_results:
                group_name = result['group_name']

                # Get weight from perspective or use default
                if goal_weights and group_name in goal_weights:
                    weight = goal_weights[group_name]
                else:
                    weight = default_weight
                    if goal_weights:
                        logger.warning(
                            f"Goal '{group_name}' not found in perspective weights. "
                            f"Using default weight: {weight:.3f}"
                        )

                goal = Goal(
                    name=group_name,
                    weight=weight,
                    direction="max",  # Higher coefficient = better impact
                    Q=0.0005,
                    S=0.003,
                    P=0.01,
                    F='t5'  # V-shape with indifference
                )
                goals.append(goal)

            logger.info(f"Created {len(goals)} goals from KPI groups")

            # Build Alternatives from measures
            # Each alternative's values are the coefficients for each goal
            alternatives = []
            for measure in measures:
                values = {}
                for result in kpi_impact_results:
                    goal_name = result['group_name']
                    # Find coefficient for this measure in this group
                    measure_coefs = result['results']['measure_coefficients']
                    coefficient = next(
                        (mcoef['coefficient']
                         for mcoef in measure_coefs if mcoef['id'] == measure.id),
                        0.0
                    )
                    values[goal_name] = coefficient

                alt = Alternative(
                    name=measure.name or f"Measure {measure.id}",
                    values=values
                )
                alternatives.append(alt)

            logger.info(
                f"Created {len(alternatives)} alternatives from measures")

            # PHASE 4: Run PROMETHEE-GAIA analysis
            logger.debug("Phase 4: Running PROMETHEE-GAIA analysis")
            mcda_analyzer = PrometheeGaiaAnalyzer(
                goals=goals,
                alternatives=alternatives
            )

            # save MCDA input data snapshot, added to previous input_data_snapshot
            mcda_input_data_snapshot = {
                "perspective": perspective,
                "goal_weights": {goal.name: goal.weight for goal in goals},
                "goals": [goal.model_dump() for goal in goals],
                "alternatives": [alt.model_dump() for alt in alternatives],
                "timestamp": datetime.utcnow().isoformat()
            }
            # update input data snapshot with MCDA input data
            input_data_snapshot.update(mcda_input_data_snapshot)
            job_repo.update_job_data(
                job_id=job_id, input_data=input_data_snapshot)
            logger.debug("MCDA input data snapshot saved")

            # Get structured MCDA output with standardized keys
            mcda_output = mcda_analyzer.run_analysis(run_visualizations=False)

            logger.info(
                f"MCDA analysis completed",
                extra={
                    "gaia_quality": mcda_output.gaia_quality,
                    "top_alternative": mcda_output.ranking[0] if mcda_output.ranking else None
                }
            )

            # PHASE 5: Save output data
            logger.debug("Phase 5: Saving MCDA output")
            output_data_snapshot = {
                "kpi_impact_results": kpi_impact_results,
                "kpi_impact_errors": error_results,
                "mcda_results": mcda_output.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            }

            job_repo.update_job_data(
                job_id=job_id, output_data=output_data_snapshot)
            logger.debug("Output data snapshot saved")

            # Update status to SUCCESS
            top_alt_key = mcda_output.ranking[0] if mcda_output.ranking else "N/A"
            top_alt_name = mcda_output.alternative_labels.get(
                top_alt_key, "N/A") if mcda_output.ranking else "N/A"

            success_count = len(kpi_impact_results)
            total_count = len(kpi_impact_results) + len(error_results)
            failed_groups = ', '.join(
                [r['group_name'] for r in error_results]) if error_results else None

            perspective_info = f" [Perspective: {perspective}]" if perspective else ""
            success_message = (
                f"MCDA analysis completed successfully{perspective_info}. "
                f"Analyzed {success_count}/{total_count} KPI groups, "
                f"{len(alternatives)} alternatives. "
                f"Top ranked: {top_alt_key} ({top_alt_name}). "
                f"GAIA quality: {mcda_output.gaia_quality:.1f}%"
            )
            if failed_groups:
                success_message += f" | Failed groups: ({failed_groups})"

            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.SUCCESS,
                message=success_message,
                completed_at=datetime.utcnow()
            )
            logger.info(f"MCDA analysis job completed successfully: {job_id}")

        except Exception as e:
            # Update status to FAILURE
            error_message = f"MCDAAnalysisJob failed: {str(e)}"
            logger.error(
                error_message,
                extra={"job_id": job_id},
                exc_info=True
            )

            # Save error output data
            job_repo.update_job_data(
                job_id=job_id,
                output_data={
                    "error": error_message,
                    "fatal": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.FAILURE,
                message=error_message,
                completed_at=datetime.utcnow()
            )
