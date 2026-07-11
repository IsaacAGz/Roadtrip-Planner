from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.services.nominatim import LatLon

OSRM_MIN_DISTANCE_KM = 0.001


@dataclass
class RouteResult:
    distance_km: float
    duration_hours: float


class OSRMClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache: dict[tuple[LatLon, LatLon], RouteResult] = {}

    def _coord_str(self, point: LatLon) -> str:
        lat, lon = point
        return f"{lon},{lat}"

    async def route(self, origin: LatLon, destination: LatLon) -> RouteResult:
        key = (origin, destination)
        if key in self._cache:
            return self._cache[key]

        coords = f"{self._coord_str(origin)};{self._coord_str(destination)}"
        url = f"{self._settings.osrm_base_url}/route/v1/driving/{coords}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"overview": "false", "steps": "false"})
            response.raise_for_status()
            data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM could not find route between {origin} and {destination}")

        route = data["routes"][0]
        result = RouteResult(
            distance_km=route["distance"] / 1000.0,
            duration_hours=route["duration"] / 3600.0,
        )
        self._cache[key] = result
        return result

    async def distance_km(self, origin: LatLon, destination: LatLon) -> float:
        return (await self.route(origin, destination)).distance_km

    async def duration_hours(self, origin: LatLon, destination: LatLon) -> float:
        return (await self.route(origin, destination)).duration_hours


_osrm_client: OSRMClient | None = None


def get_osrm_client() -> OSRMClient:
    global _osrm_client
    if _osrm_client is None:
        _osrm_client = OSRMClient()
    return _osrm_client
