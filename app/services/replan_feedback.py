from app.models.scaffold import TripScaffold
from app.models.validation import RuleViolation

RULE_PRIORITY = {
    "STRUCT-001": 0,
    "STRUCT-004": 1,
    "STRUCT-003": 2,
    "STRUCT-002": 3,
    "DRIVE-001": 4,
    "DRIVE-002": 5,
    "SCHED-001": 6,
    "ROUTE-001": 7,
    "ROUTE-002": 8,
    "POI-003": 9,
    "GEO-001": 10,
    "WEATHER-001": 11,
}

MAX_FEEDBACK_ITEMS = 8


def _scaffold_city_for_day(scaffold: TripScaffold | None, day: int | None) -> str | None:
    if scaffold is None or day is None:
        return None
    for spec in scaffold.days:
        if spec.day == day:
            return spec.suggested_overnight_city
    return None


def _format_violation(violation: RuleViolation, scaffold: TripScaffold | None) -> str:
    rule_id = violation.rule_id
    day = violation.day
    suggested = _scaffold_city_for_day(scaffold, day)

    if rule_id == "STRUCT-004":
        city = violation.message
        hint = f"; use scaffold city '{suggested}'" if suggested else ""
        return (
            f"STRUCT-004 day {day}: change overnight — cannot stay in the same city "
            f"two nights in a row{hint} ({violation.message})"
        )

    if rule_id == "STRUCT-003":
        return (
            f"STRUCT-003 day {day}: set is_return_stop=true on the return visit "
            f"or pick a different overnight city"
        )

    if rule_id == "STRUCT-001":
        return f"STRUCT-001: fix day count and dates to match the request ({violation.message})"

    if rule_id == "STRUCT-002":
        return f"STRUCT-002 day {day}: reduce consecutive nights in one city ({violation.message})"

    if rule_id == "DRIVE-001":
        return (
            f"DRIVE-001 day {day}: reduce driving to ≤{violation.limit}h "
            f"(OSRM shows {violation.actual}h); shorten the leg or remove distant stops"
        )

    if rule_id == "DRIVE-002":
        return (
            f"DRIVE-002 day {day}: ensure leg_start/leg_end coordinates are valid "
            f"and routable via OSRM"
        )

    if rule_id == "ROUTE-001":
        return (
            f"ROUTE-001 day {day}: remove or replace the stop that adds "
            f"{violation.actual} km detour (limit {violation.limit} km)"
        )

    if rule_id == "ROUTE-002":
        return (
            "ROUTE-002: reorder overnight cities to progress toward the destination; "
            "avoid backtracking"
        )

    if rule_id == "POI-003":
        return (
            f"POI-003 day {day}: remove stop with excluded category "
            f"'{violation.actual}'"
        )

    if rule_id == "SCHED-001":
        return f"SCHED-001 day {day}: reduce stops to ≤{violation.limit}"

    if rule_id == "GEO-001":
        return f"GEO-001 day {day}: use stops and overnights in allowed countries ({violation.message})"

    if rule_id == "WEATHER-001":
        return f"WEATHER-001 day {day}: adjust outdoor activities for forecast ({violation.message})"

    return f"{rule_id}: {violation.message}"


def _format_warning(violation: RuleViolation) -> str:
    if violation.rule_id == "DRIVE-001":
        return (
            f"DRIVE-001 warning day {violation.day}: driving {violation.actual}h is near "
            f"limit {violation.limit}h — reduce the leg or stop durations"
        )
    if violation.rule_id == "SCHED-001":
        return (
            f"SCHED-001 warning day {violation.day}: stop count is at the limit "
            f"({violation.limit}) — reduce activities for relaxed pacing"
        )
    if violation.rule_id == "ROUTE-001":
        return (
            f"ROUTE-001 warning day {violation.day}: a stop is near the detour limit "
            f"({violation.actual} km of {violation.limit} km)"
        )
    if violation.rule_id == "ROUTE-002":
        return (
            f"ROUTE-002 warning: total backtracking {violation.actual}% is near "
            f"limit {violation.limit}%"
        )
    return f"{violation.rule_id} warning: {violation.message}"


def format_replan_feedback(
    violations: list[RuleViolation],
    *,
    scaffold: TripScaffold | None = None,
) -> list[str]:
    sorted_violations = sorted(
        violations,
        key=lambda item: (RULE_PRIORITY.get(item.rule_id, 99), item.day or 0),
    )
    feedback = [_format_violation(violation, scaffold) for violation in sorted_violations]
    return feedback[:MAX_FEEDBACK_ITEMS]


def format_warning_replan_feedback(warnings: list[RuleViolation]) -> list[str]:
    targeted = [
        warning
        for warning in warnings
        if warning.rule_id in {"DRIVE-001", "SCHED-001", "ROUTE-001", "ROUTE-002"}
    ]
    if not targeted:
        return []
    return [_format_warning(warning) for warning in targeted[:MAX_FEEDBACK_ITEMS]]
