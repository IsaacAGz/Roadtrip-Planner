from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.job import JobStatus, PlanningJobCreatedResponse, PlanningJobResponse
from app.models.trip import TripRequest
from app.services.job_store import job_store
from app.services.planning_job import run_planning_job
from app.validators.feasibility import FeasibilityError, check_trip_feasibility

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post(
    "/plan",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PlanningJobCreatedResponse,
)
async def plan_trip(
    request: TripRequest,
    background_tasks: BackgroundTasks,
) -> PlanningJobCreatedResponse:
    try:
        await check_trip_feasibility(request)
    except FeasibilityError as exc:
        raise HTTPException(status_code=422, detail=exc.to_dict()) from exc

    job = job_store.create_job(request)
    background_tasks.add_task(run_planning_job, job.job_id, request)
    return PlanningJobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        status_url=f"/trips/jobs/{job.job_id}",
        events_url=f"/trips/jobs/{job.job_id}/events",
    )


@router.get("/jobs/{job_id}", response_model=PlanningJobResponse)
async def get_planning_job(job_id: str) -> PlanningJobResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_response()


async def _stream_job_events(job_id: str) -> AsyncIterator[str]:
    queue = job_store.subscribe(job_id)
    try:
        job = job_store.get_job(job_id)
        if job is not None:
            current = job.to_response()
            yield f"data: {current.model_dump_json()}\n\n"
            if current.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return

        while True:
            update = await queue.get()
            if update is None:
                break
            yield f"data: {update.model_dump_json()}\n\n"
            if update.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                break
    finally:
        job_store.unsubscribe(job_id, queue)


@router.get("/jobs/{job_id}/events")
async def stream_planning_job_events(job_id: str) -> StreamingResponse:
    if job_store.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return StreamingResponse(
        _stream_job_events(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
