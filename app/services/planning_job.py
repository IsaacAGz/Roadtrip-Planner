from app.agents.planner import run_planner
from app.agents.validator import run_validator
from app.models.job import ProgressStage
from app.models.trip import TripRequest, TripResponse
from app.models.validation import ValidationReport
from app.services.job_store import job_store
from app.validators.hard import run_hard_validators


async def run_planning_job(job_id: str, request: TripRequest) -> None:
    try:
        job_store.set_running(job_id)
        result = await _execute_planning_loop(job_id, request)
        job_store.complete(job_id, result)
    except Exception as exc:
        job_store.fail(job_id, str(exc))


async def _execute_planning_loop(job_id: str, request: TripRequest) -> TripResponse:
    constraints = request.constraints
    feedback: list[str] = []
    last_plan = None
    last_hard_report: ValidationReport | None = None
    attempts = 0

    for attempt in range(constraints.max_replan_attempts + 1):
        attempts = attempt
        replan_note = f" (replan {attempt})" if attempt > 0 else ""
        job_store.add_progress(
            job_id,
            ProgressStage.PLANNING,
            f"Running planner{replan_note}",
            attempt=attempt,
        )

        plan = await run_planner(request, feedback)
        last_plan = plan

        job_store.add_progress(
            job_id,
            ProgressStage.HARD_VALIDATION,
            f"Running hard validators{replan_note}",
            attempt=attempt,
        )
        hard_report = await run_hard_validators(plan, request)
        last_hard_report = hard_report

        if hard_report.hard_failures:
            feedback = [violation.message for violation in hard_report.hard_failures]
            continue

        job_store.add_progress(
            job_id,
            ProgressStage.SOFT_VALIDATION,
            f"Running validator agent{replan_note}",
            attempt=attempt,
        )
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
        raise RuntimeError("Planner did not produce an itinerary")

    validation = ValidationReport(
        approved=False,
        hard_failures=last_hard_report.hard_failures,
        warnings=last_hard_report.warnings,
        replan_attempts=attempts,
    )
    return TripResponse(plan=last_plan, validation=validation, replan_attempts=attempts)
