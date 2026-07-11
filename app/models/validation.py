from typing import Literal

from pydantic import BaseModel, Field


class RuleViolation(BaseModel):
    rule_id: str
    severity: Literal["error", "warning", "info"]
    day: int | None = None
    message: str
    actual: float | str | None = None
    limit: float | str | None = None


class ValidationReport(BaseModel):
    approved: bool
    hard_failures: list[RuleViolation] = Field(default_factory=list)
    warnings: list[RuleViolation] = Field(default_factory=list)
    replan_attempts: int = 0


class ValidationResult(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list)
    replan_instructions: list[str] = Field(default_factory=list)
    severity: Literal["ok", "minor", "major"] = "ok"
