"""
Unit tests for the full impact refresh orchestration service.
"""
from datetime import datetime
from unittest.mock import ANY, Mock, patch

import pytest

from src.sum_impact_assessment.schemas.job import JobStatusEnum
from src.sum_impact_assessment.services.full_impact_refresh_service import (
    build_dispatch_plan,
    build_initial_dispatch_state,
    dispatch_full_refresh,
    dispatch_full_refresh_sync,
)


def test_build_dispatch_plan_returns_expected_jobs():
    """The configured plan should include the expected 7 jobs in order."""
    started_at = datetime(2026, 5, 12, 10, 0, 0)

    plan = build_dispatch_plan(started_at)

    assert len(plan) == 7
    assert plan[0]["job_name"] == "kpi_measures_analysis"
    assert plan[0]["params"] == {"kpi_group_type": "KPI_SIEF"}
    assert plan[1]["actual_job_name"] == "mcda_analysis_quantitative_regulatory"
    assert plan[4]["actual_job_name"] == "mcda_analysis_qualitative_regulatory"
    assert plan[-1]["params"] == {"perspective": "nsm_providers"}


def test_build_initial_dispatch_state_sets_pending_status():
    """Initial dispatch state should mark all configured jobs as pending."""
    started_at = datetime(2026, 5, 12, 10, 0, 0)
    plan = build_dispatch_plan(started_at)

    dispatch_state = build_initial_dispatch_state(plan)

    assert len(dispatch_state) == len(plan)
    assert all(item["dispatch_status"] == "pending" for item in dispatch_state)
    assert all(item["job_run_id"] is None for item in dispatch_state)


@patch("src.sum_impact_assessment.services.full_impact_refresh_service.threading.Thread")
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.time.sleep")
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.JobRepository")
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.get_db_session")
def test_dispatch_full_refresh_sync_dispatches_all_children(
    mock_get_db_session,
    mock_job_repository_class,
    mock_sleep,
    mock_thread_class,
):
    """Dispatching the full refresh should create all child job runs and mark the parent successful."""
    started_at = datetime(2026, 5, 12, 10, 0, 0)
    plan = build_dispatch_plan(started_at)

    child_job_runs = [
        Mock(id=f"child-{index}", created_at=datetime(2026, 5, 12, 10, 0, index))
        for index in range(len(plan))
    ]

    repo_instance = Mock()
    repo_instance.create_job_run.side_effect = child_job_runs
    mock_job_repository_class.return_value = repo_instance

    db_context = Mock()
    db_context.__enter__ = Mock(return_value=Mock())
    db_context.__exit__ = Mock(return_value=None)
    mock_get_db_session.return_value = db_context

    dispatch_full_refresh_sync("parent-1", plan)

    assert repo_instance.create_job_run.call_count == 7
    assert repo_instance.update_dispatched_job.call_count == 7
    repo_instance.update_job_status.assert_any_call(
        "parent-1",
        status=JobStatusEnum.STARTED,
        started_at=ANY,
    )
    final_call = repo_instance.update_job_status.call_args_list[-1]
    assert final_call.kwargs["status"] == JobStatusEnum.SUCCESS
    assert mock_thread_class.call_count == 7
    assert mock_thread_class.return_value.start.call_count == 7
    assert mock_sleep.call_count == 6  # no trailing sleep after the last job
    first_thread_call = mock_thread_class.call_args_list[0]
    assert first_thread_call.kwargs["args"][1] == "child-0"
    first_update = repo_instance.update_dispatched_job.call_args_list[0]
    assert first_update.args[2]["job_run_id"] == "child-0"
    assert first_update.args[2]["scheduled_at"] == "2026-05-12T10:00:00"


@patch("src.sum_impact_assessment.services.full_impact_refresh_service.threading.Thread")
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.time.sleep")
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.JobRepository")
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.get_db_session")
def test_dispatch_full_refresh_sync_all_seven_children_are_started(
    mock_get_db_session,
    mock_job_repository_class,
    mock_sleep,
    mock_thread_class,
):
    """Regression: all 7 configured jobs must be passed to a started Thread — including the last one.

    Previously the last child (mcda_analysis_qualitative_nsm_providers) was never executed because
    asyncio.create_task was used without awaiting, and asyncio.run() closed the loop before the
    task had a chance to run in Docker environments with CPU contention.
    """
    started_at = datetime(2026, 5, 12, 10, 0, 0)
    plan = build_dispatch_plan(started_at)

    child_job_runs = [
        Mock(id=f"child-{i}", created_at=datetime(2026, 5, 12, 10, 0, i))
        for i in range(len(plan))
    ]

    repo_instance = Mock()
    repo_instance.create_job_run.side_effect = child_job_runs
    mock_job_repository_class.return_value = repo_instance

    db_context = Mock()
    db_context.__enter__ = Mock(return_value=Mock())
    db_context.__exit__ = Mock(return_value=None)
    mock_get_db_session.return_value = db_context

    dispatch_full_refresh_sync("parent-reg", plan)

    thread_child_ids = [
        call.kwargs["args"][1]
        for call in mock_thread_class.call_args_list
    ]
    expected_child_ids = [f"child-{i}" for i in range(7)]
    assert thread_child_ids == expected_child_ids, (
        f"Expected all 7 children to be started, got: {thread_child_ids}"
    )


@pytest.mark.anyio
@patch("src.sum_impact_assessment.services.full_impact_refresh_service.dispatch_full_refresh_sync")
async def test_dispatch_full_refresh_delegates_to_sync(
    mock_dispatch_full_refresh_sync,
):
    """The async wrapper should delegate to dispatch_full_refresh_sync."""
    plan = build_dispatch_plan(datetime(2026, 5, 12, 10, 0, 0))

    await dispatch_full_refresh("parent-1", plan)

    mock_dispatch_full_refresh_sync.assert_called_once_with("parent-1", plan)