import httpx

from app.services.poi_providers.base import POIResult, poi_result_from_osm_item
from app.tools.overpass import _clamp_radius_m, query_osm_pois_nearby


class OsmPOIProvider:
    source_label = "OpenStreetMap"

    async def search_nearby(
        self,
        lat: float,
        lon: float,
        interest: str,
        radius_km: float,
    ) -> list[POIResult]:
        try:
            items = await query_osm_pois_nearby(lat, lon, radius_km, interest)
        except httpx.HTTPError:
            return []
        return [poi_result_from_osm_item(item) for item in items]

    async def search_nearby_or_error(
        self,
        lat: float,
        lon: float,
        interest: str,
        radius_km: float,
    ) -> tuple[list[POIResult], str | None]:
        radius_m = _clamp_radius_m(radius_km)
        try:
            items = await query_osm_pois_nearby(lat, lon, radius_km, interest)
        except httpx.HTTPStatusError as exc:
            return [], (
                f"Overpass POI search failed near ({lat}, {lon}): "
                f"HTTP {exc.response.status_code}"
            )
        except httpx.RequestError as exc:
            return [], f"Overpass POI search failed near ({lat}, {lon}): {exc}"

        return [poi_result_from_osm_item(item) for item in items], None
