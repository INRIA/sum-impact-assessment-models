"""Tests for data loading utility functions."""
import pytest
import json
from sum_impact_assessment.schemas.core import KPI, LivingLab, Measure, KPIGroup, KPIValueType
from sum_impact_assessment.utils.tools import (
    load_kpis_from_file,
    load_measures_from_file,
    load_kpi_groups_from_file,
    load_living_labs_from_file
)


class TestLoadKpisFromFile:
    """Test load_kpis_from_file function."""

    def test_load_valid_kpis(self, tmp_path):
        """Test loading valid KPI definitions from file."""
        kpis_data = [
            {
                "id": "kpi_1",
                "name": "Test KPI 1",
                "progression_target": 1,
                "value_type": "percentage",
                "value_min": 0.0,
                "value_max": 1.0
            },
            {
                "id": "kpi_2",
                "name": "Test KPI 2",
                "progression_target": 0,
                "value_type": "ratio",
                "value_min": None,
                "value_max": None
            }
        ]

        file_path = tmp_path / "test_kpis.json"
        with open(file_path, "w") as f:
            json.dump(kpis_data, f)

        kpis = load_kpis_from_file(str(file_path))

        assert len(kpis) == 2
        assert all(isinstance(kpi, KPI) for kpi in kpis)
        assert kpis[0].id == "kpi_1"
        assert kpis[0].name == "Test KPI 1"
        assert kpis[0].progression_target == 1
        assert kpis[0].value_type == KPIValueType.percentage
        assert kpis[1].id == "kpi_2"
        assert kpis[1].progression_target == 0

    def test_load_kpis_with_all_value_types(self, tmp_path):
        """Test loading KPIs with all value types."""
        kpis_data = [
            {"id": "kpi_1", "name": "Percentage KPI",
                "progression_target": 1, "value_type": "percentage"},
            {"id": "kpi_2", "name": "Ratio KPI",
                "progression_target": 1, "value_type": "ratio"},
            {"id": "kpi_3", "name": "Custom Unit KPI",
                "progression_target": 1, "value_type": "custom_unit"},
            {"id": "kpi_4", "name": "Score KPI",
                "progression_target": 1, "value_type": "score"}
        ]

        file_path = tmp_path / "test_kpis.json"
        with open(file_path, "w") as f:
            json.dump(kpis_data, f)

        kpis = load_kpis_from_file(str(file_path))

        assert len(kpis) == 4
        assert kpis[0].value_type == KPIValueType.percentage
        assert kpis[1].value_type == KPIValueType.ratio
        assert kpis[2].value_type == KPIValueType.custom_unit
        assert kpis[3].value_type == KPIValueType.score

    def test_load_empty_kpis_file(self, tmp_path):
        """Test loading empty KPI list."""
        file_path = tmp_path / "empty_kpis.json"
        with open(file_path, "w") as f:
            json.dump([], f)

        kpis = load_kpis_from_file(str(file_path))

        assert len(kpis) == 0
        assert isinstance(kpis, list)

    def test_load_kpis_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_kpis_from_file("/nonexistent/path/kpis.json")

    def test_load_kpis_invalid_json(self, tmp_path):
        """Test error with invalid JSON."""
        file_path = tmp_path / "invalid.json"
        with open(file_path, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_kpis_from_file(str(file_path))


class TestLoadMeasuresFromFile:
    """Test load_measures_from_file function."""

    def test_load_valid_measures(self, tmp_path):
        """Test loading valid measures from file."""
        measures_data = [
            {"id": "measure_001", "name": "Congestion charges"},
            {"id": "measure_002", "name": "Parking charges"},
            {"id": "measure_003", "name": "Road pricing"}
        ]

        file_path = tmp_path / "test_measures.json"
        with open(file_path, "w") as f:
            json.dump(measures_data, f)

        measures = load_measures_from_file(str(file_path))

        assert len(measures) == 3
        assert all(isinstance(m, Measure) for m in measures)
        assert measures[0].id == "measure_001"
        assert measures[0].name == "Congestion charges"
        assert measures[2].id == "measure_003"
        assert measures[2].name == "Road pricing"

    def test_load_empty_measures_file(self, tmp_path):
        """Test loading empty measures list."""
        file_path = tmp_path / "empty_measures.json"
        with open(file_path, "w") as f:
            json.dump([], f)

        measures = load_measures_from_file(str(file_path))

        assert len(measures) == 0
        assert isinstance(measures, list)

    def test_load_measures_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_measures_from_file("/nonexistent/path/measures.json")


class TestLoadKpiGroupsFromFile:
    """Test load_kpi_groups_from_file function."""

    def test_load_valid_kpi_groups(self, tmp_path, sample_kpi_definitions):
        """Test loading valid KPI groups and populating kpis field."""
        groups_data = [
            {
                "id": "group_1",
                "name": "Policies",
                "kpi_ids": ["kpi_1", "kpi_2"]
            },
            {
                "id": "group_2",
                "name": "Modal Split",
                "kpi_ids": ["kpi_2", "kpi_3"]
            }
        ]

        file_path = tmp_path / "test_groups.json"
        with open(file_path, "w") as f:
            json.dump(groups_data, f)

        groups = load_kpi_groups_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(groups) == 2
        assert all(isinstance(g, KPIGroup) for g in groups)

        # Check first group
        assert groups[0].id == "group_1"
        assert groups[0].name == "Policies"
        assert groups[0].kpi_ids == ["kpi_1", "kpi_2"]
        assert groups[0].kpis is not None
        assert len(groups[0].kpis) == 2
        assert all(isinstance(kpi, KPI) for kpi in groups[0].kpis)
        assert groups[0].kpis[0].id == "kpi_1"
        assert groups[0].kpis[1].id == "kpi_2"

    def test_kpi_groups_with_missing_kpi_ids(self, tmp_path, sample_kpi_definitions):
        """Test loading groups when some KPI IDs don't exist in definitions."""
        groups_data = [
            {
                "id": "group_1",
                "name": "Test Group",
                # kpi_999 doesn't exist
                "kpi_ids": ["kpi_1", "kpi_999", "kpi_2"]
            }
        ]

        file_path = tmp_path / "test_groups.json"
        with open(file_path, "w") as f:
            json.dump(groups_data, f)

        groups = load_kpi_groups_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(groups) == 1
        # Should only include KPIs that exist in definitions
        assert len(groups[0].kpis) == 2
        assert groups[0].kpis[0].id == "kpi_1"
        assert groups[0].kpis[1].id == "kpi_2"

    def test_kpi_groups_with_empty_kpi_ids(self, tmp_path, sample_kpi_definitions):
        """Test loading groups with empty kpi_ids list."""
        groups_data = [
            {
                "id": "group_1",
                "name": "Empty Group",
                "kpi_ids": []
            }
        ]

        file_path = tmp_path / "test_groups.json"
        with open(file_path, "w") as f:
            json.dump(groups_data, f)

        groups = load_kpi_groups_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(groups) == 1
        assert groups[0].kpi_ids == []
        # Should be None when no KPIs are found
        assert groups[0].kpis is None

    def test_kpi_groups_with_no_matching_kpis(self, tmp_path, sample_kpi_definitions):
        """Test loading groups when no KPI IDs match definitions."""
        groups_data = [
            {
                "id": "group_1",
                "name": "Test Group",
                "kpi_ids": ["kpi_999", "kpi_888"]
            }
        ]

        file_path = tmp_path / "test_groups.json"
        with open(file_path, "w") as f:
            json.dump(groups_data, f)

        groups = load_kpi_groups_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(groups) == 1
        assert groups[0].kpis is None

    def test_load_empty_groups_file(self, tmp_path, sample_kpi_definitions):
        """Test loading empty groups list."""
        file_path = tmp_path / "empty_groups.json"
        with open(file_path, "w") as f:
            json.dump([], f)

        groups = load_kpi_groups_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(groups) == 0


class TestLoadLivingLabsFromFile:
    """Test load_living_labs_from_file function."""

    def test_load_valid_living_labs(self, tmp_path, sample_kpi_definitions):
        """Test loading valid living labs with KPI merging."""
        labs_data = [
            {
                "id": "lab_munich",
                "name": "Munich",
                "kpis": [
                    {
                        "id": "kpi_1",
                        "value_before": 1.0,
                        "value_after": 0.83
                    },
                    {
                        "id": "kpi_2",
                        "value_before": 0.5,
                        "value_after": 0.4
                    }
                ],
                "measures": [
                    {"id": "measure_001", "name": "Congestion charges"}
                ]
            }
        ]

        file_path = tmp_path / "test_labs.json"
        with open(file_path, "w") as f:
            json.dump(labs_data, f)

        labs = load_living_labs_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(labs) == 1
        assert isinstance(labs[0], LivingLab)
        assert labs[0].id == "lab_munich"
        assert labs[0].name == "Munich"
        assert len(labs[0].kpis) == 2
        assert len(labs[0].measures) == 1

    def test_kpi_merging_with_definitions(self, tmp_path, sample_kpi_definitions):
        """Test that lab KPI data is merged with KPI definitions."""
        labs_data = [
            {
                "id": "lab_test",
                "name": "Test Lab",
                "kpis": [
                    {
                        "id": "kpi_1",
                        "value_before": 0.5,
                        "value_after": 0.8
                    }
                ],
                "measures": []
            }
        ]

        file_path = tmp_path / "test_labs.json"
        with open(file_path, "w") as f:
            json.dump(labs_data, f)

        labs = load_living_labs_from_file(
            str(file_path), sample_kpi_definitions)

        kpi = labs[0].kpis[0]
        # Check that definition fields are present
        assert kpi.id == "kpi_1"
        assert kpi.name == "Level of completion of SUMP measures"  # From definition
        assert kpi.progression_target == 1  # From definition
        assert kpi.value_type == KPIValueType.percentage  # From definition
        # Check that lab-specific fields are present
        assert kpi.value_before == 0.5
        assert kpi.value_after == 0.8
        assert kpi.living_lab_id == "lab_test"  # Injected during loading

    def test_living_lab_id_injection(self, tmp_path, sample_kpi_definitions):
        """Test that living_lab_id is injected into KPIs."""
        labs_data = [
            {
                "id": "lab_injection_test",
                "name": "Injection Test Lab",
                "kpis": [
                    {
                        "id": "kpi_1",
                        "value_before": 0.5,
                        "value_after": 0.8
                    }
                ],
                "measures": []
            }
        ]

        file_path = tmp_path / "test_labs.json"
        with open(file_path, "w") as f:
            json.dump(labs_data, f)

        labs = load_living_labs_from_file(
            str(file_path), sample_kpi_definitions)

        assert labs[0].kpis[0].living_lab_id == "lab_injection_test"

    def test_variations_calculated_after_loading(self, tmp_path, sample_kpi_definitions):
        """Test that variations are calculated when LivingLab is instantiated."""
        labs_data = [
            {
                "id": "lab_test",
                "name": "Test Lab",
                "kpis": [
                    {
                        "id": "kpi_1",
                        "value_before": 0.5,
                        "value_after": 0.8
                    }
                ],
                "measures": []
            }
        ]

        file_path = tmp_path / "test_labs.json"
        with open(file_path, "w") as f:
            json.dump(labs_data, f)

        labs = load_living_labs_from_file(
            str(file_path), sample_kpi_definitions)

        kpi = labs[0].kpis[0]
        # Variations should be calculated by LivingLab.__init__
        assert kpi.abs_variation is not None
        assert kpi.ratio_variation is not None
        assert kpi.abs_variation == pytest.approx(0.3)
        assert kpi.ratio_variation == pytest.approx(0.6)

    def test_kpi_without_definition(self, tmp_path, sample_kpi_definitions):
        """Test handling of KPI without matching definition."""
        labs_data = [
            {
                "id": "lab_test",
                "name": "Test Lab",
                "kpis": [
                    {
                        "id": "kpi_999",  # Doesn't exist in definitions
                        "value_before": 0.5,
                        "value_after": 0.8
                    }
                ],
                "measures": []
            }
        ]

        file_path = tmp_path / "test_labs.json"
        with open(file_path, "w") as f:
            json.dump(labs_data, f)

        # Should not raise error, but KPI won't have definition fields
        # This will likely cause validation errors since required fields are missing
        with pytest.raises(Exception):  # Will fail validation
            labs = load_living_labs_from_file(
                str(file_path), sample_kpi_definitions)

    def test_multiple_living_labs(self, tmp_path, sample_kpi_definitions):
        """Test loading multiple living labs."""
        labs_data = [
            {
                "id": "lab_1",
                "name": "Lab 1",
                "kpis": [{"id": "kpi_1", "value_before": 0.5, "value_after": 0.8}],
                "measures": []
            },
            {
                "id": "lab_2",
                "name": "Lab 2",
                "kpis": [{"id": "kpi_2", "value_before": 0.7, "value_after": 0.5}],
                "measures": []
            }
        ]

        file_path = tmp_path / "test_labs.json"
        with open(file_path, "w") as f:
            json.dump(labs_data, f)

        labs = load_living_labs_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(labs) == 2
        assert labs[0].id == "lab_1"
        assert labs[1].id == "lab_2"
        assert labs[0].kpis[0].living_lab_id == "lab_1"
        assert labs[1].kpis[0].living_lab_id == "lab_2"

    def test_load_empty_labs_file(self, tmp_path, sample_kpi_definitions):
        """Test loading empty living labs list."""
        file_path = tmp_path / "empty_labs.json"
        with open(file_path, "w") as f:
            json.dump([], f)

        labs = load_living_labs_from_file(
            str(file_path), sample_kpi_definitions)

        assert len(labs) == 0


class TestDataLoadersIntegration:
    """Test integration between data loaders."""

    def test_load_all_data_types_together(self, tmp_path):
        """Test loading all data types in a typical workflow."""
        # Create KPI definitions
        kpis_data = [
            {"id": "kpi_1", "name": "Test KPI 1",
                "progression_target": 1, "value_type": "percentage"},
            {"id": "kpi_2", "name": "Test KPI 2",
                "progression_target": 0, "value_type": "ratio"}
        ]
        kpis_file = tmp_path / "kpis.json"
        with open(kpis_file, "w") as f:
            json.dump(kpis_data, f)

        # Create measures
        measures_data = [
            {"id": "measure_001", "name": "Measure 1"}
        ]
        measures_file = tmp_path / "measures.json"
        with open(measures_file, "w") as f:
            json.dump(measures_data, f)

        # Create groups
        groups_data = [
            {"id": "group_1", "name": "Group 1", "kpi_ids": ["kpi_1", "kpi_2"]}
        ]
        groups_file = tmp_path / "groups.json"
        with open(groups_file, "w") as f:
            json.dump(groups_data, f)

        # Create living labs
        labs_data = [
            {
                "id": "lab_1",
                "name": "Lab 1",
                "kpis": [{"id": "kpi_1", "value_before": 0.5, "value_after": 0.8}],
                "measures": [{"id": "measure_001", "name": "Measure 1"}]
            }
        ]
        labs_file = tmp_path / "labs.json"
        with open(labs_file, "w") as f:
            json.dump(labs_data, f)

        # Load all data
        kpis = load_kpis_from_file(str(kpis_file))
        measures = load_measures_from_file(str(measures_file))
        groups = load_kpi_groups_from_file(str(groups_file), kpis)
        labs = load_living_labs_from_file(str(labs_file), kpis)

        # Verify integration
        assert len(kpis) == 2
        assert len(measures) == 1
        assert len(groups) == 1
        assert len(labs) == 1
        assert groups[0].kpis is not None
        assert len(groups[0].kpis) == 2
        assert labs[0].kpis[0].name == "Test KPI 1"  # Merged from definition
