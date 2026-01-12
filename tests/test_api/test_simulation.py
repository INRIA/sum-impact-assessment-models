"""
Unit tests for simulation API routes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from src.sum_impact_assessment.api.main import app

# Create test client
client = TestClient(app)


class TestSimulationAPI:
    """Test suite for simulation API endpoints."""

    @patch("src.sum_impact_assessment.api.routes.simulation.settings")
    def test_simulation_blocked_in_production(self, mock_settings):
        """Test that simulation endpoint returns 403 in production."""
        # Mock production environment
        mock_settings.ENV = "production"

        # Attempt to run simulation
        response = client.post(
            "/simulation/kpi-results",
            json={
                "baseline_years": [2023],
                "target_year": 2025,
                "min_variation": 0.5,
                "max_variation": 1.5
            }
        )

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not available in production" in response.json()["detail"]

    @patch("src.sum_impact_assessment.api.routes.simulation.settings")
    @patch("src.sum_impact_assessment.api.routes.simulation.KpiResultsSimulationService")
    def test_simulation_success_in_development(self, mock_service_class, mock_settings):
        """Test successful simulation in development environment."""
        # Mock development environment
        mock_settings.ENV = "development"

        # Mock service
        mock_service = Mock()
        mock_service.run.return_value = {
            "deleted": 100,
            "baseline_year": 2023,
            "target_year": 2025,
            "generated": 150
        }
        mock_service_class.return_value = mock_service

        # Run simulation
        response = client.post(
            "/simulation/kpi-results",
            json={
                "baseline_years": [2023],
                "target_year": 2025,
                "min_variation": 0.5,
                "max_variation": 1.5
            }
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["generated"] == 150
        assert data["deleted"] == 100
        assert data["target_year"] == 2025

    @patch("src.sum_impact_assessment.api.routes.simulation.settings")
    @patch("src.sum_impact_assessment.api.routes.simulation.KpiResultsSimulationService")
    def test_simulation_invalid_parameters(self, mock_service_class, mock_settings):
        """Test simulation with invalid parameters returns 400."""
        # Mock development environment
        mock_settings.ENV = "development"

        # Mock service to raise ValueError
        mock_service = Mock()
        mock_service.run.side_effect = ValueError(
            "baseline_year must be less than target_year")
        mock_service_class.return_value = mock_service

        # Run simulation with invalid params
        response = client.post(
            "/simulation/kpi-results",
            json={
                "baseline_years": [2025],
                "target_year": 2023,  # Invalid: target < baseline
                "min_variation": 0.5,
                "max_variation": 1.5
            }
        )

        # Should return bad request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid simulation parameters" in response.json()["detail"]

    @patch("src.sum_impact_assessment.api.routes.simulation.settings")
    def test_environment_status_development(self, mock_settings):
        """Test environment status endpoint in development."""
        mock_settings.ENV = "development"

        response = client.get("/simulation/environment")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["environment"] == "development"
        assert data["simulation_endpoints_enabled"] is True

    @patch("src.sum_impact_assessment.api.routes.simulation.settings")
    def test_environment_status_production(self, mock_settings):
        """Test environment status endpoint in production."""
        mock_settings.ENV = "production"

        response = client.get("/simulation/environment")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["environment"] == "production"
        assert data["simulation_endpoints_enabled"] is False
