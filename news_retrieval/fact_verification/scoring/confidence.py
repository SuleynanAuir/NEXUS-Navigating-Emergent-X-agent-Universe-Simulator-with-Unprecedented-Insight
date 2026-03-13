from ..data.models import ScoreBreakdown
from .confidence_levels import ConfidenceLevelManager


def compute_confidence_score(score: ScoreBreakdown) -> float:
    """
    计算综合置信度分数（0-100）
    
    权重分配：
    - factuality (38%)：事实性 - 证据支持强度，是最重要维度
    - source_credibility (26%)：来源可信度
    - evidence_consistency (20%)：证据一致性
    - logical_rigor (10%)：逻辑严密度
    - premise_coverage (6%)：前提覆盖度
    """
    weighted = (
        0.40 * score.factuality
        + 0.22 * score.source_credibility
        + 0.22 * score.evidence_consistency
        + 0.10 * score.logical_rigor
        + 0.06 * score.premise_coverage
    )

    base_score = weighted * 100

    # 非线性校准：对高质量样本给出更合理的提升，避免“正确内容仅20多分”
    quality_anchor = (
        0.52 * score.factuality
        + 0.30 * score.evidence_consistency
        + 0.18 * score.source_credibility
    )
    if quality_anchor >= 0.75:
        base_score += 8.0
    elif quality_anchor >= 0.65:
        base_score += 5.0
    elif quality_anchor >= 0.55:
        base_score += 2.5

    # 轻度约束：逻辑/前提过低时不过度拔高
    if score.logical_rigor < 0.5 or score.premise_coverage < 0.45:
        base_score -= 4.0

    return round(max(0.0, min(100.0, base_score)), 2)


def verdict_from_score(confidence_score: float) -> str:
    """基于置信度分数生成结论"""
    if confidence_score >= 92:
        return "fully_supported"
    elif confidence_score >= 80:
        return "strongly_supported"
    elif confidence_score >= 65:
        return "moderately_supported"
    elif confidence_score >= 45:
        return "uncertain"
    elif confidence_score >= 30:
        return "insufficient"
    else:
        return "strongly_refuted"


def get_confidence_level_info(confidence_score: float) -> dict:
    """获取置信度等级详细信息"""
    return ConfidenceLevelManager.get_level_dict(confidence_score)
