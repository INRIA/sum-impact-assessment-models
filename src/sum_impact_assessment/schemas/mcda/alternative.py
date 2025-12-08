"""
MCDA Alternative Schema

Represents a decision alternative with its performance values.
"""
from pydantic import BaseModel, Field
from typing import Dict


class Alternative(BaseModel):
    """
    Represents a single alternative/option in MCDA analysis.

    Attributes:
        name: Unique identifier for the alternative
        values: Dictionary mapping goal names to performance values
    """
    name: str = Field(..., description="Unique alternative identifier")
    values: Dict[str, float] = Field(...,
                                     description="Performance values per goal")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Project A",
                "values": {
                    "Environmental Impact": 0.8,
                    "Economic Cost": 1200.0,
                    "Social Acceptance": 0.65
                }
            }
        }
