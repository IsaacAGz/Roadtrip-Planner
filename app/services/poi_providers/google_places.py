from app.services.poi_providers.base import POIResult


class GooglePlacesPOIProvider:
    source_label = "Google Places"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search_nearby(
        self,
        lat: float,
        lon: float,
        interest: str,
        radius_km: float,
    ) -> list[POIResult]:
        raise NotImplementedError(
            "Google Places POI search is not implemented yet. "
            "Set POI_PROVIDER=osm or leave GOOGLE_PLACES_API_KEY unset."
        )
