from app.models.trip import TripRequest
from app.models.validation import RuleViolation
from app.services.soft_precheck import run_soft_precheck


def _request(**kwargs) -> TripRequest:
    from datetime import date

    defaults = {
        "origin": "San Diego, CA",
        "destination": "Portland, OR",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 15),
        "structured_preferences": {"pace": "relaxed"},
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


def test_soft_precheck_replans_for_relaxed_pacing_warnings():
    request = _request()
    warnings = [
        RuleViolation(
            rule_id="DRIVE-001",
            severity="warning",
            day=1,
            message="Near limit",
            actual=5.5,
            limit=6.0,
        )
    ]

    result = run_soft_precheck(request, warnings)

    assert result.should_replan is True
    assert result.feedback[0].startswith("DRIVE-001 warning")


def test_soft_precheck_skips_non_relaxed_pace():
    request = _request(structured_preferences={"pace": "moderate"})
    warnings = [
        RuleViolation(
            rule_id="DRIVE-001",
            severity="warning",
            day=1,
            message="Near limit",
            actual=5.5,
            limit=6.0,
        )
    ]

    result = run_soft_precheck(request, warnings)

    assert result.should_replan is False
    assert result.feedback == []
