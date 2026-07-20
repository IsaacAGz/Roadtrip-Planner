from app.models.scaffold import DayLegSpec, TripScaffold
from app.models.validation import RuleViolation
from app.services.nominatim import GeocodedLocation
from app.services.replan_feedback import (
    format_replan_feedback,
    format_warning_replan_feedback,
)


def _scaffold() -> TripScaffold:
    return TripScaffold(
        origin=GeocodedLocation("San Diego", 32.7, -117.1, "US"),
        destination=GeocodedLocation("Portland", 45.5, -122.7, "US"),
        days=[
            DayLegSpec(
                day=1,
                leg_start_lat=32.7,
                leg_start_lon=-117.1,
                leg_end_lat=34.0,
                leg_end_lon=-118.2,
                max_driving_hours=6.0,
                suggested_overnight_city="Los Angeles",
                suggested_overnight_lat=34.0,
                suggested_overnight_lon=-118.2,
                country_code="US",
            )
        ],
    )


def test_format_replan_feedback_includes_rule_id_prefix():
    violations = [
        RuleViolation(
            rule_id="DRIVE-001",
            severity="error",
            day=2,
            message="Too much driving",
            actual=7.0,
            limit=6.0,
        )
    ]

    feedback = format_replan_feedback(violations)

    assert feedback[0].startswith("DRIVE-001 day 2:")
    assert "7.0" in feedback[0]
    assert "6.0" in feedback[0]


def test_format_replan_feedback_includes_scaffold_hint_for_struct_004():
    violations = [
        RuleViolation(
            rule_id="STRUCT-004",
            severity="error",
            day=1,
            message="Consecutive stay in 'monterey'",
        )
    ]

    feedback = format_replan_feedback(violations, scaffold=_scaffold())

    assert "STRUCT-004 day 1:" in feedback[0]
    assert "Los Angeles" in feedback[0]


def test_format_replan_feedback_prioritizes_structure_before_driving():
    violations = [
        RuleViolation(
            rule_id="DRIVE-001",
            severity="error",
            day=1,
            message="Too much driving",
            actual=7.0,
            limit=6.0,
        ),
        RuleViolation(
            rule_id="STRUCT-004",
            severity="error",
            day=2,
            message="Consecutive stay",
        ),
    ]

    feedback = format_replan_feedback(violations)

    assert feedback[0].startswith("STRUCT-004")


def test_format_replan_feedback_caps_items():
    violations = [
        RuleViolation(rule_id="POI-003", severity="error", day=day, message=f"Stop {day}")
        for day in range(1, 12)
    ]

    feedback = format_replan_feedback(violations)

    assert len(feedback) == 8


def test_format_warning_replan_feedback_targets_pacing_rules():
    warnings = [
        RuleViolation(
            rule_id="DRIVE-001",
            severity="warning",
            day=1,
            message="Near limit",
            actual=5.5,
            limit=6.0,
        ),
        RuleViolation(
            rule_id="ROUTE-002",
            severity="warning",
            message="Near backtrack",
            actual=12.0,
            limit=15.0,
        ),
    ]

    feedback = format_warning_replan_feedback(warnings)

    assert any(item.startswith("DRIVE-001 warning") for item in feedback)
    assert any(item.startswith("ROUTE-002 warning") for item in feedback)
