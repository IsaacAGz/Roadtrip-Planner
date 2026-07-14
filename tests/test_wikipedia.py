from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.tools.wikipedia import search_wikipedia_nearby


def _mock_httpx_client(*, json_data: dict, raise_request_error: bool = False):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = json_data

    mock_client = AsyncMock()
    if raise_request_error:
        mock_client.get.side_effect = httpx.RequestError("connection failed")
    else:
        mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.mark.asyncio
async def test_geosearch_returns_formatted_results():
    mock_client = _mock_httpx_client(
        json_data={
            "query": {
                "geosearch": [
                    {
                        "title": "Monterey Bay Aquarium",
                        "lat": 36.618,
                        "lon": -121.901,
                        "dist": 1200,
                    }
                ]
            }
        }
    )

    with patch("app.tools.wikipedia.httpx.AsyncClient", return_value=mock_client):
        result = await search_wikipedia_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "topic": "aquarium"}
        )

    assert "Monterey Bay Aquarium" in result
    assert "lat=36.618" in result
    assert "1.2 km away" in result


@pytest.mark.asyncio
async def test_geosearch_clamps_radius_to_api_max():
    mock_client = _mock_httpx_client(json_data={"query": {"geosearch": []}})

    with patch("app.tools.wikipedia.httpx.AsyncClient", return_value=mock_client):
        await search_wikipedia_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 50, "topic": "museum"}
        )

    call_kwargs = mock_client.get.call_args.kwargs
    assert call_kwargs["params"]["gsradius"] == 10_000


@pytest.mark.asyncio
async def test_geosearch_handles_http_error():
    mock_response = MagicMock()
    http_error = httpx.HTTPStatusError(
        "Service Unavailable",
        request=httpx.Request("GET", "https://en.wikipedia.org/w/api.php"),
        response=httpx.Response(503, request=httpx.Request("GET", "https://example.com")),
    )
    mock_response.raise_for_status.side_effect = http_error

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.tools.wikipedia.httpx.AsyncClient", return_value=mock_client):
        result = await search_wikipedia_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "topic": "aquarium"}
        )

    assert "Wikipedia geosearch failed near (36.6, -121.9)" in result
    assert "HTTP 503" in result


@pytest.mark.asyncio
async def test_geosearch_handles_request_error():
    mock_client = _mock_httpx_client(json_data={}, raise_request_error=True)

    with patch("app.tools.wikipedia.httpx.AsyncClient", return_value=mock_client):
        result = await search_wikipedia_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "topic": "aquarium"}
        )

    assert "Wikipedia geosearch failed near (36.6, -121.9)" in result


@pytest.mark.asyncio
async def test_geosearch_empty_results():
    mock_client = _mock_httpx_client(json_data={"query": {"geosearch": []}})

    with patch("app.tools.wikipedia.httpx.AsyncClient", return_value=mock_client):
        result = await search_wikipedia_nearby.ainvoke(
            {"lat": 36.6, "lon": -121.9, "radius_km": 10, "topic": "aquarium"}
        )

    assert "No Wikipedia geosearch results for 'aquarium'" in result
    assert "within 10 km of (36.6, -121.9)" in result
