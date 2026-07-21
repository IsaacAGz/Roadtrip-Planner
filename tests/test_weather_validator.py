from datetime import date
from unittest.mock import patch

import pytest

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan, Stop
from app.models.preferences import TripPreferences
from app.models.trip import TripRequest
from app.services.openweather import DailyForecast
from app.validators.hard import run_hard_validators
from app.validators.weather import validate_weather


class FakeOpenWeatherClient:
    def __init__(
        self,
        forecasts_by_city: dict[str, dict[str, DailyForecast]] | None = None,
        *,
        configured: bool = True,
    ) -> None:
        self.forecasts_by_city = forecasts_by_city or {}
        self._configured = configured

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def forecast_by_city(self, city: str) -> dict[str, DailyForecast]:
        return self.forecasts_by_city.get(city, {})


def _good_forecast() -> DailyForecast:
    return DailyForecast(
        date="2026-07-15",
        min_temp_c=18.0,
        max_temp_c=24.0,
        max_precip_chance=0.1,
        description="clear sky",
    )


def _rainy_forecast() -> DailyForecast:
    return DailyForecast(
        date="2026-07-15",
        min_temp_c=14.0,
        max_temp_c=17.0,
        max_precip_chance=0.85,
        description="heavy rain",
    )


def _cold_forecast() -> DailyForecast:
    return DailyForecast(
        date="2026-07-15",
        min_temp_c=2.0,
        max_temp_c=8.0,
        max_precip_chance=0.2,
        description="clear sky",
    )


def _day(*, stops: list[Stop] | None = None, overnight_city: str = "Monterey") -> DayPlan:
    return DayPlan(
        day=1,
        date=date(2026, 7, 15),
        route_summary="Test day",
        driving_hours=2.0,
        stops=stops or [],
        overnight=OvernightStop(city=overnight_city, lat=36.6, lon=-121.9, country_code="US"),
        leg_start_lat=37.0,
        leg_start_lon=-122.0,
        leg_end_lat=36.6,
        leg_end_lon=-121.9,
    )


def _plan(day: DayPlan) -> RoadtripPlan:
    return RoadtripPlan(
        title="Weather test",
        total_days=1,
        origin_lat=37.0,
        origin_lon=-122.0,
        destination_lat=36.6,
        destination_lon=-121.9,
        days=[day],
    )


def _request(*, interests: list[str] | None = None) -> TripRequest:
    return TripRequest(
        origin="San Jose, CA",
        destination="Monterey, CA",
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
        structured_preferences=TripPreferences(interests=interests or []),
    )


def _weather_constraints(**kwargs) -> TripConstraints:
    return TripConstraints(fail_on_weather_warnings=True, **kwargs)


@pytest.mark.asyncio
async def test_weather_skips_when_fail_on_weather_warnings_false():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _rainy_forecast()}})
    plan = _plan(_day(stops=[Stop(name="Beach", lat=36.6, lon=-121.9, category="beach", country_code="US")]))
    request = _request()
    constraints = TripConstraints(fail_on_weather_warnings=False)

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert violations == []


@pytest.mark.asyncio
async def test_weather_skips_when_api_not_configured():
    client = FakeOpenWeatherClient(configured=False)
    plan = _plan(_day(stops=[Stop(name="Beach", lat=36.6, lon=-121.9, category="beach", country_code="US")]))
    request = _request()
    constraints = _weather_constraints()

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert violations == []


@pytest.mark.asyncio
async def test_weather_passes_for_good_forecast_and_outdoor_stop():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _good_forecast()}})
    plan = _plan(_day(stops=[Stop(name="Carmel Beach", lat=36.6, lon=-121.9, category="beach", country_code="US")]))
    request = _request(interests=["beaches"])
    constraints = _weather_constraints()

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert violations == []


@pytest.mark.asyncio
async def test_weather_fails_on_high_precipitation_for_outdoor_stop():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _rainy_forecast()}})
    plan = _plan(_day(stops=[Stop(name="Carmel Beach", lat=36.6, lon=-121.9, category="beach", country_code="US")]))
    request = _request()
    constraints = _weather_constraints(max_precip_chance=0.5)

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "WEATHER-001"
    assert violations[0].actual == 0.85
    assert "precipitation" in violations[0].message


@pytest.mark.asyncio
async def test_weather_fails_on_low_temperature_for_outdoor_stop():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _cold_forecast()}})
    plan = _plan(
        _day(stops=[Stop(name="Trailhead", lat=36.6, lon=-121.9, category="viewpoint", country_code="US")])
    )
    request = _request(interests=["hiking"])
    constraints = _weather_constraints(min_temp_c=10.0)

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert len(violations) == 1
    assert violations[0].rule_id == "WEATHER-001"
    assert violations[0].actual == 2.0
    assert "temperature" in violations[0].message


@pytest.mark.asyncio
async def test_weather_fails_for_outdoor_interests_with_any_stop():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _rainy_forecast()}})
    plan = _plan(_day(stops=[Stop(name="Local Museum", lat=36.6, lon=-121.9, category="museum", country_code="US")]))
    request = _request(interests=["beaches"])
    constraints = _weather_constraints()

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert len(violations) == 1
    assert "outdoor interests" in violations[0].message


@pytest.mark.asyncio
async def test_weather_skips_indoor_only_day_without_outdoor_interests():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _rainy_forecast()}})
    plan = _plan(_day(stops=[Stop(name="Museum", lat=36.6, lon=-121.9, category="museum", country_code="US")]))
    request = _request()
    constraints = _weather_constraints()

    with patch("app.validators.weather.get_openweather_client", return_value=client):
        violations = await validate_weather(plan, request, constraints)

    assert violations == []


@pytest.mark.asyncio
async def test_run_hard_validators_includes_weather_failures():
    client = FakeOpenWeatherClient({"Monterey": {"2026-07-15": _rainy_forecast()}})
    plan = _plan(_day(stops=[Stop(name="Beach", lat=36.6, lon=-121.9, category="beach", country_code="US")]))
    request = TripRequest(
        origin="San Jose, CA",
        destination="Monterey, CA",
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
        constraints=_weather_constraints(),
    )

    class FakeOSRMClient:
        async def duration_hours(self, origin, destination):
            return 2.0

        async def distance_km(self, origin, destination):
            return 50.0

    with (
        patch("app.validators.weather.get_openweather_client", return_value=client),
        patch("app.validators.driving.get_osrm_client", return_value=FakeOSRMClient()),
        patch("app.validators.routing.get_osrm_client", return_value=FakeOSRMClient()),
        patch("app.validators.warnings.get_osrm_client", return_value=FakeOSRMClient()),
    ):
        report = await run_hard_validators(plan, request)

    assert report.approved is False
    assert any(v.rule_id == "WEATHER-001" for v in report.hard_failures)
