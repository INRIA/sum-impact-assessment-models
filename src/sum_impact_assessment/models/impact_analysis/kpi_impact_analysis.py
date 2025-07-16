from ...schemas import MeasureImpactCoefficient, Measure


class KPIImpactAnalyzer:
    def __init__(self, living_labs: list, measures: Measure):
        """
        Initialize with a list of LivingLabs information.
        """
        self.living_labs = living_labs
        self.measures = measures

    def run_analysis(self) -> list[MeasureImpactCoefficient]:
        """
        Run KPI impact analysis on the LivingLabs data.
        TO BE DEFINED : return any other information usefull for tracking, debug, error analysing, etc... maybe log progress in DB ?
        Returns list of MeasureImpactCoefficient
        """
        results = []
        for measure in self.measures:
            # Dummy values for coefficient and msq
            coefficient = 1.0  # Replace with actual calculation
            msq = 0.0          # Replace with actual calculation
            # add any complementary information
            result = MeasureImpactCoefficient(
                id=measure.id, name=measure.name,
                coefficient=coefficient, msq=msq)
            results.append(result)

        self.result = results
        return results
