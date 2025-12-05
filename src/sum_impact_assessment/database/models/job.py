"""
SQLAlchemy model for job runs.
"""
from sqlalchemy import Column, String, Text, DateTime, JSON
from datetime import datetime
import uuid
from ..connection import Base


class JobRun(Base):
    """
    Represents a job run in the database.

    Attributes:
        id: Unique identifier for the job run (UUID)
        job_name: Name of the job being executed
        status: Current status (PENDING, STARTED, SUCCESS, FAILURE)
        message: Optional message (error details or success message)
        created_at: Timestamp when the job was created
        started_at: Timestamp when the job started execution
        completed_at: Timestamp when the job completed (success or failure)
        input_data: JSON snapshot of input data used for the job
        output_data: JSON snapshot of output/results from the job
    """
    __tablename__ = "job_runs"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    job_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<JobRun(id={self.id}, job_name={self.job_name}, status={self.status})>"
