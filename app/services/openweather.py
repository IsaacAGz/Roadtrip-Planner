from collections import defaultdict
from dataclasses import dataclass

import httpx

from app.config import get_settings


@dataclass(frozen=True)
class DailyForecast:
    date: str
    min_temp_c: float
    max_temp_c: float
    max_precip_chance: float
    description: str


def _aggregate_daily_forecasts(forecasts: list[dict]) -> dict[str, DailyForecast]:
    by_date: dict[str, list[dict]] = defaultdict(list)
    for item in forecasts:
        date = item.get("dt_txt", "")[:10]
        if date:
            by_date[date].append(item)

    daily: dict[str, DailyForecast] = {}
    for date, entries in by_date.items():
        temps = [entry["main"]["temp"] for entry in entries]
        descriptions = [
            entry["weather"][0]["description"]
            for entry in entries
            if entry.get("weather")
        ]
        precip_chance = max(entry.get("pop", 0.0) for entry in entries)
        daily[date] = DailyForecast(
            date=date,
            min_temp_c=min(temps),
            max_temp_c=max(temps),
            max_precip_chance=precip_chance,
            description=descriptions[len(descriptions) // 2] if descriptions else "unknown",
        )
    return daily


class OpenWeatherClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache: dict[str, dict[str, DailyForecast]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.openweather_api_key)

    async def forecast_by_city(self, city: str) -> dict[str, DailyForecast]:
        city = city.strip()
        if not city:
            return {}
        if city in self._cache:
            return self._cache[city]
        if not self.is_configured:
            return {}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self._settings.openweather_base_url}/forecast",
                    params={
                        "q": city,
                        "appid": self._settings.openweather_api_key,
                        "units": "metric",
                    },
                )
                if response.status_code == 404:
                    return {}
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return {}

        forecasts = data.get("list", [])
        daily = _aggregate_daily_forecasts(forecasts)
        self._cache[city] = daily
        return daily


_openweather_client: OpenWeatherClient | None = None


def get_openweather_client() -> OpenWeatherClient:
    global _openweather_client
    if _openweather_client is None:
        _openweather_client = OpenWeatherClient()
    return _openweather_client
