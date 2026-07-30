from typing import Literal

from pydantic import BaseModel, Field


DiagnosticVerdict = Literal[
    "reachable",
    "degraded",
    "unreachable",
    "inconclusive",
]
DiagnosticStage = Literal[
    "client",
    "dns",
    "route",
    "tcp",
    "tls",
    "http",
    "application",
]
Confidence = Literal["low", "medium", "high"]


class AgentDiagnosis(BaseModel):
    """The user-facing conclusion returned by the diagnostic agent."""

    verdict: DiagnosticVerdict
    headline: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=1200)
    failure_stage: DiagnosticStage | None
    confidence: Confidence
    evidence: list[str] = Field(min_length=1, max_length=8)
    likely_causes: list[str] = Field(max_length=5)
    actions: list[str] = Field(max_length=5)
