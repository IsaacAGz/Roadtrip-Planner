from typing import Any

import httpx

from app.config import get_settings
from app.models.itinerary import PlaceContact, RoadtripPlan
from app.models.trip import TripRequest
from app.tools.accommodations import (
    _build_accommodation_query,
    _clamp_accommodation_radius_m,
    _normalize_budget,
    _normalize_stay_type,
    _parse_accommodation_elements,
)


async def _fetch_accommodations_nearby(
    lat: float,
    lon: float,
    stay_type: str,
    budget: str,
    *,
    radius_km: float = 15.0,
) -> list[dict[str, Any]]:
    settings = get_settings()
    radius_m = _clamp_accommodation_radius_m(radius_km)
    query = _build_accommodation_query(
        lat,
        lon,
        radius_m,
        _normalize_stay_type(stay_type),
        _normalize_budget(budget),
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.overpass_api_url,
                data={"data": query},
                headers={"User-Agent": settings.nominatim_user_agent},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []

    return _parse_accommodation_elements(data.get("elements", []), lat=lat, lon=lon)


def _contact_from_result(item: dict[str, Any]) -> PlaceContact:
    return PlaceContact(
        phone=item.get("phone"),
        website=item.get("website"),
        address=item.get("address"),
        opening_hours=item.get("opening_hours"),
        reservation_required=bool(item.get("reservation_required", False)),
    )


async def enrich_accommodations(plan: RoadtripPlan, request: TripRequest) -> RoadtripPlan:
    budget = request.structured_preferences.budget

    for day_plan in plan.days:
        overnight = day_plan.overnight
        if overnight.property_name:
            continue

        results = await _fetch_accommodations_nearby(
            overnight.lat,
            overnight.lon,
            overnight.stay_type,
            budget,
        )
        if not results:
            continue

        best = results[0]
        overnight.property_name = best["property_name"]
        overnight.contact = _contact_from_result(best)

    return plan
