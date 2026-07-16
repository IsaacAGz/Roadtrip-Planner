from typing import Literal

from pydantic import BaseModel, Field, field_validator

Pace = Literal["relaxed", "moderate", "packed"]
Budget = Literal["budget", "moderate", "luxury"]


class TripPreferences(BaseModel):
    pace: Pace = "moderate"
    budget: Budget = "moderate"
    accessibility: bool = False
    interests: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("interests")
    @classmethod
    def normalize_interests(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            stripped = item.strip().lower().replace(" ", "_")
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized


def format_preferences_for_prompt(
    *,
    structured: TripPreferences,
    free_text: str | None,
) -> str:
    lines = [
        f"pace: {structured.pace}",
        f"budget: {structured.budget}",
        f"accessibility: {structured.accessibility}",
    ]
    if structured.interests:
        lines.append(f"interests: {', '.join(structured.interests)}")
    if free_text and free_text.strip():
        lines.append(f"additional notes: {free_text.strip()}")
    return "\n".join(lines)
