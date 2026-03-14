"""
ReflectionAgent (Original) - 全局反思与迭代判断
Adapted from mards/agents/reflection.py for v2 integration.
Note: v2 has its own ReflectionAgent for section-level reflection.
"""

from typing import List, Dict, Any


class OriginalReflectionAgent:
    """Original ReflectionAgent for global iteration decision.
    
    Different from v2's ReflectionAgent which focuses on section-level reflection.
    This agent makes global iteration decisions based on overall evaluation.
    """
    
    def __init__(self, client=None):
        self.client = client
        self.temperature = 0.4
    
    @staticmethod
    def identify_missing_topics(sub_questions: List[str], claims: List[str]) -> List[str]:
        """Identify missing topics that were not covered.
        
        This logic helps determine if another iteration is needed.
        """
        missing = []
        
        for sq in sub_questions:
            # Check if sub-question is covered in claims
            question_keywords = sq[:10]  # First 10 chars as keywords
            if not any(question_keywords in claim for claim in claims):
                missing.append(sq)
        
        return missing
    
    @staticmethod
    def should_iterate(contradictions: List[str], source_confidence: float, threshold: float = 0.6) -> bool:
        """Determine if another iteration is needed."""
        has_contradictions = bool(contradictions)
        low_confidence = source_confidence < threshold
        
        return has_contradictions or low_confidence
