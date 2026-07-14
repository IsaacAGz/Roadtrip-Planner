import httpx
from langchain_core.tools import tool

from app.config import get_settings

MAX_GEOSEARCH_RADIUS_M = 10_000
DEFAULT_LIMIT = 5


def _format_geosearch_results(
    results: list[dict],
    *,
    lat: float,
    lon: float,
    radius_km: float,
    topic: str,
) -> str:
    if not results:
        return (
            f"No Wikipedia geosearch results for '{topic}' "
            f"within {radius_km:g} km of ({lat}, {lon})"
        )

    lines = [
        f"Wikipedia POIs within {radius_km:g} km of ({lat}, {lon})"
        + (f" matching '{topic}'" if topic else "")
        + ":"
    ]

    for item in results:
        title = item["title"]
        item_lat = item.get("lat")
        item_lon = item.get("lon")
        dist_m = item.get("dist")
        dist_km = f", {dist_m / 1000:.1f} km away" if dist_m is not None else ""
        lines.append(f"- {title}: lat={item_lat}, lon={item_lon}{dist_km}")

    return "\n".join(lines)


@tool
async def search_wikipedia_attractions(location: str, topic: str = "attractions") -> str:
    """Search Wikipedia for attractions and points of interest near or in a location."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                settings.wikipedia_api_url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{topic} {location}",
                    "srlimit": 5,
                    "format": "json",
                },
                headers={"User-Agent": settings.nominatim_user_agent},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        return (
            f"Wikipedia search failed for '{topic}' in '{location}': "
            f"HTTP {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        return f"Wikipedia search failed for '{topic}' in '{location}': {exc}"

    results = data.get("query", {}).get("search", [])
    if not results:
        return f"No Wikipedia results for '{topic}' in '{location}'"

    lines = []
    for item in results:
        snippet = item.get("snippet", "").replace("\n", " ")
        lines.append(f"- {item['title']}: {snippet}")
    return "\n".join(lines)


@tool
async def search_wikipedia_nearby(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    topic: str = "attractions",
) -> str:
    """Search Wikipedia for geo-tagged articles near lat/lon within radius_km."""
    settings = get_settings()

    radius_m = int(radius_km * 1000)
    if radius_m < 10:
        radius_m = 10
    if radius_m > MAX_GEOSEARCH_RADIUS_M:
        radius_m = MAX_GEOSEARCH_RADIUS_M

    params: dict[str, str | int] = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": radius_m,
        "gslimit": DEFAULT_LIMIT,
        "format": "json",
    }
    if topic.strip():
        params["gsrsearch"] = topic.strip()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                settings.wikipedia_api_url,
                params=params,
                headers={"User-Agent": settings.nominatim_user_agent},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        return (
            f"Wikipedia geosearch failed near ({lat}, {lon}): "
            f"HTTP {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        return f"Wikipedia geosearch failed near ({lat}, {lon}): {exc}"

    results = data.get("query", {}).get("geosearch", [])
    return _format_geosearch_results(
        results,
        lat=lat,
        lon=lon,
        radius_km=radius_m / 1000,
        topic=topic,
    )
