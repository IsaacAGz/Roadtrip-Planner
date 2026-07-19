from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.constraints import TripConstraints
from app.models.trip import TripRequest
from app.services.nominatim import GeocodedLocation
from app.services.osrm import RouteResult
from app.validators.feasibility import FeasibilityError, check_trip_feasibility


def _geocoded(name: str, *, lat: float, lon: float, country_code: str = "US") -> GeocodedLocation:
    return GeocodedLocation(
        display_name=name,
        lat=lat,
        lon=lon,
        country_code=country_code,
    )


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Diego, CA",
        "destination": "Portland, OR",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 19),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


class FakeNominatimClient:
    def __init__(self, locations: dict[str, GeocodedLocation] | None = None) -> None:
        self.locations = locations or {}

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


@pytest.fixture
def geocoded_locations():
    return {
        "san diego, ca": _geocoded("San Diego, CA", lat=32.7, lon=-117.1),
        "portland, or": _geocoded("Portland, OR", lat=45.5, lon=-122.7),
        "vancouver, bc": _geocoded("Vancouver, BC", lat=49.2, lon=-123.1, country_code="CA"),
    }


@pytest.mark.asyncio
async def test_feasibility_passes_for_sufficient_days(geocoded_locations):
    nominatim = FakeNominatimClient(geocoded_locations)
    osrm = FakeOSRMClient(duration_hours=17.0)
    request = _request()

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
    ):
        await check_trip_feasibility(request)


@pytest.mark.asyncio
async def test_feasibility_fails_when_trip_too_short(geocoded_locations):
    nominatim = FakeNominatimClient(geocoded_locations)
    osrm = FakeOSRMClient(duration_hours=17.0)
    request = _request(end_date=date(2026, 7, 16))

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
    ):
        with pytest.raises(FeasibilityError) as exc_info:
            await check_trip_feasibility(request)

    assert exc_info.value.rule_id == "FEAS-001"
    assert exc_info.value.actual == 2
    assert exc_info.value.limit == 3


@pytest.mark.asyncio
async def test_feasibility_doubles_hours_for_return_stops(geocoded_locations):
    nominatim = FakeNominatimClient(geocoded_locations)
    osrm = FakeOSRMClient(duration_hours=10.0)
    request = _request(
        end_date=date(2026, 7, 17),
        constraints=TripConstraints(allow_return_stops=True, max_backtracking_percent=25.0),
    )

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
    ):
        with pytest.raises(FeasibilityError) as exc_info:
            await check_trip_feasibility(request)

    assert exc_info.value.rule_id == "FEAS-001"
    assert exc_info.value.limit == 4


@pytest.mark.asyncio
async def test_feasibility_fails_when_origin_cannot_be_geocoded():
    nominatim = FakeNominatimClient({})
    osrm = FakeOSRMClient()
    request = _request()

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
    ):
        with pytest.raises(FeasibilityError) as exc_info:
            await check_trip_feasibility(request)

    assert exc_info.value.rule_id == "FEAS-002"
    assert exc_info.value.actual == "San Diego, CA"


@pytest.mark.asyncio
async def test_feasibility_fails_when_country_not_allowed(geocoded_locations):
    nominatim = FakeNominatimClient(geocoded_locations)
    osrm = FakeOSRMClient()
    request = _request(destination="Vancouver, BC")

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
    ):
        with pytest.raises(FeasibilityError) as exc_info:
            await check_trip_feasibility(request)

    assert exc_info.value.rule_id == "FEAS-002"
    assert exc_info.value.actual == "CA"


@pytest.mark.asyncio
async def test_feasibility_fails_when_osrm_route_not_found(geocoded_locations):
    nominatim = FakeNominatimClient(geocoded_locations)
    osrm = FakeOSRMClient(raise_error=True)
    request = _request()

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
    ):
        with pytest.raises(FeasibilityError) as exc_info:
            await check_trip_feasibility(request)

    assert exc_info.value.rule_id == "FEAS-003"


@pytest.mark.asyncio
async def test_feasibility_error_to_dict():
    error = FeasibilityError(
        rule_id="FEAS-001",
        message="Trip too short",
        actual=2,
        limit=3,
    )

    assert error.to_dict() == {
        "rule_id": "FEAS-001",
        "message": "Trip too short",
        "actual": 2,
        "limit": 3,
    }


@pytest.mark.asyncio
async def test_plan_endpoint_rejects_infeasible_trip_without_starting_job(api_client, geocoded_locations):
    nominatim = FakeNominatimClient(geocoded_locations)
    osrm = FakeOSRMClient(duration_hours=17.0)
    run_job = AsyncMock()

    with (
        patch("app.validators.feasibility.get_nominatim_client", return_value=nominatim),
        patch("app.validators.feasibility.get_osrm_client", return_value=osrm),
        patch("app.routers.trips.run_planning_job", run_job),
    ):
        response = await api_client.post(
            "/trips/plan",
            json={
                "origin": "San Diego, CA",
                "destination": "Portland, OR",
                "start_date": "2026-07-15",
                "end_date": "2026-07-16",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["rule_id"] == "FEAS-001"
    run_job.assert_not_called()
