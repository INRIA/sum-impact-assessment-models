"""Tests for LivingLab class - automatic variation calculation on initialization."""
import pytest
from sum_impact_assessment.schemas.core import KPI, KPILivingLabResult, LivingLab, Measure, KPIValueType


class TestLivingLabInstantiation:
    """Test basic instantiation of LivingLab."""
    
    def test_instantiation_with_all_fields(self, sample_measures):
        """Test creating LivingLab with complete data."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Test KPI 1",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            ),
            KPILivingLabResult(
                id="kpi_2",
                name="Test KPI 2",
                progression_target=0,
                value_type=KPIValueType.ratio,
                living_lab_id="lab_001",
                value_before=0.8,
                value_after=0.5
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=sample_measures
        )
        
        assert living_lab.id == "lab_001"
        assert living_lab.name == "Test Lab"
        assert len(living_lab.kpis) == 2
        assert len(living_lab.measures) == 2
    
    def test_instantiation_with_empty_kpis(self, sample_measures):
        """Test creating LivingLab with empty KPI list."""
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=[],
            measures=sample_measures
        )
        
        assert len(living_lab.kpis) == 0
        assert len(living_lab.measures) == 2
    
    def test_instantiation_with_empty_measures(self):
        """Test creating LivingLab with empty measures list."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Test KPI 1",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=[]
        )
        
        assert len(living_lab.kpis) == 1
        assert len(living_lab.measures) == 0


class TestLivingLabAutomaticVariationCalculation:
    """Test that __init__ automatically calculates variations for all KPIs."""
    
    def test_single_kpi_variations_calculated_on_init(self):
        """Test that a single KPI has variations calculated automatically."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Test KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=[]
        )
        
        # Verify variations were calculated
        kpi = living_lab.kpis[0]
        assert kpi.abs_variation is not None
        assert kpi.ratio_variation is not None
        assert kpi.abs_variation == pytest.approx(0.3)
        assert kpi.ratio_variation == pytest.approx(0.6)
    
    def test_multiple_kpis_variations_calculated_on_init(self):
        """Test that all KPIs have variations calculated automatically."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Test KPI 1",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            ),
            KPILivingLabResult(
                id="kpi_2",
                name="Test KPI 2",
                progression_target=0,
                value_type=KPIValueType.ratio,
                living_lab_id="lab_001",
                value_before=0.8,
                value_after=0.5
            ),
            KPILivingLabResult(
                id="kpi_3",
                name="Test KPI 3",
                progression_target=1,
                value_type=KPIValueType.custom_unit,
                living_lab_id="lab_001",
                value_before=100.0,
                value_after=150.0
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=[]
        )
        
        # Verify all KPIs have variations calculated
        for kpi in living_lab.kpis:
            assert kpi.abs_variation is not None, f"abs_variation not set for {kpi.id}"
            assert kpi.ratio_variation is not None, f"ratio_variation not set for {kpi.id}"
        
        # Verify specific calculations
        # KPI 1: progression_target=1, 0.5 -> 0.8 (increase)
        assert living_lab.kpis[0].abs_variation == pytest.approx(0.3)
        assert living_lab.kpis[0].ratio_variation == pytest.approx(0.6)
        
        # KPI 2: progression_target=0, 0.8 -> 0.5 (decrease, good)
        assert living_lab.kpis[1].abs_variation == pytest.approx(0.3)
        assert living_lab.kpis[1].ratio_variation == pytest.approx(0.375)
        
        # KPI 3: progression_target=1, 100 -> 150 (increase)
        assert living_lab.kpis[2].abs_variation == pytest.approx(50.0)
        assert living_lab.kpis[2].ratio_variation == pytest.approx(0.5)
    
    def test_empty_kpis_list_does_not_error(self):
        """Test that empty KPI list doesn't cause errors."""
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=[],
            measures=[]
        )
        
        assert len(living_lab.kpis) == 0
    
    def test_variations_with_no_change_kpi(self):
        """Test KPI with no change has zero variations."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="No Change KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.5
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=[]
        )
        
        kpi = living_lab.kpis[0]
        assert kpi.abs_variation == pytest.approx(0.0)
        assert kpi.ratio_variation == pytest.approx(0.0)
    
    def test_variations_with_modal_split_kpi(self):
        """Test KPI with transport mode fields."""
        kpis = [
            KPILivingLabResult(
                id="kpi_modal_split",
                name="Modal Split - Car",
                progression_target=0,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                transport_mode_id="mode_car",
                transport_mode_name="Car",
                value_before=0.6,
                value_after=0.4
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=[]
        )
        
        kpi = living_lab.kpis[0]
        assert kpi.transport_mode_id == "mode_car"
        assert kpi.transport_mode_name == "Car"
        # progression_target=0, decreased from 0.6 to 0.4 (good outcome)
        assert kpi.abs_variation == pytest.approx(0.2)
        assert kpi.ratio_variation == pytest.approx(0.2 / 0.6)


class TestLivingLabErrorPropagation:
    """Test error handling during automatic initialization."""
    
    def test_error_when_kpi_has_zero_value_before(self):
        """Test that ValueError is raised when a KPI has value_before=0."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Zero Before KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.0,
                value_after=0.5
            )
        ]
        
        with pytest.raises(ValueError, match="Value before is zero"):
            LivingLab(
                id="lab_001",
                name="Test Lab",
                kpis=kpis,
                measures=[]
            )
    
    def test_error_when_kpi_has_none_value_before(self):
        """Test that ValueError is raised when a KPI has value_before=None."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="None Before KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=None,
                value_after=0.5
            )
        ]
        
        with pytest.raises(ValueError, match="No value after or before"):
            LivingLab(
                id="lab_001",
                name="Test Lab",
                kpis=kpis,
                measures=[]
            )
    
    def test_error_when_kpi_has_none_value_after(self):
        """Test that ValueError is raised when a KPI has value_after=None."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="None After KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=None
            )
        ]
        
        with pytest.raises(ValueError, match="No value after or before"):
            LivingLab(
                id="lab_001",
                name="Test Lab",
                kpis=kpis,
                measures=[]
            )
    
    def test_error_stops_at_first_invalid_kpi(self):
        """Test that error is raised for first invalid KPI, stopping initialization."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Valid KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            ),
            KPILivingLabResult(
                id="kpi_2",
                name="Invalid KPI - Zero Before",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.0,
                value_after=0.5
            ),
            KPILivingLabResult(
                id="kpi_3",
                name="Another Valid KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.3,
                value_after=0.6
            )
        ]
        
        with pytest.raises(ValueError, match="Value before is zero"):
            LivingLab(
                id="lab_001",
                name="Test Lab",
                kpis=kpis,
                measures=[]
            )


class TestLivingLabDataIntegrity:
    """Test data integrity after initialization."""
    
    def test_kpi_data_preserved_after_init(self):
        """Test that KPI data is preserved after automatic calculation."""
        original_kpi = KPILivingLabResult(
            id="kpi_1",
            name="Test KPI",
            progression_target=1,
            value_type=KPIValueType.percentage,
            value_min=0.0,
            value_max=1.0,
            living_lab_id="lab_001",
            transport_mode_id="mode_001",
            transport_mode_name="Car",
            value_before=0.5,
            value_after=0.8
        )
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=[original_kpi],
            measures=[]
        )
        
        kpi = living_lab.kpis[0]
        # Verify original data is intact
        assert kpi.id == "kpi_1"
        assert kpi.name == "Test KPI"
        assert kpi.progression_target == 1
        assert kpi.value_type == KPIValueType.percentage
        assert kpi.value_min == 0.0
        assert kpi.value_max == 1.0
        assert kpi.living_lab_id == "lab_001"
        assert kpi.transport_mode_id == "mode_001"
        assert kpi.transport_mode_name == "Car"
        assert kpi.value_before == 0.5
        assert kpi.value_after == 0.8
        # Verify calculated fields
        assert kpi.abs_variation == pytest.approx(0.3)
        assert kpi.ratio_variation == pytest.approx(0.6)
    
    def test_measures_preserved_after_init(self):
        """Test that measures list is preserved after initialization."""
        measures = [
            Measure(id="measure_001", name="Congestion charges"),
            Measure(id="measure_002", name="Parking charges")
        ]
        
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Test KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=measures
        )
        
        assert len(living_lab.measures) == 2
        assert living_lab.measures[0].id == "measure_001"
        assert living_lab.measures[0].name == "Congestion charges"
        assert living_lab.measures[1].id == "measure_002"
        assert living_lab.measures[1].name == "Parking charges"
    
    def test_serialization_after_init(self):
        """Test that LivingLab can be serialized after initialization."""
        kpis = [
            KPILivingLabResult(
                id="kpi_1",
                name="Test KPI",
                progression_target=1,
                value_type=KPIValueType.percentage,
                living_lab_id="lab_001",
                value_before=0.5,
                value_after=0.8
            )
        ]
        
        living_lab = LivingLab(
            id="lab_001",
            name="Test Lab",
            kpis=kpis,
            measures=[]
        )
        
        # Test model_dump()
        data = living_lab.model_dump()
        assert data["id"] == "lab_001"
        assert data["name"] == "Test Lab"
        assert len(data["kpis"]) == 1
        assert data["kpis"][0]["abs_variation"] == pytest.approx(0.3)
        assert data["kpis"][0]["ratio_variation"] == pytest.approx(0.6)


class TestLivingLabFromJsonFile:
    """Test from_json_file class method."""
    
    def test_from_json_file_method_exists(self):
        """Test that from_json_file class method exists."""
        assert hasattr(LivingLab, 'from_json_file')
        assert callable(LivingLab.from_json_file)
