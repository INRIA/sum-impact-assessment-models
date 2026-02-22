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
    
    # NOTE B doesn't use this field 'kpis', because it will need all KPI's for all living labs, in case not needed can delete
    kpis: Optional[List[KPI]] = Field(
        None, description="Optional list of KPI objects belonging this group") 
    transport_mode_type_filter: Optional[List[str]] = Field(
        None,
        description="Optional transport mode type filters for Modal Split subgroup analysis"
    )

    def __eq__(self, other):
        if not isinstance(other, KPIGroup):
            return NotImplemented
        return self.id == other.id
    
    
    

    