import httpx
from langchain_core.tools import tool

from app.config import get_settings


@tool
async def search_wikipedia_attractions(location: str, topic: str = "attractions") -> str:
    """Search Wikipedia for attractions and points of interest near or in a location."""
    settings = get_settings()
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
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("query", {}).get("search", [])
    if not results:
        return f"No Wikipedia results for '{topic}' in '{location}'"

    lines = []
    for item in results:
        snippet = item.get("snippet", "").replace("\n", " ")
        lines.append(f"- {item['title']}: {snippet}")
    return "\n".join(lines)
