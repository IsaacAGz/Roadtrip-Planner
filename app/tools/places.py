from langchain_core.tools import tool

from app.config import get_settings
from app.services.poi_providers import get_poi_provider
from app.services.poi_providers.base import format_poi_results
from app.services.poi_providers.osm import OsmPOIProvider
from app.tools.overpass import _clamp_radius_m


@tool
async def search_places_nearby(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    interest: str = "attractions",
) -> str:
    """Search POIs with contact info near lat/lon; uses configured provider (OSM or Google Places)."""
    settings = get_settings()
    provider = get_poi_provider(settings)
    radius_m = _clamp_radius_m(radius_km)
    effective_radius_km = radius_m / 1000

    if isinstance(provider, OsmPOIProvider):
        results, error = await provider.search_nearby_or_error(
            lat, lon, interest, effective_radius_km
        )
        if error:
            return error
        return format_poi_results(
            results,
            lat=lat,
            lon=lon,
            radius_km=effective_radius_km,
            interest=interest,
            source_label=provider.source_label,
        )

    try:
        results = await provider.search_nearby(lat, lon, interest, effective_radius_km)
    except NotImplementedError as exc:
        return str(exc)

    source_label = getattr(provider, "source_label", "Places")
    return format_poi_results(
        results,
        lat=lat,
        lon=lon,
        radius_km=effective_radius_km,
        interest=interest,
        source_label=source_label,
    )
