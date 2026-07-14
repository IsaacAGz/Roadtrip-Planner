from datetime import date
from unittest.mock import patch

import pytest

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.models.trip import TripRequest
from app.validators.hard import run_hard_validators
from app.validators.warnings import collect_warnings


def _distance_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    return ((origin[0] - destination[0]) ** 2 + (origin[1] - destination[1]) ** 2) ** 0.5 * 100


class FakeOSRMClient:
    def __init__(
        self,
        *,
        duration_hours: float = 2.0,
        distance_scale: float = 100.0,
    ) -> None:
        self.duration_hours_value = duration_hours
        self.distance_scale = distance_scale

    async def duration_hours(self, origin: tuple[float, float], destination: tuple[float, float]) -> float:
        return self.duration_hours_value

    async def distance_km(self, origin: tuple[float, float], destination: tuple[float, float]) -> float:
        return _distance_km(origin, destination) * (self.distance_scale / 100.0)


def _day(
    *,
    driving_hours: float = 2.0,
    stops: list[Stop] | None = None,
    overnight: tuple[float, float] = (36.6, -121.9),
    overnight_city: str = "Monterey",
    leg_start: tuple[float, float] = (37.0, -122.0),
    leg_end: tuple[float, float] = (36.6, -121.9),
) -> DayPlan:
    return DayPlan(
        day=1,
        date=date(2026, 7, 15),
        route_summary="Test day",
        driving_hours=driving_hours,
        stops=stops or [],
        overnight=OvernightStop(
            city=overnight_city,
            lat=overnight[0],
            lon=overnight[1],
            country_code="US",
        ),
        leg_start_lat=leg_start[0],
        leg_start_lon=leg_start[1],
        leg_end_lat=leg_end[0],
        leg_end_lon=leg_end[1],
    )


def _plan(*days: DayPlan, origin: tuple[float, float] = (0.0, 0.0), destination: tuple[float, float] = (10.0, 0.0)) -> RoadtripPlan:
    return RoadtripPlan(
        title="Warnings test",
        total_days=len(days),
        origin_lat=origin[0],
        origin_lon=origin[1],
        destination_lat=destination[0],
        destination_lon=destination[1],
        days=list(days),
    )


@pytest.fixture
def fake_osrm():
    client = FakeOSRMClient()
    with (
        patch("app.validators.warnings.get_osrm_client", return_value=client),
        patch("app.validators.routing.get_osrm_client", return_value=client),
        patch("app.validators.driving.get_osrm_client", return_value=client),
    ):
        yield client


@pytest.mark.asyncio
async def test_drive_warning_when_near_daily_limit(fake_osrm):
    fake_osrm.duration_hours_value = 5.5
    plan = _plan(_day(driving_hours=5.5))
    constraints = TripConstraints(max_driving_hours_per_day=6.0)

    warnings = await collect_warnings(plan, constraints)

    assert len(warnings) == 1
    assert warnings[0].rule_id == "DRIVE-001"
    assert warnings[0].severity == "warning"
    assert warnings[0].actual == 5.5


@pytest.mark.asyncio
async def test_no_drive_warning_when_well_below_limit(fake_osrm):
    fake_osrm.duration_hours_value = 4.0
    plan = _plan(_day(driving_hours=4.0))
    constraints = TripConstraints(max_driving_hours_per_day=6.0)

    warnings = await collect_warnings(plan, constraints)

    assert not any(w.rule_id == "DRIVE-001" for w in warnings)


@pytest.mark.asyncio
async def test_no_drive_warning_when_already_over_limit(fake_osrm):
    fake_osrm.duration_hours_value = 7.0
    plan = _plan(_day(driving_hours=7.0))
    constraints = TripConstraints(max_driving_hours_per_day=6.0)

    warnings = await collect_warnings(plan, constraints)

    assert not any(w.rule_id == "DRIVE-001" for w in warnings)


@pytest.mark.asyncio
async def test_sched_warning_when_at_stop_limit(fake_osrm):
    stops = [
        Stop(name="Stop A", lat=36.5, lon=-121.5, country_code="US"),
        Stop(name="Stop B", lat=36.6, lon=-121.4, country_code="US"),
    ]
    plan = _plan(_day(stops=stops))
    constraints = TripConstraints(max_stops_per_day=2)

    warnings = await collect_warnings(plan, constraints)

    assert len(warnings) == 1
    assert warnings[0].rule_id == "SCHED-001"
    assert warnings[0].severity == "warning"


@pytest.mark.asyncio
async def test_route_001_warning_when_detour_near_limit(fake_osrm):
    stop = Stop(name="Near detour", lat=5.0, lon=1.2, country_code="US")
    plan = _plan(
        _day(
            stops=[stop],
            leg_start=(0.0, 0.0),
            leg_end=(10.0, 0.0),
            overnight=(10.0, 0.0),
        ),
        origin=(0.0, 0.0),
        destination=(10.0, 0.0),
    )
    constraints = TripConstraints(max_detour_km_per_stop=30.0)

    warnings = await collect_warnings(plan, constraints)

    route_warnings = [w for w in warnings if w.rule_id == "ROUTE-001"]
    assert len(route_warnings) == 1
    assert route_warnings[0].severity == "warning"
    assert route_warnings[0].actual >= 24.0


@pytest.mark.asyncio
async def test_route_002_warning_when_backtracking_near_limit(fake_osrm):
    plan = _plan(
        DayPlan(
            day=1,
            date=date(2026, 7, 15),
            route_summary="Forward",
            driving_hours=2.0,
            overnight=OvernightStop(city="Far", lat=8.0, lon=0.0, country_code="US"),
            leg_start_lat=0.0,
            leg_start_lon=0.0,
            leg_end_lat=8.0,
            leg_end_lon=0.0,
        ),
        DayPlan(
            day=2,
            date=date(2026, 7, 16),
            route_summary="Slight back",
            driving_hours=2.0,
            overnight=OvernightStop(city="Closer", lat=6.8, lon=0.0, country_code="US"),
            leg_start_lat=8.0,
            leg_start_lon=0.0,
            leg_end_lat=6.8,
            leg_end_lon=0.0,
        ),
        origin=(0.0, 0.0),
        destination=(10.0, 0.0),
    )
    constraints = TripConstraints(max_backtracking_percent=15.0)

    warnings = await collect_warnings(plan, constraints)

    route_warnings = [w for w in warnings if w.rule_id == "ROUTE-002"]
    assert len(route_warnings) == 1
    assert route_warnings[0].severity == "warning"
    assert route_warnings[0].actual >= 12.0


@pytest.mark.asyncio
async def test_run_hard_validators_includes_warnings(fake_osrm):
    fake_osrm.duration_hours_value = 5.5
    plan = _plan(_day(driving_hours=5.5))
    request = TripRequest(
        origin="A",
        destination="B",
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
        constraints=TripConstraints(max_driving_hours_per_day=6.0),
    )

    report = await run_hard_validators(plan, request)

    assert report.approved is True
    assert report.hard_failures == []
    assert any(w.rule_id == "DRIVE-001" and w.severity == "warning" for w in report.warnings)
