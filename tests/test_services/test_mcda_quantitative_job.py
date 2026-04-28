"""
Unit tests for McdaQuantitativeJob helper methods.
"""
import pytest
from unittest.mock import patch, Mock
from sum_impact_assessment.services.mcda_quantitative_job import McdaQuantitativeJob
from src.sum_impact_assessment.schemas.core import Measure
from src.sum_impact_assessment.schemas.mcda import Alternative, Goal


class TestGetWeightByGoal:
    """Test suite for _get_weight_by_goal static method."""

    def test_returns_weight_when_goal_exists_in_weights(self):
        """Test that the method returns the correct weight when goal exists."""
        goal_name = "Sustainability"
        goal_weights = {"Sustainability": 0.4,
                        "Safety": 0.3, "Efficiency": 0.3}
        default_weight = 0.25

        result = McdaQuantitativeJob._get_weight_by_goal(
            goal_name, goal_weights, default_weight)

        assert result == 0.4

    def test_returns_default_weight_when_goal_not_in_weights(self):
        """Test that the method returns default weight when goal doesn't exist."""
        goal_name = "NonExistent"
        goal_weights = {"Sustainability": 0.4,
                        "Safety": 0.3, "Efficiency": 0.3}
        default_weight = 0.25

        result = McdaQuantitativeJob._get_weight_by_goal(
            goal_name, goal_weights, default_weight)

        assert result == 0.25

    def test_returns_default_weight_when_goal_weights_is_none(self):
        """Test that the method returns default weight when goal_weights is None."""
        goal_name = "Sustainability"
        goal_weights = None
        default_weight = 0.33

        result = McdaQuantitativeJob._get_weight_by_goal(
            goal_name, goal_weights, default_weight)

        assert result == 0.33

    def test_returns_default_weight_when_goal_weights_is_empty(self):
        """Test that the method returns default weight when goal_weights is empty."""
        goal_name = "Sustainability"
        goal_weights = {}
        default_weight = 0.5

        result = McdaQuantitativeJob._get_weight_by_goal(
            goal_name, goal_weights, default_weight)

        assert result == 0.5


class TestBuildGoalValuesByMeasure:
    """Test suite for _build_goal_values_by_measure static method."""

    def test_builds_values_for_single_goal(self):
        """Test building goal values for a measure with one goal."""
        measure = Measure(id="M1", name="Measure 1")
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {
                    'measure_coefficients': [
                        {'id': 'M1', 'coefficient': 0.75},
                        {'id': 'M2', 'coefficient': 0.50}
                    ]
                }
            }
        ]

        result = McdaQuantitativeJob._build_goal_values_by_measure(
            measure, kpi_impact_results)

        assert result == {'Sustainability': 0.75}

    def test_builds_values_for_multiple_goals(self):
        """Test building goal values for a measure with multiple goals."""
        measure = Measure(id="M2", name="Measure 2")
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {
                    'measure_coefficients': [
                        {'id': 'M1', 'coefficient': 0.75},
                        {'id': 'M2', 'coefficient': 0.50}
                    ]
                }
            },
            {
                'group_name': 'Safety',
                'results': {
                    'measure_coefficients': [
                        {'id': 'M1', 'coefficient': 0.60},
                        {'id': 'M2', 'coefficient': 0.80}
                    ]
                }
            }
        ]

        result = McdaQuantitativeJob._build_goal_values_by_measure(
            measure, kpi_impact_results)

        assert result == {'Sustainability': 0.50, 'Safety': 0.80}

    def test_returns_zero_when_measure_not_found(self):
        """Test that zero is returned when measure is not in coefficients."""
        measure = Measure(id="M3", name="Measure 3")
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {
                    'measure_coefficients': [
                        {'id': 'M1', 'coefficient': 0.75},
                        {'id': 'M2', 'coefficient': 0.50}
                    ]
                }
            }
        ]

        result = McdaQuantitativeJob._build_goal_values_by_measure(
            measure, kpi_impact_results)

        assert result == {'Sustainability': 0.0}

    def test_handles_empty_kpi_impact_results(self):
        """Test that an empty dict is returned for empty results."""
        measure = Measure(id="M1", name="Measure 1")
        kpi_impact_results = []

        result = McdaQuantitativeJob._build_goal_values_by_measure(
            measure, kpi_impact_results)

        assert result == {}


class TestGetMinMaxValuesPerGoal:
    """Test suite for _get_min_max_values_per_goal static method."""

    def test_calculates_min_max_correctly(self):
        """Test that min and max values are calculated correctly."""
        goal_name = "Sustainability"
        alternatives = [
            Alternative(name="Alt1", values={
                        "Sustainability": 0.5, "Safety": 0.3}),
            Alternative(name="Alt2", values={
                        "Sustainability": 0.8, "Safety": 0.6}),
            Alternative(name="Alt3", values={
                        "Sustainability": 0.2, "Safety": 0.9})
        ]

        min_val, max_val = McdaQuantitativeJob._get_min_max_values_per_goal(
            goal_name, alternatives)

        assert min_val == 0.2
        assert max_val == 0.8

    def test_returns_none_when_goal_not_in_alternatives(self):
        """Test that None is returned when goal doesn't exist in alternatives."""
        goal_name = "NonExistent"
        alternatives = [
            Alternative(name="Alt1", values={"Sustainability": 0.5}),
            Alternative(name="Alt2", values={"Sustainability": 0.8})
        ]

        min_val, max_val = McdaQuantitativeJob._get_min_max_values_per_goal(
            goal_name, alternatives)

        assert min_val is None
        assert max_val is None

    def test_handles_empty_alternatives_list(self):
        """Test that None is returned for empty alternatives list."""
        goal_name = "Sustainability"
        alternatives = []

        min_val, max_val = McdaQuantitativeJob._get_min_max_values_per_goal(
            goal_name, alternatives)

        assert min_val is None
        assert max_val is None

    def test_handles_single_alternative(self):
        """Test that same min and max are returned for single alternative."""
        goal_name = "Sustainability"
        alternatives = [
            Alternative(name="Alt1", values={"Sustainability": 0.7})
        ]

        min_val, max_val = McdaQuantitativeJob._get_min_max_values_per_goal(
            goal_name, alternatives)

        assert min_val == 0.7
        assert max_val == 0.7

    def test_ignores_none_values(self):
        """Test that None values are ignored in calculation."""
        goal_name = "Sustainability"
        alternatives = [
            Alternative(name="Alt1", values={"Sustainability": 0.5}),
            # Missing Sustainability
            Alternative(name="Alt2", values={"Safety": 0.8}),
            Alternative(name="Alt3", values={"Sustainability": 0.9})
        ]

        min_val, max_val = McdaQuantitativeJob._get_min_max_values_per_goal(
            goal_name, alternatives)

        assert min_val == 0.5
        assert max_val == 0.9


class TestBuildAlternatives:
    """Test suite for build_alternatives static method."""

    def test_builds_alternatives_from_measures(self):
        """Test that alternatives are correctly built from measures."""
        measures = [
            Measure(id="M1", name="Measure 1"),
            Measure(id="M2", name="Measure 2")
        ]
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {
                    'measure_coefficients': [
                        {'id': 'M1', 'coefficient': 0.75},
                        {'id': 'M2', 'coefficient': 0.50}
                    ]
                }
            },
            {
                'group_name': 'Safety',
                'results': {
                    'measure_coefficients': [
                        {'id': 'M1', 'coefficient': 0.60},
                        {'id': 'M2', 'coefficient': 0.80}
                    ]
                }
            }
        ]

        result = McdaQuantitativeJob.build_alternatives(
            measures, kpi_impact_results)

        assert len(result) == 2
        assert result[0].name == "Measure 1"
        assert result[0].values == {'Sustainability': 0.75, 'Safety': 0.60}
        assert result[1].name == "Measure 2"
        assert result[1].values == {'Sustainability': 0.50, 'Safety': 0.80}

    def test_handles_empty_measures_list(self):
        """Test that empty list is returned for empty measures."""
        measures = []
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            }
        ]

        result = McdaQuantitativeJob.build_alternatives(
            measures, kpi_impact_results)

        assert result == []


class TestBuildGoals:
    """Test suite for build_goals static method."""

    def test_builds_goals_with_perspective_weights(self):
        """Test that goals are built correctly with perspective weights."""
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Safety',
                'results': {'measure_coefficients': []}
            }
        ]
        alternatives = [
            Alternative(name="Alt1", values={
                        "Sustainability": 0.5, "Safety": 0.3}),
            Alternative(name="Alt2", values={
                        "Sustainability": 0.8, "Safety": 0.6})
        ]
        goal_weights = {"Sustainability": 0.6, "Safety": 0.4}

        result = McdaQuantitativeJob.build_goals(
            kpi_impact_results, alternatives, goal_weights)

        assert len(result) == 2
        assert result[0].name == "Sustainability"
        assert result[0].weight == 0.6
        assert result[0].Q == 0  # min value, changed to 0 after MCDA review
        # max - min (0.8 - 0.5), using approximate comparison
        assert abs(result[0].P - 0.3) < 0.001
        assert result[1].name == "Safety"
        assert result[1].weight == 0.4

    def test_builds_goals_with_equal_weights(self):
        """Test that goals are built with equal weights when no weights provided."""
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Safety',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Efficiency',
                'results': {'measure_coefficients': []}
            }
        ]
        alternatives = [
            Alternative(name="Alt1", values={
                        "Sustainability": 0.5, "Safety": 0.3, "Efficiency": 0.7}),
            Alternative(name="Alt2", values={
                        "Sustainability": 0.8, "Safety": 0.6, "Efficiency": 0.9})
        ]

        result = McdaQuantitativeJob.build_goals(
            kpi_impact_results, alternatives, None)

        assert len(result) == 3
        expected_weight = 1.0 / 3
        assert abs(result[0].weight - expected_weight) < 0.001
        assert abs(result[1].weight - expected_weight) < 0.001
        assert abs(result[2].weight - expected_weight) < 0.001

    def test_skips_goals_with_missing_min_max_values(self):
        """Test that goals with missing min/max values are skipped."""
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Safety',
                'results': {'measure_coefficients': []}
            }
        ]
        alternatives = [
            Alternative(name="Alt1", values={"Sustainability": 0.5}),
            Alternative(name="Alt2", values={"Sustainability": 0.8})
            # Note: Safety values are missing
        ]

        result = McdaQuantitativeJob.build_goals(
            kpi_impact_results, alternatives, None)

        # Only Sustainability should be included
        assert len(result) == 1
        assert result[0].name == "Sustainability"

    def test_goal_attributes_are_correct(self):
        """Test that goal attributes are set correctly."""
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            }
        ]
        alternatives = [
            Alternative(name="Alt1", values={"Sustainability": 0.2}),
            Alternative(name="Alt2", values={"Sustainability": 0.9})
        ]

        result = McdaQuantitativeJob.build_goals(
            kpi_impact_results, alternatives, None)

        assert len(result) == 1
        goal = result[0]
        assert goal.name == "Sustainability"
        assert goal.direction == "max"
        assert goal.Q == 0
        assert goal.S == 0
        assert goal.P == 0.7  # 0.9 - 0.2
        assert goal.F == 't3'

    def test_normalizes_weights_after_skipping_goals_with_missing_values(self):
        """Surviving goals should be normalized to sum to 1.0 after filtering."""
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Safety',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Efficiency',
                'results': {'measure_coefficients': []}
            }
        ]
        alternatives = [
            Alternative(name="Alt1", values={
                        "Sustainability": 0.5, "Safety": 0.3}),
            Alternative(name="Alt2", values={
                        "Sustainability": 0.8, "Safety": 0.6})
            # Efficiency is missing in all alternatives and will be skipped.
        ]
        goal_weights = {
            "Sustainability": 0.6,
            "Safety": 0.3,
            "Efficiency": 0.1
        }

        result = McdaQuantitativeJob.build_goals(
            kpi_impact_results, alternatives, goal_weights)

        assert len(result) == 2
        weights_by_goal = {goal.name: goal.weight for goal in result}
        assert sum(weights_by_goal.values()) == pytest.approx(1.0)
        assert weights_by_goal["Sustainability"] == pytest.approx(2.0 / 3.0)
        assert weights_by_goal["Safety"] == pytest.approx(1.0 / 3.0)

    def test_normalizes_default_weights_when_some_goals_are_skipped(self):
        """Default weights should also be normalized against kept goals only."""
        kpi_impact_results = [
            {
                'group_name': 'Sustainability',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Safety',
                'results': {'measure_coefficients': []}
            },
            {
                'group_name': 'Efficiency',
                'results': {'measure_coefficients': []}
            }
        ]
        alternatives = [
            Alternative(name="Alt1", values={
                        "Sustainability": 0.5, "Safety": 0.3}),
            Alternative(name="Alt2", values={
                        "Sustainability": 0.8, "Safety": 0.6})
            # Efficiency is missing in all alternatives and will be skipped.
        ]

        result = McdaQuantitativeJob.build_goals(
            kpi_impact_results, alternatives, None)

        assert len(result) == 2
        weights_by_goal = {goal.name: goal.weight for goal in result}
        assert sum(weights_by_goal.values()) == pytest.approx(1.0)
        assert weights_by_goal["Sustainability"] == pytest.approx(0.5)
        assert weights_by_goal["Safety"] == pytest.approx(0.5)


class TestGetGoalWeights:
    """Test suite for get_goal_weights static method."""

    def test_returns_weights_for_valid_perspective(self):
        """Test that weights are returned for a valid perspective."""
        perspective = "regulatory"
        expected_weights = {
            "Improve Accessibility": 0.146747967,
            "Improve Mobility Service": 0.143144298,
            "Improve Multimodality": 0.117543175,
            "Noise Hinderance": 0.074956122,
            "Improve Public Transport": 0.162734706,
            "Reduction of Congestion": 0.122695883,
            "Reduction of Emission": 0.115356371,
            "Improve Safety": 0.116821478
        }

        result = McdaQuantitativeJob.get_goal_weights(perspective)

        assert result == expected_weights

    def test_returns_none_when_perspective_loading_fails(self):
        """Test that None is returned when loading perspective fails."""
        perspective = "invalid_perspective_name"

        result = McdaQuantitativeJob.get_goal_weights(perspective)

        assert result is None

    def test_returns_none_when_perspective_is_none(self):
        """Test that None is returned when perspective is None."""
        result = McdaQuantitativeJob.get_goal_weights(None)

        assert result is None

    def test_returns_none_when_perspective_is_empty_string(self):
        """Test that None is returned when perspective is empty string."""
        result = McdaQuantitativeJob.get_goal_weights("")

        assert result is None


class TestRunUserPersonalized:
    """Integration-style tests for user-personalized quantitative runs."""

    @patch('sum_impact_assessment.services.mcda_quantitative_job.PrometheeGaiaAnalyzer')
    @patch('sum_impact_assessment.services.mcda_quantitative_job.JobRepository')
    @patch('sum_impact_assessment.services.mcda_quantitative_job.KpiMeasuresAnalysisJob.run_kpi_impact_analysis')
    def test_run_uses_user_personalized_goal_weights_and_saves_name(
        self,
        mock_run_kpi_impact_analysis,
        mock_job_repository,
        mock_analyzer_class
    ):
        input_data_snapshot = {
            "measures": [
                {"id": "M1", "name": "Measure 1"},
                {"id": "M2", "name": "Measure 2"}
            ]
        }
        kpi_impact_results = [
            {
                "group_name": "Improve Accessibility",
                "results": {
                    "measure_coefficients": [
                        {"id": "M1", "coefficient": 0.8},
                        {"id": "M2", "coefficient": 0.5}
                    ]
                }
            },
            {
                "group_name": "Improve Safety",
                "results": {
                    "measure_coefficients": [
                        {"id": "M1", "coefficient": 0.6},
                        {"id": "M2", "coefficient": 0.4}
                    ]
                }
            }
        ]
        mock_run_kpi_impact_analysis.return_value = (
            input_data_snapshot,
            kpi_impact_results,
            []
        )

        repo_instance = mock_job_repository.return_value

        mock_mcda_output = Mock()
        mock_mcda_output.gaia_quality = 84.0
        mock_mcda_output.ranking = ["a1"]
        mock_mcda_output.alternative_labels = {"a1": "Measure 1"}
        mock_mcda_output.model_dump.return_value = {
            "ranking": ["a1"],
            "gaia_quality": 84.0
        }

        analyzer_instance = mock_analyzer_class.return_value
        analyzer_instance.run_analysis.return_value = mock_mcda_output

        McdaQuantitativeJob.run(
            job_id="job-personalized-quant",
            db=Mock(),
            params={
                "kpi_group_type": "MCDA_GOALS",
                "perspective": "user_personalized",
                "name": "Custom quantitative analysis",
                "goals_weights": {
                    "Improve Accessibility": 3.0,
                    "Improve Safety": 1.0
                }
            }
        )

        analyzer_call_kwargs = mock_analyzer_class.call_args.kwargs
        goals = analyzer_call_kwargs["goals"]
        goal_weights = {goal.name: goal.weight for goal in goals}

        assert goal_weights["Improve Accessibility"] == 0.75
        assert goal_weights["Improve Safety"] == 0.25

        second_call_kwargs = repo_instance.update_job_data.call_args_list[1].kwargs
        assert second_call_kwargs["input_data"]["name"] == "Custom quantitative analysis"
        snapshot_weights = {
            g["name"]: g["weight"] for g in second_call_kwargs["input_data"]["goals"]
        }
        assert snapshot_weights["Improve Accessibility"] == 0.75
        assert snapshot_weights["Improve Safety"] == 0.25
