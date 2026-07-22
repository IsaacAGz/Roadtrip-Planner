from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.trip import TripRequest
from app.models.validation import RuleViolation, ValidationReport, ValidationResult
from app.services.job_store import JobStore
from app.services.planning_job import run_planning_job
from app.services.trip_scaffold import ScaffoldValidationError
from tests.helpers import sample_plan


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Diego, CA",
        "destination": "Portland, OR",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 19),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


@pytest.fixture
def store():
    job_store = JobStore()
    with patch("app.services.planning_job.job_store", job_store):
        yield job_store


@pytest.mark.asyncio
async def test_run_planning_job_completes_successfully(store):
    plan = sample_plan()
    hard_report = ValidationReport(approved=True, hard_failures=[], warnings=[])
    soft_result = ValidationResult(approved=True)
    job = store.create_job(_request())

    with (
        patch("app.services.planning_job.resolve_feasibility", AsyncMock()),
        patch("app.services.planning_job.build_trip_scaffold", AsyncMock(return_value=None)),
        patch("app.services.planning_job.validate_scaffold_legs", AsyncMock()),
        patch("app.services.planning_job.enrich_plan", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_weather", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_accommodations", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_planner", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_hard_validators", AsyncMock(return_value=hard_report)),
        patch("app.services.planning_job.run_validator", AsyncMock(return_value=soft_result)),
    ):
        await run_planning_job(job.job_id, job.request)

    updated = store.get_job(job.job_id)
    assert updated is not None
    assert updated.status.value == "completed"
    assert updated.result is not None
    assert updated.result.validation.approved is True


@pytest.mark.asyncio
async def test_run_planning_job_marks_failed_on_exception(store):
    job = store.create_job(_request())

    with (
        patch("app.services.planning_job.resolve_feasibility", AsyncMock()),
        patch("app.services.planning_job.build_trip_scaffold", AsyncMock(return_value=None)),
        patch("app.services.planning_job.run_planner", AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        await run_planning_job(job.job_id, job.request)

    updated = store.get_job(job.job_id)
    assert updated is not None
    assert updated.status.value == "failed"
    assert updated.error == "boom"


@pytest.mark.asyncio
async def test_run_planning_job_records_progress_events(store):
    plan = sample_plan()
    hard_report = ValidationReport(approved=True, hard_failures=[], warnings=[])
    soft_result = ValidationResult(approved=True)
    job = store.create_job(_request())

    with (
        patch("app.services.planning_job.resolve_feasibility", AsyncMock()),
        patch("app.services.planning_job.build_trip_scaffold", AsyncMock(return_value=None)),
        patch("app.services.planning_job.validate_scaffold_legs", AsyncMock()),
        patch("app.services.planning_job.enrich_plan", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_weather", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_accommodations", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_planner", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_hard_validators", AsyncMock(return_value=hard_report)),
        patch("app.services.planning_job.run_validator", AsyncMock(return_value=soft_result)),
    ):
        await run_planning_job(job.job_id, job.request)

    updated = store.get_job(job.job_id)
    assert updated is not None
    stages = [event.stage.value for event in updated.progress]
    assert "planning" in stages
    assert "hard_validation" in stages
    assert "soft_validation" in stages


@pytest.mark.asyncio
async def test_run_planning_job_retries_on_hard_failures(store):
    plan = sample_plan()
    hard_failure = RuleViolation(
        rule_id="DRIVE-001",
        severity="error",
        day=1,
        message="Too much driving",
        actual=7.0,
        limit=6.0,
    )
    hard_report = ValidationReport(approved=False, hard_failures=[hard_failure], warnings=[])
    planner = AsyncMock(return_value=plan)
    job = store.create_job(_request(constraints={"max_replan_attempts": 1}))

    with (
        patch("app.services.planning_job.resolve_feasibility", AsyncMock()),
        patch("app.services.planning_job.build_trip_scaffold", AsyncMock(return_value=None)),
        patch("app.services.planning_job.validate_scaffold_legs", AsyncMock()),
        patch("app.services.planning_job.enrich_plan", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_weather", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_accommodations", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_planner", planner),
        patch("app.services.planning_job.run_hard_validators", AsyncMock(return_value=hard_report)),
        patch("app.services.planning_job.run_validator", AsyncMock()),
    ):
        await run_planning_job(job.job_id, job.request)

    updated = store.get_job(job.job_id)
    assert updated is not None
    assert updated.result is not None
    assert updated.result.validation.approved is False
    assert planner.call_count == 2
    assert planner.call_args_list[1].args[1][0].startswith("DRIVE-001 day 1:")


@pytest.mark.asyncio
async def test_run_planning_job_fails_when_scaffold_validation_fails(store):
    job = store.create_job(_request())
    planner = AsyncMock()

    with (
        patch("app.services.planning_job.resolve_feasibility", AsyncMock()),
        patch("app.services.planning_job.build_trip_scaffold", AsyncMock(return_value=object())),
        patch(
            "app.services.planning_job.validate_scaffold_legs",
            AsyncMock(
                side_effect=ScaffoldValidationError(
                    rule_id="SCAFFOLD-001",
                    message="Day 7 would require 14.9h driving",
                    day=7,
                    actual=14.9,
                    limit=6.0,
                )
            ),
        ),
        patch("app.services.planning_job.run_planner", planner),
    ):
        await run_planning_job(job.job_id, job.request)

    updated = store.get_job(job.job_id)
    assert updated is not None
    assert updated.status.value == "failed"
    assert "14.9h" in (updated.error or "")
    planner.assert_not_called()


@pytest.mark.asyncio
async def test_run_planning_job_uses_structure_only_enrichment_after_drive_failure(store):
    plan = sample_plan()
    hard_failure = RuleViolation(
        rule_id="DRIVE-001",
        severity="error",
        day=7,
        message="Too much driving",
        actual=14.9,
        limit=6.0,
    )
    hard_report = ValidationReport(approved=False, hard_failures=[hard_failure], warnings=[])
    enrich = AsyncMock(return_value=plan)
    job = store.create_job(_request(constraints={"max_replan_attempts": 1}))

    with (
        patch("app.services.planning_job.resolve_feasibility", AsyncMock()),
        patch("app.services.planning_job.build_trip_scaffold", AsyncMock(return_value=None)),
        patch("app.services.planning_job.validate_scaffold_legs", AsyncMock()),
        patch("app.services.planning_job.enrich_plan", enrich),
        patch("app.services.planning_job.enrich_weather", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.enrich_accommodations", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_planner", AsyncMock(return_value=plan)),
        patch("app.services.planning_job.run_hard_validators", AsyncMock(return_value=hard_report)),
        patch("app.services.planning_job.run_validator", AsyncMock()),
    ):
        await run_planning_job(job.job_id, job.request)

    assert enrich.call_args_list[1].kwargs["scaffold_mode"] == "structure_only"
