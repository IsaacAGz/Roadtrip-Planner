from typing import Any

from app.models.itinerary import RESERVABLE_CATEGORIES

CUISINE_INTERESTS: dict[str, str] = {
    "thai": "thai",
    "thai_food": "thai",
    "bbq": "barbecue",
    "barbecue": "barbecue",
    "seafood": "seafood",
    "mexican": "mexican",
    "italian": "italian",
    "japanese": "japanese",
    "chinese": "chinese",
    "indian": "indian",
    "french": "french",
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "pizza": "pizza",
    "sushi": "sushi",
    "local_food": "regional",
    "fine_dining": "fine_dining",
}


def cuisine_for_interest(interest: str) -> str | None:
    normalized = interest.strip().lower().replace(" ", "_")
    return CUISINE_INTERESTS.get(normalized)


def _format_address(tags: dict[str, Any]) -> str | None:
    parts: list[str] = []
    street = tags.get("addr:street") or tags.get("addr:housename")
    if street:
        house = tags.get("addr:housenumber")
        parts.append(f"{house} {street}".strip() if house else str(street))
    for key in ("addr:city", "addr:state", "addr:postcode"):
        value = tags.get(key)
        if value:
            parts.append(str(value))
    return ", ".join(parts) if parts else None


def _reservation_required(tags: dict[str, Any], category: str) -> bool:
    reservation = tags.get("reservation")
    if reservation is not None:
        normalized = str(reservation).strip().lower()
        if normalized in {"yes", "required", "recommended", "only"}:
            return True
        if normalized in {"no", "not_required", "never"}:
            return False
    return category in RESERVABLE_CATEGORIES


def extract_osm_contact(tags: dict[str, Any], *, category: str = "general") -> dict[str, Any]:
    phone = tags.get("phone") or tags.get("contact:phone")
    website = tags.get("website") or tags.get("contact:website")
    address = _format_address(tags)
    opening_hours = tags.get("opening_hours")
    reservation_required = _reservation_required(tags, category)

    return {
        "phone": str(phone) if phone else None,
        "website": str(website) if website else None,
        "address": address,
        "opening_hours": str(opening_hours) if opening_hours else None,
        "reservation_required": reservation_required,
    }


def format_contact_suffix(contact: dict[str, Any]) -> str:
    parts: list[str] = []
    if contact.get("phone"):
        parts.append(f"phone={contact['phone']}")
    if contact.get("website"):
        parts.append(f"website={contact['website']}")
    if contact.get("address"):
        parts.append(f"address={contact['address']}")
    if contact.get("opening_hours"):
        parts.append(f"hours={contact['opening_hours']}")
    if contact.get("reservation_required"):
        parts.append("reservation recommended")
    return f" | {' | '.join(parts)}" if parts else ""
