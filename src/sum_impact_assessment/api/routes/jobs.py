"""
Job management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from ...database.connection import get_db, get_db_session
from ...repositories.job_repository import JobRepository
from ...schemas.job import JobNameEnum, JobRunResponse
from ...jobs import get_job_class
from ...utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/jobs")


def execute_job_in_background(job_name: JobNameEnum, job_id: str):
    """
    Execute a job in the background.

    Args:
        job_name: The name of the job to execute
        job_id: The UUID of the job run to track
    """
    logger.info(
        f"Background task started for job",
        extra={
            "job_name": job_name.value,
            "job_id": job_id
        }
    )

    # Get a new database session for the background task
    with get_db_session() as db:
        try:
            # Get the job class and execute
            job_class = get_job_class(job_name)
            job_class.run(job_id=job_id, db=db)
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


@router.post("/{job_name}", response_model=JobRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_job(
    job_name: JobNameEnum,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger a job execution.

    Creates a new job run with PENDING status, schedules it for background execution,
    and returns the job run details.

    Args:
        job_name: Name of the job to trigger (must be a valid JobNameEnum value)
        background_tasks: FastAPI background tasks manager
        db: Database session (injected)

    Returns:
        JobRunResponse with job run details

    Raises:
        HTTPException 404: If the job name is not found in the registry
        HTTPException 500: If there's a database error
    """
    logger.info(f"Job trigger request received",
                extra={"job_name": job_name.value})

    try:
        # Verify the job exists in the registry
        try:
            get_job_class(job_name)
        except KeyError:
            logger.warning(f"Job not found in registry: {job_name.value}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_name.value}' not found in registry"
            )

        # Create a new job run with PENDING status
        job_repo = JobRepository(db)
        job_run = job_repo.create_job_run(job_name=job_name.value)

        logger.info(
            f"Job run created",
            extra={
                "job_name": job_name.value,
                "job_id": job_run.id,
                "status": job_run.status
            }
        )

        # Schedule the job for background execution
        background_tasks.add_task(
            execute_job_in_background, job_name, job_run.id)

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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering job: {str(e)}"
        )
