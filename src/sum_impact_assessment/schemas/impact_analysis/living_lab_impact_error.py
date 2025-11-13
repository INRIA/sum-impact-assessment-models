from ..core import LivingLab


class LivingLabImpactError(LivingLab):
    """
    Extends LivingLab to include estimation squared error (sqe).
    - kpi_group_id (str): KPI Group for which measure impact was estimated.
    - sqe (float): Squared Error of the estimation.
    """
    kpi_group_id: str 
    sqe: float