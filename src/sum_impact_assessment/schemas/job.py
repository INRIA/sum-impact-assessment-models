"""
Pydantic schemas for job management.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class JobNameEnum(str, Enum):
    """
    Enumeration of valid job names.
    """
    KPI_MEASURES_ANALYSIS = "kpi_measures_analysis"


class JobStatusEnum(str, Enum):
    """
    Enumeration of job run statuses.
    """
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class JobRunResponse(BaseModel):
    """
    Response schema for job run information.
    """
    id: str = Field(..., description="Unique identifier for the job run")
    job_name: str = Field(..., description="Name of the job")
    status: str = Field(..., description="Current status of the job run")
    message: Optional[str] = Field(
        None, description="Optional message (error or success details)")
    created_at: datetime = Field(...,
                                 description="Timestamp when the job was created")
    started_at: Optional[datetime] = Field(
        None, description="Timestamp when the job started")
    completed_at: Optional[datetime] = Field(
        None, description="Timestamp when the job completed")

    class Config:
        from_attributes = True
