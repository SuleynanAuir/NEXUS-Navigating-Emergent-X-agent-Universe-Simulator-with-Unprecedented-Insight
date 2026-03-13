from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Claim:
    text: str
    source_type: str = "text"
    context: str = ""
    source_url: str = ""
    original_text: str = ""  # 原始文本，用于上下文分析


@dataclass
class Evidence:
    quote: str
    source: str
    url: str
    stance: str  # support | refute
    credibility: float = 0.5
    relevance: float = 0.0
    rationale: str = ""
    context_alignment: float = 0.0  # 与原文上下文的一致性 0-1
    semantic_depth: float = 0.0  # 语义深度评分 0-1
    evidence_strength: float = 0.0  # 综合证据强度 0-1（新增）


@dataclass
class ScoreBreakdown:
    factuality: float = 0.0
    source_credibility: float = 0.0
    evidence_consistency: float = 0.0
    logical_rigor: float = 0.0
    premise_coverage: float = 0.0


@dataclass
class VerificationReport:
    claim: str
    supporting_evidence: List[Evidence] = field(default_factory=list)
    refuting_evidence: List[Evidence] = field(default_factory=list)
    logic_conditions: List[str] = field(default_factory=list)
    hidden_premises: List[str] = field(default_factory=list)
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    confidence_score: float = 0.0
    confidence_level: Dict = field(default_factory=dict)  # 新增：置信度等级信息
    verdict: str = "insufficient"
    trace: Dict[str, str] = field(default_factory=dict)
    reasoning_chain: List[str] = field(default_factory=list)
