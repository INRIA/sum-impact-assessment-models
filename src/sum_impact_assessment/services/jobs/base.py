"""
Base class for all background jobs — centralises the job lifecycle.

``BaseJob.run`` handles the common three-step lifecycle:
  1. Mark the run STARTED.
  2. Delegate to ``_execute`` (implemented by each concrete subclass).
  3. On unhandled exception: save error output and mark the run FAILURE.

Subclasses only need to implement ``_execute`` with the domain logic and
the final SUCCESS status update.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional

from sqlalchemy.orm import Session

from ...repositories.job_repository import JobRepository
from ...schemas.job import JobStatusEnum
from ...utils.logger import get_logger
from ...utils.time import utc_now

logger = get_logger(__name__)


class BaseJob(ABC):
    """Abstract base class that provides standard job lifecycle management."""

    @classmethod
    def run(cls, job_id: str, db: Session, params: Optional[Dict] = None) -> None:
        """Execute the job with standard lifecycle management."""
        job_repo = JobRepository(db)
        logger.info(f"Starting {cls.__name__}: {job_id}")
        job_repo.update_job_status(
            job_id=job_id,
            status=JobStatusEnum.STARTED,
            started_at=utc_now(),
        )
        try:
            cls._execute(job_id=job_id, db=db, params=params, job_repo=job_repo)
        except Exception as e:
            error_message = f"{cls.__name__} failed: {str(e)}"
            logger.error(error_message, extra={"job_id": job_id}, exc_info=True)
            job_repo.update_job_data(
                job_id=job_id,
                output_data={
                    "error": error_message,
                    "fatal": True,
                    "timestamp": utc_now().isoformat(),
                },
            )
            job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.FAILURE,
                message=error_message,
                completed_at=utc_now(),
            )

    @classmethod
    @abstractmethod
    def _execute(
        cls,
        job_id: str,
        db: Session,
        params: Optional[Dict],
        job_repo: JobRepository,
    ) -> None:
        """Implement domain logic — called by ``run`` with a ready ``job_repo``."""
        ...
