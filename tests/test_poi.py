from datetime import date

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.validators.poi import validate_poi


def _plan(stops: list[Stop]) -> RoadtripPlan:
    return RoadtripPlan(
        title="POI test",
        total_days=1,
        origin_lat=37.0,
        origin_lon=-122.0,
        destination_lat=36.6,
        destination_lon=-121.9,
        days=[
            DayPlan(
                day=1,
                date=date(2026, 7, 15),
                route_summary="Test day",
                driving_hours=2.0,
                stops=stops,
                overnight=OvernightStop(city="Monterey", lat=36.6, lon=-121.9, country_code="US"),
            )
        ],
    )


def test_poi_003_passes_for_allowed_categories():
    plan = _plan([Stop(name="Museum", lat=36.6, lon=-121.9, category="museum", country_code="US")])
    constraints = TripConstraints()

    violations = validate_poi(plan, constraints)

    assert violations == []


def test_poi_003_fails_for_system_excluded_category():
    plan = _plan(
        [Stop(name="Bad stop", lat=36.6, lon=-121.9, category="illegal", country_code="US")]
    )
    constraints = TripConstraints()

    violations = validate_poi(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "POI-003"
    assert violations[0].actual == "illegal"


def test_poi_003_fails_for_custom_excluded_category():
    plan = _plan(
        [Stop(name="Casino", lat=36.6, lon=-121.9, category="casino", country_code="US")]
    )
    constraints = TripConstraints(excluded_poi_categories=["extremely_dangerous", "illegal", "casino"])

    violations = validate_poi(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "POI-003"
    assert violations[0].actual == "casino"


def test_poi_003_normalizes_category_before_matching():
    plan = _plan(
        [
            Stop(
                name="Danger zone",
                lat=36.6,
                lon=-121.9,
                category="Extremely Dangerous",
                country_code="US",
            )
        ]
    )
    constraints = TripConstraints()

    violations = validate_poi(plan, constraints)

    assert len(violations) == 1
    assert violations[0].actual == "extremely_dangerous"
