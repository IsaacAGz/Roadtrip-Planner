from dataclasses import dataclass

from app.models.trip import TripRequest
from app.models.validation import RuleViolation
from app.services.replan_feedback import format_warning_replan_feedback


@dataclass
class SoftPrecheckResult:
    should_replan: bool
    feedback: list[str]


def run_soft_precheck(
    request: TripRequest,
    warnings: list[RuleViolation],
) -> SoftPrecheckResult:
    if request.structured_preferences.pace != "relaxed":
        return SoftPrecheckResult(should_replan=False, feedback=[])

    pacing_warnings = [
        warning
        for warning in warnings
        if warning.rule_id in {"DRIVE-001", "SCHED-001"}
    ]
    if not pacing_warnings:
        return SoftPrecheckResult(should_replan=False, feedback=[])

    return SoftPrecheckResult(
        should_replan=True,
        feedback=format_warning_replan_feedback(pacing_warnings),
    )
