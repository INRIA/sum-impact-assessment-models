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
from .mcda_goal_builder import (
    apply_normalized_goal_weights,
    build_goal_for_name,
    get_goal_weights as get_resolved_goal_weights,
    get_min_max_values_per_goal,
    get_weight_by_goal,
    resolve_goal_weights,
)

# Initialize logger
logger = get_logger(__name__)


class McdaQuantitativeJob:
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
    def _get_weight_by_goal(goal_name: str, goal_weights: Optional[Dict[str, float]], default_weight: float) -> float:
        """
        Retrieve weight for a specific goal by name.

        Args:
            goal_name: Name of the goal (kpi group)
            goal_weights: Dictionary mapping goal names to weights (perspective-based)
            default_weight: Fallback weight if goal not found in weights

        Returns:
            Weight value for the goal
        """
        return get_weight_by_goal(goal_name, goal_weights, default_weight)

    @staticmethod
    def _build_goal_values_by_measure(measure: Measure, kpi_impact_results: list) -> Dict[str, float]:
        """
        Build coefficient values for a measure (alternative) across all goals.

        Args:
            measure: The measure to get coefficients for
            kpi_impact_results: List of KPI impact analysis results by group

        Returns:
            Dictionary mapping goal names to coefficient values
        """
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
        return values

    @staticmethod
    def _get_min_max_values_per_goal(goal_name: str, alternatives: list[Alternative]) -> tuple[Optional[float], Optional[float]]:
        """
        Calculate minimum and maximum values for a specific goal across all alternatives.

        Args:
            goal_name: Name of the goal to get min/max values for
            alternatives: List of Alternative objects with values for each goal

        Returns:
            Tuple of (min_value, max_value) for the goal, or (None, None) if no values found
        """
        return get_min_max_values_per_goal(goal_name, alternatives)

    @staticmethod
    def build_alternatives(measures: list[Measure], kpi_impact_results: list) -> list[Alternative]:
        """
        Build Alternative objects from measures and KPI impact results.

        Each alternative represents a measure with coefficient values for each goal.

        Args:
            measures: List of Measure objects
            kpi_impact_results: List of KPI impact analysis results by group

        Returns:
            List of Alternative objects with goal values populated
        """
        alternatives = []
        for measure in measures:
            # Get all coefficients for this measure across all goals
            values = McdaQuantitativeJob._build_goal_values_by_measure(
                measure, kpi_impact_results)

            alt = Alternative(
                name=measure.name or f"Measure {measure.id}",
                values=values
            )
            alternatives.append(alt)

        logger.info(f"Created {len(alternatives)} alternatives from measures")
        return alternatives

    @staticmethod
    def build_goals(kpi_impact_results: list, alternatives: list[Alternative], goal_weights: Optional[Dict[str, float]] = None) -> list[Goal]:
        """
        Build Goal objects from KPI impact results with appropriate weights and thresholds.

        Args:
            kpi_impact_results: List of KPI impact analysis results by group
            alternatives: List of Alternative objects (needed to calculate min/max thresholds)
            goal_weights: Optional dictionary mapping goal names to weights (perspective-based)

        Returns:
            List of Goal objects with weights and PROMETHEE thresholds configured
        """
        # Default to equal weights if no perspective provided
        default_weight = 1.0 / len(kpi_impact_results)
        goals = []

        for result in kpi_impact_results:
            group_name = result['group_name']

            goal = build_goal_for_name(
                goal_name=group_name,
                alternatives=alternatives,
                goal_weights=goal_weights,
                default_weight=default_weight,
            )
            if goal is None:
                continue
            goals.append(goal)

        apply_normalized_goal_weights(goals, context_label="quantitative MCDA")

        logger.info(f"Created {len(goals)} goals from KPI groups")
        return goals

    @staticmethod
    def get_goal_weights(perspective: Optional[str]) -> Optional[Dict[str, float]]:
        """
        Get goal weights for a specific perspective.

        Args:
            perspective: Stakeholder perspective name (e.g., "regulatory", "pto"), or None

        Returns:
            Dictionary mapping goal names to weights, or None if no perspective or loading fails
        """
        return get_resolved_goal_weights(perspective)

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
            analysis_name = params.get("name") if params else None
            personalized_goal_weights = params.get(
                "goals_weights") if params else None
            logger.debug(
                f"MCDA analysis parameters",
                extra={
                    "kpi_group_filter": kpi_group_filter,
                    "perspective": perspective,
                    "analysis_name": analysis_name,
                    "personalized_goal_weights": bool(personalized_goal_weights)
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
            goal_weights = resolve_goal_weights(
                perspective=perspective,
                personalized_goal_weights=personalized_goal_weights,
                personalized_message="Using user-personalized quantitative goal weights",
            )

            # Build Alternatives from measures
            alternatives = McdaQuantitativeJob.build_alternatives(
                measures, kpi_impact_results)

            # Build Goals from KPI groups with perspective-based weights
            goals = McdaQuantitativeJob.build_goals(
                kpi_impact_results, alternatives, goal_weights)
            # PHASE 4: Run PROMETHEE-GAIA analysis
            logger.debug("Phase 4: Running PROMETHEE-GAIA analysis")
            mcda_analyzer = PrometheeGaiaAnalyzer(
                goals=goals,
                alternatives=alternatives
            )

            # save MCDA input data snapshot, added to previous input_data_snapshot
            mcda_input_data_snapshot = {
                "perspective": perspective,
                "name": analysis_name,
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
                "name": analysis_name,
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
            error_message = f"McdaQuantitativeJob failed: {str(e)}"
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
