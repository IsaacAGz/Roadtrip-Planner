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


_nominatim_client: NominatimClient | None = None


def get_nominatim_client() -> NominatimClient:
    global _nominatim_client
    if _nominatim_client is None:
        _nominatim_client = NominatimClient()
    return _nominatim_client
