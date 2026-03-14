"""
SynthesisAgent - 报告综合生成
Adapted from mards/agents/synthesis.py for v2 integration.
"""

from typing import List, Dict, Any


class SynthesisAgent:
    """Original SynthesisAgent for report generation."""
    
    def __init__(self, client=None):
        self.client = client
        self.temperature = 0.4
    
    @staticmethod
    def generate_markdown_report(
        query: str,
        sub_questions: List[str],
        findings: List[str],
        contradictions: List[str],
        uncertainty: Dict[str, Any],
        evaluations: List[Dict[str, Any]],
        loop_count: int = 0
    ) -> str:
        """Generate structured markdown report.
        
        This template is now integrated into v2's FinalFormatterAgent._generate_structured_report().
        """
        
        # Calculate metrics
        avg_confidence = (
            sum(e.get("source_confidence", 0.5) for e in evaluations) / len(evaluations)
            if evaluations else 0.5
        )
        
        missing_topics = uncertainty.get("missing_topics", [])
        global_unc = uncertainty.get("global_uncertainty", 0.0)
        conflict_rate = uncertainty.get("conflict_rate", 0.0)
        info_gap = uncertainty.get("info_gap_score", 0.0)
        
        # Generate report sections
        report = f"""# Executive Summary

本报告针对查询"{query}"进行了系统性的多智能体深度搜索。
共分解为{len(sub_questions)}个子问题，完成{loop_count}轮迭代。

# Structured Findings

{chr(10).join(f"- {f}" for f in findings[:10])}

# Evidence Strength

平均源置信度: {avg_confidence:.2f}

# Contradictions Resolved

{chr(10).join(f"- {c}" for c in contradictions[:5]) if contradictions else "未发现显著矛盾。"}

# Knowledge Gaps

{chr(10).join(f"- {t}" for t in missing_topics[:5]) if missing_topics else "已覆盖主要话题。"}

# Final Uncertainty Score

- Global Uncertainty: {global_unc:.2f}
- Conflict Rate: {conflict_rate:.2f}
- Info Gap Score: {info_gap:.2f}

# Verified Source List

参见检索结果（已通过域名多样性过滤）。
"""
        return report
