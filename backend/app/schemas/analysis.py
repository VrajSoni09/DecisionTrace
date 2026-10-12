from typing import Any, Literal

from pydantic import BaseModel, Field


class MeetingRecord(BaseModel):
    id: str | None = None
    timestamp: str | None = None
    speaker: str | None = None
    text: str = Field(..., min_length=1)


class DecisionCandidate(BaseModel):
    text: str
    topic: str
    status: str
    confidence: float
    reversal: bool = False
    related_to: str | None = None
    evidence: list[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    meeting_records: list[MeetingRecord] | list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    summary: str
    candidates: list[DecisionCandidate]
    reversed_decisions: list[dict[str, Any]]
    total_records: int
    total_candidates: int
    generated_at: str
    traces: list[dict[str, Any]] = Field(default_factory=list)
    processing_summary: dict[str, int] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    dataset_size: int
    accuracy: float
    deterministic: bool
    results: list[dict[str, Any]]


class ExportRequest(BaseModel):
    format: Literal["json", "csv"] = "json"
    payload: dict[str, Any] | None = None
