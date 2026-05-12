"""
Job management API routes.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Query, Request, status as api_status
from sqlalchemy.orm import Session

from ...api.dependencies.admin_refresh_guards import (
    check_rate_limit,
    enforce_ip_allowlist,
    mark_rate_limit,
    remember_idempotency_key,
    validate_idempotency_key,
)
from ...api.dependencies.auth import verify_admin_refresh_api_key, verify_api_key
from ...database.connection import get_db
from ...repositories.job_repository import JobRepository
from ...schemas.job import (
    FullImpactRefreshStatusResponse,
    FullImpactRefreshTriggerResponse,
    JobNameEnum,
    JobRunResponse,
    TriggerJobRequest,
)
from ...jobs import get_job_class
from ...services.full_impact_refresh_service import (
    build_dispatch_plan,
    build_initial_dispatch_state,
    build_status_response,
    build_trigger_response,
    dispatch_full_refresh_sync,
)
from ...services.job_dispatch_service import execute_job_in_background, resolve_actual_job_name
from ...utils.exceptions import translate_errors
from ...utils.logger import get_logger
from ...utils.time import utc_now

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/jobs", dependencies=[Depends(verify_api_key)])
admin_router = APIRouter(
    prefix="/jobs",
    dependencies=[
        Depends(verify_admin_refresh_api_key),
        Depends(enforce_ip_allowlist),
    ],
)


@router.post("/runs/{job_name}", response_model=JobRunResponse, status_code=api_status.HTTP_201_CREATED)
@translate_errors
def trigger_job(
    job_name: JobNameEnum,
    background_tasks: BackgroundTasks,
    request: Optional[TriggerJobRequest] = Body(
        None,
        openapi_examples={
            "impact_analysis_sief": {
                "summary": "Impact analysis for SIEF KPIs",
                "description": "Run impact analysis filtering only SIEF KPIs",
                "value": {
                    "params": {
                        "kpi_group_type": "KPI_SIEF"
                    }
                }
            },
            "mcda_qualitative_regulatory_perspective": {
                "summary": "Qualitative MCDA Analysis for regulatory perspective",
                "description": "Run MCDA analysis with regulatory stakeholder weights, from qualitative data from expert surveys",
                "value": {
                    "params": {
                        "perspective": "regulatory"
                    }
                }
            },
            "mcda_qualitative_pto_perspective": {
                "summary": "Qualitative MCDA Analysis for PTO perspective",
                "description": "Run MCDA analysis with PTO stakeholder weights, from qualitative data from expert surveys",
                "value": {
                    "params": {
                        "perspective": "pto"
                    }
                }
            },
            "mcda_qualitative_nsm_providers_perspective": {
                "summary": "Qualitative MCDA Analysis for NSM providers perspective",
                "description": "Run MCDA analysis with NSM providers stakeholder weights, from qualitative data from expert surveys",
                "value": {
                    "params": {
                        "perspective": "nsm_providers"
                    }
                }
            },
            "mcda_custom_analysis": {
                "summary": "Custom MCDA Analysis with user-defined goals and alternatives",
                "description": "Run MCDA analysis using fully customized goals, weights, and alternative scores",
                "value": {
                    "params": {
                        "name": "Custom MCDA Run",
                        "goals": [
                            {
                                "name": "Environmental Impact",
                                "weight": 0.35,
                                "direction": "max"
                            },
                            {
                                "name": "Economic Cost",
                                "weight": 0.25,
                                "direction": "min"
                            },
                            {
                                "name": "Social Acceptance",
                                "weight": 0.40,
                                "direction": "max"
                            }
                        ],
                        "alternatives": [
                            {
                                "name": "Project A",
                                "values": {
                                    "Environmental Impact": 0.82,
                                    "Economic Cost": 1200.0,
                                    "Social Acceptance": 0.67
                                }
                            },
                            {
                                "name": "Project B",
                                "values": {
                                    "Environmental Impact": 0.75,
                                    "Economic Cost": 980.0,
                                    "Social Acceptance": 0.74
                                }
                            }
                        ]
                    }
                }
            },
            "mcda_quantitative_regulatory_perspective": {
                "summary": "Quantitative MCDA Analysis for regulatory perspective",
                "description": "Run MCDA analysis with regulatory stakeholder weights, from quantitative data form KPI/measures impact analysis",
                "value": {
                    "params": {
                        "kpi_group_type": "MCDA_GOALS",
                        "perspective": "regulatory"
                    }
                }
            },
            "mcda_quantitative_pto_perspective": {
                "summary": "Quantitative MCDA Analysis for PTO perspective",
                "description": "Run MCDA analysis with PTO stakeholder weights, from quantitative data form KPI/measures impact analysis",
                "value": {
                    "params": {
                        "kpi_group_type": "MCDA_GOALS",
                        "perspective": "pto"
                    }
                }
            },
            "mcda_quantitative_nsm_providers_perspective": {
                "summary": "Quantitative MCDA Analysis for NSM providers perspective",
                "description": "Run MCDA analysis with NSM providers stakeholder weights, from quantitative data form KPI/measures impact analysis",
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
    actual_job_name = resolve_actual_job_name(job_name, params)

    if actual_job_name != job_name.value and params:
        logger.info(f"MCDA job with perspective: {params['perspective']}")

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


@admin_router.post(
    "/runs/full_impact_refresh",
    response_model=FullImpactRefreshTriggerResponse,
    status_code=api_status.HTTP_202_ACCEPTED,
)
def trigger_full_impact_refresh(
    background_tasks: BackgroundTasks,
    request: Request,
    api_key: str = Depends(verify_admin_refresh_api_key),
    idempotency_key: Optional[str] = Depends(validate_idempotency_key),
    triggered_by: Optional[str] = Header(default=None, alias="X-Triggered-By"),
    request_id: Optional[str] = Header(default=None, alias="X-Request-Id"),
    db: Session = Depends(get_db),
):
    """
    Trigger the full impact refresh orchestration.
    """
    client_host = request.client.host if request.client else None
    job_repo = JobRepository(db)
    check_rate_limit(api_key)

    in_progress_run = job_repo.get_in_progress_full_refresh()
    if in_progress_run is not None:
        raise HTTPException(
            status_code=api_status.HTTP_409_CONFLICT,
            detail={
                "error": "refresh_in_progress",
                "current_run_id": in_progress_run.id,
            },
        )

    started_at = utc_now()
    plan = build_dispatch_plan(started_at)
    parent_run = job_repo.create_job_run(job_name=JobNameEnum.FULL_IMPACT_REFRESH.value)
    job_repo.update_job_data(
        parent_run.id,
        input_data={
            "plan": plan,
            "triggered_by": triggered_by,
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "source_ip": client_host,
        },
        output_data={
            "dispatched_jobs": build_initial_dispatch_state(plan),
        },
    )

    remember_idempotency_key(idempotency_key, parent_run.id)
    mark_rate_limit(api_key)

    logger.info(
        "Admin full impact refresh accepted",
        extra={
            "run_id": parent_run.id,
            "triggered_by": triggered_by,
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "source_ip": client_host,
            "status_code": api_status.HTTP_202_ACCEPTED,
        },
    )

    background_tasks.add_task(dispatch_full_refresh_sync, parent_run.id, plan)
    return build_trigger_response(plan, parent_run.id, started_at)


@admin_router.get(
    "/runs/full_impact_refresh/{run_id}",
    response_model=FullImpactRefreshStatusResponse,
)
def get_full_impact_refresh_status(
    run_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve the status of a previously triggered full impact refresh run.
    """
    job_repo = JobRepository(db)
    parent_run = job_repo.get_job_run(run_id)

    if parent_run is None or parent_run.job_name != JobNameEnum.FULL_IMPACT_REFRESH.value:
        raise HTTPException(
            status_code=api_status.HTTP_404_NOT_FOUND,
            detail=f"Full impact refresh run with ID '{run_id}' not found",
        )

    return build_status_response(parent_run, job_repo)


@router.get("/{job_id}", response_model=JobRunResponse)
@translate_errors
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


@router.get("/", response_model=List[JobRunResponse])
@translate_errors
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
