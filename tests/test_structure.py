from datetime import date, timedelta

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan
from app.models.trip import TripRequest
from app.validators.structure import validate_structure


def _overnight(city: str, day_offset: int = 0, is_return_stop: bool = False) -> OvernightStop:
    base_lat = 37.0 + day_offset
    return OvernightStop(
        city=city,
        lat=base_lat,
        lon=-122.0,
        country_code="US",
        is_return_stop=is_return_stop,
    )


def _day(day: int, start: date, city: str, is_return_stop: bool = False) -> DayPlan:
    return DayPlan(
        day=day,
        date=start + timedelta(days=day - 1),
        route_summary=f"Day {day}",
        driving_hours=2.0,
        overnight=_overnight(city, day - 1, is_return_stop=is_return_stop),
    )


def _request(days: int = 2, **constraint_kwargs) -> TripRequest:
    start = date(2026, 7, 15)
    end = start + timedelta(days=days - 1)
    return TripRequest(
        origin="A",
        destination="B",
        start_date=start,
        end_date=end,
        constraints=TripConstraints(**constraint_kwargs),
    )


def _plan(request: TripRequest, day_plans: list[DayPlan]) -> RoadtripPlan:
    return RoadtripPlan(
        title="Test trip",
        total_days=request.days,
        origin_lat=37.0,
        origin_lon=-122.0,
        destination_lat=38.0,
        destination_lon=-121.0,
        days=day_plans,
    )


def test_valid_two_day_plan_with_different_overnight_cities():
    request = _request(days=2)
    plan = _plan(
        request,
        [
            _day(1, request.start_date, "Gilroy"),
            _day(2, request.start_date, "Monterey"),
        ],
    )

    violations = validate_structure(plan, request, request.constraints)

    assert violations == []


def test_struct_001_rejects_wrong_total_days():
    request = _request(days=2)
    plan = _plan(request, [_day(1, request.start_date, "Gilroy")])

    violations = validate_structure(plan, request, request.constraints)

    assert any(v.rule_id == "STRUCT-001" for v in violations)


def test_struct_001_rejects_mismatched_date():
    request = _request(days=1)
    bad_day = _day(1, request.start_date, "Monterey")
    bad_day.date = date(2026, 1, 1)
    plan = _plan(request, [bad_day])

    violations = validate_structure(plan, request, request.constraints)

    assert any(v.rule_id == "STRUCT-001" and "date" in v.message.lower() for v in violations)


def test_struct_004_rejects_consecutive_nights_without_extended_stays():
    request = _request(days=2)
    plan = _plan(
        request,
        [
            _day(1, request.start_date, "Monterey"),
            _day(2, request.start_date, "Monterey"),
        ],
    )

    violations = validate_structure(plan, request, request.constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "STRUCT-004"
    assert violations[0].day == 1


def test_struct_002_rejects_too_many_consecutive_nights_when_extended_stays_allowed():
    request = _request(days=3, allow_extended_stays=True, max_nights_per_stop=2)
    plan = _plan(
        request,
        [
            _day(1, request.start_date, "Monterey"),
            _day(2, request.start_date, "Monterey"),
            _day(3, request.start_date, "Monterey"),
        ],
    )

    violations = validate_structure(plan, request, request.constraints)

    assert any(v.rule_id == "STRUCT-002" for v in violations)


def test_struct_003_rejects_non_consecutive_city_repeat_without_return_stops():
    request = _request(days=3)
    plan = _plan(
        request,
        [
            _day(1, request.start_date, "Monterey"),
            _day(2, request.start_date, "Salinas"),
            _day(3, request.start_date, "Monterey"),
        ],
    )

    violations = validate_structure(plan, request, request.constraints)

    assert any(v.rule_id == "STRUCT-003" for v in violations)


def test_struct_003_requires_is_return_stop_flag_when_return_stops_allowed():
    request = _request(days=3, allow_return_stops=True)
    plan = _plan(
        request,
        [
            _day(1, request.start_date, "Monterey"),
            _day(2, request.start_date, "Salinas"),
            _day(3, request.start_date, "Monterey", is_return_stop=False),
        ],
    )

    violations = validate_structure(plan, request, request.constraints)

    assert any(
        v.rule_id == "STRUCT-003" and "is_return_stop=true" in v.message for v in violations
    )
