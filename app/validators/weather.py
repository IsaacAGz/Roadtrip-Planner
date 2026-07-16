from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, RoadtripPlan, Stop
from app.models.preferences import TripPreferences
from app.models.trip import TripRequest
from app.models.validation import RuleViolation
from app.services.openweather import DailyForecast, get_openweather_client

OUTDOOR_INTERESTS = frozenset(
    {
        "beaches",
        "beach",
        "hiking",
        "camping",
        "campgrounds",
        "parks",
        "park",
        "scenic_viewpoints",
        "scenic_views",
        "coastal_views",
        "swimming",
        "surfing",
        "kayaking",
        "fishing",
        "climbing",
        "wildlife",
        "outdoor",
        "nature",
    }
)

OUTDOOR_STOP_CATEGORIES = frozenset(
    {
        "beach",
        "viewpoint",
        "camp_site",
        "park",
        "peak",
        "picnic_site",
        "waterfall",
        "nature_reserve",
        "marina",
        "trail",
        "golf_course",
        "zoo",
    }
)


def _normalize_category(category: str) -> str:
    return category.strip().lower().replace(" ", "_")


def _is_outdoor_stop(stop: Stop) -> bool:
    return _normalize_category(stop.category) in OUTDOOR_STOP_CATEGORIES


def _has_outdoor_interests(preferences: TripPreferences) -> bool:
    return any(interest in OUTDOOR_INTERESTS for interest in preferences.interests)


def _day_needs_weather_check(day: DayPlan, request: TripRequest) -> bool:
    if any(_is_outdoor_stop(stop) for stop in day.stops):
        return True
    if _has_outdoor_interests(request.structured_preferences) and day.stops:
        return True
    return False


def _check_forecast_against_limits(
    *,
    forecast: DailyForecast,
    constraints: TripConstraints,
    day: int,
    context: str,
) -> list[RuleViolation]:
    violations: list[RuleViolation] = []

    if forecast.max_precip_chance > constraints.max_precip_chance:
        violations.append(
            RuleViolation(
                rule_id="WEATHER-001",
                severity="error",
                day=day,
                message=(
                    f"Day {day} {context}: precipitation chance "
                    f"{forecast.max_precip_chance * 100:.0f}% exceeds limit "
                    f"{constraints.max_precip_chance * 100:.0f}% "
                    f"({forecast.description})"
                ),
                actual=round(forecast.max_precip_chance, 2),
                limit=constraints.max_precip_chance,
            )
        )

    if forecast.min_temp_c < constraints.min_temp_c:
        violations.append(
            RuleViolation(
                rule_id="WEATHER-001",
                severity="error",
                day=day,
                message=(
                    f"Day {day} {context}: minimum temperature "
                    f"{forecast.min_temp_c:.0f}°C is below limit "
                    f"{constraints.min_temp_c:.0f}°C ({forecast.description})"
                ),
                actual=round(forecast.min_temp_c, 1),
                limit=constraints.min_temp_c,
            )
        )

    return violations


async def validate_weather(
    plan: RoadtripPlan,
    request: TripRequest,
    constraints: TripConstraints,
) -> list[RuleViolation]:
    if not constraints.fail_on_weather_warnings:
        return []

    client = get_openweather_client()
    if not client.is_configured:
        return []

    violations: list[RuleViolation] = []
    forecast_cache: dict[str, dict[str, DailyForecast]] = {}

    for day_plan in plan.days:
        if not _day_needs_weather_check(day_plan, request):
            continue

        city = day_plan.overnight.city.strip()
        if not city:
            continue

        if city not in forecast_cache:
            forecast_cache[city] = await client.forecast_by_city(city)
        daily_forecasts = forecast_cache[city]

        date_key = day_plan.date.isoformat()
        forecast = daily_forecasts.get(date_key)
        if forecast is None:
            continue

        outdoor_stops = [stop.name for stop in day_plan.stops if _is_outdoor_stop(stop)]
        if outdoor_stops:
            context = f"outdoor stops ({', '.join(outdoor_stops)})"
        elif _has_outdoor_interests(request.structured_preferences):
            context = "outdoor interests"
        else:
            context = "outdoor activities"

        violations.extend(
            _check_forecast_against_limits(
                forecast=forecast,
                constraints=constraints,
                day=day_plan.day,
                context=context,
            )
        )

    return violations
