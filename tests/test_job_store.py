import asyncio
from datetime import date

import pytest

from app.models.job import JobStatus, ProgressStage
from app.models.trip import TripRequest, TripResponse
from app.models.validation import ValidationReport
from app.services.job_store import JobStore
from tests.helpers import sample_plan


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Jose, CA",
        "destination": "Monterey, CA",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 15),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


def test_create_job_starts_queued():
    store = JobStore()
    job = store.create_job(_request())

    assert job.status == JobStatus.QUEUED
    assert job.progress[0].stage == ProgressStage.QUEUED


def test_get_job_returns_none_for_missing_id():
    store = JobStore()

    assert store.get_job("missing") is None


def test_complete_job_sets_result_and_completed_status():
    store = JobStore()
    job = store.create_job(_request())

    result = TripResponse(
        plan=sample_plan(days=1),
        validation=ValidationReport(approved=True),
        replan_attempts=0,
    )

    store.complete(job.job_id, result)
    updated = store.get_job(job.job_id)

    assert updated is not None
    assert updated.status == JobStatus.COMPLETED
    assert updated.result == result
    assert updated.progress[-1].stage == ProgressStage.COMPLETED


def test_fail_job_sets_error_and_failed_status():
    store = JobStore()
    job = store.create_job(_request())

    store.fail(job.job_id, "planner crashed")
    updated = store.get_job(job.job_id)

    assert updated is not None
    assert updated.status == JobStatus.FAILED
    assert updated.error == "planner crashed"
    assert updated.progress[-1].stage == ProgressStage.FAILED


@pytest.mark.asyncio
async def test_job_store_notifies_subscribers_on_update():
    store = JobStore()
    job = store.create_job(_request())
    queue = store.subscribe(job.job_id)

    store.set_running(job.job_id)
    update = await asyncio.wait_for(queue.get(), timeout=1)

    assert update is not None
    assert update.status == JobStatus.RUNNING
    assert update.job_id == job.job_id
