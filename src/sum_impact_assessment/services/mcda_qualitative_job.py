"""
MCDA Qualitative Analysis Job - Executes PROMETHEE-GAIA MCDA using configured business activities.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from ..repositories.job_repository import JobRepository
from .jobs.base import BaseJob
from ..models.mcda_analysis.promethee_gaia_analysis import PrometheeGaiaAnalyzer
from ..schemas.job import JobStatusEnum
from ..schemas.mcda import Goal, Alternative
from ..utils.logger import get_logger
from ..utils.data_loaders import load_mcda_config
from ..utils.time import utc_now
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


class McdaQualitativeJob(BaseJob):
    """
    Job that executes PROMETHEE-GAIA MCDA using configured business activities.

    This job:
    1. Loads perspective weights and business activity scores from MCDA config
    2. Builds Goals and Alternatives from static qualitative data
    3. Runs PROMETHEE-GAIA multi-criteria decision analysis
    4. Saves structured MCDA input and output snapshots
    """

    @staticmethod
    def _normalize_goal_scores(goal_scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize all goal score keys to lower-case."""
        return {
            goal_name: score
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
        return get_weight_by_goal(goal_name, goal_weights, default_weight)

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
            values = McdaQualitativeJob._normalize_goal_scores(
                activity_goal_scores)
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

        goal_names = list(alternatives[0].values.keys())
        if not goal_names:
            return []

        default_weight = 1.0 / len(goal_names)
        goals = []

        for goal_name in goal_names:
            goal = build_goal_for_name(
                goal_name=goal_name,
                alternatives=alternatives,
                goal_weights=goal_weights,
                default_weight=default_weight,
            )
            if goal is None:
                continue
            goals.append(goal)

        apply_normalized_goal_weights(goals, context_label="qualitative MCDA")

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
        return get_resolved_goal_weights(
            perspective,
            use_qualitative_prefix=True,
        )

    @classmethod
    def _execute(cls, job_id: str, db: Session, params: Optional[Dict], job_repo: JobRepository) -> None:
        """
        Domain logic for the qualitative MCDA analysis job.
        """
        perspective = params.get("perspective") if params else None
        analysis_name = params.get("name") if params else None
        personalized_goal_weights = params.get(
            "goals_weights") if params else None
        logger.debug(
            "Qualitative MCDA analysis parameters",
            extra={
                "perspective": perspective,
                "analysis_name": analysis_name,
                "personalized_goal_weights": bool(personalized_goal_weights)
            }
        )

        config = load_mcda_config()

        input_data_snapshot = {
            "perspectives": config.get("perspectives", {}),
            "business_activities": config.get("business_activities", {})
        }
        job_repo.update_job_data(
            job_id=job_id, input_data=input_data_snapshot)

        goal_weights = resolve_goal_weights(
            perspective=perspective,
            personalized_goal_weights=personalized_goal_weights,
            personalized_message="Using user-personalized qualitative goal weights",
            use_qualitative_prefix=True,
        )

        alternatives = McdaQualitativeJob.build_alternatives(config)
        goals = McdaQualitativeJob.build_goals(alternatives, goal_weights)

        if not alternatives:
            raise Exception(
                "No business activities were found. Cannot proceed with qualitative MCDA.")
        if not goals:
            raise Exception(
                "No goals were built from business activity scores. Cannot proceed with qualitative MCDA.")

        mcda_analyzer = PrometheeGaiaAnalyzer(
            goals=goals,
            alternatives=alternatives
        )

        mcda_input_data_snapshot = {
            "perspective": perspective,
            "name": analysis_name,
            "goals": [goal.model_dump() for goal in goals],
            "alternatives": [alt.model_dump() for alt in alternatives],
            "timestamp": utc_now().isoformat()
        }
        input_data_snapshot.update(mcda_input_data_snapshot)
        job_repo.update_job_data(
            job_id=job_id, input_data=input_data_snapshot)

        mcda_output = mcda_analyzer.run_analysis(run_visualizations=False)

        output_data_snapshot = {
            "name": analysis_name,
            "kpi_impact_results": [],
            "kpi_impact_errors": [],
            "mcda_results": mcda_output.model_dump(),
            "timestamp": utc_now().isoformat()
        }
        job_repo.update_job_data(
            job_id=job_id, output_data=output_data_snapshot)

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
            completed_at=utc_now()
        )
        logger.info(
            f"Qualitative MCDA analysis job completed successfully: {job_id}")
