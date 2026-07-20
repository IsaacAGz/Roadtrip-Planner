from app.models.itinerary import DayPlan, Stop
from app.services.nominatim import LatLon
from app.services.osrm import get_osrm_client


def day_leg(day_plan: DayPlan) -> tuple[LatLon, LatLon] | None:
    if (
        day_plan.leg_start_lat is None
        or day_plan.leg_start_lon is None
        or day_plan.leg_end_lat is None
        or day_plan.leg_end_lon is None
    ):
        return None
    origin = (day_plan.leg_start_lat, day_plan.leg_start_lon)
    destination = (day_plan.leg_end_lat, day_plan.leg_end_lon)
    return origin, destination


async def detour_km(origin: LatLon, destination: LatLon, stop: Stop) -> float:
    osrm = get_osrm_client()
    stop_point = (stop.lat, stop.lon)
    base = await osrm.distance_km(origin, destination)
    via = await osrm.distance_km(origin, stop_point) + await osrm.distance_km(
        stop_point, destination
    )
    return via - base
