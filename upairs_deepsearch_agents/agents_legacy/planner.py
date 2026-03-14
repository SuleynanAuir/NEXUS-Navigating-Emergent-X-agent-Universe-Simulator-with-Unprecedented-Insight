"""
PlannerAgent - 问题分解
Adapted from mards/agents/planner.py for v2 integration.
"""

import re
from typing import List


class PlannerAgent:
    """Original PlannerAgent for query decomposition."""
    
    def __init__(self, client=None):
        self.client = client
        self.temperature = 0.1
    
    def local_decompose(self, query: str) -> List[str]:
        """Decompose query into sub-questions.
        
        This logic is now integrated into v2's StructurePlannerAgent.
        """
        parts = re.split(r"\band\b|；|;|、", query)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) >= 2:
            return [f"{p} 的关键证据是什么？" for p in parts]
        
        return [
            f"{query} 的定义与范围是什么？",
            f"{query} 的核心证据与数据有哪些？",
            f"{query} 的影响与应用场景是什么？",
            f"{query} 的最新进展与趋势是什么？",
            f"{query} 的挑战与未来展望是什么？",
        ]
