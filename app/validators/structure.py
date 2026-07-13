from datetime import timedelta

from app.models.constraints import TripConstraints
from app.models.itinerary import DayPlan, OvernightStop, RoadtripPlan
from app.models.trip import TripRequest
from app.models.validation import RuleViolation


def _normalize_city(city: str) -> str:
    return city.strip().lower()


def _group_consecutive_day_sequences(days: list[int]) -> list[list[int]]:
    if not days:
        return []

    sorted_days = sorted(set(days))
    sequences: list[list[int]] = [[sorted_days[0]]]
    for day in sorted_days[1:]:
        if day == sequences[-1][-1] + 1:
            sequences[-1].append(day)
        else:
            sequences.append([day])
    return sequences


def _overnight_by_day(plan: RoadtripPlan) -> dict[int, OvernightStop]:
    return {day_plan.day: day_plan.overnight for day_plan in plan.days}


def validate_structure(
    plan: RoadtripPlan, request: TripRequest, constraints: TripConstraints
) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    expected_days = request.days

    if plan.total_days != expected_days:
        violations.append(
            RuleViolation(
                rule_id="STRUCT-001",
                severity="error",
                message=(
                    f"Plan has {plan.total_days} days but request spans {expected_days} days"
                ),
                actual=plan.total_days,
                limit=expected_days,
            )
        )

    if len(plan.days) != expected_days:
        violations.append(
            RuleViolation(
                rule_id="STRUCT-001",
                severity="error",
                message=(
                    f"Itinerary contains {len(plan.days)} day entries; expected {expected_days}"
                ),
                actual=len(plan.days),
                limit=expected_days,
            )
        )

    for index, day_plan in enumerate(plan.days):
        expected_date = request.start_date + timedelta(days=index)
        if day_plan.date != expected_date:
            violations.append(
                RuleViolation(
                    rule_id="STRUCT-001",
                    severity="error",
                    day=day_plan.day,
                    message=(
                        f"Day {day_plan.day} date {day_plan.date} does not match "
                        f"expected {expected_date}"
                    ),
                    actual=str(day_plan.date),
                    limit=str(expected_date),
                )
            )

    overnight_by_day = _overnight_by_day(plan)
    city_occurrences: dict[str, list[int]] = {}
    for day_plan in plan.days:
        city_key = _normalize_city(day_plan.overnight.city)
        city_occurrences.setdefault(city_key, []).append(day_plan.day)

    for city_key, days in city_occurrences.items():
        sequences = _group_consecutive_day_sequences(days)

        for sequence in sequences:
            if len(sequence) <= 1:
                continue

            first_day = sequence[0]
            last_day = sequence[-1]
            night_count = len(sequence)

            if not constraints.allow_extended_stays:
                violations.append(
                    RuleViolation(
                        rule_id="STRUCT-004",
                        severity="error",
                        day=first_day,
                        message=(
                            f"Consecutive {night_count}-night stay in '{city_key}' "
                            f"(days {first_day}-{last_day}) requires allow_extended_stays=true"
                        ),
                        actual=night_count,
                        limit=1,
                    )
                )
            elif night_count > constraints.max_nights_per_stop:
                violations.append(
                    RuleViolation(
                        rule_id="STRUCT-002",
                        severity="error",
                        day=first_day,
                        message=(
                            f"Consecutive stay in '{city_key}' for {night_count} nights "
                            f"(days {first_day}-{last_day}) exceeds max_nights_per_stop "
                            f"({constraints.max_nights_per_stop})"
                        ),
                        actual=night_count,
                        limit=constraints.max_nights_per_stop,
                    )
                )

        if len(sequences) > 1:
            for sequence in sequences[1:]:
                first_day = sequence[0]
                overnight = overnight_by_day[first_day]
                if not constraints.allow_return_stops:
                    violations.append(
                        RuleViolation(
                            rule_id="STRUCT-003",
                            severity="error",
                            day=first_day,
                            message=(
                                f"Non-consecutive repeat of '{city_key}' on day {first_day} "
                                f"requires allow_return_stops=true"
                            ),
                        )
                    )
                elif not overnight.is_return_stop:
                    violations.append(
                        RuleViolation(
                            rule_id="STRUCT-003",
                            severity="error",
                            day=first_day,
                            message=(
                                f"Return stop '{city_key}' on day {first_day} must set "
                                f"is_return_stop=true"
                            ),
                        )
                    )

    return violations
