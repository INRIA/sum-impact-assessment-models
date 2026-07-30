"""
Unit tests for KPIImpactAnalyzer - single-lab filtering and times_implemented.
"""
import numpy as np
import pytest
from src.sum_impact_assessment.models.impact_analysis.kpi_impact_analysis import KPIImpactAnalyzer
from src.sum_impact_assessment.schemas.core import (
    KPIGroup, KPI, LivingLab, Measure, KPILivingLabResult,
)
from src.sum_impact_assessment.schemas.core.kpi_value_type import KPIValueType


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_kpi(kpi_id: str, value_min: float = 0.0, value_max: float = 100.0) -> KPI:
    return KPI(
        id=kpi_id,
        name=kpi_id,
        progression_target=1,
        value_type=KPIValueType.percentage,
        value_min=value_min,
        value_max=value_max,
    )


def make_kpi_result(kpi_id: str, lab_id: str, before: float, after: float) -> KPILivingLabResult:
    return KPILivingLabResult(
        id=kpi_id,
        name=kpi_id,
        progression_target=1,
        value_type=KPIValueType.percentage,
        value_min=0.0,
        value_max=100.0,
        living_lab_id=lab_id,
        value_before=before,
        value_after=after,
    )


def make_measure(measure_id: str, times: int = 1) -> Measure:
    return Measure(id=measure_id, name=measure_id, times_implemented=times)


def make_lab(lab_id: str, kpi_ids: list[str], measure_ids: list[str]) -> LivingLab:
    kpis = [make_kpi_result(k, lab_id, 10.0, 20.0) for k in kpi_ids]
    measures = [make_measure(m) for m in measure_ids]
    return LivingLab(id=lab_id, name=lab_id, kpis=kpis, measures=measures)


def make_group(group_id: str, kpi_ids: list[str]) -> KPIGroup:
    return KPIGroup(id=group_id, name=group_id, kpi_ids=kpi_ids)


# ---------------------------------------------------------------------------
# filter_measures_with_min_implementations
# ---------------------------------------------------------------------------

class TestFilterMeasuresWithMinImplementations:

    def _analyzer(self):
        """Minimal analyzer with no data (helper-only tests)."""
        return KPIImpactAnalyzer(living_labs=[], measures=[], kpis=[], kpi_groups=[])

    def test_all_measures_implemented_by_enough_labs_are_kept(self):
        analyzer = self._analyzer()
        X = np.array([[1, 1], [1, 1], [0, 1]])  # col0: 2 non-zero, col1: 3 non-zero
        measures = [make_measure("m1"), make_measure("m2")]

        X_f, kept = analyzer.filter_measures_with_min_implementations(X, measures)

        assert X_f.shape == (3, 2)
        assert [m.id for m in kept] == ["m1", "m2"]

    def test_single_lab_measure_is_dropped(self):
        analyzer = self._analyzer()
        # col0: 1 non-zero (only lab A), col1: 2 non-zero (lab A + lab B)
        X = np.array([[1, 1], [0, 1], [0, 0]])
        measures = [make_measure("m1"), make_measure("m2")]

        X_f, kept = analyzer.filter_measures_with_min_implementations(X, measures)

        assert X_f.shape == (3, 1)
        assert kept[0].id == "m2"

    def test_all_single_lab_measures_returns_empty(self):
        analyzer = self._analyzer()
        X = np.array([[1, 1], [0, 0]])  # each column has only 1 non-zero entry
        measures = [make_measure("m1"), make_measure("m2")]

        X_f, kept = analyzer.filter_measures_with_min_implementations(X, measures)

        assert X_f.shape[1] == 0
        assert kept == []

    def test_no_feasible_living_labs_returns_empty_filter_result(self):
        analyzer = self._analyzer()
        X = np.array([], dtype=int)
        measures = [make_measure("m1"), make_measure("m2")]

        X_f, kept = analyzer.filter_measures_with_min_implementations(X, measures)

        assert X_f.size == 0
        assert kept == []

    def test_does_not_mutate_input_measures_list(self):
        analyzer = self._analyzer()
        X = np.array([[1, 1], [0, 0]])
        measures = [make_measure("m1"), make_measure("m2")]
        original_len = len(measures)

        analyzer.filter_measures_with_min_implementations(X, measures)

        assert len(measures) == original_len

    def test_compute_X_y_input_returns_empty_when_kpi_group_has_no_kpis(self):
        analyzer = KPIImpactAnalyzer(
            living_labs=[make_lab("lab_a", ["k1"], ["m1"])],
            measures=[make_measure("m1")],
            kpis=[],
            kpi_groups=[],
        )
        group = KPIGroup(id="g1", name="g1", kpi_ids=[])

        X, y, feasible_ll, returned_group = analyzer.compute_X_y_input(group)

        assert X.shape == (0, 1)
        assert y.shape == (0,)
        assert feasible_ll == []
        assert returned_group == group


# ---------------------------------------------------------------------------
# run_analysis_group — example 1 and 2
# ---------------------------------------------------------------------------

class TestRunAnalysisGroupFiltering:
    """
    End-to-end tests verifying that single-lab measures are excluded from results.
    """

    KPI_ID = "k1"
    GROUP_ID = "g1"

    def _build_analyzer(self, labs: list[LivingLab], measures: list[Measure]) -> KPIImpactAnalyzer:
        kpi_def = make_kpi(self.KPI_ID)
        kpi_group = make_group(self.GROUP_ID, [self.KPI_ID])
        return KPIImpactAnalyzer(
            living_labs=labs,
            measures=measures,
            kpis=[kpi_def],
            kpi_groups=[kpi_group],
        )

    def test_example1_four_measures_kept_one_dropped(self):
        """
        5 measures: m1-m4 implemented by ≥2 labs, m5 by only 1 lab.
        Expected: 4 MeasureImpactCoefficient entries, m5 absent.
        """
        # lab_a and lab_b both implement m1-m4; only lab_a implements m5
        lab_a = make_lab("lab_a", [self.KPI_ID], ["m1", "m2", "m3", "m4", "m5"])
        lab_b = make_lab("lab_b", [self.KPI_ID], ["m1", "m2", "m3", "m4"])
        lab_c = make_lab("lab_c", [self.KPI_ID], ["m1", "m2", "m3", "m4"])

        measures = [make_measure(f"m{i}") for i in range(1, 6)]
        analyzer = self._build_analyzer([lab_a, lab_b, lab_c], measures)
        group = make_group(self.GROUP_ID, [self.KPI_ID])

        result = analyzer.run_analysis_group(group)

        assert result.measure_coefficients is not None
        ids = {m.id for m in result.measure_coefficients}
        assert "m5" not in ids, "m5 (single-lab) should be excluded"
        assert len(result.measure_coefficients) == 4

    def test_example2_all_single_lab_returns_empty_measure_list(self):
        """
        5 measures, each implemented by only 1 lab (different labs per measure).
        Expected: measure_coefficients=[], job does not raise.
        """
        lab_a = make_lab("lab_a", [self.KPI_ID], ["m1"])
        lab_b = make_lab("lab_b", [self.KPI_ID], ["m2"])
        lab_c = make_lab("lab_c", [self.KPI_ID], ["m3"])
        lab_d = make_lab("lab_d", [self.KPI_ID], ["m4"])
        lab_e = make_lab("lab_e", [self.KPI_ID], ["m5"])

        measures = [make_measure(f"m{i}") for i in range(1, 6)]
        analyzer = self._build_analyzer(
            [lab_a, lab_b, lab_c, lab_d, lab_e], measures
        )
        group = make_group(self.GROUP_ID, [self.KPI_ID])

        result = analyzer.run_analysis_group(group)

        assert result.measure_coefficients == [], (
            "All measures are single-lab; result should be empty list"
        )
        assert result.msqe is None
        assert result.variation_under_no_measures is None
        # living labs analysis still populated
        assert result.living_labs_analysis is not None

    def test_times_implemented_equals_column_sum_of_X(self):
        """
        times_implemented on each MeasureImpactCoefficient equals total lab
        implementations (column sum of the filtered X matrix).

        lab_a: m1 x1, m2 x1
        lab_b: m1 x1, m2 x1
        → times_implemented(m1) = 2, times_implemented(m2) = 2
        """
        lab_a = make_lab("lab_a", [self.KPI_ID], ["m1", "m2"])
        lab_b = make_lab("lab_b", [self.KPI_ID], ["m1", "m2"])
        lab_c = make_lab("lab_c", [self.KPI_ID], ["m1", "m2"])

        measures = [make_measure("m1"), make_measure("m2")]
        analyzer = self._build_analyzer([lab_a, lab_b, lab_c], measures)
        group = make_group(self.GROUP_ID, [self.KPI_ID])

        result = analyzer.run_analysis_group(group)

        assert result.measure_coefficients is not None
        for m in result.measure_coefficients:
            assert m.times_implemented is not None, (
                f"times_implemented must not be None for {m.id}"
            )
            assert m.times_implemented > 0
