from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.models.itinerary import RoadtripPlan
from app.models.trip import TripRequest
from app.prompts.planner import (
    PLANNER_HUMAN_TEMPLATE,
    PLANNER_SYSTEM_PROMPT,
    STRUCTURED_OUTPUT_SYSTEM,
)
from app.tools.geocode import geocode_location
from app.tools.routing import get_driving_route
from app.tools.weather import get_weather_forecast
from app.tools.wikipedia import search_wikipedia_attractions

PLANNER_TOOLS = [
    geocode_location,
    get_driving_route,
    search_wikipedia_attractions,
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


async def run_planner(request: TripRequest, feedback: list[str] | None = None) -> RoadtripPlan:
    settings = get_settings()
    feedback = feedback or []

    human_message = PLANNER_HUMAN_TEMPLATE.format(
        days=request.days,
        origin=request.origin,
        destination=request.destination,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        preferences=request.preferences or "scenic routes, local food",
        constraints=request.constraints.model_dump_json(),
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
