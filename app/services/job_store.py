import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.models.job import (
    JobStatus,
    PlanningJobResponse,
    ProgressEvent,
    ProgressStage,
)
from app.models.trip import TripRequest, TripResponse


@dataclass
class PlanningJobRecord:
    job_id: str
    status: JobStatus
    request: TripRequest
    progress: list[ProgressEvent] = field(default_factory=list)
    result: TripResponse | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_response(self) -> PlanningJobResponse:
        return PlanningJobResponse(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            result=self.result,
            error=self.error,
        )


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, PlanningJobRecord] = {}
        self._subscribers: dict[str, list[asyncio.Queue[PlanningJobResponse | None]]] = (
            defaultdict(list)
        )

    def clear(self) -> None:
        self._jobs.clear()
        for subscribers in self._subscribers.values():
            for queue in subscribers:
                queue.put_nowait(None)
        self._subscribers.clear()

    def subscribe(self, job_id: str) -> asyncio.Queue[PlanningJobResponse | None]:
        queue: asyncio.Queue[PlanningJobResponse | None] = asyncio.Queue()
        self._subscribers[job_id].append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[PlanningJobResponse | None]) -> None:
        subscribers = self._subscribers.get(job_id, [])
        if queue in subscribers:
            subscribers.remove(queue)

    def _publish(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        response = job.to_response()
        for queue in list(self._subscribers.get(job_id, [])):
            queue.put_nowait(response)

    def create_job(self, request: TripRequest) -> PlanningJobRecord:
        job_id = str(uuid4())
        job = PlanningJobRecord(
            job_id=job_id,
            status=JobStatus.QUEUED,
            request=request,
            progress=[
                ProgressEvent(
                    stage=ProgressStage.QUEUED,
                    message="Planning job queued",
                )
            ],
        )
        self._jobs[job_id] = job
        self._publish(job_id)
        return job

    def get_job(self, job_id: str) -> PlanningJobRecord | None:
        return self._jobs.get(job_id)

    def set_running(self, job_id: str) -> None:
        job = self._require_job(job_id)
        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(timezone.utc)
        self._publish(job_id)

    def add_progress(
        self,
        job_id: str,
        stage: ProgressStage,
        message: str,
        *,
        attempt: int | None = None,
    ) -> None:
        job = self._require_job(job_id)
        job.progress.append(
            ProgressEvent(
                stage=stage,
                message=message,
                attempt=attempt,
            )
        )
        job.updated_at = datetime.now(timezone.utc)
        self._publish(job_id)

    def complete(self, job_id: str, result: TripResponse) -> None:
        job = self._require_job(job_id)
        job.status = JobStatus.COMPLETED
        job.result = result
        job.progress.append(
            ProgressEvent(
                stage=ProgressStage.COMPLETED,
                message="Planning completed",
            )
        )
        job.updated_at = datetime.now(timezone.utc)
        self._publish(job_id)

    def fail(self, job_id: str, error: str) -> None:
        job = self._require_job(job_id)
        job.status = JobStatus.FAILED
        job.error = error
        job.progress.append(
            ProgressEvent(
                stage=ProgressStage.FAILED,
                message=error,
            )
        )
        job.updated_at = datetime.now(timezone.utc)
        self._publish(job_id)

    def _require_job(self, job_id: str) -> PlanningJobRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job


job_store = JobStore()
