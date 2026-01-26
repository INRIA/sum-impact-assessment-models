"""
MCDA Goal Schema

Represents a decision criterion/goal in multi-criteria decision analysis.
"""
from pydantic import BaseModel, Field
from typing import Literal


class Goal(BaseModel):
    """
    Represents a single criterion/goal in MCDA analysis.

    Attributes:
        name: Unique identifier for the goal
        weight: Importance weight (must sum to 1 across all goals)
        direction: 'max' for benefit criteria, 'min' for cost criteria
        Q: Indifference threshold (only when necessary), default to min value to disabled the effect (only used for preference functions t5, t6 and t7)
        S: Preference threshold (only used for preference functions t6 and t7), default to 0.0
        P: Veto threshold (max - min value)
        F: Preference function type (t1–t7), for SUM we use t3 or t5 (when Q is defined) for continuous data
    """
    name: str = Field(..., description="Unique goal identifier")
    weight: float = Field(..., gt=0, le=1,
                          description="Goal weight (0 < w ≤ 1)")
    direction: Literal['max',
                       'min'] = Field(..., description="Optimization direction")

    # PROMETHEE parameters: Default to commonly used values
    Q: float = Field(0.0, description="Indifference threshold")
    S: float = Field(0.0, description="Preference threshold")
    P: float = Field(0.0, description="Veto threshold")
    F: str = Field('t3', description="Preference function type (t1–t7): 't1' = Usual; 't2' = U-Shape; 't3' = V-Shape; 't4' = Level; 't5' = V-Shape with Indifference; 't6' = Gaussian; 't7' = C-Form")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Environmental Impact",
                "weight": 0.3,
                "direction": "max"
            }
        }
