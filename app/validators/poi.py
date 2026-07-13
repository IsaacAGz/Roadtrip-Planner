from app.models.constraints import TripConstraints, effective_excluded_categories
from app.models.itinerary import RoadtripPlan
from app.models.validation import RuleViolation


def validate_poi(plan: RoadtripPlan, constraints: TripConstraints) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    excluded = effective_excluded_categories(constraints.excluded_poi_categories)

    for day_plan in plan.days:
        for stop in day_plan.stops:
            category = stop.category.strip().lower().replace(" ", "_")
            if category in excluded:
                violations.append(
                    RuleViolation(
                        rule_id="POI-003",
                        severity="error",
                        day=day_plan.day,
                        message=(
                            f"Stop '{stop.name}' has excluded category '{category}'"
                        ),
                        actual=category,
                        limit=", ".join(sorted(excluded)),
                    )
                )

    return violations
