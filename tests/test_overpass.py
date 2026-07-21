from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.tools.overpass import (
    _build_overpass_query,
    _format_overpass_results,
    _interest_tags,
    _parse_overpass_elements,
    search_osm_pois_nearby,
)


@pytest.fixture(autouse=True)
def mock_settings():
    settings = MagicMock()
    settings.overpass_api_url = "https://overpass-api.de/api/interpreter"
    settings.nominatim_user_agent = "RoadtripPlanner/1.0 (test@example.com)"
    with patch("app.tools.overpass.get_settings", return_value=settings):
        yield


def test_interest_tags_maps_breweries():
    tags = _interest_tags("breweries")
    assert ("amenity", "brewery") in tags


def test_interest_tags_maps_theatre():
    tags = _interest_tags("shows")
    assert ("amenity", "theatre") in tags
    assert ("amenity", "cinema") in tags


def test_build_overpass_query_includes_cuisine_filter_for_thai():
    query = _build_overpass_query(36.6, -121.9, 5000, "thai")
    assert '["amenity"="restaurant"]["cuisine"="thai"]' in query


def test_parse_overpass_elements_includes_contact_fields():
    elements = [
        {
            "type": "node",
            "lat": 36.601,
            "lon": -121.901,
            "tags": {
                "name": "Near Museum",
                "tourism": "museum",
                "phone": "+1-555-0100",
                "website": "https://museum.example",
            },
        }
    ]

    results = _parse_overpass_elements(elements, lat=36.6, lon=-121.9)

    assert results[0]["phone"] == "+1-555-0100"
    assert results[0]["website"] == "https://museum.example"
    assert results[0]["reservation_required"] is True


def test_format_overpass_results_includes_contact_suffix():
    formatted = _format_overpass_results(
        [
            {
                "name": "Near Museum",
                "category": "museum",
                "lat": 36.601,
                "lon": -121.901,
                "dist_km": 0.2,
                "phone": "+1-555-0100",
                "website": "https://museum.example",
                "address": None,
                "opening_hours": None,
                "reservation_required": True,
            }
        ],
        lat=36.6,
        lon=-121.9,
        radius_km=10,
        interest="museum",
    )

    assert "phone=+1-555-0100" in formatted
    assert "website=https://museum.example" in formatted
    assert "reservation recommended" in formatted


def test_build_overpass_query_includes_around_filter():
    query = _build_overpass_query(36.6, -121.9, 5000, "museums")
    assert 'node["tourism"="museum"](around:5000,36.6,-121.9);' in query
    assert "out:json" in query


def test_parse_overpass_elements_sorts_by_distance_and_limits():
    elements = [
        {
            "type": "node",
            "lat": 36.62,
            "lon": -121.88,
            "tags": {"name": "Far Museum", "tourism": "museum"},
        },
        {
            "type": "node",
            "lat": 36.601,
            "lon": -121.901,
            "tags": {"name": "Near Museum", "tourism": "museum"},
        },
        {
            "type": "way",
            "center": {"lat": 36.601, "lon": -121.901},
            "tags": {"name": "Near Museum", "tourism": "museum"},
        },
    ]

    results = _parse_overpass_elements(elements, lat=36.6, lon=-121.9)

    assert len(results) == 2
    assert results[0]["name"] == "Near Museum"
    assert results[0]["category"] == "museum"
    assert results[0]["lat"] == 36.601


@pytest.mark.asyncio
async def test_search_osm_pois_nearby_returns_formatted_results():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = {
        "elements": [
            {
                "type": "node",
                "lat": 36.618,
                "lon": -121.901,
                "tags": {"name": "Monterey Bay Aquarium", "tourism": "aquarium"},
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.tools.overpass.httpx.AsyncClient", return_value=mock_client):
        result = await search_osm_pois_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "interest": "aquarium"}
        )

    assert "Monterey Bay Aquarium" in result
    assert "lat=36.618" in result
    assert "aquarium" in result
    assert mock_client.post.call_args.kwargs["data"]["data"]


@pytest.mark.asyncio
async def test_search_osm_pois_nearby_clamps_radius():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = {"elements": []}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.tools.overpass.httpx.AsyncClient", return_value=mock_client):
        await search_osm_pois_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 50, "interest": "museum"}
        )

    query = mock_client.post.call_args.kwargs["data"]["data"]
    assert "around:10000," in query


@pytest.mark.asyncio
async def test_search_osm_pois_nearby_handles_http_error():
    mock_response = MagicMock()
    http_error = httpx.HTTPStatusError(
        "Gateway Timeout",
        request=httpx.Request("POST", "https://overpass-api.de/api/interpreter"),
        response=httpx.Response(504, request=httpx.Request("POST", "https://example.com")),
    )
    mock_response.raise_for_status.side_effect = http_error

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.tools.overpass.httpx.AsyncClient", return_value=mock_client):
        result = await search_osm_pois_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "interest": "museum"}
        )

    assert "Overpass POI search failed near (36.6, -121.9)" in result
    assert "HTTP 504" in result


@pytest.mark.asyncio
async def test_search_osm_pois_nearby_handles_empty_results():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = {"elements": []}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.tools.overpass.httpx.AsyncClient", return_value=mock_client):
        result = await search_osm_pois_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "interest": "museum"}
        )

    assert "No OpenStreetMap POIs for 'museum'" in result
