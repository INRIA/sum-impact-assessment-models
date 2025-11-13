from pydantic import Field
from typing import Optional
from .kpi import KPI


class KPILivingLab(KPI):
    """
    KPI schema:
    - living_lab_id: identifier for the related living lab
    - value_before: value before intervention
    - value_after: value after intervention
    - abs_variation: calculated absolute variation between before and after values
    - variation: calculated variation (e.g. percent change)
    """
    living_lab_id: str = Field(...,
                               description="Identifier for the related living lab")
    value_before: Optional[float] = Field(None, description="Value before")
    value_after: Optional[float] = Field(None, description="Value after")
    abs_variation: Optional[float] = Field(
        None, description="Computed absolute variation (float)")
    variation: Optional[float] = Field(
        None, description="Computed variation (float)")

    def update_absolute_variation(self):
        """
        Updates each KPI's 'abs_variation' field based on value_before and value_after.
        Absolute variation is calculated as absolute change in KPI value. The sign is adjusted according to progression_target:
        - progression_target == 1 (increase desired): positive if value Increases
        - progression_target == 0 (decrease desired): positive if value Decreases
        """

        if (self.value_before is None) or (self.value_after is None):
            raise ValueError("No value after or before for variation calculation.")
        
        abs_variation = (self.value_after - self.value_before)
        self.abs_variation = abs_variation if self.progression_target == 1 else -abs_variation



