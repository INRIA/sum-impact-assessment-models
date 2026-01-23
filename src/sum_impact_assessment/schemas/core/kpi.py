from pydantic import BaseModel, Field
from typing import Optional
from .kpi_value_type import KPIValueType


class KPI(BaseModel):
    """
    KPI schema:
    - id: unique identifier
    - name: human-readable name of the KPI
    - progression_target: expected progression of the KPI, to define negative or positive change. 0: expected to go down, 1: expected to go up
    - value_type: specifies the expected type of the value, must be one of KPIValueType
    - value_min: optional minimum value for the KPI (can be empty)
    - value_max: optional maximum value for the KPI (can be empty)
    """
    id: str
    name: str
    kpi_number: Optional[str] = Field(
        None, description="KPI number identifier")
    progression_target: int = Field(
        ..., description="0: expected to go down, 1: expected to go up")
    value_type: KPIValueType = Field(
        ..., description="Type of the values: percentage, ratio, custom_unit, score")
    value_min: Optional[float] = Field(
        None, description="Optional minimum value for the KPI")
    value_max: Optional[float] = Field(
        None, description="Optional maximum value for the KPI")
    parent_kpi_id: Optional[str] = Field(
        None, description="Identifier for the parent KPI, if any")
    parent_kpi_name: Optional[str] = Field(
        None, description="Name of the parent KPI, if any")
    parent_kpi_number: Optional[str] = Field(
        None, description="KPI number of the parent KPI, if any")
