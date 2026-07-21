import math
from dataclasses import dataclass
from typing import Any

from app.models.trip import TripRequest
from app.services.nominatim import GeocodedLocation, get_nominatim_client
from app.services.osrm import RouteResult, get_osrm_client


class FeasibilityError(Exception):
    def __init__(
        self,
        *,
        rule_id: str,
        message: str,
        actual: float | int | str | None = None,
        limit: float | int | str | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.message = message
        self.actual = actual
        self.limit = limit
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "actual": self.actual,
            "limit": self.limit,
        }


@dataclass
class FeasibilityContext:
    origin: GeocodedLocation
    destination: GeocodedLocation
    route: RouteResult


def _check_country_allowed(
    location: GeocodedLocation,
    *,
    role: str,
    allowed_countries: list[str],
) -> None:
    allowed = {country.upper() for country in allowed_countries}
    code = location.country_code.upper()
    if code and code not in allowed:
        raise FeasibilityError(
            rule_id="FEAS-002",
            message=(
                f"{role} '{location.display_name}' country '{code}' is not in "
                f"allowed countries {sorted(allowed)}"
            ),
            actual=code,
            limit=", ".join(sorted(allowed)),
        )


async def resolve_feasibility(request: TripRequest) -> FeasibilityContext:
    nominatim = get_nominatim_client()
    constraints = request.constraints

    try:
        origin = await nominatim.geocode(request.origin)
    except ValueError as exc:
        raise FeasibilityError(
            rule_id="FEAS-002",
            message=str(exc),
            actual=request.origin,
        ) from exc

    try:
        destination = await nominatim.geocode(request.destination)
    except ValueError as exc:
        raise FeasibilityError(
            rule_id="FEAS-002",
            message=str(exc),
            actual=request.destination,
        ) from exc

    _check_country_allowed(origin, role="Origin", allowed_countries=constraints.allowed_countries)
    _check_country_allowed(
        destination,
        role="Destination",
        allowed_countries=constraints.allowed_countries,
    )

    osrm = get_osrm_client()
    origin_coords = (origin.lat, origin.lon)
    destination_coords = (destination.lat, destination.lon)

    try:
        route = await osrm.route(origin_coords, destination_coords)
    except ValueError as exc:
        raise FeasibilityError(
            rule_id="FEAS-003",
            message=str(exc),
        ) from exc

    effective_hours = route.duration_hours
    if constraints.allow_return_stops:
        effective_hours *= 2

    min_days_required = max(
        1,
        math.ceil(effective_hours / constraints.max_driving_hours_per_day),
    )

    if request.days < min_days_required:
        trip_type = "round-trip" if constraints.allow_return_stops else "one-way"
        raise FeasibilityError(
            rule_id="FEAS-001",
            message=(
                f"Trip requires at least {min_days_required} driving days at "
                f"{constraints.max_driving_hours_per_day}h/day "
                f"(OSRM {trip_type} {effective_hours:.1f}h) but request allows "
                f"{request.days} days"
            ),
            actual=request.days,
            limit=min_days_required,
        )

    return FeasibilityContext(origin=origin, destination=destination, route=route)


async def check_trip_feasibility(request: TripRequest) -> None:
    await resolve_feasibility(request)
