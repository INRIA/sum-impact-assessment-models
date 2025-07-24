from pydantic import BaseModel, Field
from typing import List, Optional
from .kpi import KPI
from .living_lab import LivingLab
from ..impact_analysis.measure_impact_coef import MeasureImpactCoefficient

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
    
    # Impact Analysis Results
    living_labs_analysis: Optional[List[LivingLab]] = Field(
        None, description="Optional list of LivingLab objects used in the impact analysis for this group") 
    msqe: Optional[float] = Field(
        None, description="Optional float of mean squared error of the impact analysis for this group")
    variation_under_no_measures: Optional[float] = Field(
        None, description="Optional float of expected variation in KPI group if no measures are implemented from the impact analysis") 
    measure_coefficients: Optional[List[MeasureImpactCoefficient]] = Field(
        None, description="Optional list of Measures with predicted impact coefficients from the impact analysis") 
    

    