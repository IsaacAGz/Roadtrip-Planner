from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.accommodations import (
    _accommodation_tags,
    _build_accommodation_query,
    _format_accommodation_results,
    _parse_accommodation_elements,
    search_osm_accommodations_nearby,
)


@pytest.fixture(autouse=True)
def mock_settings():
    settings = MagicMock()
    settings.overpass_api_url = "https://overpass-api.de/api/interpreter"
    settings.nominatim_user_agent = "RoadtripPlanner/1.0 (test@example.com)"
    with patch("app.tools.accommodations.get_settings", return_value=settings):
        yield


def test_accommodation_tags_budget_hotel():
    tags = _accommodation_tags("hotel", "budget")
    assert ("tourism", "motel") in tags
    assert ("tourism", "guest_house") in tags


def test_accommodation_tags_camping():
    tags = _accommodation_tags("camping", "moderate")
    assert tags == [("tourism", "camp_site")]


def test_build_accommodation_query_includes_hotel_tags():
    query = _build_accommodation_query(36.6, -121.9, 5000, "hotel", "moderate")
    assert 'node["tourism"="hotel"](around:5000,36.6,-121.9);' in query


def test_parse_accommodation_elements_includes_contact():
    results = _parse_accommodation_elements(
        [
            {
                "type": "node",
                "lat": 36.601,
                "lon": -121.901,
                "tags": {
                    "name": "Monterey Inn",
                    "tourism": "hotel",
                    "phone": "+1-555-0100",
                    "website": "https://hotel.example",
                },
            }
        ],
        lat=36.6,
        lon=-121.9,
    )

    assert results[0]["property_name"] == "Monterey Inn"
    assert results[0]["phone"] == "+1-555-0100"
    assert results[0]["website"] == "https://hotel.example"


def test_format_accommodation_results_includes_contact_suffix():
    formatted = _format_accommodation_results(
        [
            {
                "property_name": "Monterey Inn",
                "category": "hotel",
                "lat": 36.601,
                "lon": -121.901,
                "dist_km": 0.2,
                "phone": "+1-555-0100",
                "website": "https://hotel.example",
                "address": None,
                "opening_hours": None,
                "reservation_required": True,
            }
        ],
        lat=36.6,
        lon=-121.9,
        radius_km=15,
        stay_type="hotel",
        budget="moderate",
    )

    assert "Monterey Inn" in formatted
    assert "phone=+1-555-0100" in formatted


@pytest.mark.asyncio
async def test_search_osm_accommodations_nearby_returns_formatted_results():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = {
        "elements": [
            {
                "type": "node",
                "lat": 36.601,
                "lon": -121.901,
                "tags": {"name": "Monterey Inn", "tourism": "hotel"},
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.tools.accommodations.httpx.AsyncClient", return_value=mock_client):
        result = await search_osm_accommodations_nearby.ainvoke(
            {
                "lat": 36.6,
                "lon": -121.9,
                "stay_type": "hotel",
                "radius_km": 15,
                "budget": "moderate",
            }
        )

    assert "Monterey Inn" in result
