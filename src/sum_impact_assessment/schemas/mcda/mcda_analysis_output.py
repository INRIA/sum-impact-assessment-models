"""
MCDA Analysis Output Schema

Comprehensive output structure for PROMETHEE-GAIA analysis results.
Designed for JSON serialization and consumption by front-end charting clients.

KEY NAMING CONVENTION:
- Alternatives use keys: a1, a2, a3, ... (alternative 1, 2, 3)
- Criteria use keys: c1, c2, c3, ... (criterion 1, 2, 3)
- Use alternative_labels and criteria_labels to map keys to full names
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


class GAIAAlternativeCoordinate(BaseModel):
    """
    2D coordinates for an alternative in the GAIA plane.
    """
    key: str = Field(..., description="Alternative key (e.g., 'a1', 'a2')")
    x: float = Field(..., description="X-coordinate in GAIA plane (PC1)")
    y: float = Field(..., description="Y-coordinate in GAIA plane (PC2)")


class GAIACriterionVector(BaseModel):
    """
    2D vector for a criterion in the GAIA plane.
    """
    key: str = Field(..., description="Criterion key (e.g., 'c1', 'c2')")
    x: float = Field(..., description="X-component of criterion vector")
    y: float = Field(..., description="Y-component of criterion vector")


class MCDAAnalysisOutput(BaseModel):
    """
    Complete output from PROMETHEE-GAIA analysis.

    Contains all data necessary for generating:
    - Net flow ranking chart (Promethee II)
    - Detailed positive/negative flows chart (Promethee I)
    - Simplified GAIA decision plane (GAIA)

    All fields are JSON-serializable for database storage and API responses.

    DATA REFERENCE SYSTEM:
    - All alternatives are referenced by keys: 'a1', 'a2', 'a3', etc.
    - All criteria are referenced by keys: 'c1', 'c2', 'c3', etc.
    - To get full names, use alternative_labels[key] or criteria_labels[key]

    Example:
        >>> output.ranking[0]  # Returns 'a5'
        >>> output.alternative_labels['a5']  # Returns 'Solar Energy Project'
        >>> output.positive_flows['a5']  # Returns 0.85
    """

    # Label mappings: keys to full names
    alternative_labels: Dict[str, str] = Field(
        ...,
        description="Maps alternative keys to full names. Example: {'a1': 'Project Alpha', 'a2': 'Project Beta'}"
    )
    criteria_labels: Dict[str, str] = Field(
        ...,
        description="Maps criterion keys to full names. Example: {'c1': 'Environmental Impact', 'c2': 'Cost'}"
    )

    # PROMETHEE I: Flow values (keyed by alternative keys)
    positive_flows: Dict[str, float] = Field(
        ...,
        description="Positive outranking flows (φ+) for each alternative. Keys: a1, a2, etc. Higher = stronger preference by this alternative over others."
    )
    negative_flows: Dict[str, float] = Field(
        ...,
        description="Negative outranking flows (φ-) for each alternative. Keys: a1, a2, etc. Higher = more preferred by others over this alternative."
    )

    # PROMETHEE II: Net flows and ranking (using alternative keys)
    net_flows: Dict[str, float] = Field(
        ...,
        description="Net flows (φ = φ+ - φ-) for each alternative. Keys: a1, a2, etc. Higher = better overall ranking."
    )
    ranking: List[str] = Field(
        ...,
        description="Alternative keys ordered by net flow (descending). First = best. Example: ['a5', 'a2', 'a1']. Use alternative_labels to get names."
    )

    # GAIA: Visual decision plane data (using keys)
    gaia_alternatives: Optional[List[GAIAAlternativeCoordinate]] = Field(
        default=None,
        description="2D coordinates for each alternative in GAIA plane. Each has 'key' (a1, a2, etc), 'x', and 'y'. None if GAIA projection could not be computed."
    )
    gaia_criteria: Optional[List[GAIACriterionVector]] = Field(
        default=None,
        description="2D vectors for each criterion in GAIA plane. Each has 'key' (c1, c2, etc), 'x', and 'y'. Arrow direction indicates preference direction. None if GAIA projection could not be computed."
    )
    gaia_decision_stick: Optional[List[float]] = Field(
        default=None,
        description="[x, y] coordinates of the decision stick (weighted sum of criterion vectors). None if GAIA projection could not be computed.",
        min_length=2,
        max_length=2
    )
    gaia_quality: Optional[float] = Field(
        default=None,
        # ge=0,
        # le=100,
        description="Quality percentage of the 2D GAIA projection. Represents how much variance is explained by PC1 and PC2. None if GAIA projection could not be computed."
    )
    gaia_method: Optional[Literal['pca', 'svd']] = Field(
        default=None,
        description="Dimensionality reduction method used for GAIA plane construction. None if GAIA projection could not be computed."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "alternative_labels": {
                    "a1": "Solar Energy Project",
                    "a2": "Wind Farm Initiative",
                    "a3": "Hydroelectric Plant"
                },
                "criteria_labels": {
                    "c1": "Environmental Impact",
                    "c2": "Economic Cost",
                    "c3": "Social Acceptance"
                },
                "positive_flows": {
                    "a1": 0.65,
                    "a2": 0.42,
                    "a3": 0.58
                },
                "negative_flows": {
                    "a1": 0.35,
                    "a2": 0.58,
                    "a3": 0.42
                },
                "net_flows": {
                    "a1": 0.30,
                    "a2": -0.16,
                    "a3": 0.16
                },
                "ranking": ["a1", "a3", "a2"],
                "gaia_alternatives": [
                    {"key": "a1", "x": 1.2, "y": 0.5},
                    {"key": "a2", "x": -0.8, "y": -0.3},
                    {"key": "a3", "x": 0.5, "y": 0.9}
                ],
                "gaia_criteria": [
                    {"key": "c1", "x": 0.8, "y": 0.2},
                    {"key": "c2", "x": -0.3, "y": 0.9},
                    {"key": "c3", "x": 0.5, "y": -0.6}
                ],
                "gaia_decision_stick": [0.35, 0.28],
                "gaia_quality": 87.5,
                "gaia_method": "pca"
            }
        }
