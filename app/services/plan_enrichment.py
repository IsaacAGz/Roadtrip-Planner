import math
from datetime import timedelta
from typing import Literal

from app.models.constraints import TripConstraints, effective_excluded_categories
from app.models.itinerary import RoadtripPlan, Stop
from app.models.scaffold import TripScaffold
from app.models.trip import TripRequest
from app.services.osrm import get_osrm_client
from app.services.routing_utils import day_leg, detour_km

ScaffoldMode = Literal["enforce", "structure_only", "off"]

CATEGORY_ALIASES = {
    "view_point": "viewpoint",
    "campground": "camp_site",
}

RELAXED_DETOUR_TARGET_RATIO = 0.75
DEFAULT_DETOUR_TARGET_RATIO = 1.0
SCAFFOLD_OVERNIGHT_DISTANCE_KM = 30.0


def normalize_stop_category(category: str) -> str:
    normalized = category.strip().lower().replace(" ", "_")
    return CATEGORY_ALIASES.get(normalized, normalized)


def _detour_target_km(constraints: TripConstraints, request: TripRequest) -> float:
    ratio = (
        RELAXED_DETOUR_TARGET_RATIO
        if request.structured_preferences.pace == "relaxed"
        else DEFAULT_DETOUR_TARGET_RATIO
    )
    return constraints.max_detour_km_per_stop * ratio


def _repair_structure(plan: RoadtripPlan, request: TripRequest) -> None:
    expected_days = request.days
    plan.total_days = expected_days

    for index, day_plan in enumerate(plan.days):
        day_plan.day = index + 1
        day_plan.date = request.start_date + timedelta(days=index)


def _chain_legs(plan: RoadtripPlan) -> None:
    for index, day_plan in enumerate(plan.days):
        if index == 0:
            day_plan.leg_start_lat = plan.origin_lat
            day_plan.leg_start_lon = plan.origin_lon
        else:
            previous = plan.days[index - 1].overnight
            day_plan.leg_start_lat = previous.lat
            day_plan.leg_start_lon = previous.lon

        day_plan.leg_end_lat = day_plan.overnight.lat
        day_plan.leg_end_lon = day_plan.overnight.lon


async def _apply_osrm_driving_hours(plan: RoadtripPlan) -> None:
    osrm = get_osrm_client()
    for day_plan in plan.days:
        leg = day_leg(day_plan)
        if leg is None:
            continue
        try:
            day_plan.driving_hours = await osrm.duration_hours(leg[0], leg[1])
        except ValueError:
            continue


def _filter_excluded_stops(plan: RoadtripPlan, constraints: TripConstraints) -> None:
    excluded = effective_excluded_categories(constraints.excluded_poi_categories)
    for day_plan in plan.days:
        filtered: list[Stop] = []
        for stop in day_plan.stops:
            category = normalize_stop_category(stop.category)
            stop.category = category
            if category not in excluded:
                filtered.append(stop)
        day_plan.stops = filtered


async def _trim_stops(plan: RoadtripPlan, request: TripRequest) -> None:
    constraints = request.constraints
    detour_limit = _detour_target_km(constraints, request)

    for day_plan in plan.days:
        while len(day_plan.stops) > constraints.max_stops_per_day:
            day_plan.stops.pop()

        leg = day_leg(day_plan)
        if leg is None or day_plan.driving_hours <= 0:
            continue

        origin, destination = leg
        while day_plan.stops:
            detours: list[tuple[float, Stop]] = []
            for stop in day_plan.stops:
                try:
                    detours.append((await detour_km(origin, destination, stop), stop))
                except ValueError:
                    detours.append((float("inf"), stop))

            worst_detour, worst_stop = max(detours, key=lambda item: item[0])
            if worst_detour <= detour_limit:
                break
            day_plan.stops = [stop for stop in day_plan.stops if stop is not worst_stop]


def _overnight_distance_km(
    overnight_lat: float,
    overnight_lon: float,
    target_lat: float,
    target_lon: float,
) -> float:
    lat_delta = overnight_lat - target_lat
    lon_delta = overnight_lon - target_lon
    return math.sqrt(lat_delta * lat_delta + lon_delta * lon_delta) * 111.0


def _consecutive_same_city(plan: RoadtripPlan, day_index: int) -> bool:
    if day_index <= 0:
        return False
    current = plan.days[day_index].overnight.city.strip().lower()
    previous = plan.days[day_index - 1].overnight.city.strip().lower()
    return current == previous


def _apply_scaffold_overnight(plan: RoadtripPlan, day_plan_index: int, spec) -> None:
    day_plan = plan.days[day_plan_index]
    day_plan.overnight.city = spec.suggested_overnight_city
    day_plan.overnight.lat = spec.suggested_overnight_lat
    day_plan.overnight.lon = spec.suggested_overnight_lon
    day_plan.overnight.country_code = spec.country_code


def _enforce_scaffold_overnights(
    plan: RoadtripPlan,
    scaffold: TripScaffold,
    *,
    scaffold_mode: ScaffoldMode,
) -> None:
    if scaffold_mode == "off":
        return

    scaffold_by_day = {spec.day: spec for spec in scaffold.days}
    for index, day_plan in enumerate(plan.days):
        spec = scaffold_by_day.get(day_plan.day)
        if spec is None:
            continue

        far_from_scaffold = _overnight_distance_km(
            day_plan.overnight.lat,
            day_plan.overnight.lon,
            spec.suggested_overnight_lat,
            spec.suggested_overnight_lon,
        ) > SCAFFOLD_OVERNIGHT_DISTANCE_KM
        consecutive_same = _consecutive_same_city(plan, index)

        if scaffold_mode == "structure_only":
            if consecutive_same:
                _apply_scaffold_overnight(plan, index, spec)
        elif consecutive_same or far_from_scaffold:
            _apply_scaffold_overnight(plan, index, spec)


async def _attach_route_geometry(
    plan: RoadtripPlan,
    scaffold: TripScaffold | None,
) -> None:
    if scaffold and scaffold.route_geometry:
        plan.route_geometry = scaffold.route_geometry
        return

    if plan.route_geometry:
        return

    osrm = get_osrm_client()
    origin = (plan.origin_lat, plan.origin_lon)
    destination = (plan.destination_lat, plan.destination_lon)
    try:
        geometry = await osrm.route_geometry(origin, destination)
    except ValueError:
        return

    plan.route_geometry = [[lat, lon] for lat, lon in geometry.coordinates]


async def enrich_plan(
    plan: RoadtripPlan,
    request: TripRequest,
    *,
    scaffold: TripScaffold | None = None,
    scaffold_mode: ScaffoldMode = "enforce",
) -> RoadtripPlan:
    constraints = request.constraints

    if len(plan.days) > request.days:
        plan.days = plan.days[: request.days]

    _repair_structure(plan, request)

    if scaffold is not None:
        _enforce_scaffold_overnights(plan, scaffold, scaffold_mode=scaffold_mode)

    _chain_legs(plan)
    await _apply_osrm_driving_hours(plan)
    _filter_excluded_stops(plan, constraints)
    await _trim_stops(plan, request)

    if scaffold is not None:
        _enforce_scaffold_overnights(plan, scaffold, scaffold_mode=scaffold_mode)
        _chain_legs(plan)
        await _apply_osrm_driving_hours(plan)

    await _attach_route_geometry(plan, scaffold)

    return plan
