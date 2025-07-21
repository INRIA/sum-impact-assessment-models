from pydantic import BaseModel, Field
from typing import List, Optional
from .kpi import KPI


class KPIGroup(BaseModel):
    """
    KPIGroup schema:
    - id: unique identifier for the group
    - name: human-readable name of the group
    - kpi_ids: list of KPI ids belonging to this group
    - kpis: optional list of KPI objects (can be empty or null)
    """
    id: str = Field(..., description="Unique identifier for the KPI group")
    name: str = Field(..., description="Human-readable name of the KPI group")
    kpi_ids: List[str] = Field(...,
                               description="List of KPI ids in this group")
    kpis: Optional[List[KPI]] = Field(
        None, description="Optional list of KPI objects belonging this group")
