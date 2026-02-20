"""
MCDA Qualitative Analysis Job - Executes PROMETHEE-GAIA MCDA using configured business activities.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from ..repositories.job_repository import JobRepository
from ..models.mcda_analysis.promethee_gaia_analysis import PrometheeGaiaAnalyzer
from ..schemas.job import JobStatusEnum
from ..schemas.mcda import Goal, Alternative
from ..utils.logger import get_logger
from ..utils.data_loaders import get_goal_weights_for_perspective, load_mcda_config

# Initialize logger
logger = get_logger(__name__)


class McdaQualitativeJob:
    """
    Job that executes PROMETHEE-GAIA MCDA using configured business activities.

    This job:
    1. Loads perspective weights and business activity scores from MCDA config
    2. Builds Goals and Alternatives from static qualitative data
    3. Runs PROMETHEE-GAIA multi-criteria decision analysis
    4. Saves structured MCDA input and output snapshots
    """

    @staticmethod
    def _normalize_goal_weights(goal_weights: Dict[str, float]) -> Dict[str, float]:
        """Normalize all goal weight keys to lower-case."""
        return {
            goal_name : weight
            for goal_name, weight in goal_weights.items()
        }

    @staticmethod
    def _normalize_goal_scores(goal_scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize all goal score keys to lower-case."""
        return {
            goal_name : score
            for goal_name, score in goal_scores.items()
        }

    @staticmethod
    def _get_weight_by_goal(goal_name: str, goal_weights: Optional[Dict[str, float]], default_weight: float) -> float:
        """
        Retrieve weight for a specific goal by name.

        Args:
            goal_name: Name of the goal
            goal_weights: Dictionary mapping normalized goal names to weights
            default_weight: Fallback weight if goal not found in weights

        Returns:
            Weight value for the goal
        """
        if goal_weights and goal_name in goal_weights:
            return goal_weights[goal_name]
        else:
            if goal_weights:
                logger.warning(
                    f"Goal '{goal_name}' not found in perspective weights. "
                    f"Using default weight: {default_weight:.3f}"
                )
            return default_weight

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
    def build_alternatives(config: Dict[str, Any]) -> list[Alternative]:
        """
        Build Alternative objects from configured business activities.

        Alternatives are business activities, and values are qualitative goal scores.
        Goal keys are normalized to lower-case for matching simplicity.

        Args:
            config: Full MCDA config dictionary

        Returns:
            List of Alternative objects
        """
        business_activities = config.get("business_activities", {})
        activity_labels = business_activities.get("labels", {})
        goals_score = business_activities.get("goals_score", {})

        alternatives = []
        for activity_key, activity_goal_scores in goals_score.items():
            values = McdaQualitativeJob._normalize_goal_scores(activity_goal_scores)
            alternative = Alternative(
                name=activity_labels.get(activity_key, activity_key),
                values=values
            )
            alternatives.append(alternative)

        logger.info(
            f"Created {len(alternatives)} qualitative alternatives from business activities")
        return alternatives

    @staticmethod
    def build_goals(alternatives: list[Alternative], goal_weights: Optional[Dict[str, float]] = None) -> list[Goal]:
        """
        Build Goal objects from alternatives and optional perspective weights.

        Goal names are normalized to lower-case and thresholds are built for PROMETHEE.

        Args:
            alternatives: List of Alternative objects
            goal_weights: Optional dictionary mapping goal names to weights

        Returns:
            List of Goal objects with weights and PROMETHEE thresholds configured
        """
        if not alternatives:
            return []

        normalized_goal_weights = (
            McdaQualitativeJob._normalize_goal_weights(goal_weights)
            if goal_weights else None
        )

        goal_names = list(alternatives[0].values.keys())
        if not goal_names:
            return []

        default_weight = 1.0 / len(goal_names)
        goals = []

        for goal_name in goal_names:
            weight = McdaQualitativeJob._get_weight_by_goal(
                goal_name, normalized_goal_weights, default_weight)

            min_value, max_value = McdaQualitativeJob._get_min_max_values_per_goal(
                goal_name, alternatives)

            if weight is None:
                logger.warning(
                    f"Skipping goal '{goal_name}' due to missing weight")
                continue
            if (min_value is None) or (max_value is None):
                logger.warning(
                    f"Skipping goal '{goal_name}' due to missing min/max values min='{min_value}', max='{max_value}'")
                continue

            goals.append(
                Goal(
                    name=goal_name,
                    weight=weight,
                    direction="max",
                    Q=0,
                    S=0,
                    P=max_value - min_value,
                    F='t3'
                )
            )

        logger.info(f"Created {len(goals)} qualitative goals")
        return goals

    @staticmethod
    def get_goal_weights(perspective: Optional[str]) -> Optional[Dict[str, float]]:
        """
        Get goal weights for a specific perspective.

        Args:
            perspective: Stakeholder perspective name (e.g., "regulatory", "pto"), or None

        Returns:
            Dictionary mapping normalized goal names to weights,
            or None if no perspective or loading fails.
        """
        if perspective:
            try:
                goal_weights = get_goal_weights_for_perspective(perspective)
                logger.info(
                    f"Using qualitative goal weights for perspective: {perspective}")
                return McdaQualitativeJob._normalize_goal_weights(goal_weights)
            except ValueError as e:
                logger.warning(
                    f"Failed to load perspective weights: {e}. Using equal weights.")
                return None
        else:
            logger.info("No perspective specified, using equal weights")
            return None

    @staticmethod
    def run(job_id: str, db: Session, params: Optional[Dict] = None) -> None:
        """
        Execute the qualitative MCDA analysis job.

        Args:
            job_id: UUID of the job run to track
            db: Database session for updating job status
            params: Optional job parameters. Supported keys:
                    - perspective: Stakeholder perspective for goal weighting
        """
        job_repo = JobRepository(db)

        try:
            logger.info(f"Starting qualitative MCDA analysis job: {job_id}")
            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.STARTED,
                started_at=datetime.utcnow()
            )

            perspective = params.get("perspective") if params else None
            logger.debug(
                "Qualitative MCDA analysis parameters",
                extra={"perspective": perspective}
            )

            config = load_mcda_config()

            input_data_snapshot = {
                "perspectives": config.get("perspectives", {}),
                "business_activities": config.get("business_activities", {})
            }
            job_repo.update_job_data(job_id=job_id, input_data=input_data_snapshot)

            goal_weights = McdaQualitativeJob.get_goal_weights(perspective)
            alternatives = McdaQualitativeJob.build_alternatives(config)
            goals = McdaQualitativeJob.build_goals(alternatives, goal_weights)

            if not alternatives:
                raise Exception("No business activities were found. Cannot proceed with qualitative MCDA.")
            if not goals:
                raise Exception("No goals were built from business activity scores. Cannot proceed with qualitative MCDA.")

            mcda_analyzer = PrometheeGaiaAnalyzer(
                goals=goals,
                alternatives=alternatives
            )

            mcda_input_data_snapshot = {
                "perspective": perspective,
                "goals": [goal.model_dump() for goal in goals],
                "alternatives": [alt.model_dump() for alt in alternatives],
                "timestamp": datetime.utcnow().isoformat()
            }
            input_data_snapshot.update(mcda_input_data_snapshot)
            job_repo.update_job_data(job_id=job_id, input_data=input_data_snapshot)

            mcda_output = mcda_analyzer.run_analysis(run_visualizations=False)

            output_data_snapshot = {
                "kpi_impact_results": [],
                "kpi_impact_errors": [],
                "mcda_results": mcda_output.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            }
            job_repo.update_job_data(job_id=job_id, output_data=output_data_snapshot)

            top_alt_key = mcda_output.ranking[0] if mcda_output.ranking else "N/A"
            top_alt_name = mcda_output.alternative_labels.get(
                top_alt_key, "N/A") if mcda_output.ranking else "N/A"

            perspective_info = f" [Perspective: {perspective}]" if perspective else ""
            success_message = (
                f"Qualitative MCDA analysis completed successfully{perspective_info}. "
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
            logger.info(f"Qualitative MCDA analysis job completed successfully: {job_id}")

        except Exception as e:
            error_message = f"McdaQualitativeJob failed: {str(e)}"
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
