"""
MCDA Custom Analysis Request Schemas

Defines input schemas for fully customized MCDA analysis:
- User-defined goals with weights and directions
- User-defined alternatives with scores per goal
"""
from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Literal, Optional, Set


class CustomGoalInput(BaseModel):
    """
    Represents a user-defined goal in a custom MCDA analysis.
    """
    name: str = Field(..., description="Goal name")
    weight: float = Field(..., gt=0, description="Goal weight (must be > 0)")
    direction: Literal["max", "min"] = Field(
        "max", description="Optimization direction for the goal"
    )


class CustomAlternativeInput(BaseModel):
    """
    Represents a user-defined alternative with scores per goal.
    """
    name: str = Field(..., description="Alternative name")
    values: Dict[str, float] = Field(
        ..., description="Scores per goal (goal name -> score)"
    )


class McdaCustomAnalysisParams(BaseModel):
    """
    Request schema for a fully customized MCDA analysis.
    """
    name: Optional[str] = Field(None, description="Optional analysis name")
    goals: List[CustomGoalInput] = Field(
        ..., description="List of goals with weights and directions"
    )
    alternatives: List[CustomAlternativeInput] = Field(
        ..., description="List of alternatives with scores per goal"
    )

    @model_validator(mode="after")
    def validate_structure(self):
        goals = self.goals or []
        alternatives = self.alternatives or []

        if len(goals) < 2:
            raise ValueError("At least two goals are required for MCDA analysis")
        if len(alternatives) < 2:
            raise ValueError("At least two alternatives are required for MCDA analysis")

        goal_names = [goal.name for goal in goals]
        unique_goal_names: Set[str] = set(goal_names)
        if len(unique_goal_names) != len(goal_names):
            raise ValueError("Goal names must be unique")

        alt_names = [alt.name for alt in alternatives]
        if len(set(alt_names)) != len(alt_names):
            raise ValueError("Alternative names must be unique")

        for alt in alternatives:
            if not alt.values:
                raise ValueError(
                    f"Alternative '{alt.name}' must define scores for all goals"
                )
            missing = unique_goal_names.difference(alt.values.keys())
            extra = set(alt.values.keys()).difference(unique_goal_names)
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(
                    f"Alternative '{alt.name}' is missing scores for goals: {missing_list}"
                )
            if extra:
                extra_list = ", ".join(sorted(extra))
                raise ValueError(
                    f"Alternative '{alt.name}' has scores for unknown goals: {extra_list}"
                )

        return self

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Custom MCDA Run",
                "goals": [
                    {"name": "Environmental Impact", "weight": 0.35, "direction": "max"},
                    {"name": "Economic Cost", "weight": 0.25, "direction": "min"},
                    {"name": "Social Acceptance", "weight": 0.40, "direction": "max"}
                ],
                "alternatives": [
                    {
                        "name": "Project A",
                        "values": {
                            "Environmental Impact": 0.82,
                            "Economic Cost": 1200.0,
                            "Social Acceptance": 0.67
                        }
                    },
                    {
                        "name": "Project B",
                        "values": {
                            "Environmental Impact": 0.75,
                            "Economic Cost": 980.0,
                            "Social Acceptance": 0.74
                        }
                    }
                ]
            }
        }
