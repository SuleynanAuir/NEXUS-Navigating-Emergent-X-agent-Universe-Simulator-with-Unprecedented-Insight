"""
Fast MARDS v2 Controller - optimized for speed and avoiding timeouts.
- Direct search without LLM query generation
- 2 max results per search (instead of 5)
- Max 3 reflection loops per section with smart early stop
- Minimal intermediate file saves
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from v2_paragraph_reflective.agents import (
    StructurePlannerAgent,
    SectionRetrieverAgent,
    SectionSummarizerAgent,
    ReflectionAgent,
    SectionUpdaterAgent,
    GlobalUncertaintyAgent,
    FinalFormatterAgent
)
from v2_paragraph_reflective.clients import DeepSeekClient, TavilyClient
from v2_paragraph_reflective.schema import Section

logger = logging.getLogger(__name__)


class MARDSControllerFast:
    """Fast MARDS controller optimized for speed."""

    @staticmethod
    def _domain_authority(domain: str) -> float:
        d = (domain or "").lower()
        if d.endswith(".gov") or ".gov." in d:
            return 1.00
        if d.endswith(".edu") or ".ac." in d:
            return 0.95
        if d.endswith(".org"):
            return 0.82
        if d.endswith(".news") or "news" in d:
            return 0.72
        return 0.60

    @staticmethod
    def _source_quality_score(source: Dict[str, Any], query: str, section_title: str) -> float:
        title = (source.get("title") or "").lower()
        content = (source.get("content") or "").lower()
        score = max(0.0, min(1.0, float(source.get("score", 0.0))))
        authority = MARDSControllerFast._domain_authority(source.get("domain", ""))

        query_terms = [t for t in (query or "").lower().split() if t]
        title_terms = [t for t in (section_title or "").lower().split() if t]
        lexical_hit = 0.0
        if query_terms or title_terms:
            hit_count = 0
            total = len(query_terms) + len(title_terms)
            for t in query_terms + title_terms:
                if t in title or t in content:
                    hit_count += 1
            lexical_hit = hit_count / total if total > 0 else 0.0

        return max(0.0, min(1.0, 0.56 * score + 0.26 * authority + 0.18 * lexical_hit))

    @staticmethod
    def _estimate_sources_consistency(sources: List[Dict[str, Any]], query: str, section_title: str) -> float:
        if not sources:
            return 0.0
        quality_scores = [
            MARDSControllerFast._source_quality_score(s, query=query, section_title=section_title)
            for s in sources
        ]
        mean_quality = sum(quality_scores) / len(quality_scores)
        if len(quality_scores) <= 1:
            return mean_quality
        variance = sum((x - mean_quality) ** 2 for x in quality_scores) / len(quality_scores)
        dispersion = min(1.0, (variance ** 0.5) / 0.5)
        return max(0.0, min(1.0, 0.70 * mean_quality + 0.30 * (1.0 - dispersion)))

    @staticmethod
    def _denoise_and_rerank_sources(
        sources: List[Dict[str, Any]],
        query: str,
        section_title: str,
        retrieval_budget: int,
    ) -> List[Dict[str, Any]]:
        if len(sources) <= 4:
            return sources

        ranked = sorted(
            sources,
            key=lambda s: MARDSControllerFast._source_quality_score(s, query=query, section_title=section_title),
            reverse=True,
        )
        keep_n = min(len(ranked), max(retrieval_budget + 3, 6))
        return ranked[:keep_n]

    @staticmethod
    def _compute_reflection_pressure(
        section_title: str,
        confidence: float,
        needs_reflection: bool,
        retrieval_budget: int,
        sources_count: int,
        retrieval_metrics: Dict[str, Any],
    ) -> float:
        """Compute reflection pressure in [0,1] from multiple weak/strong signals."""
        mean_rel = retrieval_metrics.get("mean_relevance", 0.0)
        rel_disp = retrieval_metrics.get("relevance_dispersion", 0.0)
        query_coverage = retrieval_metrics.get("query_coverage", 0.0)
        consensus = retrieval_metrics.get("cross_query_consensus", 0.0)
        authority = retrieval_metrics.get("authority_score", 0.0)
        evidence_consistency = retrieval_metrics.get("evidence_consistency", max(0.0, 1.0 - rel_disp))

        missing_ratio = 0.0
        if retrieval_budget > 0:
            missing_ratio = max(0.0, (retrieval_budget - sources_count) / retrieval_budget)

        # Increased low_conf threshold to be more sensitive to medium confidence
        low_conf = max(0.0, 0.72 - confidence)  # Raised from 0.68
        low_rel = max(0.0, 0.52 - mean_rel)
        high_disp = max(0.0, rel_disp - 0.14)
        low_coverage = max(0.0, 0.75 - query_coverage)
        low_consensus = max(0.0, 0.58 - consensus)
        low_authority = max(0.0, 0.62 - authority)
        weak_consistency = max(0.0, 0.70 - evidence_consistency)

        # Increased low_conf weight to prioritize confidence improvement
        pressure = (
            0.28 * low_conf  # Increased from 0.24
            + 0.18 * low_rel  # Reduced from 0.20 to rebalance
            + 0.14 * high_disp
            + 0.12 * low_coverage
            + 0.10 * low_consensus  # Reduced from 0.11
            + 0.08 * low_authority
            + 0.06 * weak_consistency
            + 0.04 * missing_ratio  # Reduced from 0.05
        )

        title = (section_title or "").lower()
        # Enhanced section-type pressure for conclusion/outlook sections
        if any(k in title for k in ["结论", "展望", "未来", "总结", "conclusion", "outlook", "future"]):
            pressure += 0.06  # Higher boost for critical summary sections
        elif any(k in title for k in ["案例", "风险", "治理", "机制", "争议", "对比", "评估"]):
            pressure += 0.04

        if needs_reflection:
            pressure += 0.08  # Increased from 0.06

        return max(0.0, min(1.0, pressure))

    @staticmethod
    def _decide_reflection_plan(
        force_reflection: bool,
        min_required_loops: int,
        max_reflection_loops: int,
        pressure: float,
        confidence: float,
        mean_rel: float,
        rel_disp: float,
        query_coverage: float,
        sources_count: int,
    ) -> Tuple[bool, int]:
        """Return (should_reflect, target_loops) with smarter gating."""
        # Much more aggressive hard_risk thresholds
        hard_risk = (
            confidence < 0.65  # Raised from 0.60 to catch 0.64 cases
            or (mean_rel < 0.48 and query_coverage < 0.80)  # Raised thresholds
            or rel_disp > 0.22
            or sources_count <= 4  # Raised from 2 - low source count is risky
        )

        should_reflect = force_reflection or hard_risk or pressure > 0.10  # Lowered from 0.13

        if not should_reflect:
            return False, 0

        # More aggressive target loop calculation
        base_target = 1 + int(pressure * 4.0)  # Increased from 3.5
        
        # Special boost for medium-confidence sections (0.60-0.70)
        if 0.60 <= confidence < 0.70:
            base_target += 1  # Ensure at least 2 loops for marginal cases
        
        if hard_risk:
            base_target += 1

        target_loops = min(
            max_reflection_loops,
            max(min_required_loops, 1, base_target),
        )
        return True, target_loops

    @staticmethod
    def _select_retrieval_budget(section_title: str) -> int:
        """Select retrieval budget by section type to reduce homogeneity."""
        title = (section_title or "").lower()
        if any(k in title for k in ["案例", "案例研究", "case", "挑战", "风险"]):
            return 3
        if any(k in title for k in ["引言", "总结", "结论", "展望", "建议"]):
            return 2
        return 3

    @staticmethod
    def _select_reflection_budget(section_title: str) -> int:
        """Select reflection search budget by section type."""
        title = (section_title or "").lower()
        if any(k in title for k in ["案例", "治理", "机制", "风险"]):
            return 3
        return 2
    
    def __init__(
        self,
        deepseek_key: str,
        tavily_key: str,
        results_dir: Optional[str] = None,
        max_reflection_loops: int = 3,
        force_reflection: bool = False,
        min_reflection_loops: int = 0,
        reflection_sensitivity: float = 1.0,
        uncertainty_threshold: float = 0.2,
        deterministic: bool = False,
        section_concurrency: int = 2
    ):
        """Initialize fast controller.
        
        Args:
            deepseek_key: DeepSeek API key
            tavily_key: Tavily API key
            results_dir: Directory to save results
            max_reflection_loops: Max reflection loops (smart mode, default: 3)
            force_reflection: Force reflection even if section quality seems sufficient
            min_reflection_loops: Minimum reflection loops per section in force mode
            reflection_sensitivity: Reflection gain sensitivity in [0.5, 2.0]
            uncertainty_threshold: Threshold for reflection
            deterministic: Deterministic mode
        """
        self.deepseek_key = deepseek_key
        self.tavily_key = tavily_key
        self.results_dir = Path(results_dir) if results_dir else Path("runs")
        self.max_reflection_loops = max(0, max_reflection_loops)
        self.force_reflection = force_reflection
        self.min_reflection_loops = max(0, min(min_reflection_loops, self.max_reflection_loops))
        self.reflection_sensitivity = max(0.5, min(2.0, reflection_sensitivity))
        self.uncertainty_threshold = uncertainty_threshold
        self.section_concurrency = max(1, section_concurrency)
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.task_id = str(uuid.uuid4())
        
        logger.info(f"MARDS Fast Controller initialized (Task ID: {self.task_id})")
    
    async def run(
        self,
        query: str,
        enable_reflection: bool = True
    ) -> Dict[str, Any]:
        """Execute fast MARDS workflow.
        
        Args:
            query: Research query
            enable_reflection: Enable reflection loops
            
        Returns:
            Final report and metadata
        """
        logger.info(f"Starting MARDS fast workflow for query: {query}")
        
        try:
            async with DeepSeekClient(self.deepseek_key) as deepseek_client:
                async with TavilyClient(self.tavily_key) as tavily_client:
                    # Step 1: Structure
                    logger.info("Step 1: Planning structure...")
                    structure_agent = StructurePlannerAgent(deepseek_client)
                    structure_response = await structure_agent.execute(
                        task_id=self.task_id,
                        query=query
                    )
                    
                    structure_data = structure_response.output["structure"]
                    sections = [
                        Section(
                            section_id=sec["section_id"],
                            section_title=sec["section_title"],
                            objective=sec["objective"]
                        )
                        for sec in structure_data["sections"]
                    ]
                    
                    # Step 2-5: Process sections (fast, 1 reflection max)
                    logger.info(f"Step 2-5: Processing {len(sections)} sections...")
                    section_metrics: List[Dict[str, Any]] = []
                    semaphore = asyncio.Semaphore(self.section_concurrency)

                    async def process_section(section: Section) -> Tuple[Section, Dict[str, Any]]:
                        async with semaphore:
                            logger.info(f"  Section: {section.section_title}")
                            retriever_agent = SectionRetrieverAgent(tavily_client)
                            summarizer_agent = SectionSummarizerAgent(deepseek_client)
                            reflection_agent = ReflectionAgent(deepseek_client)
                            updater_agent = SectionUpdaterAgent(deepseek_client)

                            retrieval_budget = self._select_retrieval_budget(section.section_title)

                            retrieval_response = await retriever_agent.execute(
                                task_id=self.task_id,
                                section=section,
                                query=query,
                                max_results=retrieval_budget
                            )
                            section.sources = retrieval_response.output.get("sources", [])
                            section.confidence = retrieval_response.confidence
                            section.uncertainty = max(0.05, 1 - section.confidence)
                            retrieval_metrics = retrieval_response.output.get("metrics", {})
                            mean_rel = retrieval_metrics.get("mean_relevance", 0.0)
                            ndcg = retrieval_metrics.get("ndcg", 0.0)
                            mrr = retrieval_metrics.get("mrr", 0.0)
                            rel_disp = retrieval_metrics.get("relevance_dispersion", 0.0)
                            query_coverage = retrieval_metrics.get("query_coverage", 0.0)
                            cross_query_consensus = retrieval_metrics.get("cross_query_consensus", 0.0)
                            evidence_consistency = retrieval_metrics.get("evidence_consistency", max(0.0, 1.0 - rel_disp))
                            retrieval_quality = max(
                                0.0,
                                min(
                                    1.0,
                                    0.33 * mean_rel
                                    + 0.20 * ndcg
                                    + 0.14 * mrr
                                    + 0.15 * query_coverage
                                    + 0.10 * cross_query_consensus
                                    + 0.08 * evidence_consistency,
                                ),
                            )

                            summary_response = await summarizer_agent.execute(
                                task_id=self.task_id,
                                section=section,
                                query=query,
                                sources=section.sources
                            )
                            section.initial_summary = summary_response.output.get("summary", "")
                            section.final_summary = section.initial_summary
                            section.confidence = min(
                                0.95,
                                max(
                                    0.05,
                                    section.confidence * 0.88
                                    + summary_response.confidence * 0.08
                                    + retrieval_quality * 0.04,
                                )
                            )
                            section.uncertainty = max(0.05, 1 - section.confidence)

                            if enable_reflection and section.initial_summary and self.max_reflection_loops > 0:
                                min_required_loops = self.min_reflection_loops if self.force_reflection else 0
                                reflection_pressure = self._compute_reflection_pressure(
                                    section_title=section.section_title,
                                    confidence=section.confidence,
                                    needs_reflection=retrieval_response.needs_reflection,
                                    retrieval_budget=retrieval_budget,
                                    sources_count=len(section.sources),
                                    retrieval_metrics=retrieval_metrics,
                                )
                                pressure_scale = 0.85 + 0.30 * self.reflection_sensitivity
                                reflection_pressure = max(
                                    0.0,
                                    min(1.0, reflection_pressure * pressure_scale),
                                )
                                should_reflect, target_loops = self._decide_reflection_plan(
                                    force_reflection=self.force_reflection,
                                    min_required_loops=min_required_loops,
                                    max_reflection_loops=self.max_reflection_loops,
                                    pressure=reflection_pressure,
                                    confidence=section.confidence,
                                    mean_rel=mean_rel,
                                    rel_disp=rel_disp,
                                    query_coverage=query_coverage,
                                    sources_count=len(section.sources),
                                )

                                logger.debug(
                                    "Reflection plan | section=%s pressure=%.3f should=%s loops=%s",
                                    section.section_title,
                                    reflection_pressure,
                                    should_reflect,
                                    target_loops,
                                )

                                current_summary = section.final_summary
                                used_reflection_queries = set()
                                denoise_applied = False
                                post_reflection_consistency = self._estimate_sources_consistency(
                                    section.sources,
                                    query=query,
                                    section_title=section.section_title,
                                )
                                for loop_idx in range(target_loops):
                                    if not should_reflect and loop_idx >= min_required_loops:
                                        break

                                    reflection_response = await reflection_agent.execute(
                                        task_id=self.task_id,
                                        section=section,
                                        query=query,
                                        current_summary=current_summary
                                    )
                                    search_query = reflection_response.output.get("search_query", "")
                                    needs_search = reflection_response.output.get("needs_deeper_search", False)

                                    if not (needs_search and search_query):
                                        if section.confidence < 0.50 and loop_idx == 0:
                                            # Fallback for weak sections when reflection fails to propose query
                                            search_query = f"{query} {section.section_title} {section.objective} 数据 案例"
                                            needs_search = True
                                        elif loop_idx < min_required_loops:
                                            search_query = f"{query} {section.section_title} 最新 证据 争议 数据"
                                            needs_search = True
                                        else:
                                            break

                                    # Prevent repeated low-yield query loops
                                    if search_query in used_reflection_queries:
                                        missing_info = reflection_response.output.get("missing_info", "")
                                        if missing_info:
                                            search_query = f"{search_query} {missing_info[:40]}"
                                        else:
                                            search_query = f"{search_query} 最新 证据"
                                    used_reflection_queries.add(search_query)

                                    if not search_query.strip():
                                        break

                                    logger.info(
                                        f"    Reflection search (loop {loop_idx + 1}/{target_loops})..."
                                    )
                                    reflection_budget = self._select_reflection_budget(section.section_title)
                                    additional_results = await tavily_client.search(
                                        query=search_query,
                                        max_results=reflection_budget
                                    )

                                    additional_sources = [
                                        {
                                            "title": r.title,
                                            "url": r.url,
                                            "content": r.content[:500],
                                            "domain": r.domain,
                                            "score": r.score,
                                        }
                                        for r in additional_results
                                    ]

                                    existing_urls = {src.get("url", "") for src in section.sources}
                                    new_unique_sources = [
                                        s for s in additional_sources if s.get("url", "") not in existing_urls
                                    ]
                                    section.sources.extend(new_unique_sources)
                                    section.reflection_count += 1

                                    update_response = await updater_agent.execute(
                                        task_id=self.task_id,
                                        section=section,
                                        current_summary=current_summary,
                                        new_sources=new_unique_sources or additional_sources,
                                    )
                                    current_summary = update_response.output.get("updated_summary", current_summary)
                                    section.final_summary = current_summary

                                    added_mean_score = (
                                        sum(src.get("score", 0.0) for src in additional_sources) / len(additional_sources)
                                        if additional_sources
                                        else 0.0
                                    )
                                    added_authority = (
                                        sum(self._domain_authority(src.get("domain", "")) for src in additional_sources) / len(additional_sources)
                                        if additional_sources
                                        else 0.0
                                    )
                                    added_consistency = self._estimate_sources_consistency(
                                        additional_sources,
                                        query=query,
                                        section_title=section.section_title,
                                    )
                                    unique_ratio = (
                                        len(new_unique_sources) / len(additional_sources)
                                        if additional_sources else 0.0
                                    )
                                    # Improved loop decay: slower decay for sustained reflection value
                                    # Old: max(0.35, 1.0 - 0.35*idx) = [1.0, 0.65, 0.35, 0.35, ...]
                                    # New: max(0.45, 1.0 - 0.25*idx) = [1.0, 0.75, 0.50, 0.45, ...]
                                    loop_decay = max(0.45, 1.0 - 0.25 * loop_idx)
                                    
                                    # Quality multiplier: reward high-value new evidence
                                    evidence_quality_bonus = 1.0
                                    if added_consistency > 0.68 and added_authority > 0.75:
                                        evidence_quality_bonus = 1.25  # Exceptional sources
                                    elif added_consistency > 0.60 and added_mean_score > 0.60:
                                        evidence_quality_bonus = 1.12  # Good sources
                                    
                                    adaptive_gain = loop_decay * evidence_quality_bonus * (
                                        0.06 * (update_response.confidence - 0.5)  # +1% update signal weight
                                        + 0.05 * (added_mean_score - 0.5)  # +1% new score weight
                                        + 0.06 * (added_consistency - 0.5)  # +2% consistency weight
                                        + 0.04 * (added_authority - 0.5)  # +1% authority weight
                                        + 0.04 * (mean_rel - 0.5)
                                        + 0.03 * (retrieval_quality - 0.5)
                                        + 0.02 * (cross_query_consensus - 0.5)
                                        + 0.03 * (unique_ratio - 0.30)  # Adjusted baseline from 0.35 to 0.30
                                        - 0.04 * rel_disp  # Reduced penalty from 0.05 to 0.04
                                    )
                                    gain_scale = 0.85 + 0.40 * self.reflection_sensitivity  # Base raised 0.80→0.85
                                    adaptive_gain = adaptive_gain * gain_scale

                                    section.confidence = min(
                                        0.95,
                                        max(0.05, section.confidence + adaptive_gain),
                                    )
                                    section.uncertainty = max(0.05, 1 - section.confidence)

                                    # Smart early-stop:
                                    # 1) confidence already sufficient
                                    # 2) tiny gain and low novel evidence
                                    # 3) diminishing returns in later loops
                                    if section.confidence >= 0.62 and (loop_idx + 1) >= min_required_loops:
                                        break
                                    if adaptive_gain <= 0.004 and unique_ratio < 0.35 and (loop_idx + 1) >= min_required_loops:
                                        break
                                    if loop_idx >= 1 and adaptive_gain <= 0.006 and (loop_idx + 1) >= min_required_loops:
                                        break

                                    # Re-check whether another loop is still worthwhile
                                    should_reflect = (
                                        self.force_reflection
                                        or (section.confidence < 0.62 and (adaptive_gain > 0.002 or unique_ratio > 0.28))
                                        or unique_ratio > 0.50
                                    )

                                pre_denoise_sources = len(section.sources)
                                if len(section.sources) >= 7 and (
                                    cross_query_consensus < 0.58
                                    or evidence_consistency < 0.66
                                    or rel_disp > 0.20
                                ):
                                    section.sources = self._denoise_and_rerank_sources(
                                        section.sources,
                                        query=query,
                                        section_title=section.section_title,
                                        retrieval_budget=retrieval_budget,
                                    )
                                    denoise_applied = len(section.sources) < pre_denoise_sources

                                post_reflection_consistency = self._estimate_sources_consistency(
                                    section.sources,
                                    query=query,
                                    section_title=section.section_title,
                                )
                                if denoise_applied:
                                    section.confidence = min(
                                        0.95,
                                        max(
                                            0.05,
                                            section.confidence
                                            + (0.02 + 0.015 * self.reflection_sensitivity)
                                            * max(0.0, post_reflection_consistency - 0.60),
                                        ),
                                    )
                                    section.uncertainty = max(0.05, 1 - section.confidence)
                            else:
                                denoise_applied = False
                                post_reflection_consistency = self._estimate_sources_consistency(
                                    section.sources,
                                    query=query,
                                    section_title=section.section_title,
                                )

                            metric = {
                                "section_id": section.section_id,
                                "section_title": section.section_title,
                                "confidence": round(section.confidence, 4),
                                "uncertainty": round(section.uncertainty, 4),
                                "sources_count": len(section.sources),
                                "reflection_count": section.reflection_count,
                                "reflection_sensitivity": self.reflection_sensitivity,
                                "denoise_applied": denoise_applied,
                                "post_reflection_consistency": round(post_reflection_consistency, 4),
                                "retrieval_budget": retrieval_budget,
                                "retrieval_metrics": retrieval_metrics,
                            }
                            return section, metric

                    processed_results = await asyncio.gather(*(process_section(section) for section in sections))
                    sections = [sec for sec, _ in processed_results]
                    section_metrics = [m for _, m in processed_results]
                    
                    # Step 6: Global uncertainty
                    logger.info("Step 6: Calculating uncertainty...")
                    uncertainty_agent = GlobalUncertaintyAgent(deepseek_client)
                    uncertainty_response = await uncertainty_agent.execute(
                        task_id=self.task_id,
                        sections=sections
                    )
                    global_uncertainty = uncertainty_response.output.get("global_uncertainty", 0.5)
                    
                    # Step 7: Format report
                    logger.info("Step 7: Formatting report...")
                    formatter_agent = FinalFormatterAgent(deepseek_client)
                    format_response = await formatter_agent.execute(
                        task_id=self.task_id,
                        title=structure_data.get("title", query),
                        sections=sections,
                        global_uncertainty=global_uncertainty
                    )
                    
                    # Final result
                    final_result = {
                        "task_id": self.task_id,
                        "query": query,
                        "timestamp": datetime.now().isoformat(),
                        "title": structure_data.get("title", query),
                        "report_markdown": format_response.output.get("report_markdown", ""),
                        "global_uncertainty": global_uncertainty,
                        "average_confidence": uncertainty_response.output.get("average_confidence", 0.0),
                        "uncertainty_analysis": {
                            "section_uncertainties": uncertainty_response.output.get("section_uncertainties", {}),
                            "recommendation": uncertainty_response.output.get("recommendation", "proceed"),
                            "reasoning": uncertainty_response.output.get("reasoning", "")
                        },
                        "section_metrics": section_metrics,
                        "sections_count": len(sections),
                        "status": "completed"
                    }
                    
                    # Save final result only
                    final_path = self.results_dir / f"{self.task_id}_final.json"
                    with open(final_path, "w", encoding="utf-8") as f:
                        json.dump(final_result, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"✓ Workflow completed | File: {final_path}")
                    
                    return final_result
        
        except Exception as e:
            logger.error(f"Error: {e}")
            raise


MARDSv2FastController = MARDSControllerFast
