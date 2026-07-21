from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.services.poi_providers import get_poi_provider
from app.services.poi_providers.google_places import GooglePlacesPOIProvider
from app.services.poi_providers.osm import OsmPOIProvider
from app.tools.places import search_places_nearby


def test_get_poi_provider_defaults_to_osm():
    settings = Settings(openai_api_key="test-key")
    assert isinstance(get_poi_provider(settings), OsmPOIProvider)


def test_get_poi_provider_uses_google_when_configured():
    settings = Settings(
        openai_api_key="test-key",
        poi_provider="google_places",
        google_places_api_key="places-key",
    )
    assert isinstance(get_poi_provider(settings), GooglePlacesPOIProvider)


@pytest.mark.asyncio
async def test_search_places_nearby_returns_osm_results():
    settings = MagicMock()
    settings.poi_provider = "osm"
    settings.google_places_api_key = ""

    mock_items = [
        {
            "name": "Near Museum",
            "lat": 36.601,
            "lon": -121.901,
            "category": "museum",
            "dist_km": 0.2,
            "phone": "+1-555-0100",
            "website": None,
            "address": None,
            "opening_hours": None,
            "reservation_required": True,
        }
    ]

    with patch("app.tools.places.get_settings", return_value=settings):
        with patch(
            "app.services.poi_providers.osm.query_osm_pois_nearby",
            new=AsyncMock(return_value=mock_items),
        ):
            result = await search_places_nearby.ainvoke(
                {"lat": 36.6, "lon": -121.9, "radius_km": 10, "interest": "museum"}
            )

    assert "Near Museum" in result
    assert "phone=+1-555-0100" in result
    assert "OpenStreetMap POIs" in result


@pytest.mark.asyncio
async def test_search_places_nearby_reports_google_stub_message():
    settings = MagicMock()
    settings.poi_provider = "google_places"
    settings.google_places_api_key = "places-key"

    with patch("app.tools.places.get_settings", return_value=settings):
        result = await search_places_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "interest": "museum"}
        )

    assert "not implemented" in result.lower()
