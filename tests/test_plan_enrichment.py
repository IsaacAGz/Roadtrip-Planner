from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.models.scaffold import DayLegSpec, TripScaffold
from app.models.trip import TripRequest
from app.services.nominatim import GeocodedLocation
from app.services.plan_enrichment import enrich_plan
from app.validators.driving import validate_driving
from app.validators.poi import validate_poi
from app.validators.routing import validate_routing
from app.validators.structure import validate_structure


class FakeOSRMClient:
    def __init__(
        self,
        *,
        duration_hours: float = 3.0,
        distance_km: float = 100.0,
        detour_km: float = 5.0,
    ) -> None:
        self.duration_hours_value = duration_hours
        self.distance_km_value = distance_km
        self.detour_km_value = detour_km

    async def duration_hours(self, origin, destination) -> float:
        return self.duration_hours_value

    async def distance_km(self, origin, destination) -> float:
        if origin == destination:
            return 0.0
        lat1, lon1 = origin
        lat2, lon2 = destination
        return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5 * 100

    async def route_geometry(self, origin, destination):
        from app.services.osrm import RouteGeometry

        return RouteGeometry(
            distance_km=100.0,
            duration_hours=self.duration_hours_value,
            coordinates=[origin, destination],
        )


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Diego, CA",
        "destination": "Portland, OR",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 15),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


def _plan_with_bad_structure() -> RoadtripPlan:
    return RoadtripPlan(
        title="Broken structure",
        total_days=99,
        origin_lat=32.7,
        origin_lon=-117.1,
        destination_lat=45.5,
        destination_lon=-122.7,
        days=[
            DayPlan(
                day=9,
                date=date(2026, 1, 1),
                route_summary="Day",
                driving_hours=9.0,
                overnight=OvernightStop(city="Monterey", lat=36.6, lon=-121.9, country_code="US"),
            )
        ],
    )


@pytest.mark.asyncio
async def test_enrich_plan_repairs_structure():
    request = _request()
    plan = _plan_with_bad_structure()

    enriched = await enrich_plan(plan, request)

    assert enriched.total_days == 1
    assert enriched.days[0].day == 1
    assert enriched.days[0].date == date(2026, 7, 15)
    violations = validate_structure(enriched, request, request.constraints)
    assert violations == []


@pytest.mark.asyncio
async def test_enrich_plan_overwrites_driving_hours_from_osrm():
    request = _request()
    plan = _plan_with_bad_structure()
    fake_osrm = FakeOSRMClient(duration_hours=2.5)

    with (
        patch("app.services.plan_enrichment.get_osrm_client", return_value=fake_osrm),
        patch("app.services.routing_utils.get_osrm_client", return_value=fake_osrm),
        patch("app.validators.driving.get_osrm_client", return_value=fake_osrm),
    ):
        enriched = await enrich_plan(plan, request)

        assert enriched.days[0].driving_hours == 2.5
        assert enriched.days[0].leg_start_lat == plan.origin_lat
        assert enriched.days[0].leg_end_lat == enriched.days[0].overnight.lat
        violations = await validate_driving(enriched, request.constraints)
        assert violations == []


@pytest.mark.asyncio
async def test_enrich_plan_sets_missing_leg_coords():
    request = _request()
    plan = _plan_with_bad_structure()
    plan.days[0].leg_start_lat = None
    plan.days[0].leg_start_lon = None
    plan.days[0].leg_end_lat = None
    plan.days[0].leg_end_lon = None

    enriched = await enrich_plan(plan, request)

    assert enriched.days[0].leg_start_lat is not None
    assert enriched.days[0].leg_end_lat is not None


@pytest.mark.asyncio
async def test_enrich_plan_drops_excluded_poi_categories():
    request = _request()
    plan = _plan_with_bad_structure()
    plan.days[0].stops = [
        Stop(
            name="Bad stop",
            lat=36.5,
            lon=-121.8,
            category="illegal",
            country_code="US",
        )
    ]

    enriched = await enrich_plan(plan, request)

    assert enriched.days[0].stops == []
    violations = validate_poi(enriched, request.constraints)
    assert violations == []


@pytest.mark.asyncio
async def test_enrich_plan_trims_over_detour_stops():
    request = _request(constraints={"max_detour_km_per_stop": 10.0})
    plan = _plan_with_bad_structure()
    plan.days[0].stops = [
        Stop(name="Near stop", lat=34.65, lon=-119.5, category="museum", country_code="US"),
        Stop(name="Far stop", lat=37.5, lon=-120.0, category="museum", country_code="US"),
    ]

    fake_osrm = FakeOSRMClient()
    with (
        patch("app.services.plan_enrichment.get_osrm_client", return_value=fake_osrm),
        patch("app.services.routing_utils.get_osrm_client", return_value=fake_osrm),
        patch("app.validators.routing.get_osrm_client", return_value=fake_osrm),
    ):
        enriched = await enrich_plan(plan, request)

        assert len(enriched.days[0].stops) == 1
        assert enriched.days[0].stops[0].name == "Near stop"
        violations = await validate_routing(enriched, request.constraints)
        assert violations == []


@pytest.mark.asyncio
async def test_enrich_plan_trims_excess_stop_count():
    request = _request(constraints={"max_stops_per_day": 2})
    plan = _plan_with_bad_structure()
    plan.days[0].stops = [
        Stop(name=f"Stop {index}", lat=36.5 + index * 0.01, lon=-121.8, country_code="US")
        for index in range(4)
    ]

    enriched = await enrich_plan(plan, request)

    assert len(enriched.days[0].stops) == 2


@pytest.mark.asyncio
async def test_enrich_plan_structure_only_preserves_far_overnight():
    request = _request()
    plan = _plan_with_bad_structure()
    scaffold = TripScaffold(
        origin=GeocodedLocation("San Diego", 32.7, -117.1, "US"),
        destination=GeocodedLocation("Portland", 45.5, -122.7, "US"),
        trip_duration_hours=17.0,
        route_geometry=[[32.7, -117.1], [34.0, -118.0]],
        days=[
            DayLegSpec(
                day=1,
                leg_start_lat=32.7,
                leg_start_lon=-117.1,
                leg_end_lat=34.0,
                leg_end_lon=-118.0,
                max_driving_hours=6.0,
                suggested_overnight_city="Scaffold City",
                suggested_overnight_lat=34.0,
                suggested_overnight_lon=-118.0,
                country_code="US",
            )
        ],
    )
    plan.days[0].overnight.city = "Planner City"
    plan.days[0].overnight.lat = 36.6
    plan.days[0].overnight.lon = -121.9

    enriched = await enrich_plan(plan, request, scaffold=scaffold, scaffold_mode="structure_only")

    assert enriched.days[0].overnight.city == "Planner City"
    assert enriched.days[0].overnight.lat == 36.6


@pytest.mark.asyncio
async def test_enrich_plan_clears_property_name_when_scaffold_replaces_overnight():
    request = _request()
    plan = _plan_with_bad_structure()
    scaffold = TripScaffold(
        origin=GeocodedLocation("San Diego", 32.7, -117.1, "US"),
        destination=GeocodedLocation("Portland", 45.5, -122.7, "US"),
        trip_duration_hours=17.0,
        route_geometry=[],
        days=[
            DayLegSpec(
                day=1,
                leg_start_lat=32.7,
                leg_start_lon=-117.1,
                leg_end_lat=34.0,
                leg_end_lon=-118.0,
                max_driving_hours=6.0,
                suggested_overnight_city="Scaffold City",
                suggested_overnight_lat=34.0,
                suggested_overnight_lon=-118.0,
                country_code="US",
            )
        ],
    )
    plan.days[0].overnight.property_name = "Planner Inn"
    plan.days[0].overnight.lat = 36.6
    plan.days[0].overnight.lon = -121.9

    enriched = await enrich_plan(plan, request, scaffold=scaffold, scaffold_mode="enforce")

    assert enriched.days[0].overnight.city == "Scaffold City"
    assert enriched.days[0].overnight.property_name is None


@pytest.mark.asyncio
async def test_enrich_plan_attaches_route_geometry_from_scaffold():
    request = _request()
    plan = _plan_with_bad_structure()
    scaffold = TripScaffold(
        origin=GeocodedLocation("San Diego", 32.7, -117.1, "US"),
        destination=GeocodedLocation("Portland", 45.5, -122.7, "US"),
        trip_duration_hours=17.0,
        route_geometry=[[32.7, -117.1], [40.0, -120.0], [45.5, -122.7]],
        days=[],
    )

    enriched = await enrich_plan(plan, request, scaffold=scaffold)

    assert enriched.route_geometry == scaffold.route_geometry


def test_plan_json_for_llm_prompt_excludes_route_geometry():
    plan = _plan_with_bad_structure()
    plan.route_geometry = [[32.7, -117.1], [40.0, -120.0], [45.5, -122.7]]

    prompt_json = plan.json_for_llm_prompt()

    assert "route_geometry" not in prompt_json
    assert plan.model_dump_json().count("route_geometry") == 1
