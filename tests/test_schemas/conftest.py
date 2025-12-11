"""Shared fixtures for schema tests."""
import pytest
from sum_impact_assessment.schemas.core import KPI, KPILivingLabResult, LivingLab, Measure, KPIGroup, KPIValueType


@pytest.fixture
def sample_kpi():
    """Sample KPI with progression_target=1 (increase desired)."""
    return KPI(
        id="kpi_test_1",
        name="Test KPI - Increase Desired",
        progression_target=1,
        value_type=KPIValueType.percentage,
        value_min=0.0,
        value_max=1.0
    )


@pytest.fixture
def sample_kpi_decrease():
    """Sample KPI with progression_target=0 (decrease desired)."""
    return KPI(
        id="kpi_test_2",
        name="Test KPI - Decrease Desired",
        progression_target=0,
        value_type=KPIValueType.ratio,
        value_min=None,
        value_max=None
    )


@pytest.fixture
def sample_kpi_no_bounds():
    """Sample KPI without min/max bounds."""
    return KPI(
        id="kpi_test_3",
        name="Test KPI - No Bounds",
        progression_target=1,
        value_type=KPIValueType.custom_unit
    )


@pytest.fixture
def sample_measure():
    """Sample Measure."""
    return Measure(
        id="measure_test_001",
        name="Test Measure"
    )


@pytest.fixture
def sample_measures():
    """List of sample measures."""
    return [
        Measure(id="measure_001", name="Congestion charges"),
        Measure(id="measure_002", name="Parking charges")
    ]


@pytest.fixture
def sample_kpi_living_lab_result(sample_kpi):
    """Sample KPILivingLabResult with valid before/after values."""
    return KPILivingLabResult(
        id=sample_kpi.id,
        name=sample_kpi.name,
        progression_target=sample_kpi.progression_target,
        value_type=sample_kpi.value_type,
        value_min=sample_kpi.value_min,
        value_max=sample_kpi.value_max,
        living_lab_id="lab_test_001",
        value_before=0.5,
        value_after=0.8
    )


@pytest.fixture
def sample_kpi_definitions():
    """List of KPI definitions for testing data loading."""
    return [
        KPI(
            id="kpi_1",
            name="Level of completion of SUMP measures",
            progression_target=1,
            value_type=KPIValueType.percentage,
            value_min=0.0,
            value_max=1.0
        ),
        KPI(
            id="kpi_2",
            name="Modal split - car",
            progression_target=0,
            value_type=KPIValueType.percentage,
            value_min=0.0,
            value_max=1.0
        ),
        KPI(
            id="kpi_3",
            name="Modal split - public transport",
            progression_target=1,
            value_type=KPIValueType.percentage,
            value_min=0.0,
            value_max=1.0
        )
    ]
