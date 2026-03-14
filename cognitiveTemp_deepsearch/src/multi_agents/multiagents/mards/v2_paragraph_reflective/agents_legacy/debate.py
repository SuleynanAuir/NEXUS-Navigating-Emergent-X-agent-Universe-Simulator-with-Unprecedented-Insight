"""
DebateAgent - 多视角辩论
Adapted from mards/agents/debate.py for v2 integration.
"""

from typing import List


class DebateAgent:
    """Original DebateAgent for multi-perspective debate."""
    
    def __init__(self, client=None):
        self.client = client
        self.temperature = 0.7
    
    @staticmethod
    def generate_fallback_resolution(contradictions: List[str]) -> str:
        """Generate fallback resolution when LLM is not available."""
        if not contradictions:
            return "基于现有证据达成一致结论。"
        
        return "基于现有证据形成暂时性折中结论，需进一步验证。"
    
    @staticmethod
    def extract_remaining_disagreements(contradictions: List[str]) -> List[str]:
        """Extract remaining disagreements after debate."""
        return contradictions[:3]  # Keep top 3 unresolved contradictions
