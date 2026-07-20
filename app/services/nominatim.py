import asyncio
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

LatLon = tuple[float, float]


@dataclass
class GeocodedLocation:
    display_name: str
    lat: float
    lon: float
    country_code: str


class NominatimClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._last_request_at = 0.0
        self._cache: dict[str, GeocodedLocation] = {}

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        self._last_request_at = time.monotonic()

    async def geocode(self, query: str) -> GeocodedLocation:
        normalized = query.strip().lower()
        if normalized in self._cache:
            return self._cache[normalized]

        await self._throttle()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._settings.nominatim_base_url}/search",
                params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": self._settings.nominatim_user_agent},
            )
            response.raise_for_status()
            data = response.json()

        if not data:
            raise ValueError(f"Could not geocode location: {query}")

        item = data[0]
        address = item.get("address", {})
        country_code = (
            address.get("country_code", "") or address.get("country_code", "")
        ).upper()

        result = GeocodedLocation(
            display_name=item["display_name"],
            lat=float(item["lat"]),
            lon=float(item["lon"]),
            country_code=country_code,
        )
        self._cache[normalized] = result
        return result

    async def reverse_geocode(self, lat: float, lon: float) -> GeocodedLocation:
        cache_key = f"{lat:.5f},{lon:.5f}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        await self._throttle()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._settings.nominatim_base_url}/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
                headers={"User-Agent": self._settings.nominatim_user_agent},
            )
            response.raise_for_status()
            item = response.json()

        if not item:
            raise ValueError(f"Could not reverse geocode location: ({lat}, {lon})")

        address = item.get("address", {})
        country_code = (address.get("country_code", "") or "").upper()
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("hamlet")
            or address.get("county")
            or item.get("display_name", "Overnight stop")
        )

        result = GeocodedLocation(
            display_name=str(city),
            lat=lat,
            lon=lon,
            country_code=country_code,
        )
        self._cache[cache_key] = result
        return result


_nominatim_client: NominatimClient | None = None


def get_nominatim_client() -> NominatimClient:
    global _nominatim_client
    if _nominatim_client is None:
        _nominatim_client = NominatimClient()
    return _nominatim_client
