from typing import List
from urllib.parse import urlparse
from ..data.models import Evidence, ScoreBreakdown


class ConsensusAgent:
    OFFICIAL_HINTS = [".gov", ".edu", "who.int", "oecd.org", "worldbank.org", "un.org", "europa.eu"]

    def build_scores(
        self,
        evidences: List[Evidence],
        logic_conditions: List[str],
        hidden_premises: List[str],
    ) -> ScoreBreakdown:
        if not evidences:
            return ScoreBreakdown(
                factuality=0.25,
                source_credibility=0.25,
                evidence_consistency=0.25,
                logical_rigor=0.5,
                premise_coverage=0.4,
            )

        support_count = sum(1 for evidence in evidences if evidence.stance == "support")
        refute_count = sum(1 for evidence in evidences if evidence.stance == "refute")
        total_count = max(1, support_count + refute_count)
        
        # 使用证据强度而非简单的credibility
        support_evidences = [e for e in evidences if e.stance == "support"]
        refute_evidences = [e for e in evidences if e.stance == "refute"]
        
        avg_credibility = sum(evidence.credibility for evidence in evidences) / len(evidences)
        avg_relevance = sum(evidence.relevance for evidence in evidences) / len(evidences)
        avg_evidence_strength = sum(getattr(evidence, 'evidence_strength', 0.5) for evidence in evidences) / len(evidences)
        
        # 新增：考虑上下文对齐和语义深度
        avg_context_alignment = sum(getattr(evidence, 'context_alignment', 0.5) for evidence in evidences) / len(evidences)
        avg_semantic_depth = sum(getattr(evidence, 'semantic_depth', 0.5) for evidence in evidences) / len(evidences)

        # 增强的支持/反驳强度计算：使用证据强度和多个维度
        support_strength = sum(
            max(0.0, 
                evidence.credibility * evidence.relevance 
                * getattr(evidence, 'context_alignment', 0.5)
                * getattr(evidence, 'semantic_depth', 0.5)
            )
            for evidence in support_evidences
        )
        refute_strength = sum(
            max(0.0, 
                evidence.credibility * evidence.relevance 
                * getattr(evidence, 'context_alignment', 0.5)
            )
            for evidence in refute_evidences
        )
        total_strength = max(1e-6, support_strength + refute_strength)

        support_ratio = support_strength / total_strength
        # 反驳影响度使用更温和的函数
        contradiction_impact = (refute_strength / (support_strength + refute_strength + 2.0)) ** 0.9

        # 源多样性计算
        support_domains = {
            urlparse(evidence.url).netloc.lower()
            for evidence in support_evidences
            if evidence.url
        }
        refute_domains = {
            urlparse(evidence.url).netloc.lower()
            for evidence in refute_evidences
            if evidence.url
        }
        support_diversity = min(1.0, len(support_domains) / 3.0)  # 调整阈值
        refute_diversity = min(1.0, len(refute_domains) / 2.0)

        # 高质量反驳检测
        high_quality_refute = sum(
            1
            for evidence in refute_evidences
            if evidence.credibility >= 0.88 and evidence.relevance >= 0.75
        )
        
        # 反驳影响度：使用更温和的公式
        contradiction_penalty = min(0.35, contradiction_impact + 0.05 * refute_diversity + 0.04 * high_quality_refute)

        # 官方来源加成
        official_support = sum(
            1
            for evidence in support_evidences
            if evidence.url
            and any(hint in urlparse(evidence.url).netloc.lower() for hint in self.OFFICIAL_HINTS)
            and evidence.credibility >= 0.82
            and evidence.relevance >= 0.7
        )
        official_boost = min(0.12, 0.03 * official_support)  # 增加官方加成上限
        
        # 高深度证据的信心增强（增大权重）
        high_semantic_depth_count = sum(
            1 for evidence in support_evidences 
            if getattr(evidence, 'semantic_depth', 0) >= 0.7
        )
        semantic_boost = min(0.08, 0.02 * high_semantic_depth_count)
        
        # 上下文对齐优化（增大权重）
        high_context_alignment = sum(
            1 for evidence in support_evidences
            if getattr(evidence, 'context_alignment', 0.5) >= 0.7
        )
        context_boost = min(0.06, 0.015 * high_context_alignment)
        
        # 证据强度加成：直接使用 evidence_strength
        high_strength_count = sum(
            1 for evidence in support_evidences
            if getattr(evidence, 'evidence_strength', 0.5) >= 0.75
        )
        strength_boost = min(0.08, 0.02 * high_strength_count)

        # 更新的置信度计算，大幅提升各个维度
        # 增强支持强度权重，降低反驳影响
        factuality = min(1.0, 
            0.75 * support_ratio  # 增加：0.68 -> 0.75
            + 0.15 * avg_evidence_strength  # 新增
            + 0.12 * support_diversity 
            + official_boost  # 增加到 0.12
            + semantic_boost  # 增加到 0.08
            + context_boost  # 增加到 0.06
            + strength_boost  # 新增：0.08
        )
        
        # 证据一致性：反驳影响度更温和
        evidence_consistency = max(0.2, 1.0 - contradiction_penalty)
        
        # 逻辑严密度
        logical_rigor = 0.95 if len(logic_conditions) <= 2 else 0.75
        
        # 前提覆盖度
        premise_coverage = 0.95 if len(hidden_premises) >= 3 else 0.7
        
        # 融入语义深度到前提覆盖度评估
        if avg_semantic_depth >= 0.7:
            premise_coverage = min(1.0, premise_coverage + 0.1)
        
        # 融入平均证据强度到源可信度
        enhanced_credibility = min(1.0, avg_credibility + avg_evidence_strength * 0.2)

        return ScoreBreakdown(
            factuality=round(factuality, 3),
            source_credibility=round(enhanced_credibility, 3),
            evidence_consistency=round(evidence_consistency, 3),
            logical_rigor=round(logical_rigor, 3),
            premise_coverage=round(premise_coverage, 3),
        )
