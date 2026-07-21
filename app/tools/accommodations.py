from typing import Any

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.tools.osm_contact import extract_osm_contact, format_contact_suffix
from app.tools.overpass import (
    MIN_RADIUS_M,
    QUERY_TIMEOUT_S,
    _element_coords,
    _element_name_and_category,
    _haversine_km,
)

ACCOMMODATION_LIMIT = 5
ACCOMMODATION_MAX_RADIUS_M = 15_000


def _normalize_stay_type(stay_type: str) -> str:
    normalized = stay_type.strip().lower().replace(" ", "_")
    if normalized in {"camping", "camp", "camp_site"}:
        return "camping"
    if normalized in {"motel", "motels"}:
        return "motel"
    if normalized in {"resort", "resorts"}:
        return "resort"
    return "hotel"


def _normalize_budget(budget: str) -> str:
    normalized = budget.strip().lower()
    if normalized in {"budget", "moderate", "luxury"}:
        return normalized
    return "moderate"


def _accommodation_tags(stay_type: str, budget: str) -> list[tuple[str, str]]:
    stay_type = _normalize_stay_type(stay_type)
    budget = _normalize_budget(budget)

    if stay_type == "camping":
        return [("tourism", "camp_site")]

    if stay_type == "motel":
        return [("tourism", "motel"), ("tourism", "guest_house")]

    if stay_type == "resort":
        return [("tourism", "hotel"), ("tourism", "resort")]

    if budget == "budget":
        return [("tourism", "motel"), ("tourism", "guest_house")]
    if budget == "luxury":
        return [("tourism", "hotel")]
    return [("tourism", "hotel"), ("tourism", "motel")]


def _build_accommodation_query(
    lat: float,
    lon: float,
    radius_m: int,
    stay_type: str,
    budget: str,
) -> str:
    tag_lines: list[str] = []
    for key, value in _accommodation_tags(stay_type, budget):
        selector = f'["{key}"="{value}"]'
        tag_lines.append(f"  node{selector}(around:{radius_m},{lat},{lon});")
        tag_lines.append(f"  way{selector}(around:{radius_m},{lat},{lon});")

    body = "\n".join(tag_lines)
    return (
        f"[out:json][timeout:{QUERY_TIMEOUT_S}];\n(\n{body}\n);\n"
        f"out center {ACCOMMODATION_LIMIT * 2};"
    )


def _clamp_accommodation_radius_m(radius_km: float) -> int:
    radius_m = int(radius_km * 1000)
    if radius_m < MIN_RADIUS_M:
        return MIN_RADIUS_M
    if radius_m > ACCOMMODATION_MAX_RADIUS_M:
        return ACCOMMODATION_MAX_RADIUS_M
    return radius_m


def _parse_accommodation_elements(
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
                "property_name": name,
                "lat": item_lat,
                "lon": item_lon,
                "category": category,
                "dist_km": _haversine_km(lat, lon, item_lat, item_lon),
                **contact,
            }
        )

    results.sort(key=lambda item: item["dist_km"])
    return results[:ACCOMMODATION_LIMIT]


def _format_accommodation_results(
    results: list[dict[str, Any]],
    *,
    lat: float,
    lon: float,
    radius_km: float,
    stay_type: str,
    budget: str,
) -> str:
    if not results:
        return (
            f"No OpenStreetMap accommodations for '{stay_type}' ({budget} budget) "
            f"within {radius_km:g} km of ({lat}, {lon})"
        )

    lines = [
        f"OpenStreetMap accommodations within {radius_km:g} km of ({lat}, {lon}) "
        f"for stay_type={stay_type}, budget={budget}:"
    ]
    for item in results:
        contact_suffix = format_contact_suffix(item)
        lines.append(
            f"- {item['property_name']} ({item['category']}): "
            f"lat={item['lat']}, lon={item['lon']}, {item['dist_km']:.1f} km away"
            f"{contact_suffix}"
        )
    return "\n".join(lines)


@tool
async def search_osm_accommodations_nearby(
    lat: float,
    lon: float,
    stay_type: str = "hotel",
    radius_km: float = 15.0,
    budget: str = "moderate",
) -> str:
    """Search OpenStreetMap for hotels, motels, resorts, or campgrounds near lat/lon."""
    settings = get_settings()
    radius_m = _clamp_accommodation_radius_m(radius_km)
    query = _build_accommodation_query(lat, lon, radius_m, stay_type, budget)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.overpass_api_url,
                data={"data": query},
                headers={"User-Agent": settings.nominatim_user_agent},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        return (
            f"Overpass accommodation search failed near ({lat}, {lon}): "
            f"HTTP {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        return f"Overpass accommodation search failed near ({lat}, {lon}): {exc}"

    elements = data.get("elements", [])
    results = _parse_accommodation_elements(elements, lat=lat, lon=lon)
    return _format_accommodation_results(
        results,
        lat=lat,
        lon=lon,
        radius_km=radius_m / 1000,
        stay_type=_normalize_stay_type(stay_type),
        budget=_normalize_budget(budget),
    )
