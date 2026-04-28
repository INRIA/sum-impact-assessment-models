"""
Shared helpers for building MCDA goals and resolving goal weights.
"""
from typing import Dict, Optional

from ..schemas.mcda import Alternative, Goal
from ..utils.data_loaders import (
    get_goal_weights_for_perspective,
    normalize_goal_weights,
)
from ..utils.logger import get_logger


logger = get_logger(__name__)


def get_weight_by_goal(
    goal_name: str,
    goal_weights: Optional[Dict[str, float]],
    default_weight: float,
) -> float:
    """Retrieve weight for a specific goal by name."""
    if goal_weights and goal_name in goal_weights:
        return goal_weights[goal_name]

    if goal_weights:
        logger.warning(
            f"Goal '{goal_name}' not found in perspective weights. "
            f"Using default weight: {default_weight:.3f}"
        )
    return default_weight


def get_min_max_values_per_goal(
    goal_name: str,
    alternatives: list[Alternative],
) -> tuple[Optional[float], Optional[float]]:
    """Calculate minimum and maximum values for a specific goal."""
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


def build_goal_for_name(
    goal_name: str,
    alternatives: list[Alternative],
    goal_weights: Optional[Dict[str, float]],
    default_weight: float,
) -> Optional[Goal]:
    """Build a goal with PROMETHEE thresholds, or return None when invalid."""
    weight = get_weight_by_goal(goal_name, goal_weights, default_weight)
    min_value, max_value = get_min_max_values_per_goal(goal_name, alternatives)

    if weight is None:
        logger.warning(f"Skipping goal '{goal_name}' due to missing weight")
        return None

    if (min_value is None) or (max_value is None):
        logger.warning(
            f"Skipping goal '{goal_name}' due to missing min/max values "
            f"min='{min_value}', max='{max_value}'"
        )
        return None

    return Goal(
        name=goal_name,
        weight=weight,
        direction="max",
        Q=0,
        S=0,
        P=max_value - min_value,
        F="t3",
    )


def apply_normalized_goal_weights(
    goals: list[Goal],
    context_label: str,
) -> None:
    """Normalize existing goal weights in place when goals are present."""
    if not goals:
        return

    raw_weights = {goal.name: goal.weight for goal in goals}
    normalized_weights = normalize_goal_weights(raw_weights)
    if not normalized_weights:
        return

    pre_normalization_total = sum(raw_weights.values())
    if abs(pre_normalization_total - 1.0) > 0.05:
        logger.warning(
            "Goal weights total before normalization deviates from 1.0",
            extra={
                "pre_normalization_total": pre_normalization_total,
                "goal_count": len(goals),
            },
        )

    logger.debug(
        f"Normalized goal weights for {context_label}",
        extra={
            "pre_normalization_total": pre_normalization_total,
            "post_normalization_total": sum(normalized_weights.values()),
            "weights": normalized_weights,
        },
    )

    for goal in goals:
        goal.weight = normalized_weights[goal.name]


def get_goal_weights(
    perspective: Optional[str],
    use_qualitative_prefix: bool = False,
) -> Optional[Dict[str, float]]:
    """Get perspective goal weights or None when perspective is missing/invalid."""
    if perspective:
        try:
            goal_weights = get_goal_weights_for_perspective(perspective)
            if use_qualitative_prefix:
                logger.info(
                    f"Using qualitative goal weights for perspective: {perspective}"
                )
            else:
                logger.info(
                    f"Using goal weights for perspective: {perspective}")
            return goal_weights
        except ValueError as error:
            logger.warning(
                f"Failed to load perspective weights: {error}. Using equal weights."
            )
            return None

    logger.info("No perspective specified, using equal weights")
    return None


def resolve_goal_weights(
    perspective: Optional[str],
    personalized_goal_weights: Optional[Dict[str, float]],
    personalized_message: str,
    use_qualitative_prefix: bool = False,
) -> Optional[Dict[str, float]]:
    """Resolve personalized or perspective-based goal weights."""
    if perspective == "user_personalized" and personalized_goal_weights:
        normalized = normalize_goal_weights(personalized_goal_weights)
        logger.info(personalized_message)
        return normalized

    return get_goal_weights(
        perspective=perspective,
        use_qualitative_prefix=use_qualitative_prefix,
    )
