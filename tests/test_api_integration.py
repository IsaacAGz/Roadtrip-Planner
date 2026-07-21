import asyncio
import json
from contextlib import contextmanager
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.itinerary import RoadtripPlan
from app.models.job import JobStatus, ProgressStage
from app.models.validation import RuleViolation, ValidationReport, ValidationResult
from app.services.nominatim import GeocodedLocation
from app.services.osrm import RouteResult
from tests.helpers import sample_plan as _sample_plan


def _geocoded(name: str, *, lat: float, lon: float, country_code: str = "US") -> GeocodedLocation:
    return GeocodedLocation(
        display_name=name,
        lat=lat,
        lon=lon,
        country_code=country_code,
    )


GEOCODED_LOCATIONS = {
    "san diego, ca": _geocoded("San Diego, CA", lat=32.7, lon=-117.1),
    "portland, or": _geocoded("Portland, OR", lat=45.5, lon=-122.7),
    "vancouver, bc": _geocoded("Vancouver, BC", lat=49.2, lon=-123.1, country_code="CA"),
}


class FakeNominatimClient:
    def __init__(self, locations: dict[str, GeocodedLocation] | None = None) -> None:
        self.locations = GEOCODED_LOCATIONS if locations is None else locations

    async def geocode(self, query: str) -> GeocodedLocation:
        normalized = query.strip().lower()
        if normalized not in self.locations:
            raise ValueError(f"Could not geocode location: {query}")
        return self.locations[normalized]


class FakeOSRMClient:
    def __init__(self, *, duration_hours: float = 17.0, raise_error: bool = False) -> None:
        self.duration_hours_value = duration_hours
        self.raise_error = raise_error

    async def route(self, origin, destination) -> RouteResult:
        if self.raise_error:
            raise ValueError(f"OSRM could not find route between {origin} and {destination}")
        return RouteResult(distance_km=1700.0, duration_hours=self.duration_hours_value)


def _plan_payload(**overrides) -> dict:
    payload = {
        "origin": "San Diego, CA",
        "destination": "Portland, OR",
        "start_date": "2026-07-15",
        "end_date": "2026-07-19",
        "constraints": {"max_replan_attempts": 2},
    }
    payload.update(overrides)
    return payload


@contextmanager
def mock_feasibility_services(
    *,
    nominatim: FakeNominatimClient | None = None,
    osrm: FakeOSRMClient | None = None,
):
    with (
        patch(
            "app.validators.feasibility.get_nominatim_client",
            return_value=nominatim or FakeNominatimClient(),
        ),
        patch(
            "app.validators.feasibility.get_osrm_client",
            return_value=osrm or FakeOSRMClient(),
        ),
    ):
        yield


@contextmanager
def mock_planning_pipeline(
    *,
    plan: RoadtripPlan | None = None,
    hard_report: ValidationReport | None = None,
    soft_result: ValidationResult | None = None,
    planner: AsyncMock | None = None,
    validator: AsyncMock | None = None,
):
    sample = plan or _sample_plan()
    hard = hard_report or ValidationReport(approved=True, hard_failures=[], warnings=[])
    soft = soft_result or ValidationResult(approved=True)
    planner_mock = planner or AsyncMock(return_value=sample)
    with (
        patch("app.services.planning_job.run_planner", planner_mock),
        patch("app.services.planning_job.run_hard_validators", AsyncMock(return_value=hard)),
        patch("app.services.planning_job.run_validator", validator or AsyncMock(return_value=soft)),
    ):
        yield planner_mock


async def _wait_for_job(api_client, job_id: str, *, timeout: float = 5.0) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        response = await api_client.get(f"/trips/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            return body
        await asyncio.sleep(0.02)
    pytest.fail(f"Job {job_id} did not finish within {timeout}s")


@pytest.mark.asyncio
async def test_health_returns_ok(api_client):
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_plan_rejects_invalid_dates_with_pydantic_422(api_client):
    response = await api_client.post(
        "/trips/plan",
        json=_plan_payload(start_date="2026-07-20", end_date="2026-07-15"),
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("end_date must be on or after start_date" in str(item) for item in detail)


@pytest.mark.asyncio
async def test_plan_rejects_empty_origin_with_pydantic_422(api_client):
    response = await api_client.post(
        "/trips/plan",
        json=_plan_payload(origin="   "),
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("origin" in item.get("loc", []) for item in detail)


@pytest.mark.asyncio
async def test_plan_rejects_infeasible_trip_with_feas_001(api_client):
    nominatim = FakeNominatimClient()
    osrm = FakeOSRMClient(duration_hours=17.0)
    run_job = AsyncMock()

    with (
        mock_feasibility_services(nominatim=nominatim, osrm=osrm),
        patch("app.routers.trips.run_planning_job", run_job),
    ):
        response = await api_client.post(
            "/trips/plan",
            json=_plan_payload(end_date="2026-07-16"),
        )

    assert response.status_code == 422
    body = response.json()["detail"]
    assert body["rule_id"] == "FEAS-001"
    assert body["actual"] == 2
    assert body["limit"] == 3
    run_job.assert_not_called()


@pytest.mark.asyncio
async def test_plan_rejects_geocode_failure_with_feas_002(api_client):
    nominatim = FakeNominatimClient(locations={})
    osrm = FakeOSRMClient()
    run_job = AsyncMock()

    with (
        mock_feasibility_services(nominatim=nominatim, osrm=osrm),
        patch("app.routers.trips.run_planning_job", run_job),
    ):
        response = await api_client.post("/trips/plan", json=_plan_payload())

    assert response.status_code == 422
    body = response.json()["detail"]
    assert body["rule_id"] == "FEAS-002"
    assert body["actual"] == "San Diego, CA"
    run_job.assert_not_called()


@pytest.mark.asyncio
async def test_plan_rejects_disallowed_country_with_feas_002(api_client):
    nominatim = FakeNominatimClient()
    osrm = FakeOSRMClient()
    run_job = AsyncMock()

    with (
        mock_feasibility_services(nominatim=nominatim, osrm=osrm),
        patch("app.routers.trips.run_planning_job", run_job),
    ):
        response = await api_client.post(
            "/trips/plan",
            json=_plan_payload(destination="Vancouver, BC"),
        )

    assert response.status_code == 422
    body = response.json()["detail"]
    assert body["rule_id"] == "FEAS-002"
    assert body["actual"] == "CA"
    run_job.assert_not_called()


@pytest.mark.asyncio
async def test_plan_rejects_osrm_failure_with_feas_003(api_client):
    nominatim = FakeNominatimClient()
    osrm = FakeOSRMClient(raise_error=True)
    run_job = AsyncMock()

    with (
        mock_feasibility_services(nominatim=nominatim, osrm=osrm),
        patch("app.routers.trips.run_planning_job", run_job),
    ):
        response = await api_client.post("/trips/plan", json=_plan_payload())

    assert response.status_code == 422
    assert response.json()["detail"]["rule_id"] == "FEAS-003"
    run_job.assert_not_called()


@pytest.mark.asyncio
async def test_plan_returns_202_with_job_id(api_client):
    with mock_feasibility_services(), mock_planning_pipeline():
        response = await api_client.post("/trips/plan", json=_plan_payload())

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == JobStatus.QUEUED.value
    assert body["job_id"]
    assert body["status_url"] == f"/trips/jobs/{body['job_id']}"
    assert body["events_url"] == f"/trips/jobs/{body['job_id']}/events"


@pytest.mark.asyncio
async def test_get_job_returns_404_for_unknown_id(api_client):
    response = await api_client.get("/trips/jobs/does-not-exist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_job_events_stream_returns_404_for_unknown_id(api_client):
    response = await api_client.get("/trips/jobs/does-not-exist/events")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_job_events_stream_returns_sse_updates(api_client):
    with mock_feasibility_services(), mock_planning_pipeline():
        create_response = await api_client.post("/trips/plan", json=_plan_payload())

    job_id = create_response.json()["job_id"]
    events: list[dict] = []

    async with api_client.stream("GET", f"/trips/jobs/{job_id}/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            events.append(json.loads(line.removeprefix("data: ")))
            if events[-1]["status"] in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
                break

    assert events
    assert events[-1]["status"] == JobStatus.COMPLETED.value
    assert events[-1]["result"]["plan"]["title"] == "Coastal road trip"
    if len(events) > 1:
        assert events[0]["status"] == JobStatus.QUEUED.value


@pytest.mark.asyncio
async def test_plan_job_completes_with_trip_response(api_client):
    with mock_feasibility_services(), mock_planning_pipeline():
        create_response = await api_client.post("/trips/plan", json=_plan_payload())

    job_id = create_response.json()["job_id"]
    body = await _wait_for_job(api_client, job_id)

    assert body["status"] == JobStatus.COMPLETED.value
    assert body["result"]["plan"]["title"] == "Coastal road trip"
    assert body["result"]["plan"]["total_days"] == 5
    assert len(body["result"]["plan"]["days"]) == 5
    assert body["result"]["validation"]["approved"] is True
    assert body["result"]["validation"]["hard_failures"] == []
    assert body["result"]["replan_attempts"] == 0


@pytest.mark.asyncio
async def test_plan_job_records_coarse_progress_stages(api_client):
    with mock_feasibility_services(), mock_planning_pipeline():
        create_response = await api_client.post("/trips/plan", json=_plan_payload())

    job_id = create_response.json()["job_id"]
    body = await _wait_for_job(api_client, job_id)
    stages = [event["stage"] for event in body["progress"]]

    assert ProgressStage.QUEUED.value in stages
    assert ProgressStage.PLANNING.value in stages
    assert ProgressStage.HARD_VALIDATION.value in stages
    assert ProgressStage.SOFT_VALIDATION.value in stages
    assert ProgressStage.COMPLETED.value in stages


@pytest.mark.asyncio
async def test_plan_job_retries_until_soft_validator_approves(api_client):
    validator = AsyncMock(
        side_effect=[
            ValidationResult(approved=False, replan_instructions=["Add more scenic stops"]),
            ValidationResult(approved=True),
        ]
    )

    with mock_feasibility_services(), mock_planning_pipeline(validator=validator) as planner:
        create_response = await api_client.post("/trips/plan", json=_plan_payload())

    body = await _wait_for_job(api_client, create_response.json()["job_id"])

    assert body["status"] == JobStatus.COMPLETED.value
    assert body["result"]["validation"]["approved"] is True
    assert body["result"]["replan_attempts"] == 1
    assert planner.call_count == 2
    assert validator.call_count == 2


@pytest.mark.asyncio
async def test_plan_job_returns_unapproved_plan_when_replan_exhausted(api_client):
    hard_failure = RuleViolation(
        rule_id="DRIVE-001",
        severity="error",
        day=1,
        message="Driving exceeds daily limit",
        actual=7.0,
        limit=6.0,
    )
    hard_report = ValidationReport(approved=False, hard_failures=[hard_failure], warnings=[])

    with mock_feasibility_services(), mock_planning_pipeline(hard_report=hard_report) as planner:
        create_response = await api_client.post(
            "/trips/plan",
            json=_plan_payload(constraints={"max_replan_attempts": 1}),
        )

    body = await _wait_for_job(api_client, create_response.json()["job_id"])

    assert body["status"] == JobStatus.COMPLETED.value
    assert body["result"]["validation"]["approved"] is False
    assert body["result"]["validation"]["hard_failures"][0]["rule_id"] == "DRIVE-001"
    assert body["result"]["replan_attempts"] == 1
    assert planner.call_count == 2
