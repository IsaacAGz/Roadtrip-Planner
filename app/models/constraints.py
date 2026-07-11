from pydantic import BaseModel, Field, field_validator

DEFAULT_EXCLUDED_CATEGORIES = ["extremely_dangerous", "illegal"]
DEFAULT_ALLOWED_COUNTRIES = ["US", "MX"]
SYSTEM_EXCLUDED_CATEGORIES = frozenset(DEFAULT_EXCLUDED_CATEGORIES)


def effective_excluded_categories(request_excluded: list[str]) -> set[str]:
    normalized = {c.strip().lower().replace(" ", "_") for c in request_excluded}
    return set(SYSTEM_EXCLUDED_CATEGORIES) | normalized


class TripConstraints(BaseModel):
    max_driving_hours_per_day: float = Field(default=6.0, ge=1.0, le=8.0)
    max_stops_per_day: int = Field(default=4, ge=1, le=8)
    max_detour_km_per_stop: float = Field(default=30.0, ge=0.0, le=100.0)
    max_backtracking_percent: float = Field(default=15.0, ge=0.0, le=50.0)
    require_progress_toward_destination: bool = True
    allowed_countries: list[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_COUNTRIES))
    excluded_poi_categories: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXCLUDED_CATEGORIES)
    )
    allow_extended_stays: bool = False
    max_nights_per_stop: int = Field(default=1, ge=1, le=7)
    allow_return_stops: bool = False
    max_replan_attempts: int = Field(default=2, ge=0, le=5)

    @field_validator("allowed_countries")
    @classmethod
    def normalize_countries(cls, value: list[str]) -> list[str]:
        return [country.strip().upper() for country in value]

    @field_validator("excluded_poi_categories")
    @classmethod
    def normalize_categories(cls, value: list[str]) -> list[str]:
        return [category.strip().lower().replace(" ", "_") for category in value]

    def effective_require_progress(self) -> bool:
        if self.allow_return_stops:
            return False
        return self.require_progress_toward_destination
