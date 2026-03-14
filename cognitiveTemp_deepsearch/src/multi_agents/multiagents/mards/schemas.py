from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    task_id: str
    agent_role: str
    output_payload: Dict
    confidence_score: float = Field(ge=0.0, le=1.0)
    uncertainty_score: float = Field(ge=0.0, le=1.0)
    needs_iteration: bool


class PlannerPayload(BaseModel):
    sub_questions: List[str]


class RetrievalItem(BaseModel):
    title: str
    url: str
    domain: str
    source_type: str
    snippet: str
    score: float = Field(ge=0.0, le=1.0)


class RetrievalPayload(BaseModel):
    query: str
    results: List[RetrievalItem]
    diversity_score: float = Field(ge=0.0, le=1.0)


class EvaluationPayload(BaseModel):
    claims: List[str]
    contradictions: List[str]
    source_confidence: float = Field(ge=0.0, le=1.0)


class ReflectionPayload(BaseModel):
    contradictions: List[str]
    follow_up_queries: List[str]
    missing_topics: List[str]
    needs_iteration: bool


class DebatePayload(BaseModel):
    resolution: str
    remaining_disagreements: List[str]


class UncertaintyPayload(BaseModel):
    global_uncertainty: float = Field(ge=0.0, le=1.0)
    conflict_rate: float = Field(ge=0.0, le=1.0)
    info_gap_score: float = Field(ge=0.0, le=1.0)
    avg_source_unreliability: float = Field(ge=0.0, le=1.0)
    missing_topics: List[str]


class SynthesisPayload(BaseModel):
    report_markdown: str


class SystemState(BaseModel):
    task_id: str
    query: str
    sub_questions: List[str] = []
    retrievals: Dict[str, RetrievalPayload] = {}
    evaluations: Dict[str, EvaluationPayload] = {}
    reflection: Optional[ReflectionPayload] = None
    debate: Optional[DebatePayload] = None
    uncertainty: Optional[UncertaintyPayload] = None
    synthesis: Optional[SynthesisPayload] = None
    loop_count: int = 0
