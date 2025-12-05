"""
Unit tests for KPINormalizer class.
"""
import json
import pytest
from pathlib import Path
from sum_impact_assessment.utils import KPINormalizer
from sum_impact_assessment.schemas.core import KPILivingLabResult


def load_kpis_from_fixture(filename: str) -> list[KPILivingLabResult]:
    """
    Load KPI test data from JSON fixture file.
    
    Args:
        filename: Name of the JSON file in tests/fixtures/
        
    Returns:
        List of KPILivingLabResult instances
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / filename
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    return [KPILivingLabResult(**kpi_data) for kpi_data in data]


class TestKPINormalizerInitialization:
    """Test KPINormalizer initialization."""
    
    @pytest.mark.unit
    def test_init_with_empty_list(self):
        """Test initialization with empty KPI list."""
        normalizer = KPINormalizer(kpis=[])
        assert normalizer.kpis == []
        assert isinstance(normalizer.kpis, list)
        assert len(normalizer.kpis) == 0
    
    @pytest.mark.unit
    def test_init_with_normal_kpis(self):
        """Test initialization with normal KPI data."""
        kpis = load_kpis_from_fixture("normal_kpis.json")
        normalizer = KPINormalizer(kpis=kpis)
        assert len(normalizer.kpis) == 3
        assert all(isinstance(kpi, KPILivingLabResult) for kpi in normalizer.kpis)


class TestKPINormalizerNormalizeKPIs:
    """Test KPINormalizer.normalizeKPIs() method."""
    
    @pytest.mark.unit
    def test_normalize_empty_list(self):
        """Test normalizeKPIs returns empty list when initialized with empty list."""
        normalizer = KPINormalizer(kpis=[])
        result = normalizer.normalizeKPIs()
        assert result == []
        assert isinstance(result, list)
    
    @pytest.mark.unit
    def test_normalize_with_zero_value_before(self):
        """Test normalization when value_before is zero."""
        kpis = load_kpis_from_fixture("edge_case_kpis.json")
        # Filter to only zero value_before cases
        zero_before_kpis = [kpi for kpi in kpis if kpi.value_before == 0]
        
        normalizer = KPINormalizer(kpis=zero_before_kpis)
        result = normalizer.normalizeKPIs()
        
        # When value_before is 0, variation should be set to 0.0
        for kpi in result:
            assert kpi.variation == 0.0
    
    @pytest.mark.unit
    def test_normalize_progression_target_increase(self):
        """Test normalization with progression_target = 1 (increase desired)."""
        kpis = load_kpis_from_fixture("normal_kpis.json")
        # Get KPI with progression_target = 1
        kpi_increase = [kpi for kpi in kpis if kpi.id == "kpi_2"][0]
        
        normalizer = KPINormalizer(kpis=[kpi_increase])
        result = normalizer.normalizeKPIs()
        
        # value_before: 0.5, value_after: 0.7
        # Expected variation: (0.7 - 0.5) / 0.5 = 0.4 (positive because increase is desired)
        expected_variation = (0.7 - 0.5) / 0.5
        assert result[0].variation == pytest.approx(expected_variation)
        assert result[0].variation > 0  # Positive variation for increase
    
    @pytest.mark.unit
    def test_normalize_progression_target_decrease(self):
        """Test normalization with progression_target = 0 (decrease desired)."""
        kpis = load_kpis_from_fixture("normal_kpis.json")
        # Get KPI with progression_target = 0
        kpi_decrease = [kpi for kpi in kpis if kpi.id == "kpi_1"][0]
        
        normalizer = KPINormalizer(kpis=[kpi_decrease])
        result = normalizer.normalizeKPIs()
        
        # value_before: 0.8, value_after: 0.6
        # Raw variation: (0.6 - 0.8) / 0.8 = -0.25
        # Expected variation: -(-0.25) = 0.25 (positive because decrease is desired)
        raw_variation = (0.6 - 0.8) / 0.8
        expected_variation = -raw_variation
        assert result[0].variation == pytest.approx(expected_variation)
        assert result[0].variation > 0  # Positive variation for desired decrease
    
    @pytest.mark.unit
    def test_normalize_no_change(self):
        """Test normalization when value_before equals value_after."""
        kpis = load_kpis_from_fixture("edge_case_kpis.json")
        no_change_kpi = [kpi for kpi in kpis if kpi.id == "kpi_no_change"][0]
        
        normalizer = KPINormalizer(kpis=[no_change_kpi])
        result = normalizer.normalizeKPIs()
        
        # No change should result in variation = 0.0
        assert result[0].variation == 0.0
    
    @pytest.mark.unit
    def test_normalize_negative_variation_with_increase_target(self):
        """Test when actual change is opposite to progression_target."""
        kpis = load_kpis_from_fixture("edge_case_kpis.json")
        # KPI with progression_target=1 but value decreased
        kpi = [kpi for kpi in kpis if kpi.id == "kpi_negative_change_target_increase"][0]
        
        normalizer = KPINormalizer(kpis=[kpi])
        result = normalizer.normalizeKPIs()
        
        # value_before: 0.8, value_after: 0.6, progression_target: 1
        # Raw variation: (0.6 - 0.8) / 0.8 = -0.25
        # Since progression_target = 1, variation stays negative
        expected_variation = (0.6 - 0.8) / 0.8
        assert result[0].variation == pytest.approx(expected_variation)
        assert result[0].variation < 0  # Negative because change is opposite to target
    
    @pytest.mark.unit
    def test_normalize_positive_variation_with_decrease_target(self):
        """Test when value increases but decrease is desired."""
        kpis = load_kpis_from_fixture("edge_case_kpis.json")
        # KPI with progression_target=0 but value increased
        kpi = [kpi for kpi in kpis if kpi.id == "kpi_positive_change_target_decrease"][0]
        
        normalizer = KPINormalizer(kpis=[kpi])
        result = normalizer.normalizeKPIs()
        
        # value_before: 0.6, value_after: 0.8, progression_target: 0
        # Raw variation: (0.8 - 0.6) / 0.6 = 0.333...
        # Since progression_target = 0, variation becomes negative
        raw_variation = (0.8 - 0.6) / 0.6
        expected_variation = -raw_variation
        assert result[0].variation == pytest.approx(expected_variation)
        assert result[0].variation < 0  # Negative because change is opposite to target
    
    @pytest.mark.unit
    def test_normalize_returns_modified_kpis(self):
        """Test that normalizeKPIs modifies and returns the KPI objects."""
        kpis = load_kpis_from_fixture("normal_kpis.json")
        normalizer = KPINormalizer(kpis=kpis)
        
        # Before normalization, variation should be None
        for kpi in normalizer.kpis:
            assert kpi.variation is None
        
        result = normalizer.normalizeKPIs()
        
        # After normalization, all KPIs should have variation set
        for kpi in result:
            assert kpi.variation is not None
            assert isinstance(kpi.variation, float)
        
        # Result should be the same list object
        assert result is normalizer.kpis
    
    @pytest.mark.unit
    def test_normalize_multiple_kpis(self):
        """Test normalizing multiple KPIs at once."""
        kpis = load_kpis_from_fixture("normal_kpis.json")
        normalizer = KPINormalizer(kpis=kpis)
        result = normalizer.normalizeKPIs()
        
        assert len(result) == 3
        # All should have variation calculated
        for kpi in result:
            assert kpi.variation is not None
