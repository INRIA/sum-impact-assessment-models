from pydantic import Field
from typing import Optional
from .kpi import KPI


class KPILivingLab(KPI):
    """
    KPI schema:
    - living_lab_id: identifier for the related living lab
    - variation: calculated variation (e.g. percent change)
    - value_before: value before intervention
    - value_after: value after intervention
    """
    living_lab_id: str = Field(...,
                               description="Identifier for the related living lab")
    value_before: Optional[float] = Field(None, description="Value before")
    value_after: Optional[float] = Field(None, description="Value after")
    variation: Optional[float] = Field(
        None, description="Computed variation (float)")
