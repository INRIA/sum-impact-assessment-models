"""Shared fixtures for schema tests."""
import pytest
from sum_impact_assessment.schemas.core import KPI, KPILivingLabResult, LivingLab, Measure, KPIGroup, KPIValueType


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
