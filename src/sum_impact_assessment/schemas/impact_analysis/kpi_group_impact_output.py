from pydantic import Field
from typing import List, Optional
from ..core import KPIGroup
from measure_impact_coef import MeasureImpactCoefficient
from living_lab_impact_error import LivingLabImpactError

class KPIGroupImpactOutput(KPIGroup):
    """
    Extends KPIGroup to include the results of the impact analysis.
    - living_labs_analysis, list of living labs with estimation squared error `LivingLabImpactError` obtained from the analysis,
    - msqe, mean square error of the estimation,
    - variation_under_no_measures, espected variation if no measures were implemented (aka intercept term),
    - measure_coefficients, list of measures with updated impact coeffients `MeasureImpactCoefficient` obtained from the analysis.
    """
    # Impact Analysis Results
    living_labs_analysis: Optional[List[LivingLabImpactError]] = Field(
        None, description="Optional list of LivingLab objects used in the impact analysis for this group") 
    msqe: Optional[float] = Field(
        None, description="Optional float of mean squared error of the impact analysis for this group")
    variation_under_no_measures: Optional[float] = Field(
        None, description="Optional float of expected variation in KPI group if no measures are implemented from the impact analysis") 
    measure_coefficients: Optional[List[MeasureImpactCoefficient]] = Field(
        None, description="Optional list of Measures with predicted impact coefficients from the impact analysis") 