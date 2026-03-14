"""
UncertaintyAgent - 不确定性量化
Adapted from mards/agents/uncertainty.py for v2 integration.
"""

from typing import List, Dict, Any


class UncertaintyAgent:
    """Original UncertaintyAgent for global uncertainty calculation."""
    
    def __init__(self, client=None):
        self.client = client
        self.temperature = 0.1
    
    @staticmethod
    def calculate_conflict_rate(evaluations: List[Dict[str, Any]]) -> float:
        """Calculate conflict rate from evaluations.
        
        This logic can be integrated into v2's GlobalUncertaintyAgent.
        """
        total_claims = sum(len(e.get("claims", [])) for e in evaluations) or 1
        contradictions = sum(len(e.get("contradictions", [])) for e in evaluations)
        
        return min(1.0, contradictions / total_claims)
    
    @staticmethod
    def calculate_info_gap_score(sub_questions: List[str], missing_topics: List[str]) -> float:
        """Calculate information gap score.
        
        This logic can be integrated into v2's GlobalUncertaintyAgent.
        """
        if not sub_questions:
            return 1.0
        
        return min(1.0, len(missing_topics) / len(sub_questions))
    
    @staticmethod
    def calculate_avg_unreliability(evaluations: List[Dict[str, Any]]) -> float:
        """Calculate average source unreliability."""
        if not evaluations:
            return 1.0
        
        avg_conf = sum(e.get("source_confidence", 0.5) for e in evaluations) / len(evaluations)
        return min(1.0, 1 - avg_conf)
    
    @staticmethod
    def calculate_global_uncertainty(
        conflict_rate: float,
        info_gap_score: float,
        avg_unreliability: float
    ) -> float:
        """Calculate global uncertainty using weighted combination.
        
        Formula: 0.4*conflict + 0.3*gap + 0.3*unreliability
        This logic can be integrated into v2's GlobalUncertaintyAgent.
        """
        return min(1.0, 0.4 * conflict_rate + 0.3 * info_gap_score + 0.3 * avg_unreliability)
