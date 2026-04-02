"""
MCDA Schemas

Pydantic models for Multi-Criteria Decision Analysis inputs and outputs.
"""
from .goal import Goal
from .alternative import Alternative
from .mcda_analysis_output import MCDAAnalysisOutput, GAIAAlternativeCoordinate, GAIACriterionVector
from .mcda_custom_params import McdaCustomAnalysisParams, CustomGoalInput, CustomAlternativeInput

__all__ = [
    'Goal',
    'Alternative',
    'MCDAAnalysisOutput',
    'GAIAAlternativeCoordinate',
    'GAIACriterionVector',
    'McdaCustomAnalysisParams',
    'CustomGoalInput',
    'CustomAlternativeInput',
]
