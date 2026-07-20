from datetime import date
from unittest.mock import patch

import pytest

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.validators.routing import validate_routing


def _distance_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    return ((origin[0] - destination[0]) ** 2 + (origin[1] - destination[1]) ** 2) ** 0.5 * 100


class FakeOSRMClient:
    async def distance_km(self, origin: tuple[float, float], destination: tuple[float, float]) -> float:
        return _distance_km(origin, destination)


def _plan_with_day(
    *,
    origin: tuple[float, float],
    destination: tuple[float, float],
    overnight: tuple[float, float],
    stops: list[Stop] | None = None,
    driving_hours: float = 2.0,
) -> RoadtripPlan:
    return RoadtripPlan(
        title="Routing test",
        total_days=1,
        origin_lat=origin[0],
        origin_lon=origin[1],
        destination_lat=destination[0],
        destination_lon=destination[1],
        days=[
            DayPlan(
                day=1,
                date=date(2026, 7, 15),
                route_summary="Test leg",
                driving_hours=driving_hours,
                stops=stops or [],
                overnight=OvernightStop(
                    city="Overnight",
                    lat=overnight[0],
                    lon=overnight[1],
                    country_code="US",
                ),
                leg_start_lat=origin[0],
                leg_start_lon=origin[1],
                leg_end_lat=destination[0],
                leg_end_lon=destination[1],
            )
        ],
    )


@pytest.fixture
def fake_osrm():
    client = FakeOSRMClient()
    with (
        patch("app.services.routing_utils.get_osrm_client", return_value=client),
        patch("app.validators.routing.get_osrm_client", return_value=client),
    ):
        yield


@pytest.mark.asyncio
async def test_route_001_passes_when_stop_is_on_direct_leg(fake_osrm):
    origin = (0.0, 0.0)
    destination = (10.0, 0.0)
    stop = Stop(name="On route", lat=5.0, lon=0.0, country_code="US")
    plan = _plan_with_day(origin=origin, destination=destination, overnight=destination, stops=[stop])
    constraints = TripConstraints(max_detour_km_per_stop=30.0)

    violations = await validate_routing(plan, constraints)

    assert violations == []


@pytest.mark.asyncio
async def test_route_001_fails_when_stop_detour_exceeds_limit(fake_osrm):
    origin = (0.0, 0.0)
    destination = (10.0, 0.0)
    stop = Stop(name="Far detour", lat=5.0, lon=8.0, country_code="US")
    plan = _plan_with_day(origin=origin, destination=destination, overnight=destination, stops=[stop])
    constraints = TripConstraints(max_detour_km_per_stop=30.0)

    violations = await validate_routing(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "ROUTE-001"
    assert violations[0].day == 1
    assert violations[0].actual > 30.0


@pytest.mark.asyncio
async def test_route_002_fails_on_backtracking(fake_osrm):
    origin = (0.0, 0.0)
    destination = (10.0, 0.0)
    plan = RoadtripPlan(
        title="Backtrack test",
        total_days=2,
        origin_lat=origin[0],
        origin_lon=origin[1],
        destination_lat=destination[0],
        destination_lon=destination[1],
        days=[
            DayPlan(
                day=1,
                date=date(2026, 7, 15),
                route_summary="Forward",
                driving_hours=2.0,
                overnight=OvernightStop(city="Mid", lat=8.0, lon=0.0, country_code="US"),
                leg_start_lat=origin[0],
                leg_start_lon=origin[1],
                leg_end_lat=8.0,
                leg_end_lon=0.0,
            ),
            DayPlan(
                day=2,
                date=date(2026, 7, 16),
                route_summary="Back",
                driving_hours=2.0,
                overnight=OvernightStop(city="Back", lat=3.0, lon=0.0, country_code="US"),
                leg_start_lat=8.0,
                leg_start_lon=0.0,
                leg_end_lat=3.0,
                leg_end_lon=0.0,
            ),
        ],
    )
    constraints = TripConstraints(max_backtracking_percent=15.0)

    violations = await validate_routing(plan, constraints)

    assert any(v.rule_id == "ROUTE-002" for v in violations)


@pytest.mark.asyncio
async def test_skips_detour_check_when_day_has_no_driving(fake_osrm):
    origin = (0.0, 0.0)
    destination = (10.0, 0.0)
    stop = Stop(name="Far detour", lat=5.0, lon=8.0, country_code="US")
    plan = _plan_with_day(
        origin=origin,
        destination=destination,
        overnight=destination,
        stops=[stop],
        driving_hours=0.0,
    )
    constraints = TripConstraints(max_detour_km_per_stop=30.0)

    violations = await validate_routing(plan, constraints)

    assert not any(v.rule_id == "ROUTE-001" for v in violations)
