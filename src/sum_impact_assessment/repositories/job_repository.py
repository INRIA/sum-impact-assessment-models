"""
Repository for job run database operations.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, List, Optional
from ..database.models.job import JobRun
from ..schemas.job import JobNameEnum, JobStatusEnum
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

    def get_in_progress_full_refresh(self) -> Optional[JobRun]:
        """
        Retrieve the most recent full refresh run that is still dispatching jobs.
        """
        return (
            self.session.query(JobRun)
            .filter(JobRun.job_name == JobNameEnum.FULL_IMPACT_REFRESH.value)
            .filter(JobRun.status.in_([JobStatusEnum.PENDING, JobStatusEnum.STARTED]))
            .order_by(JobRun.created_at.desc())
            .first()
        )

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

        logger.debug(
            f"Job run data updated successfully",
            extra={
                "job_run_id": job_id,
                "has_input_data": input_data is not None,
                "has_output_data": output_data is not None
            }
        )

        return job_run

    def update_dispatched_job(
        self,
        job_id: str,
        sequence: int,
        updates: Dict,
    ) -> Optional[JobRun]:
        """
        Update a child dispatch entry inside the parent refresh run output payload.
        """
        job_run = self.get_job_run(job_id)

        if not job_run:
            logger.warning(f"Job run not found: {job_id}")
            return None

        output_data = job_run.output_data or {}
        dispatched_jobs = output_data.get("dispatched_jobs", [])
        entry_found = False

        for index, dispatched_job in enumerate(dispatched_jobs):
            if dispatched_job.get("sequence") == sequence:
                dispatched_jobs[index] = {
                    **dispatched_job,
                    **updates,
                }
                entry_found = True
                break

        if not entry_found:
            dispatched_jobs.append({"sequence": sequence, **updates})

        output_data["dispatched_jobs"] = dispatched_jobs
        job_run.output_data = output_data

        self.session.commit()
        self.session.refresh(job_run)

        return job_run

    def get_job_runs(
        self,
        job_name: Optional[str] = None,
        status: Optional[str] = None,
        created_at_from: Optional[datetime] = None,
        created_at_to: Optional[datetime] = None
    ) -> List[JobRun]:
        """
        Retrieve job runs with optional filters.

        Args:
            job_name: Filter by job name (exact match)
            status: Filter by status (exact match)
            created_at_from: Filter by creation date (inclusive start)
            created_at_to: Filter by creation date (inclusive end)

        Returns:
            List of JobRun instances matching the filters, ordered by created_at DESC
        """
        logger.debug(
            f"Retrieving job runs with filters",
            extra={
                "job_name": job_name,
                "status": status,
                "created_at_from": created_at_from,
                "created_at_to": created_at_to
            }
        )

        query = self.session.query(JobRun)

        # Apply filters dynamically
        if job_name is not None:
            query = query.filter(JobRun.job_name == job_name)

        if status is not None:
            query = query.filter(JobRun.status == status)

        if created_at_from is not None:
            query = query.filter(JobRun.created_at >= created_at_from)

        if created_at_to is not None:
            query = query.filter(JobRun.created_at <= created_at_to)

        # Order by created_at DESC (most recent first)
        query = query.order_by(JobRun.created_at.desc())

        results = query.all()

        logger.debug(
            f"Retrieved {len(results)} job run(s)",
            extra={
                "count": len(results),
                "filters_applied": {
                    "job_name": job_name,
                    "status": status,
                    "created_at_from": created_at_from,
                    "created_at_to": created_at_to
                }
            }
        )

        return results
