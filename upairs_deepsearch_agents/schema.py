"""
Type definitions and communication protocol for MARDS v2.
"""

from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class AgentResponse:
    """Standard response format for all agents."""
    
    task_id: str
    agent_role: str
    section: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    output: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0-1
    uncertainty: float = 0.0  # 0-1
    needs_reflection: bool = False
    reflection_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Section:
    """Report section definition."""
    
    section_id: str
    section_title: str
    objective: str
    initial_summary: Optional[str] = None
    final_summary: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    reflection_history: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: float = 0.0
    reflection_count: int = 0


@dataclass
class ReportStructure:
    """Overall report structure."""
    
    title: str
    query: str
    sections: List[Section]
    objective: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "query": self.query,
            "objective": self.objective,
            "sections": [
                {
                    "section_id": s.section_id,
                    "section_title": s.section_title,
                    "objective": s.objective,
                }
                for s in self.sections
            ]
        }


@dataclass
class SearchResult:
    """Search result from Tavily API."""
    
    title: str
    url: str
    content: str
    domain: str = ""
    score: float = 0.0
    relevance: float = 0.0


@dataclass
class ReflectionEvaluation:
    """Reflection evaluation result."""
    
    missing_perspectives: List[str] = field(default_factory=list)
    weak_evidence_areas: List[str] = field(default_factory=list)
    bias_risks: List[str] = field(default_factory=list)
    needs_deeper_search: bool = False
    recommended_search_queries: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class GlobalUncertaintyResult:
    """Global uncertainty quantification result."""
    
    global_uncertainty: float  # 0-1
    section_uncertainties: Dict[str, float] = field(default_factory=dict)
    average_confidence: float = 0.0
    recommendation: Literal["proceed", "reflect", "escalate"] = "proceed"
    reasoning: str = ""
    reflection_needed: bool = False


@dataclass
class FinalReport:
    """Final formatted research report."""
    
    title: str
    executive_summary: str
    sections: Dict[str, str]
    cross_section_insights: str
    evidence_strength: str
    contradictions: str
    knowledge_gaps: str
    uncertainty_score: float
    references: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        md = f"# {self.title}\n\n"
        md += f"## Executive Summary\n\n{self.executive_summary}\n\n"
        
        for i, (section_title, content) in enumerate(self.sections.items(), 1):
            md += f"## {i}. {section_title}\n\n{content}\n\n"
        
        md += f"## Cross-Section Insights\n\n{self.cross_section_insights}\n\n"
        md += f"## Evidence Strength Overview\n\n{self.evidence_strength}\n\n"
        md += f"## Contradictions\n\n{self.contradictions}\n\n"
        md += f"## Knowledge Gaps\n\n{self.knowledge_gaps}\n\n"
        md += f"## Uncertainty Score\n\n{self.uncertainty_score:.2%}\n\n"
        
        md += "## References\n\n"
        for i, ref in enumerate(self.references, 1):
            md += f"{i}. [{ref.get('title', 'N/A')}]({ref.get('url', '#')})\n"
        
        return md


class MARDSException(Exception):
    """Base exception for MARDS system."""
    pass


class APIException(MARDSException):
    """API call exception."""
    pass


class ValidationException(MARDSException):
    """Validation exception."""
    pass
