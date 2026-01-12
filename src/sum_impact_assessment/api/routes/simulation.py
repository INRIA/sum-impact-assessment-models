"""
Simulation API routes - DEVELOPMENT/PREPRODUCTION ONLY.

These endpoints are only available in non-production environments
for testing and data generation purposes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from ...database.connection import get_db
from ...services.kpi_results_simulation import KpiResultsSimulationService
from ...config.settings import settings
from ...utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/simulation")


# Dependency to check environment
def check_non_production_environment():
    """
    Dependency that raises 403 if called in production environment.

    Raises:
        HTTPException: 403 Forbidden if ENV is 'production'
    """
    if settings.ENV.lower() != "production" and settings.DB_NAME != "sumodp":
        return True
    logger.warning(
        "Attempted to access simulation endpoint in production environment",
        extra={"env": settings.ENV}
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Simulation endpoints are not available in production environment"
    )


class SimulateKPIResultsRequest(BaseModel):
    """
    Request schema for KPI results simulation.
    """
    baseline_years: List[int] = Field(
        ...,
        description="Years to use as baseline for simulation (e.g., [2017, 2023, 2024])",
        min_length=1,
        examples=[[2017, 2023, 2024]]
    )
    target_year: int = Field(
        ...,
        description="Year to assign to generated results",
        gt=2000,
        examples=[2025]
    )
    min_variation: float = Field(
        ...,
        description="Minimum variation multiplier (e.g., 0.5 for -50%)",
        gt=0,
        examples=[0.5]
    )
    max_variation: float = Field(
        ...,
        description="Maximum variation multiplier (e.g., 1.5 for +50%)",
        gt=0,
        examples=[1.5]
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "baseline_years": [2017, 2023, 2024],
                    "target_year": 2025,
                    "min_variation": 0.5,
                    "max_variation": 1.5
                },
                {
                    "baseline_years": [2023],
                    "target_year": 2026,
                    "min_variation": 0.8,
                    "max_variation": 1.2
                },
                {
                    "baseline_years": [2020, 2021, 2022],
                    "target_year": 2024,
                    "min_variation": 0.7,
                    "max_variation": 1.3
                }
            ]
        }


class SimulateKPIResultsResponse(BaseModel):
    """
    Response schema for KPI results simulation.
    """
    success: bool = Field(..., description="Whether the simulation succeeded")
    message: str = Field(..., description="Summary message")
    deleted: int = Field(..., description="Number of existing records deleted")
    baseline_years: List[int] = Field(..., description="Baseline years used")
    target_year: int = Field(..., description="Target year for generated data")
    generated: int = Field(..., description="Number of mock results generated")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully generated 450 KPI results for year 2025 (deleted 450 existing records)",
                "deleted": 450,
                "baseline_years": [2017, 2023, 2024],
                "target_year": 2025,
                "generated": 450
            }
        }


@router.post(
    "/kpi-results",
    response_model=SimulateKPIResultsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Simulate KPI results data",
    description=(
        "**⚠️ DEVELOPMENT/PREPRODUCTION ONLY** - "
        "This endpoint is disabled in production environments.\n\n"
        "Generates mock KPI results by applying random variations to baseline year data. "
        "Useful for testing and development purposes.\n\n"
        "**Process:**\n"
        "1. Deletes existing results for target year\n"
        "2. Fetches baseline results from specified years\n"
        "3. Applies random variations within specified range\n"
        "4. Saves new mock results with target year date"
    ),
    dependencies=[Depends(check_non_production_environment)]
)
def simulate_kpi_results(
    request: SimulateKPIResultsRequest,
    db: Session = Depends(get_db)
) -> SimulateKPIResultsResponse:
    """
    Generate mock KPI results data for testing.

    **Access:** Development and preproduction environments only.

    Args:
        request: Simulation parameters
        db: Database session

    Returns:
        Simulation summary with counts of deleted and generated records

    Raises:
        HTTPException 400: Invalid parameters (e.g., baseline >= target year)
        HTTPException 403: Called in production environment
        HTTPException 500: Database or processing error
    """
    logger.info(
        "Simulation request received",
        extra={
            "baseline_years": request.baseline_years,
            "target_year": request.target_year,
            "min_variation": request.min_variation,
            "max_variation": request.max_variation,
            "environment": settings.ENV
        }
    )

    try:
        # Initialize simulation service
        simulator = KpiResultsSimulationService(db)

        # Run simulation
        result = simulator.run(
            baseline_years=request.baseline_years,
            target_year=request.target_year,
            min_variation=request.min_variation,
            max_variation=request.max_variation
        )

        success_message = (
            f"Successfully generated {result['generated']} KPI results for year {result['target_year']} "
            f"(deleted {result['deleted']} existing records)"
        )

        logger.info("Simulation completed successfully", extra=result)

        return SimulateKPIResultsResponse(
            success=True,
            message=success_message,
            deleted=result['deleted'],
            baseline_years=request.baseline_years,
            target_year=result['target_year'],
            generated=result['generated']
        )

    except ValueError as e:
        # Invalid parameters
        error_msg = f"Invalid simulation parameters: {str(e)}"
        logger.warning(error_msg, extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    except Exception as e:
        # Unexpected error
        error_msg = f"Simulation failed: {str(e)}"
        logger.error(
            error_msg,
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@router.get(
    "/environment",
    summary="Check environment status",
    description="Returns current environment and whether simulation endpoints are available"
)
def get_environment_status():
    """
    Get current environment configuration.

    Useful for checking if simulation endpoints are accessible.
    """
    try:
        check_non_production_environment()
        is_production = False
    except HTTPException:
        is_production = True

    return {
        "environment": settings.ENV,
        "db_name": settings.DB_NAME,
        "simulation_endpoints_enabled": not is_production,
        "message": "Simulation endpoints disabled" if is_production else "Simulation endpoints enabled"
    }
