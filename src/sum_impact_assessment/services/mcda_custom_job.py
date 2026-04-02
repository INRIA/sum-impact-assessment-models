"""
MCDA Custom Analysis Job - Executes PROMETHEE-GAIA MCDA using user-defined goals and alternatives.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict, Optional
from ..repositories.job_repository import JobRepository
from ..models.mcda_analysis.promethee_gaia_analysis import PrometheeGaiaAnalyzer
from ..schemas.job import JobStatusEnum
from ..schemas.mcda import Goal, Alternative, McdaCustomAnalysisParams
from ..utils.logger import get_logger
from ..utils.data_loaders import normalize_goal_weights

# Initialize logger
logger = get_logger(__name__)


class McdaCustomJob:
    """
    Job that executes PROMETHEE-GAIA MCDA using fully customized inputs.

    This job:
    1. Validates user-defined goals, weights, and alternatives
    2. Builds Goals and Alternatives from provided inputs
    3. Runs PROMETHEE-GAIA multi-criteria decision analysis
    4. Saves structured MCDA input and output snapshots
    """

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
        min_value = None
        max_value = None
        for alt in alternatives:
            alt_goal_value = alt.values.get(goal_name)
            if alt_goal_value is not None:
                if (min_value is None) or (alt_goal_value < min_value):
                    min_value = alt_goal_value
                if (max_value is None) or (alt_goal_value > max_value):
                    max_value = alt_goal_value
        return min_value, max_value

    @staticmethod
    def build_alternatives(params: McdaCustomAnalysisParams) -> list[Alternative]:
        """
        Build Alternative objects from user-defined inputs.

        Args:
            params: Validated custom analysis parameters

        Returns:
            List of Alternative objects
        """
        alternatives = [
            Alternative(name=alt.name, values=alt.values) for alt in params.alternatives
        ]
        logger.info(
            f"Created {len(alternatives)} custom alternatives from request")
        return alternatives

    @staticmethod
    def build_goals(params: McdaCustomAnalysisParams, alternatives: list[Alternative]) -> list[Goal]:
        """
        Build Goal objects from user-defined inputs, with weights normalized.

        Args:
            params: Validated custom analysis parameters
            alternatives: List of Alternative objects for min/max calculations

        Returns:
            List of Goal objects with weights and PROMETHEE thresholds configured
        """
        if not alternatives:
            return []

        raw_weights: Dict[str, float] = {goal.name: goal.weight for goal in params.goals}
        normalized_weights = normalize_goal_weights(raw_weights)
        if not normalized_weights:
            raise ValueError("Failed to normalize goal weights for custom analysis")

        goals = []
        for goal in params.goals:
            weight = normalized_weights.get(goal.name)
            min_value, max_value = McdaCustomJob._get_min_max_values_per_goal(
                goal.name, alternatives
            )

            if weight is None:
                raise ValueError(
                    f"Missing normalized weight for goal '{goal.name}'"
                )
            if (min_value is None) or (max_value is None):
                raise ValueError(
                    f"Missing min/max values for goal '{goal.name}'"
                )

            goals.append(
                Goal(
                    name=goal.name,
                    weight=weight,
                    direction=goal.direction,
                    Q=0,
                    S=0,
                    P=max_value - min_value,
                    F="t3"
                )
            )

        logger.info(f"Created {len(goals)} custom goals")
        return goals

    @staticmethod
    def run(job_id: str, db: Session, params: Optional[Dict] = None) -> None:
        """
        Execute the custom MCDA analysis job.

        Args:
            job_id: UUID of the job run to track
            db: Database session for updating job status
            params: Custom analysis parameters with goals and alternatives
        """
        job_repo = JobRepository(db)

        try:
            logger.info(f"Starting custom MCDA analysis job: {job_id}")
            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.STARTED,
                started_at=datetime.utcnow()
            )

            if not params:
                raise ValueError("Custom MCDA analysis requires parameters")

            custom_params = McdaCustomAnalysisParams.model_validate(params)
            analysis_name = custom_params.name

            alternatives = McdaCustomJob.build_alternatives(custom_params)
            goals = McdaCustomJob.build_goals(custom_params, alternatives)

            if not alternatives:
                raise ValueError(
                    "No alternatives were provided. Cannot proceed with custom MCDA."
                )
            if not goals:
                raise ValueError(
                    "No goals were provided. Cannot proceed with custom MCDA."
                )

            mcda_analyzer = PrometheeGaiaAnalyzer(
                goals=goals,
                alternatives=alternatives
            )

            input_data_snapshot = {
                "name": analysis_name,
                "goals": [goal.model_dump() for goal in goals],
                "alternatives": [alt.model_dump() for alt in alternatives],
                "timestamp": datetime.utcnow().isoformat()
            }
            job_repo.update_job_data(
                job_id=job_id, input_data=input_data_snapshot)

            mcda_output = mcda_analyzer.run_analysis(run_visualizations=False)

            output_data_snapshot = {
                "name": analysis_name,
                "kpi_impact_results": [],
                "kpi_impact_errors": [],
                "mcda_results": mcda_output.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            }
            job_repo.update_job_data(
                job_id=job_id, output_data=output_data_snapshot)

            top_alt_key = mcda_output.ranking[0] if mcda_output.ranking else "N/A"
            top_alt_name = mcda_output.alternative_labels.get(
                top_alt_key, "N/A") if mcda_output.ranking else "N/A"

            name_info = f" [Name: {analysis_name}]" if analysis_name else ""
            success_message = (
                f"Custom MCDA analysis completed successfully{name_info}. "
                f"Analyzed {len(goals)} goals, {len(alternatives)} alternatives. "
                f"Top ranked: {top_alt_key} ({top_alt_name}). "
                f"GAIA quality: {mcda_output.gaia_quality:.1f}%"
            )

            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.SUCCESS,
                message=success_message,
                completed_at=datetime.utcnow()
            )
            logger.info(
                f"Custom MCDA analysis job completed successfully: {job_id}")

        except Exception as e:
            error_message = f"McdaCustomJob failed: {str(e)}"
            logger.error(
                error_message,
                extra={"job_id": job_id},
                exc_info=True
            )

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
