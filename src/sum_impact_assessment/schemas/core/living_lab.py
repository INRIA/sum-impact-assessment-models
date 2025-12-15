from typing import List
from pydantic import BaseModel
from .kpi_living_lab import KPILivingLabResult
from .measure import Measure
import json


class LivingLab(BaseModel):
    """
    Living Lab schema:
    - id: unique identifier
    - name: human-readable name of the living lab
    - kpis: list of associated KPIs
    - measures: list of associated measures
    """
    id: str
    name: str
    kpis: List[KPILivingLabResult]
    measures: List[Measure]

    def __init__(self, **data):
        super().__init__(**data)
        for kpi in self.kpis:
            if (kpi.value_before is not None and kpi.value_before > 0 and kpi.value_after is not None and kpi.value_after > 0):
                kpi.update_ratio_variation()

    @classmethod
    def from_json_file(cls, file_path: str):
        """
        Initialize KPI instance from a JSON file.
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
