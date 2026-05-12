"""
Orchestration service for admin-triggered full impact refresh runs.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..config.settings import JOB_RUN_CONFIGURATION, settings
from ..database.models.job import JobRun
from ..database.connection import get_db_session
from ..repositories.job_repository import JobRepository
from ..schemas.job import (
    FullImpactRefreshStatusResponse,
    FullImpactRefreshTriggerResponse,
    FullRefreshDispatchedJob,
    JobNameEnum,
    JobStatusEnum,
)
from ..utils.logger import get_logger
from .job_dispatch_service import execute_job_in_background, resolve_actual_job_name

logger = get_logger(__name__)


def build_dispatch_plan(started_at: datetime) -> List[Dict[str, Any]]:
    """
    Build the ordered child-job dispatch plan from static configuration.
    """
    plan: List[Dict[str, Any]] = []

    for sequence, job_config in enumerate(JOB_RUN_CONFIGURATION):
        params = {
            key: value for key, value in job_config.items()
            if key != "job_name" and value is not None
        }
        job_name = job_config["job_name"]
        scheduled_at = started_at + timedelta(
            seconds=sequence * settings.REFRESH_DISPATCH_INTERVAL_SECONDS
        )

        plan.append({
            "sequence": sequence,
            "job_name": job_name.value,
            "actual_job_name": resolve_actual_job_name(job_name, params or None),
            "params": params or None,
            "scheduled_at": scheduled_at.isoformat(),
        })

    return plan


def build_initial_dispatch_state(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build the initial parent output payload for all planned child dispatches.
    """
    return [
        {
            **item,
            "job_run_id": None,
            "dispatch_status": "pending",
            "error": None,
        }
        for item in plan
    ]


async def dispatch_full_refresh(parent_run_id: str, plan: List[Dict[str, Any]]) -> None:
    """
    Create child job runs for the configured plan and launch each execution asynchronously.
    """
    dispatch_failures = 0
    dispatch_count = len(plan)

    try:
        with get_db_session() as db:
            job_repository = JobRepository(db)
            job_repository.update_job_status(
                parent_run_id,
                status=JobStatusEnum.STARTED,
                started_at=datetime.utcnow(),
            )

        for index, plan_item in enumerate(plan):
            job_name = JobNameEnum(plan_item["job_name"])
            params = plan_item.get("params")
            sequence = plan_item["sequence"]

            try:
                with get_db_session() as db:
                    job_repository = JobRepository(db)
                    child_job_run = job_repository.create_job_run(
                        job_name=plan_item["actual_job_name"]
                    )
                    job_repository.update_job_data(
                        child_job_run.id,
                        input_data={
                            "params": params,
                            "parent_run_id": parent_run_id,
                            "triggered_by_job": JobNameEnum.FULL_IMPACT_REFRESH.value,
                        },
                    )
                    job_repository.update_dispatched_job(
                        parent_run_id,
                        sequence,
                        {
                            "job_run_id": child_job_run.id,
                            "dispatch_status": "scheduled",
                            "scheduled_at": child_job_run.created_at.isoformat(),
                            "error": None,
                        },
                    )

                asyncio.create_task(
                    asyncio.to_thread(
                        execute_job_in_background,
                        job_name,
                        child_job_run.id,
                        params,
                    )
                )
            except Exception as error:
                dispatch_failures += 1
                logger.error(
                    "Failed to dispatch child job from full refresh",
                    extra={
                        "parent_run_id": parent_run_id,
                        "job_name": plan_item["job_name"],
                        "sequence": sequence,
                        "error": str(error),
                    },
                    exc_info=True,
                )
                with get_db_session() as db:
                    job_repository = JobRepository(db)
                    job_repository.update_dispatched_job(
                        parent_run_id,
                        sequence,
                        {
                            "dispatch_status": "failed",
                            "error": str(error),
                        },
                    )

            if index < dispatch_count - 1:
                await asyncio.sleep(settings.REFRESH_DISPATCH_INTERVAL_SECONDS)

        with get_db_session() as db:
            job_repository = JobRepository(db)
            final_status = JobStatusEnum.SUCCESS
            if dispatch_failures:
                final_status = JobStatusEnum.FAILURE

            job_repository.update_job_status(
                parent_run_id,
                status=final_status,
                message=f"Dispatched {dispatch_count - dispatch_failures}/{dispatch_count} jobs",
                completed_at=datetime.utcnow(),
            )
    except Exception as error:
        logger.error(
            "Full impact refresh orchestration failed",
            extra={
                "parent_run_id": parent_run_id,
                "error": str(error),
            },
            exc_info=True,
        )
        with get_db_session() as db:
            job_repository = JobRepository(db)
            job_repository.update_job_status(
                parent_run_id,
                status=JobStatusEnum.FAILURE,
                message=str(error),
                completed_at=datetime.utcnow(),
            )


def build_trigger_response(plan: List[Dict[str, Any]], parent_run_id: str, started_at: datetime) -> FullImpactRefreshTriggerResponse:
    """
    Build the trigger response for the newly accepted refresh run.
    """
    dispatched_jobs = [
        FullRefreshDispatchedJob(
            sequence=item["sequence"],
            job_name=item["job_name"],
            actual_job_name=item["actual_job_name"],
            params=item.get("params"),
            scheduled_at=datetime.fromisoformat(item["scheduled_at"]),
            dispatch_status="pending",
        )
        for item in plan
    ]

    return FullImpactRefreshTriggerResponse(
        run_id=parent_run_id,
        status="dispatching",
        started_at=started_at,
        dispatched_jobs=dispatched_jobs,
    )


def build_status_response(parent_run: JobRun, job_repository: JobRepository) -> FullImpactRefreshStatusResponse:
    """
    Build the status response for an existing parent refresh run.
    """
    input_data = parent_run.input_data or {}
    output_data = parent_run.output_data or {}
    dispatched_jobs = []

    for item in output_data.get("dispatched_jobs", []):
        child_status = None
        child_message = None
        child_run_id = item.get("job_run_id")

        if child_run_id:
            child_job_run = job_repository.get_job_run(child_run_id)
            if child_job_run is not None:
                child_status = child_job_run.status
                child_message = child_job_run.message

        scheduled_at = item.get("scheduled_at")
        dispatched_jobs.append(
            FullRefreshDispatchedJob(
                sequence=item["sequence"],
                job_name=item["job_name"],
                actual_job_name=item["actual_job_name"],
                params=item.get("params"),
                scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None,
                dispatch_status=item.get("dispatch_status", "pending"),
                job_run_id=child_run_id,
                child_status=child_status,
                child_message=child_message,
                error=item.get("error"),
            )
        )

    return FullImpactRefreshStatusResponse(
        run_id=parent_run.id,
        status=parent_run.status,
        message=parent_run.message,
        started_at=parent_run.started_at,
        created_at=parent_run.created_at,
        completed_at=parent_run.completed_at,
        triggered_by=input_data.get("triggered_by"),
        request_id=input_data.get("request_id"),
        idempotency_key=input_data.get("idempotency_key"),
        source_ip=input_data.get("source_ip"),
        dispatched_jobs=dispatched_jobs,
    )