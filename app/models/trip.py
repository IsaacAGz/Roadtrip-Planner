from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.constraints import TripConstraints


class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: date
    end_date: date
    preferences: str | None = None
    constraints: TripConstraints = Field(default_factory=TripConstraints)

    @model_validator(mode="after")
    def validate_dates(self) -> "TripRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
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
