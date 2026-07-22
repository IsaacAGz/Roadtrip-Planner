from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.trip import TripRequest
from app.services.openweather import DailyForecast
from app.services.weather_enrichment import enrich_weather
from tests.helpers import sample_plan


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Jose, CA",
        "destination": "Monterey, CA",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 15),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


@pytest.mark.asyncio
async def test_enrich_weather_skips_when_not_configured():
    plan = sample_plan(days=1)
    request = _request()

    with patch(
        "app.services.weather_enrichment.get_openweather_client",
        return_value=type("Client", (), {"is_configured": False})(),
    ):
        result = await enrich_weather(plan, request)

    assert result.days[0].weather is None


@pytest.mark.asyncio
async def test_enrich_weather_attaches_daily_forecast():
    plan = sample_plan(days=1)
    request = _request()
    forecast = {
        "2026-07-15": DailyForecast(
            date="2026-07-15",
            min_temp_c=12.0,
            max_temp_c=22.0,
            max_precip_chance=0.2,
            description="clear sky",
        )
    }

    mock_client = type(
        "Client",
        (),
        {"is_configured": True, "forecast_by_city": AsyncMock(return_value=forecast)},
    )()

    with patch("app.services.weather_enrichment.get_openweather_client", return_value=mock_client):
        result = await enrich_weather(plan, request)

    weather = result.days[0].weather
    assert weather is not None
    assert weather.summary == "clear sky"
    assert weather.min_temp_c == 12.0
    assert weather.max_temp_c == 22.0
    assert weather.max_precip_chance == 0.2
