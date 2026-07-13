from fastapi import APIRouter, HTTPException

from app.agents.planner import run_planner
from app.agents.validator import run_validator
from app.models.trip import TripRequest, TripResponse
from app.models.validation import ValidationReport
from app.validators.hard import run_hard_validators

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/plan", response_model=TripResponse)
async def plan_trip(request: TripRequest) -> TripResponse:
    constraints = request.constraints
    feedback: list[str] = []
    last_plan = None
    last_hard_report: ValidationReport | None = None
    attempts = 0

    for attempt in range(constraints.max_replan_attempts + 1):
        attempts = attempt
        plan = await run_planner(request, feedback)
        last_plan = plan

        hard_report = await run_hard_validators(plan, request)
        last_hard_report = hard_report

        if hard_report.hard_failures:
            feedback = [violation.message for violation in hard_report.hard_failures]
            continue

        soft_result = await run_validator(plan, request, hard_report.warnings)
        if soft_result.approved:
            validation = ValidationReport(
                approved=True,
                hard_failures=[],
                warnings=hard_report.warnings,
                replan_attempts=attempt,
            )
            return TripResponse(plan=plan, validation=validation, replan_attempts=attempt)

        feedback = soft_result.replan_instructions or soft_result.issues

    if last_plan is None or last_hard_report is None:
        raise HTTPException(status_code=500, detail="Planner did not produce an itinerary")

    validation = ValidationReport(
        approved=False,
        hard_failures=last_hard_report.hard_failures,
        warnings=last_hard_report.warnings,
        replan_attempts=attempts,
    )
    return TripResponse(plan=last_plan, validation=validation, replan_attempts=attempts)
