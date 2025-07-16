from pydantic import BaseModel, Field
from typing import Optional


class KPI(BaseModel):
    """
    KPI schema:
    - id: unique identifier
    - name: human-readable name of the KPI
    - variation: calculated variation (e.g. percent change)
    - value_before: value before intervention
    - value_after: value after intervention
    """
    id: str
    name: str
    variation: Optional[float] = Field(None, description="Computed variation (float)")
    value_before: float = Field(..., description="Value before")
    value_after: float = Field(..., description="Value after")
    progression_target: int = Field(
        ..., description="0: expected to go down, 1: expected to go up")
