import math
from typing import Any

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.tools.osm_contact import (
    cuisine_for_interest,
    extract_osm_contact,
    format_contact_suffix,
)

MAX_RADIUS_M = 10_000
MIN_RADIUS_M = 10
DEFAULT_LIMIT = 10
QUERY_TIMEOUT_S = 25

DEFAULT_POI_TAGS: list[tuple[str, str]] = [
    ("tourism", "attraction"),
    ("tourism", "museum"),
    ("tourism", "viewpoint"),
    ("tourism", "artwork"),
    ("amenity", "restaurant"),
    ("amenity", "cafe"),
    ("amenity", "brewery"),
]

INTEREST_TAG_MAP: dict[str, list[tuple[str, str]]] = {
    "attractions": DEFAULT_POI_TAGS,
    "breweries": [("amenity", "brewery")],
    "brewery": [("amenity", "brewery")],
    "museums": [("tourism", "museum")],
    "museum": [("tourism", "museum")],
    "hiking": [("tourism", "viewpoint"), ("natural", "peak")],
    "beaches": [("natural", "beach")],
    "beach": [("natural", "beach")],
    "seafood": [("amenity", "restaurant")],
    "aquarium": [("tourism", "aquarium")],
    "aquariums": [("tourism", "aquarium")],
    "scenic_viewpoints": [("tourism", "viewpoint")],
    "scenic_views": [("tourism", "viewpoint")],
    "coastal_views": [("tourism", "viewpoint")],
    "campgrounds": [("tourism", "camp_site")],
    "camping": [("tourism", "camp_site")],
    "parks": [("leisure", "park")],
    "park": [("leisure", "park")],
    "food": [("amenity", "restaurant"), ("amenity", "cafe")],
    "restaurants": [("amenity", "restaurant")],
    "theatre": [("amenity", "theatre"), ("amenity", "cinema")],
    "theater": [("amenity", "theatre"), ("amenity", "cinema")],
    "shows": [("amenity", "theatre"), ("amenity", "cinema")],
    "live_music": [
        ("amenity", "nightclub"),
        ("amenity", "bar"),
        ("amenity", "music_venue"),
    ],
    "fine_dining": [("amenity", "restaurant")],
    "local_food": [("amenity", "restaurant")],
    "hotels": [("tourism", "hotel")],
    "hotel": [("tourism", "hotel")],
    "motels": [("tourism", "motel")],
    "motel": [("tourism", "motel")],
}


def _normalize_interest(interest: str) -> str:
    return interest.strip().lower().replace(" ", "_")


def _interest_tags(interest: str) -> list[tuple[str, str]]:
    normalized = _normalize_interest(interest)
    if not normalized:
        return DEFAULT_POI_TAGS
    return INTEREST_TAG_MAP.get(normalized, DEFAULT_POI_TAGS)


def _clamp_radius_m(radius_km: float) -> int:
    radius_m = int(radius_km * 1000)
    if radius_m < MIN_RADIUS_M:
        return MIN_RADIUS_M
    if radius_m > MAX_RADIUS_M:
        return MAX_RADIUS_M
    return radius_m


def _build_overpass_query(lat: float, lon: float, radius_m: int, interest: str) -> str:
    tag_lines: list[str] = []
    cuisine = cuisine_for_interest(interest)
    for key, value in _interest_tags(interest):
        cuisine_filter = f'["cuisine"="{cuisine}"]' if cuisine and value == "restaurant" else ""
        selector = f'["{key}"="{value}"]{cuisine_filter}'
        tag_lines.append(f"  node{selector}(around:{radius_m},{lat},{lon});")
        tag_lines.append(f"  way{selector}(around:{radius_m},{lat},{lon});")

    body = "\n".join(tag_lines)
    return f"[out:json][timeout:{QUERY_TIMEOUT_S}];\n(\n{body}\n);\nout center {DEFAULT_LIMIT * 2};"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _element_coords(element: dict[str, Any]) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if isinstance(center, dict):
        return center.get("lat"), center.get("lon")
    return None, None


def _element_name_and_category(element: dict[str, Any]) -> tuple[str, str]:
    tags = element.get("tags", {})
    name = tags.get("name") or tags.get("brand") or "Unnamed place"
    category = (
        tags.get("tourism")
        or tags.get("amenity")
        or tags.get("leisure")
        or tags.get("natural")
        or "general"
    )
    return str(name), str(category)


def _parse_overpass_elements(
    elements: list[dict[str, Any]],
    *,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, float, float]] = set()

    for element in elements:
        item_lat, item_lon = _element_coords(element)
        if item_lat is None or item_lon is None:
            continue

        tags = element.get("tags", {})
        name, category = _element_name_and_category(element)
        dedupe_key = (name.casefold(), round(item_lat, 4), round(item_lon, 4))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        contact = extract_osm_contact(tags, category=category)
        results.append(
            {
                "name": name,
                "lat": item_lat,
                "lon": item_lon,
                "category": category,
                "dist_km": _haversine_km(lat, lon, item_lat, item_lon),
                **contact,
            }
        )

    results.sort(key=lambda item: item["dist_km"])
    return results[:DEFAULT_LIMIT]


async def query_osm_pois_nearby(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    interest: str = "attractions",
) -> list[dict[str, Any]]:
    settings = get_settings()
    radius_m = _clamp_radius_m(radius_km)
    query = _build_overpass_query(lat, lon, radius_m, interest)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.overpass_api_url,
            data={"data": query},
            headers={"User-Agent": settings.nominatim_user_agent},
        )
        response.raise_for_status()
        data = response.json()

    elements = data.get("elements", [])
    return _parse_overpass_elements(elements, lat=lat, lon=lon)


def _format_overpass_results(
    results: list[dict[str, Any]],
    *,
    lat: float,
    lon: float,
    radius_km: float,
    interest: str,
) -> str:
    if not results:
        return (
            f"No OpenStreetMap POIs for '{interest}' "
            f"within {radius_km:g} km of ({lat}, {lon})"
        )

    lines = [
        f"OpenStreetMap POIs within {radius_km:g} km of ({lat}, {lon})"
        + (f" matching '{interest}'" if interest else "")
        + ":"
    ]
    for item in results:
        contact_suffix = format_contact_suffix(item)
        lines.append(
            f"- {item['name']} ({item['category']}): "
            f"lat={item['lat']}, lon={item['lon']}, {item['dist_km']:.1f} km away"
            f"{contact_suffix}"
        )
    return "\n".join(lines)


@tool
async def search_osm_pois_nearby(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    interest: str = "attractions",
) -> str:
    """Search OpenStreetMap (Overpass API) for POIs near lat/lon within radius_km."""
    radius_m = _clamp_radius_m(radius_km)
    try:
        results = await query_osm_pois_nearby(lat, lon, radius_km, interest)
    except httpx.HTTPStatusError as exc:
        return (
            f"Overpass POI search failed near ({lat}, {lon}): "
            f"HTTP {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        return f"Overpass POI search failed near ({lat}, {lon}): {exc}"

    return _format_overpass_results(
        results,
        lat=lat,
        lon=lon,
        radius_km=radius_m / 1000,
        interest=interest,
    )
