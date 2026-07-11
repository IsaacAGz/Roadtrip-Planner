from app.models.constraints import TripConstraints
from app.models.itinerary import RoadtripPlan
from app.models.validation import RuleViolation
from app.services.osrm import get_osrm_client


async def validate_driving(plan: RoadtripPlan, constraints: TripConstraints) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    osrm = get_osrm_client()

    for day_plan in plan.days:
        if day_plan.driving_hours > constraints.max_driving_hours_per_day:
            violations.append(
                RuleViolation(
                    rule_id="DRIVE-001",
                    severity="error",
                    day=day_plan.day,
                    message=(
                        f"Day {day_plan.day} driving {day_plan.driving_hours:.1f}h exceeds "
                        f"limit {constraints.max_driving_hours_per_day}h"
                    ),
                    actual=round(day_plan.driving_hours, 1),
                    limit=constraints.max_driving_hours_per_day,
                )
            )

        if (
            day_plan.leg_start_lat is not None
            and day_plan.leg_start_lon is not None
            and day_plan.leg_end_lat is not None
            and day_plan.leg_end_lon is not None
        ):
            origin = (day_plan.leg_start_lat, day_plan.leg_start_lon)
            destination = (day_plan.leg_end_lat, day_plan.leg_end_lon)
            try:
                osrm_hours = await osrm.duration_hours(origin, destination)
                tolerance = 0.5
                if abs(osrm_hours - day_plan.driving_hours) > tolerance and day_plan.driving_hours > 0:
                    if osrm_hours > constraints.max_driving_hours_per_day:
                        violations.append(
                            RuleViolation(
                                rule_id="DRIVE-001",
                                severity="error",
                                day=day_plan.day,
                                message=(
                                    f"Day {day_plan.day} OSRM-verified driving {osrm_hours:.1f}h "
                                    f"exceeds limit {constraints.max_driving_hours_per_day}h"
                                ),
                                actual=round(osrm_hours, 1),
                                limit=constraints.max_driving_hours_per_day,
                            )
                        )
            except ValueError:
                violations.append(
                    RuleViolation(
                        rule_id="DRIVE-002",
                        severity="error",
                        day=day_plan.day,
                        message=f"Day {day_plan.day} driving segment could not be verified via OSRM",
                    )
                )

        if len(day_plan.stops) > constraints.max_stops_per_day:
            violations.append(
                RuleViolation(
                    rule_id="SCHED-001",
                    severity="error",
                    day=day_plan.day,
                    message=(
                        f"Day {day_plan.day} has {len(day_plan.stops)} stops; "
                        f"limit is {constraints.max_stops_per_day}"
                    ),
                    actual=len(day_plan.stops),
                    limit=constraints.max_stops_per_day,
                )
            )

    return violations
