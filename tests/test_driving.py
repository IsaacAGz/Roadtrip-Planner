from datetime import date
from unittest.mock import patch

import pytest

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.validators.driving import validate_driving


class FakeOSRMClient:
    def __init__(self, duration_hours: float = 2.0, *, raise_error: bool = False) -> None:
        self.duration_hours_value = duration_hours
        self.raise_error = raise_error

    async def duration_hours(self, origin: tuple[float, float], destination: tuple[float, float]) -> float:
        if self.raise_error:
            raise ValueError("OSRM route not found")
        return self.duration_hours_value


def _day(
    *,
    driving_hours: float = 2.0,
    stops: list[Stop] | None = None,
    with_leg: bool = True,
) -> DayPlan:
    return DayPlan(
        day=1,
        date=date(2026, 7, 15),
        route_summary="Test day",
        driving_hours=driving_hours,
        stops=stops or [],
        overnight=OvernightStop(city="Monterey", lat=36.6, lon=-121.9, country_code="US"),
        leg_start_lat=37.0 if with_leg else None,
        leg_start_lon=-122.0 if with_leg else None,
        leg_end_lat=36.6 if with_leg else None,
        leg_end_lon=-121.9 if with_leg else None,
    )


def _plan(day: DayPlan) -> RoadtripPlan:
    return RoadtripPlan(
        title="Driving test",
        total_days=1,
        origin_lat=37.0,
        origin_lon=-122.0,
        destination_lat=36.6,
        destination_lon=-121.9,
        days=[day],
    )


@pytest.fixture
def fake_osrm():
    with patch("app.validators.driving.get_osrm_client") as mock_get:
        yield mock_get


@pytest.mark.asyncio
async def test_drive_001_fails_when_stated_driving_hours_exceed_limit(fake_osrm):
    fake_osrm.return_value = FakeOSRMClient(duration_hours=2.0)
    plan = _plan(_day(driving_hours=7.0))
    constraints = TripConstraints(max_driving_hours_per_day=6.0)

    violations = await validate_driving(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "DRIVE-001"
    assert violations[0].actual == 7.0


@pytest.mark.asyncio
async def test_drive_001_fails_when_osrm_verified_hours_exceed_limit(fake_osrm):
    fake_osrm.return_value = FakeOSRMClient(duration_hours=7.0)
    plan = _plan(_day(driving_hours=2.0))
    constraints = TripConstraints(max_driving_hours_per_day=6.0)

    violations = await validate_driving(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "DRIVE-001"
    assert "OSRM-verified" in violations[0].message
    assert violations[0].actual == 7.0


@pytest.mark.asyncio
async def test_drive_002_fails_when_osrm_cannot_verify_leg(fake_osrm):
    fake_osrm.return_value = FakeOSRMClient(raise_error=True)
    plan = _plan(_day(driving_hours=2.0))
    constraints = TripConstraints()

    violations = await validate_driving(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "DRIVE-002"


@pytest.mark.asyncio
async def test_sched_001_fails_when_too_many_stops(fake_osrm):
    fake_osrm.return_value = FakeOSRMClient()
    stops = [
        Stop(name=f"Stop {index}", lat=36.0 + index * 0.1, lon=-121.0, country_code="US")
        for index in range(3)
    ]
    plan = _plan(_day(stops=stops))
    constraints = TripConstraints(max_stops_per_day=2)

    violations = await validate_driving(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "SCHED-001"
    assert violations[0].actual == 3


@pytest.mark.asyncio
async def test_passes_with_valid_driving_and_stop_count(fake_osrm):
    fake_osrm.return_value = FakeOSRMClient(duration_hours=2.0)
    plan = _plan(_day(driving_hours=2.0, stops=[Stop(name="One stop", lat=36.5, lon=-121.5, country_code="US")]))
    constraints = TripConstraints(max_driving_hours_per_day=6.0, max_stops_per_day=2)

    violations = await validate_driving(plan, constraints)

    assert violations == []
