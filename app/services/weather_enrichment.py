from app.models.itinerary import DayWeather, RoadtripPlan
from app.models.trip import TripRequest
from app.services.openweather import get_openweather_client


async def enrich_weather(plan: RoadtripPlan, request: TripRequest) -> RoadtripPlan:
    client = get_openweather_client()
    if not client.is_configured:
        return plan

    city_forecasts: dict[str, dict] = {}

    for day_plan in plan.days:
        city = day_plan.overnight.city.strip()
        if not city:
            continue

        if city not in city_forecasts:
            city_forecasts[city] = await client.forecast_by_city(city)

        daily = city_forecasts[city].get(day_plan.date.isoformat())
        if daily is None:
            continue

        day_plan.weather = DayWeather(
            summary=daily.description,
            min_temp_c=daily.min_temp_c,
            max_temp_c=daily.max_temp_c,
            max_precip_chance=daily.max_precip_chance,
        )

    return plan
