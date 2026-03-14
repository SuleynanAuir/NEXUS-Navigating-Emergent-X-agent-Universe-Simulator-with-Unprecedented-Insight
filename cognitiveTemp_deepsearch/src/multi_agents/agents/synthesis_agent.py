"""
Synthesis Agent - Scientific Synthesis & Structured Reporting

Objective: Generate publication-level structured report from multi-agent findings.

Format:
# Abstract
# Background
# Key Findings
# Evidence Strength
# Contradictions
# Limitations
# Future Research Directions
# Confidence Assessment

Rules:
- No new claims
- Separate fact vs inference
- Highlight uncertainty explicitly
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SynthesisReport:
    abstract: str
    background: str
    key_findings: List[str]
    evidence_strength: str
    contradictions: List[str]
    limitations: List[str]
    future_research: List[str]
    confidence_assessment: str
    uncertainty_highlight: List[str] = field(default_factory=list)
    fact_vs_inference: Dict[str, List[str]] = field(default_factory=lambda: {"facts": [], "inferences": []})

    def to_dict(self) -> Dict:
        return {
            "abstract": self.abstract,
            "background": self.background,
            "key_findings": self.key_findings,
            "evidence_strength": self.evidence_strength,
            "contradictions": self.contradictions,
            "limitations": self.limitations,
            "future_research": self.future_research,
            "confidence_assessment": self.confidence_assessment,
            "uncertainty_highlight": self.uncertainty_highlight,
            "fact_vs_inference": self.fact_vs_inference,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

class SynthesisAgent:
    """
    Scientific Synthesis Agent
    Generates publication-level structured report from multi-agent outputs.
    """
    def __init__(self, llm_client: Optional[object] = None, model: str = "gpt-4"):
        self.llm_client = llm_client
        self.model = model
        logger.info(f"Initialized Synthesis Agent (model={model})")

    def synthesize(
        self,
        background: str,
        findings: List[str],
        evidence_strength: str,
        contradictions: List[str],
        limitations: List[str],
        future_research: List[str],
        confidence_assessment: str,
        uncertainty_highlight: Optional[List[str]] = None,
        fact_vs_inference: Optional[Dict[str, List[str]]] = None,
        abstract: Optional[str] = None,
    ) -> SynthesisReport:
        """
        Generate structured synthesis report.
        All content must be derived from input, no new claims.
        """
        # Abstract自动生成（如未提供）
        if abstract is None:
            abstract = self._generate_abstract(background, findings, evidence_strength, contradictions, limitations, confidence_assessment)
        # 事实与推断分离
        if fact_vs_inference is None:
            fact_vs_inference = self._separate_fact_inference(findings)
        # 显式突出不确定性
        if uncertainty_highlight is None:
            uncertainty_highlight = self._extract_uncertainty(confidence_assessment, limitations, contradictions)
        return SynthesisReport(
            abstract=abstract,
            background=background,
            key_findings=findings,
            evidence_strength=evidence_strength,
            contradictions=contradictions,
            limitations=limitations,
            future_research=future_research,
            confidence_assessment=confidence_assessment,
            uncertainty_highlight=uncertainty_highlight,
            fact_vs_inference=fact_vs_inference,
        )

    def _generate_abstract(self, background, findings, evidence_strength, contradictions, limitations, confidence_assessment):
        """自动生成摘要（不引入新内容）"""
        abstract = (
            f"{background}\n主要发现包括：{', '.join(findings[:2])}。证据强度为{evidence_strength}，存在主要矛盾：{', '.join(contradictions[:1]) if contradictions else '无'}。"
            f"局限性：{', '.join(limitations[:1]) if limitations else '未明确'}。整体置信度评估：{confidence_assessment}。"
        )
        return abstract

    def _separate_fact_inference(self, findings: List[str]) -> Dict[str, List[str]]:
        """分离事实与推断（简单规则：含“可能”“推测”“建议”为推断）"""
        facts, inferences = [], []
        for f in findings:
            if any(kw in f for kw in ["可能", "推测", "建议", "或许", "假设", "推断"]):
                inferences.append(f)
            else:
                facts.append(f)
        return {"facts": facts, "inferences": inferences}

    def _extract_uncertainty(self, confidence_assessment, limitations, contradictions) -> List[str]:
        """提取不确定性描述"""
        highlights = []
        if "不确定" in confidence_assessment or "低" in confidence_assessment:
            highlights.append(f"置信度评估提示不确定性：{confidence_assessment}")
        for lim in limitations:
            if any(kw in lim for kw in ["样本量小", "方法有限", "数据不足", "偏见", "外推有限"]):
                highlights.append(f"局限性提示：{lim}")
        for c in contradictions:
            if c:
                highlights.append(f"存在矛盾：{c}")
        return highlights

    def validate_report(self, report: SynthesisReport) -> (bool, List[str]):
        """验证报告结构和规则"""
        errors = []
        if not report.abstract:
            errors.append("摘要不能为空")
        if not report.key_findings:
            errors.append("主要发现不能为空")
        if any("新发现" in kf for kf in report.key_findings):
            errors.append("不得引入新主张")
        if not isinstance(report.fact_vs_inference, dict):
            errors.append("事实与推断分离格式错误")
        return len(errors) == 0, errors

def create_synthesis_agent(llm_client: Optional[object] = None, model: str = "gpt-4") -> SynthesisAgent:
    """工厂函数，创建Synthesis Agent"""
    return SynthesisAgent(llm_client=llm_client, model=model)
