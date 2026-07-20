import math
from typing import Any

from app.models.scaffold import DayLegSpec, TripScaffold
from app.models.trip import TripRequest
from app.services.nominatim import GeocodedLocation, get_nominatim_client
from app.services.osrm import get_osrm_client
from app.validators.feasibility import FeasibilityContext

RELAXED_DRIVING_TARGET_RATIO = 0.85
DEFAULT_DRIVING_TARGET_RATIO = 0.95
SCAFFOLD_LEG_TOLERANCE_HOURS = 0.25


class ScaffoldValidationError(Exception):
    def __init__(
        self,
        *,
        rule_id: str,
        message: str,
        day: int | None = None,
        actual: float | None = None,
        limit: float | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.message = message
        self.day = day
        self.actual = actual
        self.limit = limit
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "day": self.day,
            "actual": self.actual,
            "limit": self.limit,
        }


def _driving_target_ratio(request: TripRequest) -> float:
    if request.structured_preferences.pace == "relaxed":
        return RELAXED_DRIVING_TARGET_RATIO
    return DEFAULT_DRIVING_TARGET_RATIO


def estimate_min_days_for_even_split(
    total_hours: float,
    max_hours_per_day: float,
    *,
    driving_target_ratio: float,
) -> int:
    target_hours = max_hours_per_day * driving_target_ratio
    if target_hours <= 0:
        return 1
    return max(1, math.ceil(total_hours / target_hours))


async def validate_scaffold_legs(scaffold: TripScaffold, request: TripRequest) -> None:
    osrm = get_osrm_client()
    max_hours = request.constraints.max_driving_hours_per_day
    limit = max_hours + SCAFFOLD_LEG_TOLERANCE_HOURS

    for spec in scaffold.days:
        if spec.max_driving_hours <= 0 and spec.suggested_overnight_lat == scaffold.destination.lat:
            continue

        start = (spec.leg_start_lat, spec.leg_start_lon)
        end = (spec.suggested_overnight_lat, spec.suggested_overnight_lon)
        try:
            actual_hours = await osrm.duration_hours(start, end)
        except ValueError as exc:
            raise ScaffoldValidationError(
                rule_id="SCAFFOLD-001",
                message=f"Day {spec.day} scaffold leg could not be verified via OSRM",
                day=spec.day,
            ) from exc

        if actual_hours > limit:
            min_days = estimate_min_days_for_even_split(
                scaffold.trip_duration_hours,
                max_hours,
                driving_target_ratio=_driving_target_ratio(request),
            )
            raise ScaffoldValidationError(
                rule_id="SCAFFOLD-001",
                message=(
                    f"Day {spec.day} would require {actual_hours:.1f}h driving at your "
                    f"{max_hours:.1f}h/day limit. This trip needs at least {min_days} days "
                    f"on the road network, or a higher daily driving limit."
                ),
                day=spec.day,
                actual=round(actual_hours, 1),
                limit=max_hours,
            )


async def build_trip_scaffold(
    request: TripRequest,
    context: FeasibilityContext | None = None,
) -> TripScaffold | None:
    if request.constraints.allow_return_stops:
        return None

    if context is not None:
        origin = context.origin
        destination = context.destination
    else:
        nominatim = get_nominatim_client()
        origin = await nominatim.geocode(request.origin)
        destination = await nominatim.geocode(request.destination)

    osrm = get_osrm_client()
    origin_coords = (origin.lat, origin.lon)
    destination_coords = (destination.lat, destination.lon)
    legs, geometry = await osrm.split_route_into_legs(
        origin_coords,
        destination_coords,
        request.days,
        request.constraints.max_driving_hours_per_day,
        driving_target_ratio=_driving_target_ratio(request),
    )

    nominatim = get_nominatim_client()
    day_specs: list[DayLegSpec] = []
    for index, leg in enumerate(legs):
        day_number = index + 1
        if leg.end == destination_coords and leg.duration_hours == 0.0 and index > 0:
            overnight_city = destination.display_name
            overnight_lat = destination.lat
            overnight_lon = destination.lon
            country_code = destination.country_code
        else:
            try:
                reverse = await nominatim.reverse_geocode(leg.end[0], leg.end[1])
                overnight_city = reverse.display_name
                country_code = reverse.country_code or origin.country_code
            except ValueError:
                overnight_city = f"Day {day_number} stop"
                country_code = origin.country_code
            overnight_lat = leg.end[0]
            overnight_lon = leg.end[1]

        day_specs.append(
            DayLegSpec(
                day=day_number,
                leg_start_lat=leg.start[0],
                leg_start_lon=leg.start[1],
                leg_end_lat=overnight_lat,
                leg_end_lon=overnight_lon,
                max_driving_hours=request.constraints.max_driving_hours_per_day
                * _driving_target_ratio(request),
                suggested_overnight_city=overnight_city,
                suggested_overnight_lat=overnight_lat,
                suggested_overnight_lon=overnight_lon,
                country_code=country_code,
            )
        )

    return TripScaffold(
        origin=origin,
        destination=destination,
        days=day_specs,
        route_geometry=[[lat, lon] for lat, lon in geometry.coordinates] if geometry else [],
        trip_duration_hours=geometry.duration_hours if geometry else 0.0,
    )
