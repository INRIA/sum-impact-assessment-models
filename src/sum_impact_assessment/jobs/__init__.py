"""
Job registry and base infrastructure for background job execution.
"""
from typing import Dict, Type
from ..services.kpi_measures_analysis_job import KpiMeasuresAnalysisJob
from ..schemas.job import JobNameEnum

# Job registry mapping job names to job classes
JOB_REGISTRY: Dict[JobNameEnum, Type] = {
    JobNameEnum.KPI_MEASURES_ANALYSIS: KpiMeasuresAnalysisJob
}


def get_job_class(job_name: JobNameEnum):
    """
    Get the job class for a given job name.

    Args:
        job_name: The name of the job (from JobNameEnum)

    Returns:
        The job class corresponding to the job name

    Raises:
        KeyError: If the job name is not registered
    """
    return JOB_REGISTRY[job_name]
