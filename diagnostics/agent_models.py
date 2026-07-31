from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


DiagnosticVerdict = Literal[
    "reachable",
    "degraded",
    "unreachable",
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
ConciseItem = Annotated[str, Field(min_length=1, max_length=500)]


class AgentDiagnosis(BaseModel):
    """The user-facing conclusion returned by the diagnostic agent."""

    model_config = ConfigDict(str_strip_whitespace=True)

    verdict: DiagnosticVerdict
    headline: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=1200)
    failure_stage: DiagnosticStage | None
    confidence: Confidence
    evidence: list[ConciseItem] = Field(min_length=1, max_length=8)
    likely_causes: list[ConciseItem] = Field(max_length=5)
    actions: list[ConciseItem] = Field(max_length=5)
