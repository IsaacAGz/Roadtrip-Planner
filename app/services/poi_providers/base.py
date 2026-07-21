from dataclasses import dataclass
from typing import Protocol

from app.models.itinerary import PlaceContact
from app.tools.osm_contact import format_contact_suffix


@dataclass
class POIResult:
    name: str
    lat: float
    lon: float
    category: str
    dist_km: float
    contact: PlaceContact
    source: str


class POIProvider(Protocol):
    async def search_nearby(
        self,
        lat: float,
        lon: float,
        interest: str,
        radius_km: float,
    ) -> list[POIResult]: ...


def poi_result_from_osm_item(item: dict) -> POIResult:
    return POIResult(
        name=str(item["name"]),
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        category=str(item["category"]),
        dist_km=float(item["dist_km"]),
        contact=PlaceContact(
            phone=item.get("phone"),
            website=item.get("website"),
            address=item.get("address"),
            opening_hours=item.get("opening_hours"),
            reservation_required=bool(item.get("reservation_required")),
        ),
        source="osm",
    )


def format_poi_results(
    results: list[POIResult],
    *,
    lat: float,
    lon: float,
    radius_km: float,
    interest: str,
    source_label: str,
) -> str:
    if not results:
        return (
            f"No {source_label} POIs for '{interest}' "
            f"within {radius_km:g} km of ({lat}, {lon})"
        )

    lines = [
        f"{source_label} POIs within {radius_km:g} km of ({lat}, {lon})"
        + (f" matching '{interest}'" if interest else "")
        + ":"
    ]
    for item in results[:10]:
        contact_suffix = format_contact_suffix(item.contact.model_dump())
        lines.append(
            f"- {item.name} ({item.category}): "
            f"lat={item.lat}, lon={item.lon}, {item.dist_km:.1f} km away"
            f"{contact_suffix}"
        )
    return "\n".join(lines)
