"""
Repository for job run database operations.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from ..database.models.job import JobRun
from ..schemas.job import JobStatusEnum
from ..utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class JobRepository:
    """
    Repository for managing job run database operations.
    """

    def __init__(self, session: Session):
        """
        Initialize the job repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create_job_run(self, job_name: str, status: str = JobStatusEnum.PENDING) -> JobRun:
        """
        Create a new job run in the database.

        Args:
            job_name: Name of the job to run
            status: Initial status (default: PENDING)

        Returns:
            The created JobRun instance
        """
        logger.debug(f"Creating job run for job: {job_name}")

        job_run = JobRun(
            job_name=job_name,
            status=status
        )

        self.session.add(job_run)
        self.session.commit()
        self.session.refresh(job_run)

        logger.info(
            f"Job run created successfully",
            extra={
                "job_run_id": job_run.id,
                "job_name": job_name,
                "status": status
            }
        )

        return job_run

    def get_job_run(self, job_id: str) -> Optional[JobRun]:
        """
        Retrieve a job run by ID.

        Args:
            job_id: UUID of the job run

        Returns:
            JobRun instance if found, None otherwise
        """
        logger.debug(f"Retrieving job run: {job_id}")
        return self.session.query(JobRun).filter(JobRun.id == job_id).first()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[JobRun]:
        """
        Update the status of a job run.

        Args:
            job_id: UUID of the job run
            status: New status to set
            message: Optional message to set
            started_at: Optional timestamp when job started
            completed_at: Optional timestamp when job completed

        Returns:
            Updated JobRun instance if found, None otherwise
        """
        logger.debug(f"Updating job run {job_id} to status: {status}")

        job_run = self.get_job_run(job_id)

        if not job_run:
            logger.warning(f"Job run not found: {job_id}")
            return None

        job_run.status = status

        if message is not None:
            job_run.message = message

        if started_at is not None:
            job_run.started_at = started_at

        if completed_at is not None:
            job_run.completed_at = completed_at

        self.session.commit()
        self.session.refresh(job_run)

        logger.info(
            f"Job run updated successfully",
            extra={
                "job_run_id": job_id,
                "status": status,
                "has_message": message is not None
            }
        )

        return job_run

    def update_job_data(
        self,
        job_id: str,
        input_data: Optional[dict] = None,
        output_data: Optional[dict] = None
    ) -> Optional[JobRun]:
        """
        Update the input/output data of a job run.

        Args:
            job_id: UUID of the job run
            input_data: Dictionary containing input data snapshot
            output_data: Dictionary containing output data snapshot

        Returns:
            Updated JobRun instance if found, None otherwise
        """
        logger.debug(f"Updating job run {job_id} with data snapshots")

        job_run = self.get_job_run(job_id)

        if not job_run:
            logger.warning(f"Job run not found: {job_id}")
            return None

        if input_data is not None:
            job_run.input_data = input_data

        if output_data is not None:
            job_run.output_data = output_data

        self.session.commit()
        self.session.refresh(job_run)

        logger.info(
            f"Job run data updated successfully",
            extra={
                "job_run_id": job_id,
                "has_input_data": input_data is not None,
                "has_output_data": output_data is not None
            }
        )

        return job_run
