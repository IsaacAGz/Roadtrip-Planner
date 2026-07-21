from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.models.itinerary import RoadtripPlan
from app.models.preferences import format_preferences_for_prompt
from app.models.scaffold import TripScaffold
from app.models.trip import TripRequest
from app.prompts.planner import (
    PLANNER_HUMAN_TEMPLATE,
    PLANNER_SYSTEM_PROMPT,
    STRUCTURED_OUTPUT_SYSTEM,
)
from app.tools.geocode import geocode_location
from app.tools.overpass import search_osm_pois_nearby
from app.tools.routing import get_driving_route
from app.tools.weather import get_weather_forecast
from app.tools.wikipedia import search_wikipedia_attractions, search_wikipedia_nearby

PLANNER_TOOLS = [
    geocode_location,
    get_driving_route,
    search_osm_pois_nearby,
    search_wikipedia_attractions,
    search_wikipedia_nearby,
    get_weather_forecast,
]


def _format_feedback(feedback: list[str]) -> str:
    if not feedback:
        return ""
    lines = "\n".join(f"- {item}" for item in feedback)
    return f"Previous validation feedback (fix these issues):\n{lines}"


def _extract_agent_output(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    last_message = messages[-1]
    content = getattr(last_message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts)
    return str(content)


def _format_scaffold(scaffold: TripScaffold | None) -> str:
    if scaffold is None:
        return ""

    lines = [
        "Deterministic route scaffold (required overnight structure — do not repeat consecutive cities):"
    ]
    for spec in scaffold.days:
        lines.append(
            f"- Day {spec.day}: drive from ({spec.leg_start_lat:.4f}, {spec.leg_start_lon:.4f}) "
            f"to overnight '{spec.suggested_overnight_city}' "
            f"({spec.suggested_overnight_lat:.4f}, {spec.suggested_overnight_lon:.4f}); "
            f"max driving {spec.max_driving_hours:.1f}h"
        )
    return "\n".join(lines)


async def run_planner(
    request: TripRequest,
    feedback: list[str] | None = None,
    *,
    scaffold: TripScaffold | None = None,
) -> RoadtripPlan:
    settings = get_settings()
    feedback = feedback or []

    human_message = PLANNER_HUMAN_TEMPLATE.format(
        days=request.days,
        origin=request.origin,
        destination=request.destination,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        preferences=format_preferences_for_prompt(
            structured=request.structured_preferences,
            free_text=request.preferences,
        ),
        constraints=request.constraints.model_dump_json(),
        scaffold_section=_format_scaffold(scaffold),
        feedback_section=_format_feedback(feedback),
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.4,
    )
    agent = create_agent(
        model=llm,
        tools=PLANNER_TOOLS,
        system_prompt=PLANNER_SYSTEM_PROMPT,
    )
    research = await agent.ainvoke({"messages": [HumanMessage(content=human_message)]})
    research_output = _extract_agent_output(research)

    structured_llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    ).with_structured_output(RoadtripPlan)

    plan = await structured_llm.ainvoke(
        [
            SystemMessage(content=STRUCTURED_OUTPUT_SYSTEM),
            HumanMessage(
                content=(
                    f"Trip request:\n{human_message}\n\n"
                    f"Research findings:\n{research_output}\n\n"
                    f"Produce a complete RoadtripPlan for {request.days} days "
                    f"from {request.start_date.isoformat()} to {request.end_date.isoformat()}."
                )
            ),
        ]
    )
    return plan
