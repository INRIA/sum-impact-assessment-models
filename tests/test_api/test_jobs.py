"""
Unit tests for job management API.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from datetime import datetime
from src.sum_impact_assessment.api.main import app
from sum_impact_assessment.database.models.job import JobRun
from src.sum_impact_assessment.schemas.job import JobNameEnum, JobStatusEnum


# Create test client
client = TestClient(app)


class TestJobsAPI:
    """Test suite for jobs API endpoints."""

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_job_success(self, mock_get_job_class, mock_job_repo_class):
        """Test successfully triggering a job returns 201 with job details."""
        # Setup mock job run
        mock_job_run = JobRun(
            id="test-job-id-123",
            job_name="kpi_measures_analysis",
            status=JobStatusEnum.PENDING,
            message=None,
            created_at=datetime(2025, 12, 4, 10, 0, 0),
            started_at=None,
            completed_at=None
        )

        # Setup mock repository
        mock_repo_instance = Mock()
        mock_repo_instance.create_job_run.return_value = mock_job_run
        mock_job_repo_class.return_value = mock_repo_instance

        # Setup mock job class
        mock_job_class = Mock()
        mock_get_job_class.return_value = mock_job_class

        # Make request
        response = client.post("/jobs/runs/kpi_measures_analysis")

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        assert response_data["id"] == "test-job-id-123"
        assert response_data["job_name"] == "kpi_measures_analysis"
        assert response_data["status"] == JobStatusEnum.PENDING
        assert response_data["message"] is None
        assert response_data["started_at"] is None
        assert response_data["completed_at"] is None

        # Verify repository was called correctly
        mock_repo_instance.create_job_run.assert_called_once_with(
            job_name=JobNameEnum.KPI_MEASURES_ANALYSIS)

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_job_not_found_in_registry(self, mock_get_job_class, mock_job_repo_class):
        """Test triggering a job that doesn't exist in registry returns 404."""
        # Setup mock to raise KeyError
        mock_get_job_class.side_effect = KeyError("Job not found")

        # Make request
        response = client.post("/jobs/runs/kpi_measures_analysis")

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found in registry" in response.json()["detail"]

        # Verify repository create was not called
        mock_job_repo_class.return_value.create_job_run.assert_not_called()

    def test_trigger_job_invalid_job_name(self):
        """Test triggering a job with invalid job name returns 422."""
        # Make request with invalid job name
        response = client.post("/jobs/runs/invalid_job_name")

        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_job_database_error(self, mock_get_job_class, mock_job_repo_class):
        """Test database error during job creation returns 500."""
        # Setup mock job class
        mock_job_class = Mock()
        mock_get_job_class.return_value = mock_job_class

        # Setup mock repository to raise exception
        mock_repo_instance = Mock()
        mock_repo_instance.create_job_run.side_effect = Exception(
            "Database connection error")
        mock_job_repo_class.return_value = mock_repo_instance

        # Make request
        response = client.post("/jobs/runs/kpi_measures_analysis")

        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error triggering job" in response.json()["detail"]

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_job_with_params(self, mock_get_job_class, mock_job_repo_class):
        """Test triggering a job with params in request body."""
        # Setup mock job run
        mock_job_run = JobRun(
            id="test-job-id-456",
            job_name="mcda_analysis",
            status=JobStatusEnum.PENDING,
            message=None,
            created_at=datetime(2025, 12, 4, 10, 0, 0),
            started_at=None,
            completed_at=None
        )

        # Setup mock repository
        mock_repo_instance = Mock()
        mock_repo_instance.create_job_run.return_value = mock_job_run
        mock_job_repo_class.return_value = mock_repo_instance

        # Setup mock job class
        mock_job_class = Mock()
        mock_get_job_class.return_value = mock_job_class

        # Make request with params
        response = client.post(
            "/jobs/runs/mcda_analysis",
            json={"params": {"kpi_group_type": "MCDA_GOALS"}}
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == "test-job-id-456"
        assert response_data["job_name"] == "mcda_analysis"
        assert response_data["status"] == JobStatusEnum.PENDING

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_mcda_analysis_job(self, mock_get_job_class, mock_job_repo_class):
        """Test triggering MCDA analysis job specifically."""
        # Setup mock job run
        mock_job_run = JobRun(
            id="mcda-job-id-999",
            job_name="mcda_analysis",
            status=JobStatusEnum.PENDING,
            message=None,
            created_at=datetime(2025, 12, 4, 10, 0, 0),
            started_at=None,
            completed_at=None
        )

        # Setup mock repository
        mock_repo_instance = Mock()
        mock_repo_instance.create_job_run.return_value = mock_job_run
        mock_job_repo_class.return_value = mock_repo_instance

        # Setup mock job class
        mock_job_class = Mock()
        mock_get_job_class.return_value = mock_job_class

        # Make request
        response = client.post("/jobs/runs/mcda_analysis")

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["job_name"] == "mcda_analysis"
        assert response_data["status"] == JobStatusEnum.PENDING

        # Verify repository was called with correct job name
        mock_repo_instance.create_job_run.assert_called_once_with(
            job_name=JobNameEnum.MCDA_ANALYSIS)

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_mcda_analysis_job_with_perspective(self, mock_get_job_class, mock_job_repo_class):
        """Test triggering MCDA analysis job with perspective parameter."""
        # Setup mock job run with perspective in name
        mock_job_run = JobRun(
            id="mcda-job-perspective-123",
            job_name="mcda_analysis_regulatory",
            status=JobStatusEnum.PENDING,
            message=None,
            created_at=datetime(2025, 12, 4, 10, 0, 0),
            started_at=None,
            completed_at=None
        )

        # Setup mock repository
        mock_repo_instance = Mock()
        mock_repo_instance.create_job_run.return_value = mock_job_run
        mock_job_repo_class.return_value = mock_repo_instance

        # Setup mock job class
        mock_job_class = Mock()
        mock_get_job_class.return_value = mock_job_class

        # Make request with perspective parameter
        response = client.post(
            "/jobs/runs/mcda_analysis",
            json={"params": {"perspective": "regulatory"}}
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == "mcda-job-perspective-123"
        assert response_data["job_name"] == "mcda_analysis_regulatory"
        assert response_data["status"] == JobStatusEnum.PENDING

        # Verify repository was called with perspective-suffixed job name
        mock_repo_instance.create_job_run.assert_called_once_with(
            job_name="mcda_analysis_regulatory")
