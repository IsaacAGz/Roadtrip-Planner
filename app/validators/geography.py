from app.models.constraints import TripConstraints
from app.models.itinerary import RoadtripPlan
from app.models.validation import RuleViolation


def validate_geography(plan: RoadtripPlan, constraints: TripConstraints) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    allowed = {country.upper() for country in constraints.allowed_countries}

    for day_plan in plan.days:
        overnight = day_plan.overnight
        if overnight.country_code:
            code = overnight.country_code.upper()
            if code not in allowed:
                violations.append(
                    RuleViolation(
                        rule_id="GEO-001",
                        severity="error",
                        day=day_plan.day,
                        message=(
                            f"Overnight '{overnight.city}' country '{code}' is not in "
                            f"allowed countries {sorted(allowed)}"
                        ),
                        actual=code,
                        limit=", ".join(sorted(allowed)),
                    )
                )

        for stop in day_plan.stops:
            if stop.country_code:
                code = stop.country_code.upper()
                if code not in allowed:
                    violations.append(
                        RuleViolation(
                            rule_id="GEO-001",
                            severity="error",
                            day=day_plan.day,
                            message=(
                                f"Stop '{stop.name}' country '{code}' is not in "
                                f"allowed countries {sorted(allowed)}"
                            ),
                            actual=code,
                            limit=", ".join(sorted(allowed)),
                        )
                    )

    return violations
