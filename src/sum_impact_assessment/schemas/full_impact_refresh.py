"""
Pydantic schemas for the full impact refresh orchestration flow.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .job_run import JobStatusEnum  # noqa: F401 — re-exported for convenience


class FullRefreshDispatchedJob(BaseModel):
    """Status entry for a child job dispatched by a full impact refresh run."""
    sequence: int = Field(..., description="Dispatch order for the child job")
    job_name: str = Field(..., description="Base job name")
    actual_job_name: str = Field(..., description="Persisted job run name")
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters passed to the child job")
    scheduled_at: Optional[datetime] = Field(None, description="Planned or actual dispatch time")
    dispatch_status: str = Field(..., description="Dispatch state for the child job")
    job_run_id: Optional[str] = Field(None, description="Child job run identifier once created")
    child_status: Optional[str] = Field(None, description="Current child job run status if available")
    child_message: Optional[str] = Field(None, description="Current child job run message if available")
    error: Optional[str] = Field(None, description="Dispatch error, if child job creation failed")


class FullImpactRefreshTriggerResponse(BaseModel):
    """Response returned when a full impact refresh run is accepted."""
    run_id: str = Field(..., description="Parent refresh run identifier")
    status: str = Field(..., description="Current orchestration status")
    started_at: datetime = Field(..., description="Timestamp when the refresh was accepted")
    dispatched_jobs: List[FullRefreshDispatchedJob] = Field(
        ..., description="Planned child job dispatches"
    )


class FullImpactRefreshStatusResponse(BaseModel):
    """Status response for an existing full impact refresh run."""
    run_id: str = Field(..., description="Parent refresh run identifier")
    status: str = Field(..., description="Parent refresh run status")
    message: Optional[str] = Field(None, description="Parent refresh run summary message")
    created_at: datetime = Field(..., description="Parent refresh run creation time")
    started_at: Optional[datetime] = Field(None, description="Parent refresh run start time")
    completed_at: Optional[datetime] = Field(None, description="Parent refresh run completion time")
    triggered_by: Optional[str] = Field(None, description="Value from X-Triggered-By header")
    request_id: Optional[str] = Field(None, description="Value from X-Request-Id header")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key used for the trigger")
    source_ip: Optional[str] = Field(None, description="Source IP of the trigger request")
    dispatched_jobs: List[FullRefreshDispatchedJob] = Field(
        ..., description="Tracked child jobs for the refresh run"
    )
