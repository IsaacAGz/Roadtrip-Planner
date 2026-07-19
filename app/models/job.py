from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.models.trip import TripResponse


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressStage(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    HARD_VALIDATION = "hard_validation"
    SOFT_VALIDATION = "soft_validation"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressEvent(BaseModel):
    stage: ProgressStage
    message: str
    attempt: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanningJobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    events_url: str


class PlanningJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: list[ProgressEvent] = Field(default_factory=list)
    result: TripResponse | None = None
    error: str | None = None
