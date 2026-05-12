"""
Shared helpers for job dispatch and naming.
"""
from typing import Optional

from ..database.connection import get_db_session
from ..jobs import get_job_class
from ..schemas.job import JobNameEnum
from ..utils.logger import get_logger

logger = get_logger(__name__)


def resolve_actual_job_name(job_name: JobNameEnum, params: Optional[dict] = None) -> str:
    """
    Resolve the persisted job run name for MCDA jobs with perspective-specific variants.
    """
    if job_name in (
        JobNameEnum.MCDA_ANALYSIS_QUANTITATIVE,
        JobNameEnum.MCDA_ANALYSIS_QUALITATIVE,
    ) and params and "perspective" in params:
        perspective = params["perspective"]
        return f"{job_name.value}_{perspective}"

    return job_name.value


def execute_job_in_background(job_name: JobNameEnum, job_id: str, params: Optional[dict] = None) -> None:
    """
    Execute a job in the background using a dedicated database session.
    """
    logger.info(
        "Background task started for job",
        extra={
            "job_name": job_name.value,
            "job_id": job_id,
            "params": params
        }
    )

    with get_db_session() as db:
        try:
            job_class = get_job_class(job_name)
            job_class.run(job_id=job_id, db=db, params=params)
        except Exception as error:
            logger.error(
                "Background job execution failed",
                extra={
                    "job_name": job_name.value,
                    "job_id": job_id,
                    "error": str(error)
                },
                exc_info=True
            )