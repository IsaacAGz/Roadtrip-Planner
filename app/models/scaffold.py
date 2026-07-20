from pydantic import BaseModel, Field

from app.services.nominatim import GeocodedLocation


class DayLegSpec(BaseModel):
    day: int = Field(ge=1)
    leg_start_lat: float
    leg_start_lon: float
    leg_end_lat: float
    leg_end_lon: float
    max_driving_hours: float = Field(ge=0.0)
    suggested_overnight_city: str
    suggested_overnight_lat: float
    suggested_overnight_lon: float
    country_code: str = ""


class TripScaffold(BaseModel):
    origin: GeocodedLocation
    destination: GeocodedLocation
    days: list[DayLegSpec]
    route_geometry: list[list[float]] = Field(default_factory=list)
    trip_duration_hours: float = 0.0
