from typing import Dict, List
from ..data.models import Evidence
from .llm_client import LLMClient


class EvidenceRetrieverAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()

    def _compute_context_alignment(self, claim_text: str, evidence_quote: str, original_text: str = "") -> float:
        """计算证据与原文上下文的一致性"""
        if not original_text:
            return 0.5
        
        # 检查证据是否在同一语义领域
        claim_tokens = set(token.lower() for token in claim_text.split() if len(token) > 2)
        original_tokens = set(token.lower() for token in original_text.split() if len(token) > 2)
        evidence_tokens = set(token.lower() for token in evidence_quote.split() if len(token) > 2)
        
        # 计算重叠度
        if not claim_tokens or not original_tokens:
            return 0.5
        
        claim_original_overlap = len(claim_tokens & original_tokens) / max(1, len(claim_tokens | original_tokens))
        evidence_overlap_with_original = len(evidence_tokens & original_tokens) / max(1, len(evidence_tokens | original_tokens))
        
        # 上下文对齐分数 = 证据与原文的相关性 × 原文的完整性信号
        context_alignment = min(1.0, (evidence_overlap_with_original + claim_original_overlap) / 2.0)
        return round(context_alignment, 3)

    def _compute_semantic_depth(self, claim_text: str, evidence_quote: str, title: str = "") -> float:
        """计算证据的语义深度（信息丰富度）"""
        # 基于证据长度、关键词密度、信息量
        claim_tokens = set(token.lower() for token in claim_text.split() if len(token) > 2)
        evidence_tokens = set(token.lower() for token in evidence_quote.split() if len(token) > 2)
        
        # 长度因子：更长的证据通常包含更多信息
        length_factor = min(1.0, len(evidence_tokens) / max(1, len(claim_tokens) * 3))
        
        # 关键词密度因子：证据中包含的声明关键词比例
        keyword_density = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
        
        # 信息丰富度：考虑数字、数据表述等
        has_numbers = any(char.isdigit() for char in evidence_quote)
        info_richness = 1.0 if (has_numbers or "%" in evidence_quote or "data" in evidence_quote.lower()) else 0.8
        
        semantic_depth = min(1.0, (length_factor * 0.3 + keyword_density * 0.5 + info_richness * 0.2))
        return round(semantic_depth, 3)

    def run(self, claim_text: str, search_result: Dict[str, List[dict]], mode: str = "fast", original_text: str = "") -> List[Evidence]:
        evidences: List[Evidence] = []
        flat_items: List[tuple] = []
        for bucket in ["trusted", "scholar", "web"]:
            for item in search_result.get(bucket, []):
                flat_items.append((bucket, item))

        claim_tokens = [token.lower() for token in claim_text.split() if token.strip()]
        llm_budget = 12 if mode == "deep" else 0
        for index, (bucket, item) in enumerate(flat_items[:35]):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            content = f"{title} {snippet}".lower()
            overlap = sum(1 for token in claim_tokens if token in content)
            search_score = float(item.get("search_score", 0.0))

            source_weight = 0.95 if bucket == "trusted" else (0.85 if bucket == "scholar" else 0.7)
            relevance = min(
                1.0,
                (overlap / max(1, len(claim_tokens))) * 0.55 + source_weight * 0.25 + search_score * 0.2,
            )
            stance = "support" if overlap >= max(1, len(claim_tokens) // 4) else "refute"

            rationale = f"token_overlap={overlap}, bucket={bucket}, search_score={search_score:.3f}"
            
            # 计算上下文一致性和语义深度
            context_alignment = self._compute_context_alignment(claim_text, snippet or title, original_text)
            semantic_depth = self._compute_semantic_depth(claim_text, snippet or title, title)

            if self.llm.enabled and mode == "deep" and snippet and index < llm_budget:
                llm_result = self.llm.json_call(
                    "你是证据判别助手。输出 JSON: {\"stance\":\"support|refute\",\"rationale\":\"...\",\"relevance\":0-1}。",
                    f"主张：{claim_text}\n证据标题：{title}\n证据摘要：{snippet}",
                )
                if llm_result:
                    stance = str(llm_result.get("stance", stance)).lower()
                    if stance not in {"support", "refute"}:
                        stance = "support" if overlap >= 1 else "refute"
                    rationale = str(llm_result.get("rationale", rationale))
                    try:
                        relevance = max(0.0, min(1.0, float(llm_result.get("relevance", relevance))))
                    except Exception:
                        pass

            # 计算综合证据强度：credibility × relevance × context_alignment × semantic_depth
            evidence_strength = min(1.0, relevance * context_alignment * semantic_depth)

            evidences.append(
                Evidence(
                    quote=snippet or title,
                    source=item.get("url", ""),
                    url=item.get("url", ""),
                    stance=stance,
                    credibility=0.5,
                    relevance=round(relevance, 3),
                    rationale=rationale,
                    context_alignment=context_alignment,
                    semantic_depth=semantic_depth,
                    evidence_strength=round(evidence_strength, 3),
                )
            )
        evidences.sort(key=lambda item: (item.stance == "support", item.evidence_strength, item.relevance), reverse=True)
        return evidences[:20]
