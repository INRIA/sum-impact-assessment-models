"""
Job management API routes.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, BackgroundTasks, status as api_status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ...database.connection import get_db, get_db_session
from ...repositories.job_repository import JobRepository
from ...schemas.job import JobNameEnum, JobRunResponse, TriggerJobRequest
from ...jobs import get_job_class
from ...utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/jobs")


def execute_job_in_background(job_name: JobNameEnum, job_id: str, params: Optional[dict] = None):
    """
    Execute a job in the background.

    Args:
        job_name: The name of the job to execute
        job_id: The UUID of the job run to track
        params: Optional parameters for the job
    """
    logger.info(
        f"Background task started for job",
        extra={
            "job_name": job_name.value,
            "job_id": job_id,
            "params": params
        }
    )

    # Get a new database session for the background task
    with get_db_session() as db:
        try:
            # Get the job class and execute
            job_class = get_job_class(job_name)
            job_class.run(job_id=job_id, db=db, params=params)
        except Exception as e:
            logger.error(
                f"Background job execution failed",
                extra={
                    "job_name": job_name.value,
                    "job_id": job_id,
                    "error": str(e)
                },
                exc_info=True
            )


@router.post("/runs/{job_name}", response_model=JobRunResponse, status_code=api_status.HTTP_201_CREATED)
def trigger_job(
    job_name: JobNameEnum,
    background_tasks: BackgroundTasks,
    request: Optional[TriggerJobRequest] = Body(
        None,
        openapi_examples={
            "kpi_group_filter": {
                "summary": "Impact analysis for SIEF KPIs",
                "description": "Run impact analysis filtering only SIEF KPIs",
                "value": {
                    "params": {
                        "kpi_group_type": "KPI_SIEF"
                    }
                }
            },
            "mcda_regulatory_perspective": {
                "summary": "MCDA Analysis for regulatory perspective",
                "description": "Run MCDA analysis with regulatory stakeholder weights",
                "value": {
                    "params": {
                        "kpi_group_type": "MCDA_GOALS",
                        "perspective": "regulatory"
                    }
                }
            },
            "mcda_pto_perspective": {
                "summary": "MCDA Analysis for PTO perspective",
                "description": "Run MCDA analysis with PTO stakeholder weights",
                "value": {
                    "params": {
                        "kpi_group_type": "MCDA_GOALS",
                        "perspective": "pto"
                    }
                }
            },
            "mcda_citizens_users_perspective": {
                "summary": "MCDA Analysis for citizens/users perspective",
                "description": "Run MCDA analysis with citizens/users stakeholder weights",
                "value": {
                    "params": {
                        "kpi_group_type": "MCDA_GOALS",
                        "perspective": "citizens_users"
                    }
                }
            },
            "mcda_nsm_providers_perspective": {
                "summary": "MCDA Analysis for NSM providers perspective",
                "description": "Run MCDA analysis with NSM providers stakeholder weights",
                "value": {
                    "params": {
                        "kpi_group_type": "MCDA_GOALS",
                        "perspective": "nsm_providers"
                    }
                }
            }
        }
    ),
    db: Session = Depends(get_db)
):
    """
    Trigger a job execution.

    Creates a new job run with PENDING status, schedules it for background execution,
    and returns the job run details.

    Args:
        job_name: Name of the job to trigger (must be a valid JobNameEnum value)
        background_tasks: FastAPI background tasks manager
        request: Optional request body with job parameters
        db: Database session (injected)

    Returns:
        JobRunResponse with job run details

    Raises:
        HTTPException 404: If the job name is not found in the registry
        HTTPException 500: If there's a database error
    """
    params = request.params if request else None
    logger.info(f"Job trigger request received",
                extra={"job_name": job_name.value, "params": params})

    try:
        # Verify the job exists in the registry
        try:
            get_job_class(job_name)
        except KeyError:
            logger.warning(f"Job not found in registry: {job_name.value}")
            raise HTTPException(
                status_code=api_status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_name.value}' not found in registry"
            )

        # Create a new job run with PENDING status
        # For MCDA analysis, append perspective to job name if provided
        job_repo = JobRepository(db)
        actual_job_name = job_name.value

        if job_name == JobNameEnum.MCDA_ANALYSIS and params and "perspective" in params:
            perspective = params["perspective"]
            actual_job_name = f"{job_name.value}_{perspective}"
            logger.info(f"MCDA job with perspective: {perspective}")

        job_run = job_repo.create_job_run(job_name=actual_job_name)

        logger.info(
            f"Job run created",
            extra={
                "job_name": actual_job_name,
                "job_id": job_run.id,
                "status": job_run.status
            }
        )

        # Schedule the job for background execution
        background_tasks.add_task(
            execute_job_in_background, job_name, job_run.id, params)

        logger.info(
            f"Job scheduled for background execution",
            extra={
                "job_name": job_name.value,
                "job_id": job_run.id
            }
        )

        # Return the job run response
        return JobRunResponse.model_validate(job_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error triggering job",
            extra={
                "job_name": job_name.value,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=api_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering job: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobRunResponse)
def get_job_run(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a job run by ID.

    Args:
        job_id: UUID of the job run to retrieve
        db: Database session (injected)

    Returns:
        JobRunResponse with job run details

    Raises:
        HTTPException 404: If the job run is not found
        HTTPException 500: If there's a database error
    """
    logger.info(f"Job run retrieval request received",
                extra={"job_id": job_id})

    try:
        job_repo = JobRepository(db)
        job_run = job_repo.get_job_run(job_id)

        if not job_run:
            logger.warning(f"Job run not found: {job_id}")
            raise HTTPException(
                status_code=api_status.HTTP_404_NOT_FOUND,
                detail=f"Job run with ID '{job_id}' not found"
            )

        logger.info(
            f"Job run retrieved successfully",
            extra={
                "job_id": job_id,
                "job_name": job_run.job_name,
                "status": job_run.status
            }
        )

        return JobRunResponse.model_validate(job_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving job run",
            extra={
                "job_id": job_id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=api_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job run: {str(e)}"
        )


@router.get("/", response_model=List[JobRunResponse])
def list_job_runs(
    job_name: Optional[JobNameEnum] = Query(
        None, description="Filter by job name"),
    status: Optional[str] = Query(
        None, description="Filter by status (PENDING, STARTED, SUCCESS, FAILURE)"),
    created_at_from: Optional[datetime] = Query(
        None, description="Filter by creation date (from, inclusive). ISO 8601 format."),
    created_at_to: Optional[datetime] = Query(
        None, description="Filter by creation date (to, inclusive). ISO 8601 format."),
    db: Session = Depends(get_db)
):
    """
    List all job runs with optional filters.

    Results are sorted by creation date in descending order (most recent first).

    Args:
        job_name: Optional filter by job name (exact match)
        status: Optional filter by status (exact match)
        created_at_from: Optional filter by creation date (from, inclusive)
        created_at_to: Optional filter by creation date (to, inclusive)
        db: Database session (injected)

    Returns:
        List of JobRunResponse with job run details

    Raises:
        HTTPException 500: If there's a database error
    """
    logger.info(
        f"Job runs list request received",
        extra={
            "job_name": job_name,
            "status": status,
            "created_at_from": created_at_from,
            "created_at_to": created_at_to
        }
    )

    try:
        job_repo = JobRepository(db)
        job_runs = job_repo.get_job_runs(
            job_name=job_name,
            status=status,
            created_at_from=created_at_from,
            created_at_to=created_at_to
        )

        logger.info(
            f"Job runs retrieved successfully",
            extra={"count": len(job_runs)}
        )

        return [JobRunResponse.model_validate(job_run) for job_run in job_runs]

    except Exception as e:
        logger.error(
            f"Error listing job runs",
            extra={
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=api_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing job runs: {str(e)}"
        )
