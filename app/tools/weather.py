from collections import defaultdict

import httpx
from langchain_core.tools import tool

from app.config import get_settings


def _format_daily_summary(date: str, entries: list[dict]) -> str:
    temps = [entry["main"]["temp"] for entry in entries]
    descriptions = [
        entry["weather"][0]["description"]
        for entry in entries
        if entry.get("weather")
    ]
    precip_chance = max(entry.get("pop", 0.0) for entry in entries)

    min_temp = min(temps)
    max_temp = max(temps)
    description = descriptions[len(descriptions) // 2] if descriptions else "unknown"

    return (
        f"- {date}: {description}, {min_temp:.0f}–{max_temp:.0f}°C, "
        f"max precip chance {precip_chance * 100:.0f}%"
    )


@tool
async def get_weather_forecast(city: str) -> str:
    """Get a multi-day weather forecast for a city (packing hints and activity planning)."""
    city = city.strip()
    if not city:
        return "City name is required for weather forecast"

    settings = get_settings()
    if not settings.openweather_api_key:
        return (
            f"Weather forecast unavailable: OPENWEATHER_API_KEY is not configured. "
            f"Skip weather for '{city}' and note generic packing tips instead."
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.openweather_base_url}/forecast",
                params={"q": city, "appid": settings.openweather_api_key, "units": "metric"},
            )
            if response.status_code == 404:
                return f"No weather forecast found for city '{city}'"
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        return f"Weather forecast failed for '{city}': HTTP {exc.response.status_code}"
    except httpx.RequestError as exc:
        return f"Weather forecast failed for '{city}': {exc}"

    forecasts = data.get("list", [])
    if not forecasts:
        return f"No forecast data returned for '{city}'"

    by_date: dict[str, list[dict]] = defaultdict(list)
    for item in forecasts:
        date = item.get("dt_txt", "")[:10]
        if date:
            by_date[date].append(item)

    lines = [f"Weather forecast for {city}:"]
    for date in sorted(by_date.keys()):
        lines.append(_format_daily_summary(date, by_date[date]))

    return "\n".join(lines)
