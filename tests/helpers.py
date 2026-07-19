from datetime import date, timedelta

from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan


def sample_plan(*, days: int = 5, start: date = date(2026, 7, 15)) -> RoadtripPlan:
    day_plans = []
    cities = ["San Diego", "Los Angeles", "San Francisco", "Eugene", "Portland"]
    for day in range(1, days + 1):
        day_plans.append(
            DayPlan(
                day=day,
                date=start + timedelta(days=day - 1),
                route_summary=f"Day {day}",
                driving_hours=3.0,
                overnight=OvernightStop(
                    city=cities[min(day - 1, len(cities) - 1)],
                    lat=32.0 + day,
                    lon=-122.0,
                    country_code="US",
                ),
            )
        )
    return RoadtripPlan(
        title="Coastal road trip",
        total_days=days,
        origin_lat=32.7,
        origin_lon=-117.1,
        destination_lat=45.5,
        destination_lon=-122.7,
        days=day_plans,
        tips=["Pack layers"],
    )
