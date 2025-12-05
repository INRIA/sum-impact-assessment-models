"""
Unit tests for KpiMeasuresAnalysisJob.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.sum_impact_assessment.jobs.kpi_measures_analysis_job import KpiMeasuresAnalysisJob
from src.sum_impact_assessment.schemas.job import JobStatusEnum
from src.sum_impact_assessment.schemas.core import KPI, Measure, KPIGroup, LivingLab, KPILivingLabResult
from src.sum_impact_assessment.schemas.impact_analysis import KPIGroupImpactOutput


class TestKpiMeasuresAnalysisJob:
    """Test suite for KpiMeasuresAnalysisJob."""

    @patch("src.sum_impact_assessment.jobs.kpi_measures_analysis_job.KPIImpactAnalyzer")
    # @patch("src.sum_impact_assessment.jobs.kpi_measures_analysis_job.AnalysisDataTransformer")
    @patch("src.sum_impact_assessment.jobs.kpi_measures_analysis_job.AnalysisDataRepository")
    @patch("src.sum_impact_assessment.jobs.kpi_measures_analysis_job.JobRepository")
    def test_job_runs_successfully(
        self,
        mock_job_repo_class,
        mock_analysis_repo_class,
        # mock_transformer_class,
        mock_analyzer_class
    ):
        """Test that the job executes successfully and updates status correctly."""
        # Setup mocks
        mock_db = Mock()
        job_id = "test-job-123"

        # Mock JobRepository
        mock_job_repo = Mock()
        mock_job_repo_class.return_value = mock_job_repo

        # Mock AnalysisDataRepository
        mock_analysis_repo = Mock()
        mock_analysis_repo.get_kpi_groups.return_value = []
        mock_analysis_repo.get_kpi_definitions.return_value = []
        mock_analysis_repo.get_measures.return_value = []
        mock_analysis_repo.get_living_lab_measures.return_value = []
        mock_analysis_repo.get_living_lab_kpi_results.return_value = []
        mock_analysis_repo.get_living_labs.return_value = []
        mock_analysis_repo_class.return_value = mock_analysis_repo

        # Mock KPIImpactAnalyzer
        mock_analyzer = Mock()
        mock_result = Mock(spec=KPIGroupImpactOutput)
        mock_analyzer.run_analysis.return_value = [mock_result]
        mock_analyzer_class.return_value = mock_analyzer

        # Run the job
        KpiMeasuresAnalysisJob.run(job_id, mock_db)

        # Verify job status updates
        assert mock_job_repo.update_job_status.call_count == 2

        # Verify STARTED status update
        first_call = mock_job_repo.update_job_status.call_args_list[0]
        assert first_call[1]["job_id"] == job_id
        assert first_call[1]["status"] == JobStatusEnum.STARTED
        assert "started_at" in first_call[1]

        # Verify SUCCESS status update
        second_call = mock_job_repo.update_job_status.call_args_list[1]
        assert second_call[1]["job_id"] == job_id
        assert second_call[1]["status"] == JobStatusEnum.SUCCESS
        assert "completed_at" in second_call[1]
        assert "Analysis completed successfully" in second_call[1]["message"]

        # Verify repository methods were called
        mock_analysis_repo.get_kpi_definitions.assert_called_once()
        mock_analysis_repo.get_measures.assert_called_once()
        mock_analysis_repo.get_kpi_groups.assert_called_once()
        mock_analysis_repo.get_living_lab_measures.assert_called_once()
        mock_analysis_repo.get_living_lab_kpi_results.assert_called_once()
        mock_analysis_repo.get_living_labs.assert_called_once()

        # run analysis was not called since no kpi groups
        mock_analyzer.run_analysis_group.assert_not_called()

    @patch("src.sum_impact_assessment.jobs.kpi_measures_analysis_job.AnalysisDataRepository")
    @patch("src.sum_impact_assessment.jobs.kpi_measures_analysis_job.JobRepository")
    def test_job_handles_database_error(
        self,
        mock_job_repo_class,
        mock_analysis_repo_class
    ):
        """Test that the job handles database errors and updates status to FAILURE."""
        # Setup mocks
        mock_db = Mock()
        job_id = "test-job-456"

        # Mock JobRepository
        mock_job_repo = Mock()
        mock_job_repo_class.return_value = mock_job_repo

        # Mock AnalysisDataRepository to raise an exception
        mock_analysis_repo = Mock()
        mock_analysis_repo.get_kpi_definitions.side_effect = Exception(
            "Database connection error")
        mock_analysis_repo_class.return_value = mock_analysis_repo

        # Run the job
        KpiMeasuresAnalysisJob.run(job_id, mock_db)

        # Verify job status updates
        assert mock_job_repo.update_job_status.call_count == 2

        # Verify STARTED status update
        first_call = mock_job_repo.update_job_status.call_args_list[0]
        assert first_call[1]["status"] == JobStatusEnum.STARTED

        # Verify FAILURE status update
        second_call = mock_job_repo.update_job_status.call_args_list[1]
        assert second_call[1]["job_id"] == job_id
        assert second_call[1]["status"] == JobStatusEnum.FAILURE
        assert "Database connection error" in second_call[1]["message"]
        assert "completed_at" in second_call[1]
