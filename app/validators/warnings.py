from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, RoadtripPlan
from app.models.validation import RuleViolation
from app.services.osrm import get_osrm_client
from app.validators.routing import _day_leg, _detour_km

DRIVING_WARN_RATIO = 0.9
DETOUR_WARN_RATIO = 0.8
BACKTRACK_WARN_RATIO = 0.8


def _effective_driving_hours(day_plan: DayPlan, osrm_hours: float | None) -> float:
    if osrm_hours is None:
        return day_plan.driving_hours
    return max(day_plan.driving_hours, osrm_hours)


async def _osrm_driving_hours(day_plan: DayPlan) -> float | None:
    leg = _day_leg(day_plan)
    if leg is None:
        return None
    osrm = get_osrm_client()
    try:
        return await osrm.duration_hours(leg[0], leg[1])
    except ValueError:
        return None


async def collect_warnings(
    plan: RoadtripPlan, constraints: TripConstraints
) -> list[RuleViolation]:
    warnings: list[RuleViolation] = []
    osrm = get_osrm_client()

    driving_warn_threshold = constraints.max_driving_hours_per_day * DRIVING_WARN_RATIO
    detour_warn_threshold = constraints.max_detour_km_per_stop * DETOUR_WARN_RATIO

    for day_plan in plan.days:
        osrm_hours = await _osrm_driving_hours(day_plan)
        effective_hours = _effective_driving_hours(day_plan, osrm_hours)
        if (
            effective_hours > 0
            and effective_hours <= constraints.max_driving_hours_per_day
            and effective_hours >= driving_warn_threshold
        ):
            warnings.append(
                RuleViolation(
                    rule_id="DRIVE-001",
                    severity="warning",
                    day=day_plan.day,
                    message=(
                        f"Day {day_plan.day} driving {effective_hours:.1f}h is near "
                        f"limit {constraints.max_driving_hours_per_day}h"
                    ),
                    actual=round(effective_hours, 1),
                    limit=constraints.max_driving_hours_per_day,
                )
            )

        if len(day_plan.stops) == constraints.max_stops_per_day:
            warnings.append(
                RuleViolation(
                    rule_id="SCHED-001",
                    severity="warning",
                    day=day_plan.day,
                    message=(
                        f"Day {day_plan.day} has {len(day_plan.stops)} stops, "
                        f"at the limit of {constraints.max_stops_per_day}"
                    ),
                    actual=len(day_plan.stops),
                    limit=constraints.max_stops_per_day,
                )
            )

        leg = _day_leg(day_plan)
        if leg is not None and day_plan.driving_hours > 0:
            origin, destination = leg
            for stop in day_plan.stops:
                try:
                    detour = await _detour_km(origin, destination, stop)
                    if (
                        detour <= constraints.max_detour_km_per_stop
                        and detour >= detour_warn_threshold
                    ):
                        warnings.append(
                            RuleViolation(
                                rule_id="ROUTE-001",
                                severity="warning",
                                day=day_plan.day,
                                message=(
                                    f"Stop '{stop.name}' on day {day_plan.day} adds "
                                    f"{detour:.1f} km detour, near limit "
                                    f"{constraints.max_detour_km_per_stop} km"
                                ),
                                actual=round(detour, 1),
                                limit=constraints.max_detour_km_per_stop,
                            )
                        )
                except ValueError:
                    continue

    try:
        trip_origin = (plan.origin_lat, plan.origin_lon)
        trip_destination = (plan.destination_lat, plan.destination_lon)
        total_km = await osrm.distance_km(trip_origin, trip_destination)

        if total_km >= 1.0:
            progress_points: list[float] = []
            for day_plan in plan.days:
                end_point = (day_plan.overnight.lat, day_plan.overnight.lon)
                progress_points.append(await osrm.distance_km(trip_origin, end_point))

            total_backtrack = 0.0
            for index in range(1, len(progress_points)):
                total_backtrack += max(0.0, progress_points[index - 1] - progress_points[index])

            backtrack_percent = (total_backtrack / total_km) * 100.0
            max_backtrack = constraints.max_backtracking_percent
            if constraints.allow_return_stops and max_backtrack < 25.0:
                max_backtrack = max(max_backtrack, 25.0)

            warn_threshold = max_backtrack * BACKTRACK_WARN_RATIO
            if backtrack_percent <= max_backtrack and backtrack_percent >= warn_threshold:
                warnings.append(
                    RuleViolation(
                        rule_id="ROUTE-002",
                        severity="warning",
                        message=(
                            f"Total backtracking {backtrack_percent:.1f}% is near "
                            f"limit {max_backtrack}%"
                        ),
                        actual=round(backtrack_percent, 1),
                        limit=max_backtrack,
                    )
                )
    except ValueError:
        pass

    return warnings
