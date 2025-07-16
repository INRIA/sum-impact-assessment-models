from typing import List
from ..schemas.kpi import KPI


class KPINormalizer:
    """
    Normalizes KPI data by calculating the variation for each KPI.
    """

    def __init__(self, kpis: List[KPI]):
        self.kpis = kpis

    def normalizeKPIs(self):
        """
        Updates each KPI's 'variation' field based on value_before and value_after.
        Variation is calculated as percent change. The sign is adjusted according to progression_target:
        - progression_target == 1 (increase desired): positive if value Increases
        - progression_target == 0 (decrease desired): positive if value Decreases
        """
        for kpi in self.kpis:
            if kpi.value_before != 0:
                variation = ((kpi.value_after - kpi.value_before) /
                             kpi.value_before)
                kpi.variation = variation if kpi.progression_target == 1 else -variation
            else:
                kpi.variation = 0.0

        return self.kpis
