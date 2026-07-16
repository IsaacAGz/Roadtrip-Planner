from pydantic import BaseModel, Field, field_validator, model_validator

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
    allowed_countries: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_COUNTRIES),
        min_length=1,
    )
    excluded_poi_categories: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXCLUDED_CATEGORIES)
    )
    allow_extended_stays: bool = False
    max_nights_per_stop: int = Field(default=1, ge=1, le=7)
    allow_return_stops: bool = False
    max_replan_attempts: int = Field(default=2, ge=0, le=5)
    fail_on_weather_warnings: bool = False
    max_precip_chance: float = Field(default=0.5, ge=0.0, le=1.0)
    min_temp_c: float = Field(default=10.0, ge=-30.0, le=40.0)

    @field_validator("allowed_countries")
    @classmethod
    def normalize_countries(cls, value: list[str]) -> list[str]:
        return [country.strip().upper() for country in value]

    @field_validator("excluded_poi_categories")
    @classmethod
    def normalize_categories(cls, value: list[str]) -> list[str]:
        return [category.strip().lower().replace(" ", "_") for category in value]

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> "TripConstraints":
        if not self.allow_extended_stays and self.max_nights_per_stop > 1:
            raise ValueError(
                "max_nights_per_stop > 1 requires allow_extended_stays=true"
            )
        if self.allow_return_stops and self.max_backtracking_percent < 25.0:
            self.max_backtracking_percent = 25.0
        return self

    def effective_require_progress(self) -> bool:
        if self.allow_return_stops:
            return False
        return self.require_progress_toward_destination
