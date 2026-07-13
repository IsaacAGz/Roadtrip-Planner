from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, RoadtripPlan, Stop
from app.models.validation import RuleViolation
from app.services.nominatim import LatLon
from app.services.osrm import get_osrm_client

MONOTONIC_TOLERANCE_KM = 5.0


def _day_leg(day_plan: DayPlan) -> tuple[LatLon, LatLon] | None:
    if (
        day_plan.leg_start_lat is None
        or day_plan.leg_start_lon is None
        or day_plan.leg_end_lat is None
        or day_plan.leg_end_lon is None
    ):
        return None
    origin = (day_plan.leg_start_lat, day_plan.leg_start_lon)
    destination = (day_plan.leg_end_lat, day_plan.leg_end_lon)
    return origin, destination


async def _detour_km(origin: LatLon, destination: LatLon, stop: Stop) -> float:
    osrm = get_osrm_client()
    stop_point = (stop.lat, stop.lon)
    base = await osrm.distance_km(origin, destination)
    via = await osrm.distance_km(origin, stop_point) + await osrm.distance_km(
        stop_point, destination
    )
    return via - base


async def validate_routing(plan: RoadtripPlan, constraints: TripConstraints) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    osrm = get_osrm_client()

    for day_plan in plan.days:
        leg = _day_leg(day_plan)
        if leg is None or day_plan.driving_hours <= 0:
            continue

        origin, destination = leg
        for stop in day_plan.stops:
            try:
                detour = await _detour_km(origin, destination, stop)
                if detour > constraints.max_detour_km_per_stop:
                    violations.append(
                        RuleViolation(
                            rule_id="ROUTE-001",
                            severity="error",
                            day=day_plan.day,
                            message=(
                                f"Stop '{stop.name}' on day {day_plan.day} adds "
                                f"{detour:.1f} km detour (limit {constraints.max_detour_km_per_stop} km)"
                            ),
                            actual=round(detour, 1),
                            limit=constraints.max_detour_km_per_stop,
                        )
                    )
            except ValueError:
                violations.append(
                    RuleViolation(
                        rule_id="ROUTE-001",
                        severity="error",
                        day=day_plan.day,
                        message=f"Could not verify detour for stop '{stop.name}' on day {day_plan.day}",
                    )
                )

    try:
        trip_origin = (plan.origin_lat, plan.origin_lon)
        trip_destination = (plan.destination_lat, plan.destination_lon)
        total_km = await osrm.distance_km(trip_origin, trip_destination)

        if total_km >= 1.0:
            progress: list[float] = []
            for day_plan in plan.days:
                end_point = (day_plan.overnight.lat, day_plan.overnight.lon)
                progress.append(await osrm.distance_km(trip_origin, end_point))

            total_backtrack = 0.0
            require_monotonic = constraints.effective_require_progress()

            for index in range(1, len(progress)):
                drop = max(0.0, progress[index - 1] - progress[index])
                total_backtrack += drop

                if require_monotonic and (progress[index - 1] - progress[index]) > MONOTONIC_TOLERANCE_KM:
                    violations.append(
                        RuleViolation(
                            rule_id="ROUTE-002",
                            severity="error",
                            day=plan.days[index].day,
                            message=(
                                f"Day {plan.days[index].day} backtracks "
                                f"{progress[index - 1] - progress[index]:.1f} km from trip origin progress"
                            ),
                            actual=round(progress[index - 1] - progress[index], 1),
                            limit=MONOTONIC_TOLERANCE_KM,
                        )
                    )

            backtrack_percent = (total_backtrack / total_km) * 100.0
            max_backtrack = constraints.max_backtracking_percent
            if constraints.allow_return_stops and max_backtrack < 25.0:
                max_backtrack = max(max_backtrack, 25.0)

            if backtrack_percent > max_backtrack:
                violations.append(
                    RuleViolation(
                        rule_id="ROUTE-002",
                        severity="error",
                        message=(
                            f"Total backtracking {backtrack_percent:.1f}% exceeds "
                            f"limit {max_backtrack}%"
                        ),
                        actual=round(backtrack_percent, 1),
                        limit=max_backtrack,
                    )
                )
    except ValueError:
        violations.append(
            RuleViolation(
                rule_id="ROUTE-002",
                severity="error",
                message="Could not verify trip backtracking via OSRM",
            )
        )

    return violations
