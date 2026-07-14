from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.models.itinerary import RoadtripPlan
from app.models.trip import TripRequest
from app.models.validation import RuleViolation, ValidationResult
from app.prompts.validator import (
    STRUCTURED_VALIDATOR_SYSTEM,
    VALIDATOR_HUMAN_TEMPLATE,
    VALIDATOR_SYSTEM_PROMPT,
)
from app.tools.routing import get_driving_route

VALIDATOR_TOOLS = [get_driving_route]


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


async def run_validator(
    plan: RoadtripPlan,
    request: TripRequest,
    warnings: list[RuleViolation] | None = None,
) -> ValidationResult:
    settings = get_settings()
    warnings = warnings or []
    warning_text = (
        "\n".join(f"- {warning.message}" for warning in warnings)
        if warnings
        else "None"
    )

    human_message = VALIDATOR_HUMAN_TEMPLATE.format(
        origin=request.origin,
        destination=request.destination,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        days=request.days,
        preferences=request.preferences or "none specified",
        constraints=request.constraints.model_dump_json(),
        plan_json=plan.model_dump_json(indent=2),
        warnings=warning_text,
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
    )
    agent = create_agent(
        model=llm,
        tools=VALIDATOR_TOOLS,
        system_prompt=VALIDATOR_SYSTEM_PROMPT,
    )
    review = await agent.ainvoke({"messages": [HumanMessage(content=human_message)]})
    review_output = _extract_agent_output(review)

    structured_llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
    ).with_structured_output(ValidationResult)

    result = await structured_llm.ainvoke(
        [
            SystemMessage(content=STRUCTURED_VALIDATOR_SYSTEM),
            HumanMessage(
                content=(
                    f"Original request and plan:\n{human_message}\n\n"
                    f"Validator review:\n{review_output}"
                )
            ),
        ]
    )
    return result
