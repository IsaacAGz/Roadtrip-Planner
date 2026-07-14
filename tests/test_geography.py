from datetime import date

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.validators.geography import validate_geography


def _plan(
    *,
    overnight_country: str = "US",
    stop_countries: list[str] | None = None,
) -> RoadtripPlan:
    stops = [
        Stop(name=f"Stop {index}", lat=36.0, lon=-121.0, country_code=code)
        for index, code in enumerate(stop_countries or [])
    ]
    return RoadtripPlan(
        title="Geography test",
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
                overnight=OvernightStop(
                    city="Overnight",
                    lat=36.6,
                    lon=-121.9,
                    country_code=overnight_country,
                ),
            )
        ],
    )


def test_geo_001_passes_for_allowed_overnight_and_stops():
    plan = _plan(overnight_country="US", stop_countries=["US", "MX"])
    constraints = TripConstraints(allowed_countries=["US", "MX"])

    violations = validate_geography(plan, constraints)

    assert violations == []


def test_geo_001_fails_for_disallowed_overnight_country():
    plan = _plan(overnight_country="CA")
    constraints = TripConstraints(allowed_countries=["US", "MX"])

    violations = validate_geography(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "GEO-001"
    assert "Overnight" in violations[0].message
    assert violations[0].actual == "CA"


def test_geo_001_fails_for_disallowed_stop_country():
    plan = _plan(overnight_country="US", stop_countries=["CA"])
    constraints = TripConstraints(allowed_countries=["US", "MX"])

    violations = validate_geography(plan, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "GEO-001"
    assert "Stop 'Stop 0'" in violations[0].message


def test_geo_001_skips_empty_country_codes():
    plan = _plan(overnight_country="", stop_countries=[""])
    constraints = TripConstraints(allowed_countries=["US"])

    violations = validate_geography(plan, constraints)

    assert violations == []
