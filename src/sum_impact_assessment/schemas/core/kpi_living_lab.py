from pydantic import Field
from typing import Optional
from .kpi import KPI


class KPILivingLabResult(KPI):
    living_lab_id: str = Field(...,
                               description="Identifier for the related living lab")
    transport_mode_id: Optional[str] = Field(
        None, description="Identifier for the transport mode, only for Modal Split KPIS")
    transport_mode_name: Optional[str] = Field(
        None, description="Name of the transport mode, only for Modal Split KPIS")
    transport_mode_type: Optional[str] = Field(
        None, description="Type of the transport mode, only for Modal Split KPIS")
    value_before: Optional[float] = Field(None, description="Value before")
    value_after: Optional[float] = Field(None, description="Value after")
    abs_variation: Optional[float] = Field(
        None, description="Computed absolute variation between before and after values (float)")
    ratio_variation: Optional[float] = Field(
        None, description="Computed ratio variation between before and after values (float)")

    def update_absolute_variation(self):
        """
        Updates each KPI's 'abs_variation' field based on value_before and value_after.
        Absolute variation is calculated as absolute change in KPI value. The sign is adjusted according to progression_target:
        - progression_target == 1 (increase desired): positive if value Increases
        - progression_target == 0 (decrease desired): positive if value Decreases
        """

        if (self.value_before is None) or (self.value_after is None):
            raise ValueError(
                "No value after or before for variation calculation.")

        abs_variation = (self.value_after - self.value_before)
        self.abs_variation = abs_variation if self.progression_target == 1 else -abs_variation

    def update_ratio_variation(self):
        """
        Updates each KPI's 'ratio_variation' field based on value_before and value_after.
        Ratio variation is calculated as ratio change in KPI value. The sign is adjusted according to progression_target:
        - progression_target == 1 (increase desired): positive if value Increases
        - progression_target == 0 (decrease desired): positive if value Decreases
        """

        if (self.value_before is None) or (self.value_after is None):
            raise ValueError(
                "No value after or before for variation calculation.")

        self.update_absolute_variation()
        if self.value_before == 0:
            if self.value_after == 0:
                self.ratio_variation = 0.0  # No change
            else:
                # Treat as 100% change in the appropriate direction
                self.ratio_variation = 1.0 if self.abs_variation > 0 else -1.0
        else:
            self.ratio_variation = self.abs_variation / self.value_before
