"""
Integration tests for McdaQualitativeJob.
"""
import pytest
from unittest.mock import Mock, patch

from sum_impact_assessment.services.mcda_qualitative_job import McdaQualitativeJob


MOCK_MCDA_CONFIG = {
    "perspectives": {
        "labels": {
            "regulatory": "Regulatory Authorities"
        },
        "weights": {
            "regulatory": {
                "Improve Accessibility": 0.6,
                "Improve Safety": 0.4
            }
        }
    },
    "business_activities": {
        "labels": {
            "BA1": "Integrated Mobility Service Platform (MaaS)",
            "BA2": "Demand-Responsive and On-Demand Mobility"
        },
        "goals_score": {
            "BA1": {
                "Improve Accessibility": 3.83,
                "Improve Safety": 2.98
            },
            "BA2": {
                "Improve Accessibility": 3.94,
                "Improve Safety": 3.42
            }
        }
    }
}


class TestBuildAlternatives:
    """Test suite for build_alternatives static method."""

    def test_builds_alternatives_with_complete_labels(self):
        """Alternatives should use business activity labels and lower-case goal keys."""
        alternatives = McdaQualitativeJob.build_alternatives(MOCK_MCDA_CONFIG)

        assert len(alternatives) == 2
        assert alternatives[0].name == "Integrated Mobility Service Platform (MaaS)"
        assert alternatives[0].values == {
            "Improve Accessibility": 3.83,
            "Improve Safety": 2.98
        }
        assert alternatives[1].name == "Demand-Responsive and On-Demand Mobility"


class TestBuildGoals:
    """Test suite for build_goals static method."""

    def test_builds_goals_with_normalized_weights_and_thresholds(self):
        """Goal weights should match after lower-case normalization."""
        alternatives = McdaQualitativeJob.build_alternatives(MOCK_MCDA_CONFIG)
        goal_weights = {
            "Improve Accessibility": 0.6,
            "Improve Safety": 0.4
        }

        goals = McdaQualitativeJob.build_goals(alternatives, goal_weights)

        assert len(goals) == 2
        assert goals[0].name == "Improve Accessibility"
        assert goals[0].weight == 0.6
        assert goals[0].Q == 0
        assert goals[0].S == 0
        assert abs(goals[0].P - 0.11) < 0.001
        assert goals[0].F == "t3"
        assert goals[1].name == "Improve Safety"
        assert goals[1].weight == 0.4

    def test_normalizes_weights_when_perspective_has_unused_goals(self):
        """Only considered goals should be normalized to sum to 1.0."""
        alternatives = McdaQualitativeJob.build_alternatives(MOCK_MCDA_CONFIG)
        goal_weights = {
            "Improve Accessibility": 0.6,
            "Improve Safety": 0.3,
            "Unused Goal": 0.1
        }

        goals = McdaQualitativeJob.build_goals(alternatives, goal_weights)

        assert len(goals) == 2
        weights_by_goal = {goal.name: goal.weight for goal in goals}
        assert sum(weights_by_goal.values()) == pytest.approx(1.0)
        assert weights_by_goal["Improve Accessibility"] == pytest.approx(2.0 / 3.0)
        assert weights_by_goal["Improve Safety"] == pytest.approx(1.0 / 3.0)

    def test_normalizes_when_default_weight_is_used_for_missing_goal_weight(self):
        """Mixed configured and defaulted weights should be normalized."""
        alternatives = McdaQualitativeJob.build_alternatives(MOCK_MCDA_CONFIG)
        goal_weights = {
            "Improve Accessibility": 0.6
            # Improve Safety falls back to default 1/2 = 0.5
        }

        goals = McdaQualitativeJob.build_goals(alternatives, goal_weights)

        assert len(goals) == 2
        weights_by_goal = {goal.name: goal.weight for goal in goals}
        assert sum(weights_by_goal.values()) == pytest.approx(1.0)
        assert weights_by_goal["Improve Accessibility"] == pytest.approx(0.6 / 1.1)
        assert weights_by_goal["Improve Safety"] == pytest.approx(0.5 / 1.1)


class TestGetGoalWeights:
    """Test suite for get_goal_weights static method."""

    @patch('sum_impact_assessment.utils.data_loaders.load_mcda_config')
    def test_returns_weights_for_valid_perspective(self, mock_load_mcda_config):
        """Goal weights should be returned normalized to lower-case keys."""
        mock_load_mcda_config.return_value = MOCK_MCDA_CONFIG

        result = McdaQualitativeJob.get_goal_weights("regulatory")

        assert result == {
            "Improve Accessibility": 0.6,
            "Improve Safety": 0.4
        }

    @patch('sum_impact_assessment.utils.data_loaders.load_mcda_config')
    def test_returns_none_when_perspective_loading_fails(self, mock_load_mcda_config):
        """Invalid perspective should return None."""
        mock_load_mcda_config.return_value = MOCK_MCDA_CONFIG

        result = McdaQualitativeJob.get_goal_weights("invalid")

        assert result is None

    def test_returns_none_when_perspective_is_none(self):
        """None perspective should return None."""
        result = McdaQualitativeJob.get_goal_weights(None)

        assert result is None

    def test_returns_none_when_perspective_is_empty_string(self):
        """Empty perspective should return None."""
        result = McdaQualitativeJob.get_goal_weights("")

        assert result is None


class TestRun:
    """Integration-style tests for qualitative run method."""

    @patch('sum_impact_assessment.services.mcda_qualitative_job.PrometheeGaiaAnalyzer')
    @patch('sum_impact_assessment.services.jobs.base.JobRepository')
    @patch('sum_impact_assessment.services.mcda_qualitative_job.load_mcda_config')
    @patch('sum_impact_assessment.utils.data_loaders.load_mcda_config')
    def test_run_saves_input_output_and_uses_cached_config_once(
        self,
        mock_loader_for_weights,
        mock_loader_for_service,
        mock_job_repository,
        mock_analyzer_class
    ):
        """Run should save snapshots and load config once in service path."""
        mock_loader_for_service.return_value = MOCK_MCDA_CONFIG
        mock_loader_for_weights.return_value = MOCK_MCDA_CONFIG

        db = Mock()
        job_id = "job-123"
        perspective = "regulatory"

        repo_instance = mock_job_repository.return_value

        mock_mcda_output = Mock()
        mock_mcda_output.gaia_quality = 88.5
        mock_mcda_output.ranking = ["a1", "a2"]
        mock_mcda_output.alternative_labels = {
            "a1": "Integrated Mobility Service Platform (MaaS)",
            "a2": "Demand-Responsive and On-Demand Mobility"
        }
        mock_mcda_output.model_dump.return_value = {
            "ranking": ["a1", "a2"],
            "gaia_quality": 88.5
        }

        analyzer_instance = mock_analyzer_class.return_value
        analyzer_instance.run_analysis.return_value = mock_mcda_output

        McdaQualitativeJob.run(job_id=job_id, db=db, params={
                               "perspective": perspective})

        # STARTED + SUCCESS status updates
        assert repo_instance.update_job_status.call_count == 2

        # input data first save, input data with MCDA snapshots, and output data
        assert repo_instance.update_job_data.call_count == 3

        # Service loader is used once and reused (single-load behavior)
        mock_loader_for_service.assert_called_once()

        # Verify analyzer invoked
        mock_analyzer_class.assert_called_once()
        analyzer_instance.run_analysis.assert_called_once_with(
            run_visualizations=False)

        # Validate first input snapshot has qualitative source fields
        first_call_kwargs = repo_instance.update_job_data.call_args_list[0].kwargs
        assert "input_data" in first_call_kwargs
        assert "business_activities" in first_call_kwargs["input_data"]

        # Validate second input snapshot has MCDA execution input format
        second_call_kwargs = repo_instance.update_job_data.call_args_list[1].kwargs
        assert "input_data" in second_call_kwargs
        assert second_call_kwargs["input_data"]["perspective"] == "regulatory"
        assert "goals" in second_call_kwargs["input_data"]
        assert "alternatives" in second_call_kwargs["input_data"]

        # Validate output snapshot format matches quantitative job shape
        third_call_kwargs = repo_instance.update_job_data.call_args_list[2].kwargs
        assert "output_data" in third_call_kwargs
        assert "kpi_impact_results" in third_call_kwargs["output_data"]
        assert "kpi_impact_errors" in third_call_kwargs["output_data"]
        assert "mcda_results" in third_call_kwargs["output_data"]


class TestRunUserPersonalized:
    """Integration-style tests for user-personalized qualitative runs."""

    @patch('sum_impact_assessment.services.mcda_qualitative_job.PrometheeGaiaAnalyzer')
    @patch('sum_impact_assessment.services.jobs.base.JobRepository')
    @patch('sum_impact_assessment.services.mcda_qualitative_job.load_mcda_config')
    def test_run_uses_user_personalized_goal_weights_and_saves_name(
        self,
        mock_loader_for_service,
        mock_job_repository,
        mock_analyzer_class
    ):
        mock_loader_for_service.return_value = MOCK_MCDA_CONFIG

        db = Mock()
        job_id = "job-personalized-qual"
        params = {
            "perspective": "user_personalized",
            "name": "My personalized run",
            "goals_weights": {
                "Improve Accessibility": 2.0,
                "Improve Safety": 1.0
            }
        }

        repo_instance = mock_job_repository.return_value

        mock_mcda_output = Mock()
        mock_mcda_output.gaia_quality = 90.0
        mock_mcda_output.ranking = ["a1"]
        mock_mcda_output.alternative_labels = {
            "a1": "Integrated Mobility Service Platform (MaaS)"
        }
        mock_mcda_output.model_dump.return_value = {
            "ranking": ["a1"],
            "gaia_quality": 90.0
        }

        analyzer_instance = mock_analyzer_class.return_value
        analyzer_instance.run_analysis.return_value = mock_mcda_output

        McdaQualitativeJob.run(job_id=job_id, db=db, params=params)

        # Analyzer should be initialized with goals using normalized personalized weights.
        analyzer_call_kwargs = mock_analyzer_class.call_args.kwargs
        goals = analyzer_call_kwargs["goals"]
        goal_weights = {goal.name: goal.weight for goal in goals}

        assert goal_weights["Improve Accessibility"] == 2.0 / 3.0
        assert goal_weights["Improve Safety"] == 1.0 / 3.0

        # Second input snapshot should contain MCDA input including goals and custom name.
        second_call_kwargs = repo_instance.update_job_data.call_args_list[1].kwargs
        assert second_call_kwargs["input_data"]["name"] == "My personalized run"
        snapshot_weights = {
            g["name"]: g["weight"] for g in second_call_kwargs["input_data"]["goals"]
        }
        assert snapshot_weights["Improve Accessibility"] == 2.0 / 3.0
        assert snapshot_weights["Improve Safety"] == 1.0 / 3.0
