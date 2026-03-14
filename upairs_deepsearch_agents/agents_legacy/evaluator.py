"""
EvidenceEvaluatorAgent - 证据评估
Adapted from mards/agents/evaluator.py for v2 integration.
"""

import re
from typing import List, Dict, Any


class EvidenceEvaluatorAgent:
    """Original EvidenceEvaluatorAgent for claims extraction and contradiction detection."""
    
    @staticmethod
    def extract_claims(results: List[Dict[str, Any]]) -> List[str]:
        """Extract claims from search results.
        
        This logic is now integrated into v2's FinalFormatterAgent._extract_all_claims().
        """
        claims = []
        
        for item in results:
            snippet = item.get("snippet", "") or item.get("content", "")
            # Split by sentence endings
            sentences = re.split(r'[。.!?！？]', snippet)
            
            for s in sentences:
                s = s.strip()
                # Keep substantial sentences
                if len(s) > 12:
                    claims.append(s)
        
        # Deduplicate
        return list(dict.fromkeys(claims))[:20]
    
    @staticmethod
    def detect_contradictions(claims: List[str]) -> List[str]:
        """Detect potential contradictions in claims.
        
        This logic is now integrated into v2's FinalFormatterAgent._detect_contradictions().
        """
        contradictions = []
        negative_indicators = [
            "not", "no", "无法", "没有", "无效", "不足",
            "but", "however", "但是", "然而", "相反"
        ]
        
        for c in claims:
            c_lower = c.lower()
            if any(neg in c_lower for neg in negative_indicators):
                contradictions.append(c)
        
        return contradictions[:10]
    
    @staticmethod
    def calculate_average_confidence(results: List[Dict[str, Any]]) -> float:
        """Calculate average confidence from search results."""
        if not results:
            return 0.2
        
        total_score = sum(r.get("score", 0.5) for r in results)
        return total_score / len(results)
