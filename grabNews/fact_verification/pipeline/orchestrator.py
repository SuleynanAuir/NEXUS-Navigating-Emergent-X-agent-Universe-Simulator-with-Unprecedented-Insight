from typing import Callable, List, Optional
from urllib.parse import urlparse
from copy import deepcopy

from ..agents.claim_extractor import ClaimExtractorAgent
from ..agents.search_agent import SearchAgent
from ..agents.evidence_retriever import EvidenceRetrieverAgent
from ..agents.credibility_agent import CredibilityAgent
from ..agents.logic_agent import LogicAgent
from ..agents.premise_agent import PremiseAgent
from ..agents.consensus_agent import ConsensusAgent
from ..data.models import VerificationReport, Evidence
from ..scoring.confidence import compute_confidence_score, verdict_from_score, get_confidence_level_info


class FactVerificationOrchestrator:
    def __init__(self) -> None:
        self.claim_extractor = ClaimExtractorAgent()
        self.search_agent = SearchAgent()
        self.evidence_agent = EvidenceRetrieverAgent()
        self.credibility_agent = CredibilityAgent()
        self.logic_agent = LogicAgent()
        self.premise_agent = PremiseAgent()
        self.consensus_agent = ConsensusAgent()

    def verify_text(
        self,
        text: str,
        source_type: str = "text",
        mode: str = "fast",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[VerificationReport]:
        claims = self.claim_extractor.extract(text, source_type=source_type)
        return self._verify_claims(claims, source_type=source_type, mode=mode, progress_callback=progress_callback)

    def verify_annotations(
        self,
        annotations: List[dict],
        mode: str = "fast",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[VerificationReport]:
        claims = self.claim_extractor.extract_annotations(annotations)
        return self._verify_claims(claims, source_type="annotations", mode=mode, progress_callback=progress_callback)

    def _screening_label(self, evidences: List[Evidence]) -> str:
        if not evidences:
            return "unsupported"
        high_support = sum(1 for evidence in evidences if evidence.stance == "support" and evidence.credibility >= 0.85)
        high_refute = sum(1 for evidence in evidences if evidence.stance == "refute" and evidence.credibility >= 0.85)
        support_total = sum(1 for evidence in evidences if evidence.stance == "support")
        refute_total = sum(1 for evidence in evidences if evidence.stance == "refute")
        if high_support >= 2 and high_refute == 0:
            return "well-supported"
        if support_total == 0 and refute_total > 0:
            return "unsupported"
        if support_total > refute_total and high_support >= 1:
            return "weakly-supported"
        return "uncertain"

    def _official_data_boost(self, evidences: List[Evidence], mode: str) -> float:
        if mode != "deep":
            return 0.0
        official_hints = [".gov", ".edu", "who.int", "oecd.org", "worldbank.org", "un.org", "europa.eu"]
        data_hints = ["official", "dataset", "statistics", "report", "government", "官方", "数据", "统计"]
        strong_count = 0
        for evidence in evidences:
            if evidence.stance != "support":
                continue
            host = urlparse(evidence.url).netloc.lower()
            quote_text = (evidence.quote or "").lower()
            has_official_source = any(hint in host for hint in official_hints) or evidence.credibility >= 0.9
            has_data_signal = any(hint in quote_text for hint in data_hints)
            if has_official_source and (has_data_signal or evidence.relevance >= 0.8):
                strong_count += 1
        if strong_count <= 0:
            return 0.0
        return min(12.0, 4.0 * strong_count)

    def _evidence_calibration_boost(self, evidences: List[Evidence], mode: str) -> float:
        if not evidences:
            return -8.0

        support = [e for e in evidences if e.stance == "support"]
        refute = [e for e in evidences if e.stance == "refute"]

        support_strength = sum(e.credibility * e.relevance for e in support)
        refute_strength = sum(e.credibility * e.relevance for e in refute)
        total_strength = max(1e-6, support_strength + refute_strength)

        support_ratio = support_strength / total_strength
        avg_relevance = sum(e.relevance for e in evidences) / len(evidences)
        avg_credibility = sum(e.credibility for e in evidences) / len(evidences)
        strong_support_count = sum(1 for e in support if e.credibility >= 0.82 and e.relevance >= 0.72)
        high_quality_refute = sum(1 for e in refute if e.credibility >= 0.86 and e.relevance >= 0.75)

        boost = 0.0
        if support_ratio >= 0.78 and avg_relevance >= 0.62:
            boost += 8.0
        elif support_ratio >= 0.68 and avg_relevance >= 0.55:
            boost += 5.0
        elif support_ratio >= 0.60 and avg_relevance >= 0.50:
            boost += 2.5

        boost += min(5.0, strong_support_count * 1.25)

        # 反驳证据影响：仅在高质量反驳出现时显著扣分
        if high_quality_refute > 0:
            boost -= min(10.0, high_quality_refute * 3.0)
        elif support_ratio < 0.45:
            boost -= 4.0

        if avg_credibility < 0.52:
            boost -= 2.0

        # deep 模式允许更高上限，fast 稍保守
        cap = 16.0 if mode == "deep" else 12.0
        return max(-14.0, min(cap, boost))

    def _verify_claims(
        self,
        claims,
        source_type: str,
        mode: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[VerificationReport]:
        reports: List[VerificationReport] = []
        if not claims:
            return reports

        claim_cache = {}

        total_steps = max(1, len(claims) * 6)
        step = 0

        def tick(message: str) -> None:
            nonlocal step
            step += 1
            if progress_callback:
                progress_callback(message, min(1.0, step / total_steps))

        for claim in claims:
            cache_key = " ".join(claim.text.lower().split())
            cached_item = claim_cache.get((cache_key, mode))

            if cached_item is not None:
                tick("命中缓存：复用检索与证据")
                search_result = deepcopy(cached_item["search_result"])
                evidences = deepcopy(cached_item["evidences"])
                screening_label = cached_item["screening_label"]
                deep_required = cached_item["deep_required"]
            else:
                tick("快速筛查：检索多源结果")
                search_result = self.search_agent.run(claim.text, mode="fast")

                tick("抽取证据并计算相关性")
                evidences = self.evidence_agent.run(claim.text, search_result, mode="fast", original_text=claim.original_text)

                tick("评估来源可信度")
                evidences = self.credibility_agent.run(evidences)

                screening_label = self._screening_label(evidences)
                deep_required = mode == "deep" and screening_label == "uncertain"

                if deep_required:
                    tick("深度搜索：扩展查询与证据增强")
                    deep_result = self.search_agent.run(claim.text, mode="deep")
                    deep_evidences = self.evidence_agent.run(claim.text, deep_result, mode="deep", original_text=claim.original_text)
                    deep_evidences = self.credibility_agent.run(deep_evidences)
                    evidences = deep_evidences
                    search_result = deep_result

                claim_cache[(cache_key, mode)] = {
                    "search_result": deepcopy(search_result),
                    "evidences": deepcopy(evidences),
                    "screening_label": screening_label,
                    "deep_required": deep_required,
                }

            tick("执行逻辑一致性分析")
            logic_conditions = self.logic_agent.run(claim.text, mode=mode)

            tick("识别隐藏前提")
            hidden_premises = self.premise_agent.run(claim.text, mode=mode)
            score_breakdown = self.consensus_agent.build_scores(evidences, logic_conditions, hidden_premises)

            tick("汇总评分并生成结论")
            confidence_score = compute_confidence_score(score_breakdown)
            confidence_score = min(100.0, confidence_score + self._official_data_boost(evidences, mode=mode))
            confidence_score = min(100.0, confidence_score + self._evidence_calibration_boost(evidences, mode=mode))
            verdict = verdict_from_score(confidence_score)
            confidence_level = get_confidence_level_info(confidence_score)

            supporting_evidence = [evidence for evidence in evidences if evidence.stance == "support"]
            refuting_evidence = [evidence for evidence in evidences if evidence.stance == "refute"]
            top_evidences = evidences[:3]

            reasoning_chain = [
                f"提取主张：{claim.text}",
                f"验证模式：{mode}，快速筛查结论：{screening_label}",
                f"生成检索查询 {len(search_result.get('queries', []))} 条，并执行多源检索。",
                f"汇总证据 {len(evidences)} 条（支持 {len(supporting_evidence)} / 反驳 {len(refuting_evidence)}）。",
                f"进行逻辑条件检查 {len(logic_conditions)} 条，识别隐含前提 {len(hidden_premises)} 条。",
                f"综合评分得到置信度 {confidence_score}，结论为 {verdict}。",
            ]
            if top_evidences:
                reasoning_chain.append(
                    "关键证据相关性：" + ", ".join(f"{evidence.relevance:.2f}" for evidence in top_evidences)
                )

            report = VerificationReport(
                claim=claim.text,
                supporting_evidence=supporting_evidence[:5],
                refuting_evidence=refuting_evidence[:5],
                logic_conditions=logic_conditions,
                hidden_premises=hidden_premises,
                score_breakdown=score_breakdown,
                confidence_score=confidence_score,
                confidence_level=confidence_level,
                verdict=verdict,
                trace={
                    "claims_extracted": str(len(claims)),
                    "evidence_total": str(len(evidences)),
                    "source_type": source_type,
                    "mode": mode,
                    "screening_label": screening_label,
                    "deep_verification_required": str(deep_required),
                    "input_source_url": claim.source_url,
                    "queries_used": " | ".join(search_result.get("queries", [])[:6]),
                    "query_count": str(len(search_result.get("queries", []))),
                    "trusted_hits": str(len(search_result.get("trusted", []))),
                    "scholar_hits": str(len(search_result.get("scholar", []))),
                    "web_hits": str(len(search_result.get("web", []))),
                    "llm_enhanced": str(bool(search_result.get("llm_enabled", False))),
                },
                reasoning_chain=reasoning_chain,
            )
            reports.append(report)

        if progress_callback:
            progress_callback("验证完成", 1.0)
        return reports
