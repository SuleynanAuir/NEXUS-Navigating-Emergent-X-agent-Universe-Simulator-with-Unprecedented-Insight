"""
RetrieverAgent - 检索与多样性过滤
Adapted from mards/agents/retriever.py for v2 integration.
"""

from typing import List, Dict, Any
from urllib.parse import urlparse


class RetrieverAgent:
    """Original RetrieverAgent for domain diversity and source classification."""
    
    @staticmethod
    def enforce_domain_diversity(items: List[Dict[str, Any]], min_count: int = 5) -> List[Dict[str, Any]]:
        """Ensure domain diversity in search results.
        
        This logic is now integrated into v2's SectionRetrieverAgent._filter_for_diversity().
        """
        seen = set()
        diverse = []
        
        for item in items:
            domain = item.get("domain", "")
            if domain not in seen:
                diverse.append(item)
                seen.add(domain)
            if len(diverse) >= min_count:
                break
        
        return diverse
    
    @staticmethod
    def diversity_score(items: List[Dict[str, Any]]) -> float:
        """Calculate diversity score based on TLDs and source types.
        
        This logic is now integrated into v2's SectionRetrieverAgent._calculate_diversity_score().
        """
        if not items:
            return 0.0
        
        tlds = set()
        types = set()
        
        for item in items:
            domain = item.get("domain", "")
            # TLD
            parts = domain.split(".")
            if parts:
                tlds.add(parts[-1])
            # Type
            types.add(RetrieverAgent.classify_source_type(domain))
        
        return min(1.0, 0.5 * (len(tlds) / len(items)) + 0.5 * (len(types) / len(items)))
    
    @staticmethod
    def classify_source_type(domain: str) -> str:
        """Classify source type based on domain.
        
        This logic is now integrated into v2's SectionRetrieverAgent._classify_source_type().
        """
        domain_lower = domain.lower()
        
        if domain_lower.endswith(".edu") or ".ac." in domain_lower:
            return "academic"
        if domain_lower.endswith(".gov"):
            return "government"
        if "news" in domain_lower or domain_lower.endswith(".news"):
            return "news"
        if domain_lower.endswith(".org"):
            return "nonprofit"
        
        return "corporate"
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""
