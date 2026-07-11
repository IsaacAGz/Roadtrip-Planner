from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Stop(BaseModel):
    name: str
    lat: float
    lon: float
    category: str = "general"
    duration_hours: float = Field(default=1.0, ge=0.25, le=8.0)
    description: str = ""
    country_code: str = ""


class OvernightStop(BaseModel):
    city: str
    lat: float
    lon: float
    stay_type: Literal["camping", "hotel", "resort", "other"] = "hotel"
    nights: int = Field(default=1, ge=1, le=7)
    is_return_stop: bool = False
    country_code: str = ""


class DayPlan(BaseModel):
    day: int = Field(ge=1)
    date: date
    route_summary: str
    driving_hours: float = Field(default=0.0, ge=0.0, le=24.0)
    stops: list[Stop] = Field(default_factory=list)
    overnight: OvernightStop
    leg_start_lat: float | None = None
    leg_start_lon: float | None = None
    leg_end_lat: float | None = None
    leg_end_lon: float | None = None


class RoadtripPlan(BaseModel):
    title: str
    total_days: int = Field(ge=1)
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    days: list[DayPlan]
    tips: list[str] = Field(default_factory=list)
