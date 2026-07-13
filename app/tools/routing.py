from langchain_core.tools import tool

from app.services.osrm import get_osrm_client


@tool
async def get_driving_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> str:
    """Get driving distance in km and duration in hours between two coordinates."""
    client = get_osrm_client()
    origin = (origin_lat, origin_lon)
    destination = (dest_lat, dest_lon)
    try:
        route = await client.route(origin, destination)
        return (
            f"Distance: {route.distance_km:.1f} km, "
            f"Duration: {route.duration_hours:.1f} hours"
        )
    except ValueError as exc:
        return str(exc)
