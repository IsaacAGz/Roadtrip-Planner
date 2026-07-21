from datetime import date

import pytest
from pydantic import ValidationError

from app.models.constraints import TripConstraints, effective_excluded_categories
from app.models.trip import TripRequest


def test_default_constraints_are_valid():
    constraints = TripConstraints()
    assert constraints.max_driving_hours_per_day == 6.0
    assert constraints.max_nights_per_stop == 1
    assert constraints.allowed_countries == ["US", "MX"]
    assert constraints.fail_on_weather_warnings is False
    assert constraints.max_precip_chance == 0.5
    assert constraints.min_temp_c == 10.0


def test_extended_stays_required_for_multi_night_stop():
    with pytest.raises(ValidationError, match="allow_extended_stays"):
        TripConstraints(max_nights_per_stop=2)


def test_extended_stays_allows_multi_night_stop():
    constraints = TripConstraints(allow_extended_stays=True, max_nights_per_stop=3)
    assert constraints.max_nights_per_stop == 3


def test_return_stops_clamps_backtracking_percent():
    constraints = TripConstraints(allow_return_stops=True, max_backtracking_percent=10.0)
    assert constraints.max_backtracking_percent == 25.0


def test_allowed_countries_normalized():
    constraints = TripConstraints(allowed_countries=[" us ", "mx"])
    assert constraints.allowed_countries == ["US", "MX"]


def test_empty_allowed_countries_rejected():
    with pytest.raises(ValidationError):
        TripConstraints(allowed_countries=[])


def test_effective_excluded_categories_merges_system_defaults():
    excluded = effective_excluded_categories(["museum"])
    assert "extremely_dangerous" in excluded
    assert "illegal" in excluded
    assert "museum" in excluded


def test_trip_request_rejects_end_date_before_start_date():
    with pytest.raises(ValidationError, match="end_date"):
        TripRequest(
            origin="A",
            destination="B",
            start_date=date(2026, 7, 17),
            end_date=date(2026, 7, 15),
        )


def test_trip_request_rejects_empty_origin():
    with pytest.raises(ValidationError, match="must not be empty"):
        TripRequest(
            origin="   ",
            destination="B",
            start_date=date(2026, 7, 15),
            end_date=date(2026, 7, 15),
        )


def test_trip_request_rejects_max_nights_exceeding_trip_length():
    with pytest.raises(ValidationError, match="trip length"):
        TripRequest(
            origin="A",
            destination="B",
            start_date=date(2026, 7, 15),
            end_date=date(2026, 7, 16),
            constraints=TripConstraints(allow_extended_stays=True, max_nights_per_stop=3),
        )


def test_trip_request_strips_origin_and_destination():
    request = TripRequest(
        origin="  San Jose, CA  ",
        destination=" Monterey, CA ",
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
    )
    assert request.origin == "San Jose, CA"
    assert request.destination == "Monterey, CA"
