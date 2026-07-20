from app.agents.planner import run_planner
from app.agents.validator import run_validator
from app.models.job import ProgressStage
from app.models.trip import TripRequest, TripResponse
from app.models.validation import ValidationReport
from app.services.job_store import job_store
from app.services.plan_enrichment import ScaffoldMode, enrich_plan
from app.services.replan_feedback import format_replan_feedback
from app.services.soft_precheck import run_soft_precheck
from app.services.trip_scaffold import (
    ScaffoldValidationError,
    build_trip_scaffold,
    validate_scaffold_legs,
)
from app.validators.feasibility import resolve_feasibility
from app.validators.hard import run_hard_validators

DRIVING_ROUTING_RULES = frozenset({"DRIVE-001", "DRIVE-002", "ROUTE-002"})


def _scaffold_mode_for_failures(rule_ids: set[str]) -> ScaffoldMode:
    if rule_ids & DRIVING_ROUTING_RULES:
        return "structure_only"
    return "enforce"


async def run_planning_job(job_id: str, request: TripRequest) -> None:
    try:
        job_store.set_running(job_id)
        result = await _execute_planning_loop(job_id, request)
        job_store.complete(job_id, result)
    except ScaffoldValidationError as exc:
        job_store.fail(job_id, exc.message)
    except Exception as exc:
        job_store.fail(job_id, str(exc))


async def _execute_planning_loop(job_id: str, request: TripRequest) -> TripResponse:
    constraints = request.constraints
    feedback: list[str] = []
    last_plan = None
    last_hard_report: ValidationReport | None = None
    attempts = 0
    scaffold_mode: ScaffoldMode = "enforce"

    feasibility_context = await resolve_feasibility(request)
    scaffold = await build_trip_scaffold(request, feasibility_context)
    if scaffold is not None:
        await validate_scaffold_legs(scaffold, request)

    for attempt in range(constraints.max_replan_attempts + 1):
        attempts = attempt
        replan_note = f" (replan {attempt})" if attempt > 0 else ""
        job_store.add_progress(
            job_id,
            ProgressStage.PLANNING,
            f"Running planner{replan_note}",
            attempt=attempt,
        )

        plan = await run_planner(request, feedback, scaffold=scaffold)
        last_plan = plan

        job_store.add_progress(
            job_id,
            ProgressStage.PLANNING,
            f"Normalizing plan (legs, driving, stops){replan_note}",
            attempt=attempt,
        )
        plan = await enrich_plan(
            plan,
            request,
            scaffold=scaffold,
            scaffold_mode=scaffold_mode,
        )

        job_store.add_progress(
            job_id,
            ProgressStage.HARD_VALIDATION,
            f"Running hard validators{replan_note}",
            attempt=attempt,
        )
        hard_report = await run_hard_validators(plan, request)
        last_hard_report = hard_report

        if hard_report.hard_failures:
            feedback = format_replan_feedback(hard_report.hard_failures, scaffold=scaffold)
            scaffold_mode = _scaffold_mode_for_failures(
                {failure.rule_id for failure in hard_report.hard_failures}
            )
            continue

        precheck = run_soft_precheck(request, hard_report.warnings)
        if precheck.should_replan:
            feedback = precheck.feedback
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
