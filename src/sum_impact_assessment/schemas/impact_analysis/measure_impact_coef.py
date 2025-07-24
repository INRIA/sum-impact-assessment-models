from ..core import Measure


class MeasureImpactCoefficient(Measure):
    """
    Extends Measure to include impact coefficient.
    - kpi_group_id (str): KPI Group for which measure impact was estimated.
    - coefficient (float): Estimated impact coefficient.
   """
    kpi_group_id: str 
    coefficient: float
