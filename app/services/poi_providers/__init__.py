from typing import Literal

from app.config import Settings
from app.services.poi_providers.base import POIProvider
from app.services.poi_providers.google_places import GooglePlacesPOIProvider
from app.services.poi_providers.osm import OsmPOIProvider

POIProviderName = Literal["osm", "google_places"]


def get_poi_provider(settings: Settings) -> POIProvider:
    if settings.poi_provider == "google_places" and settings.google_places_api_key:
        return GooglePlacesPOIProvider(settings.google_places_api_key)
    return OsmPOIProvider()
