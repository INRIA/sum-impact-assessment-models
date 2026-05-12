"""
Unit tests for job management API.
"""
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

os.environ["INTERNAL_API_KEY"] = "test-key"
os.environ["ADMIN_REFRESH_API_KEY"] = "admin-key"

from src.sum_impact_assessment.api.main import app
from src.sum_impact_assessment.config.settings import settings
from src.sum_impact_assessment.api.dependencies.admin_refresh_guards import reset_admin_refresh_guards_state
from sum_impact_assessment.database.models.job import JobRun
from src.sum_impact_assessment.schemas.job import JobNameEnum, JobStatusEnum


# Create test client
client = TestClient(app)
AUTH_HEADERS = {"X-Internal-API-Key": "test-key"}
ADMIN_HEADERS = {"X-Admin-Refresh-Key": "admin-key"}


@pytest.fixture(autouse=True)
def reset_admin_guard_state():
    """Reset in-memory admin refresh guard state between tests."""
    original_internal_api_key = settings.INTERNAL_API_KEY
    original_admin_refresh_api_key = settings.ADMIN_REFRESH_API_KEY
    original_allowed_ips = settings.ADMIN_REFRESH_ALLOWED_IPS

    settings.INTERNAL_API_KEY = "test-key"
    settings.ADMIN_REFRESH_API_KEY = "admin-key"
    settings.ADMIN_REFRESH_ALLOWED_IPS = ["127.0.0.1", "::1", "localhost", "testclient"]
    reset_admin_refresh_guards_state()
    yield
    settings.INTERNAL_API_KEY = original_internal_api_key
    settings.ADMIN_REFRESH_API_KEY = original_admin_refresh_api_key
    settings.ADMIN_REFRESH_ALLOWED_IPS = original_allowed_ips
    reset_admin_refresh_guards_state()


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
        response = client.post("/jobs/runs/kpi_measures_analysis", headers=AUTH_HEADERS)

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
        response = client.post("/jobs/runs/kpi_measures_analysis", headers=AUTH_HEADERS)

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found in registry" in response.json()["detail"]

        # Verify repository create was not called
        mock_job_repo_class.return_value.create_job_run.assert_not_called()

    def test_trigger_job_invalid_job_name(self):
        """Test triggering a job with invalid job name returns 422."""
        # Make request with invalid job name
        response = client.post("/jobs/runs/invalid_job_name", headers=AUTH_HEADERS)

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
        response = client.post("/jobs/runs/kpi_measures_analysis", headers=AUTH_HEADERS)

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
            job_name="mcda_analysis_quantitative",
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
            "/jobs/runs/mcda_analysis_quantitative",
            headers=AUTH_HEADERS,
            json={"params": {"kpi_group_type": "MCDA_GOALS"}}
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == "test-job-id-456"
        assert response_data["job_name"] == "mcda_analysis_quantitative"
        assert response_data["status"] == JobStatusEnum.PENDING

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_mcda_analysis_job(self, mock_get_job_class, mock_job_repo_class):
        """Test triggering MCDA analysis job specifically."""
        # Setup mock job run
        mock_job_run = JobRun(
            id="mcda-job-id-999",
            job_name="mcda_analysis_quantitative",
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
        response = client.post("/jobs/runs/mcda_analysis_quantitative", headers=AUTH_HEADERS)

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["job_name"] == "mcda_analysis_quantitative"
        assert response_data["status"] == JobStatusEnum.PENDING

        # Verify repository was called with correct job name
        mock_repo_instance.create_job_run.assert_called_once_with(
            job_name=JobNameEnum.MCDA_ANALYSIS_QUANTITATIVE)

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    @patch("src.sum_impact_assessment.api.routes.jobs.get_job_class")
    def test_trigger_mcda_analysis_job_with_perspective(self, mock_get_job_class, mock_job_repo_class):
        """Test triggering MCDA analysis job with perspective parameter."""
        # Setup mock job run with perspective in name
        mock_job_run = JobRun(
            id="mcda-job-perspective-123",
            job_name="mcda_analysis_quantitative_regulatory",
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
            "/jobs/runs/mcda_analysis_quantitative",
            headers=AUTH_HEADERS,
            json={"params": {"perspective": "regulatory"}}
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == "mcda-job-perspective-123"
        assert response_data["job_name"] == "mcda_analysis_quantitative_regulatory"
        assert response_data["status"] == JobStatusEnum.PENDING

        # Verify repository was called with perspective-suffixed job name
        mock_repo_instance.create_job_run.assert_called_once_with(
            job_name="mcda_analysis_quantitative_regulatory")


class TestAdminFullRefreshAPI:
    """Test suite for the admin full impact refresh endpoints."""

    @patch("src.sum_impact_assessment.api.routes.jobs.dispatch_full_refresh", new_callable=Mock)
    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    def test_trigger_full_impact_refresh_success(self, mock_job_repo_class, mock_dispatch_full_refresh):
        """Admin refresh endpoint should accept a new refresh run and return the dispatch plan."""
        mock_parent_run = JobRun(
            id="parent-run-1",
            job_name="full_impact_refresh",
            status=JobStatusEnum.PENDING,
            created_at=datetime(2026, 5, 12, 10, 0, 0),
        )

        mock_repo_instance = Mock()
        mock_repo_instance.get_in_progress_full_refresh.return_value = None
        mock_repo_instance.create_job_run.return_value = mock_parent_run
        mock_job_repo_class.return_value = mock_repo_instance

        response = client.post(
            "/jobs/runs/full_impact_refresh",
            headers={
                **ADMIN_HEADERS,
                "X-Triggered-By": "admin@example.com",
                "X-Request-Id": "request-123",
                "Idempotency-Key": "idem-123",
            },
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["run_id"] == "parent-run-1"
        assert response_data["status"] == "dispatching"
        assert len(response_data["dispatched_jobs"]) == 7
        assert response_data["dispatched_jobs"][0]["job_name"] == "kpi_measures_analysis"
        assert response_data["dispatched_jobs"][1]["actual_job_name"] == "mcda_analysis_quantitative_regulatory"
        mock_repo_instance.get_in_progress_full_refresh.assert_called_once()
        mock_dispatch_full_refresh.assert_called_once()

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    def test_trigger_full_impact_refresh_conflict(self, mock_job_repo_class):
        """Admin refresh endpoint should reject a trigger if another refresh is still dispatching."""
        mock_repo_instance = Mock()
        mock_repo_instance.get_in_progress_full_refresh.return_value = JobRun(
            id="existing-parent",
            job_name="full_impact_refresh",
            status=JobStatusEnum.STARTED,
            created_at=datetime(2026, 5, 12, 10, 0, 0),
        )
        mock_job_repo_class.return_value = mock_repo_instance

        response = client.post("/jobs/runs/full_impact_refresh", headers=ADMIN_HEADERS)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"]["error"] == "refresh_in_progress"

    def test_trigger_full_impact_refresh_requires_admin_key(self):
        """Admin refresh endpoint should reject missing admin refresh credentials."""
        response = client.post("/jobs/runs/full_impact_refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_trigger_full_impact_refresh_rejects_disallowed_ip(self):
        """Admin refresh endpoint should reject requests from a non-allowlisted client host."""
        original_ips = settings.ADMIN_REFRESH_ALLOWED_IPS
        settings.ADMIN_REFRESH_ALLOWED_IPS = ["127.0.0.1"]

        try:
            response = client.post("/jobs/runs/full_impact_refresh", headers=ADMIN_HEADERS)
        finally:
            settings.ADMIN_REFRESH_ALLOWED_IPS = original_ips

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.sum_impact_assessment.api.routes.jobs.dispatch_full_refresh", new_callable=Mock)
    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    def test_trigger_full_impact_refresh_rejects_duplicate_idempotency_key(self, mock_job_repo_class, mock_dispatch_full_refresh):
        """Admin refresh endpoint should reject a duplicate idempotent request within the configured window."""
        mock_parent_run = JobRun(
            id="parent-run-1",
            job_name="full_impact_refresh",
            status=JobStatusEnum.PENDING,
            created_at=datetime(2026, 5, 12, 10, 0, 0),
        )

        mock_repo_instance = Mock()
        mock_repo_instance.get_in_progress_full_refresh.return_value = None
        mock_repo_instance.create_job_run.return_value = mock_parent_run
        mock_job_repo_class.return_value = mock_repo_instance

        first_response = client.post(
            "/jobs/runs/full_impact_refresh",
            headers={**ADMIN_HEADERS, "Idempotency-Key": "idem-123"},
        )
        second_response = client.post(
            "/jobs/runs/full_impact_refresh",
            headers={**ADMIN_HEADERS, "Idempotency-Key": "idem-123"},
        )

        assert first_response.status_code == status.HTTP_202_ACCEPTED
        assert second_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert second_response.json()["detail"]["error"] == "duplicate_request"
        mock_dispatch_full_refresh.assert_called_once()

    @patch("src.sum_impact_assessment.api.routes.jobs.dispatch_full_refresh", new_callable=Mock)
    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    def test_trigger_full_impact_refresh_rate_limit(self, mock_job_repo_class, mock_dispatch_full_refresh):
        """Admin refresh endpoint should rate limit repeated successful triggers."""
        mock_parent_run = JobRun(
            id="parent-run-1",
            job_name="full_impact_refresh",
            status=JobStatusEnum.PENDING,
            created_at=datetime(2026, 5, 12, 10, 0, 0),
        )

        mock_repo_instance = Mock()
        mock_repo_instance.get_in_progress_full_refresh.return_value = None
        mock_repo_instance.create_job_run.return_value = mock_parent_run
        mock_job_repo_class.return_value = mock_repo_instance

        first_response = client.post("/jobs/runs/full_impact_refresh", headers=ADMIN_HEADERS)
        second_response = client.post(
            "/jobs/runs/full_impact_refresh",
            headers={**ADMIN_HEADERS, "Idempotency-Key": "different-idem"},
        )

        assert first_response.status_code == status.HTTP_202_ACCEPTED
        assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert second_response.json()["detail"]["error"] == "rate_limited"
        mock_dispatch_full_refresh.assert_called_once()

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    def test_get_full_impact_refresh_status(self, mock_job_repo_class):
        """Status endpoint should return the parent refresh run and child job statuses."""
        parent_run = JobRun(
            id="parent-run-1",
            job_name="full_impact_refresh",
            status=JobStatusEnum.SUCCESS,
            message="Dispatched 7/7 jobs",
            created_at=datetime(2026, 5, 12, 10, 0, 0),
            started_at=datetime(2026, 5, 12, 10, 0, 1),
            completed_at=datetime(2026, 5, 12, 10, 0, 9),
            input_data={
                "triggered_by": "admin@example.com",
                "request_id": "request-123",
                "idempotency_key": "idem-123",
                "source_ip": "testclient",
            },
            output_data={
                "dispatched_jobs": [
                    {
                        "sequence": 0,
                        "job_name": "kpi_measures_analysis",
                        "actual_job_name": "kpi_measures_analysis",
                        "params": {"kpi_group_type": "KPI_SIEF"},
                        "scheduled_at": "2026-05-12T10:00:00",
                        "dispatch_status": "scheduled",
                        "job_run_id": "child-1",
                        "error": None,
                    }
                ]
            },
        )
        child_run = JobRun(
            id="child-1",
            job_name="kpi_measures_analysis",
            status=JobStatusEnum.SUCCESS,
            message="Completed",
            created_at=datetime(2026, 5, 12, 10, 0, 0),
        )

        mock_repo_instance = Mock()
        mock_repo_instance.get_job_run.side_effect = [parent_run, child_run]
        mock_job_repo_class.return_value = mock_repo_instance

        response = client.get(
            "/jobs/runs/full_impact_refresh/parent-run-1",
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["run_id"] == "parent-run-1"
        assert response_data["dispatched_jobs"][0]["child_status"] == JobStatusEnum.SUCCESS
        assert response_data["dispatched_jobs"][0]["child_message"] == "Completed"

    @patch("src.sum_impact_assessment.api.routes.jobs.JobRepository")
    def test_get_full_impact_refresh_status_not_found(self, mock_job_repo_class):
        """Status endpoint should return 404 when the parent refresh run does not exist."""
        mock_repo_instance = Mock()
        mock_repo_instance.get_job_run.return_value = None
        mock_job_repo_class.return_value = mock_repo_instance

        response = client.get(
            "/jobs/runs/full_impact_refresh/missing-run",
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
