from langchain_core.tools import tool

from app.services.nominatim import get_nominatim_client


@tool
async def geocode_location(query: str) -> str:
    """Convert a place name (city, landmark) to latitude, longitude, and country code."""
    client = get_nominatim_client()
    try:
        result = await client.geocode(query)
        return (
            f"{result.display_name} -> lat={result.lat}, lon={result.lon}, "
            f"country_code={result.country_code}"
        )
    except ValueError as exc:
        return str(exc)
