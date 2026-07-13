from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.models.constraints import TripConstraints


class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: date
    end_date: date
    preferences: str | None = None
    constraints: TripConstraints = Field(default_factory=TripConstraints)

    @field_validator("origin", "destination")
    @classmethod
    def validate_non_empty_location(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @model_validator(mode="after")
    def validate_request(self) -> "TripRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.constraints.max_nights_per_stop > self.days:
            raise ValueError(
                f"max_nights_per_stop ({self.constraints.max_nights_per_stop}) "
                f"cannot exceed trip length ({self.days} days)"
            )
        return self

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class TripResponse(BaseModel):
    plan: "RoadtripPlan"
    validation: "ValidationReport"
    replan_attempts: int


from app.models.itinerary import RoadtripPlan  # noqa: E402
from app.models.validation import ValidationReport  # noqa: E402

TripResponse.model_rebuild()
