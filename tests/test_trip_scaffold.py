from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.scaffold import DayLegSpec, TripScaffold
from app.models.trip import TripRequest
from app.services.nominatim import GeocodedLocation
from app.services.osrm import LegSegment, RouteResult
from app.services.trip_scaffold import (
    ScaffoldValidationError,
    build_trip_scaffold,
    validate_scaffold_legs,
)
from app.validators.feasibility import FeasibilityContext


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Diego, CA",
        "destination": "Portland, OR",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 19),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


def _context() -> FeasibilityContext:
    return FeasibilityContext(
        origin=GeocodedLocation("San Diego, CA", 32.7, -117.1, "US"),
        destination=GeocodedLocation("Portland, OR", 45.5, -122.7, "US"),
        route=RouteResult(distance_km=1700.0, duration_hours=17.0),
    )


class FakeOSRMClient:
    async def split_route_into_legs(self, origin, destination, num_days, max_hours_per_day, **kwargs):
        legs = []
        for index in range(num_days):
            start_lat = origin[0] + index
            end_lat = origin[0] + index + 1
            legs.append(
                LegSegment(
                    start=(start_lat, origin[1]),
                    end=(end_lat, origin[1] + 0.5),
                    duration_hours=min(max_hours_per_day, 5.0),
                    distance_km=200.0,
                )
            )
        legs[-1] = LegSegment(
            start=legs[-1].start,
            end=destination,
            duration_hours=4.0,
            distance_km=250.0,
        )
        geometry = type(
            "Geometry",
            (),
            {
                "coordinates": [leg.end for leg in legs],
                "duration_hours": sum(leg.duration_hours for leg in legs),
            },
        )()
        return legs, geometry


class FakeNominatimClient:
    async def reverse_geocode(self, lat, lon):
        return GeocodedLocation(f"City at {lat:.1f}", lat, lon, "US")


@pytest.mark.asyncio
async def test_build_trip_scaffold_returns_none_for_return_trips():
    request = _request(constraints={"allow_return_stops": True})

    scaffold = await build_trip_scaffold(request, context=_context())

    assert scaffold is None


@pytest.mark.asyncio
async def test_build_trip_scaffold_produces_distinct_day_specs():
    request = _request()

    with (
        patch("app.services.trip_scaffold.get_osrm_client", return_value=FakeOSRMClient()),
        patch("app.services.trip_scaffold.get_nominatim_client", return_value=FakeNominatimClient()),
    ):
        scaffold = await build_trip_scaffold(request, context=_context())

    assert scaffold is not None
    assert len(scaffold.days) == 5
    overnight_coords = {
        (spec.suggested_overnight_lat, spec.suggested_overnight_lon) for spec in scaffold.days
    }
    assert len(overnight_coords) == 5
    assert scaffold.days[-1].leg_end_lat == _context().destination.lat
    assert all(spec.max_driving_hours <= request.constraints.max_driving_hours_per_day for spec in scaffold.days)
    assert len(scaffold.route_geometry) == 5


@pytest.mark.asyncio
async def test_build_trip_scaffold_uses_feasibility_context_endpoints():
    request = _request()

    with (
        patch("app.services.trip_scaffold.get_osrm_client", return_value=FakeOSRMClient()),
        patch("app.services.trip_scaffold.get_nominatim_client", return_value=FakeNominatimClient()),
    ):
        scaffold = await build_trip_scaffold(request, context=_context())

    assert scaffold is not None
    assert scaffold.origin.display_name == "San Diego, CA"
    assert scaffold.destination.display_name == "Portland, OR"


@pytest.mark.asyncio
async def test_validate_scaffold_legs_raises_when_leg_exceeds_limit():
    request = _request()
    scaffold = TripScaffold(
        origin=_context().origin,
        destination=_context().destination,
        trip_duration_hours=17.0,
        days=[
            DayLegSpec(
                day=1,
                leg_start_lat=32.7,
                leg_start_lon=-117.1,
                leg_end_lat=45.5,
                leg_end_lon=-122.7,
                max_driving_hours=6.0,
                suggested_overnight_city="Portland",
                suggested_overnight_lat=45.5,
                suggested_overnight_lon=-122.7,
                country_code="US",
            )
        ],
    )

    with patch(
        "app.services.trip_scaffold.get_osrm_client",
        return_value=type(
            "Client",
            (),
            {"duration_hours": AsyncMock(return_value=14.9)},
        )(),
    ):
        with pytest.raises(ScaffoldValidationError) as exc_info:
            await validate_scaffold_legs(scaffold, request)

    assert exc_info.value.rule_id == "SCAFFOLD-001"
    assert exc_info.value.day == 1
    assert "14.9h" in exc_info.value.message
