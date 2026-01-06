"""
PROMETHEE-GAIA Analysis Result Schema

Contains complete results from PROMETHEE ranking and GAIA visualization.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# TODO use this instead of MCDAAnalysisOutput?


class PrometheeGaiaResult(BaseModel):
    """
    Complete result from PROMETHEE-GAIA analysis.

    Contains both PROMETHEE flows (for ranking) and GAIA projection data
    (for 2D visualization and decision stick computation).
    """

    # PROMETHEE Results
    positive_flows: Dict[str, float] = Field(
        ...,
        description="Positive (leaving) flows per alternative"
    )
    negative_flows: Dict[str, float] = Field(
        ...,
        description="Negative (entering) flows per alternative"
    )
    net_flows: Dict[str, float] = Field(
        ...,
        description="Net flows (positive - negative) per alternative"
    )
    ranking: List[str] = Field(
        ...,
        description="Alternatives ranked by net flow (descending)"
    )

    # GAIA Results
    gaia_method: str = Field(
        ...,
        description="Decomposition method used: 'svd' or 'pca'"
    )
    quality_percentage: float = Field(
        ...,
        description="% of information retained in 2D projection"
    )
    alternative_coordinates: Dict[str, List[float]] = Field(
        ...,
        description="2D coordinates for each alternative [x, y]"
    )
    goal_coordinates: Dict[str, List[float]] = Field(
        ...,
        description="2D coordinates for each goal axis [x, y]"
    )
    decision_stick: List[float] = Field(
        ...,
        description="Decision stick coordinates [x, y] weighted by goal importance"
    )

    # Metadata
    num_alternatives: int = Field(...,
                                  description="Number of alternatives analyzed")
    num_goals: int = Field(..., description="Number of goals/criteria")

    class Config:
        json_schema_extra = {
            "example": {
                "positive_flows": {"A1": 0.45, "A2": 0.38, "A3": 0.52},
                "negative_flows": {"A1": 0.32, "A2": 0.41, "A3": 0.29},
                "net_flows": {"A1": 0.13, "A2": -0.03, "A3": 0.23},
                "ranking": ["A3", "A1", "A2"],
                "gaia_method": "svd",
                "quality_percentage": 87.5,
                "alternative_coordinates": {
                    "A1": [0.2, 0.3],
                    "A2": [-0.1, -0.2],
                    "A3": [0.4, 0.1]
                },
                "goal_coordinates": {
                    "G1": [0.8, 0.2],
                    "G2": [-0.3, 0.7],
                    "G3": [0.1, -0.6]
                },
                "decision_stick": [0.35, 0.15],
                "num_alternatives": 3,
                "num_goals": 3
            }
        }
