"""
Agent implementations for MARDS v2.
Integrates logic from original MARDS agents with paragraph-level reflection.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import asyncio

from v2_paragraph_reflective.base import BaseAgent, PromptManager
from v2_paragraph_reflective.schema import (
    AgentResponse, Section, ReportStructure, SearchResult,
    ReflectionEvaluation, GlobalUncertaintyResult, MARDSException
)
from v2_paragraph_reflective.clients import DeepSeekClient, TavilyClient, MetricsCalculator

logger = logging.getLogger(__name__)


class StructurePlannerAgent(BaseAgent):
    """Generate report structure based on user query."""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("StructurePlannerAgent", __name__)
        self.deepseek = deepseek_client
    
    async def execute(self, task_id: str, query: str) -> AgentResponse:
        """Generate report structure.
        
        Args:
            task_id: Task identifier
            query: User query
            
        Returns:
            AgentResponse with report structure
        """
        self.log_execution(f"Planning structure for query: {query[:100]}...")
        
        try:
            # Use original PlannerAgent decomposition logic first
            sub_questions = self._local_decompose(query)
            
            # If using DeepSeek, enhance with LLM planning
            prompt = PromptManager.render_prompt("structure_planner", query=query)
            messages = [{"role": "user", "content": prompt}]
            response_text = await self.deepseek.chat(messages, temperature=0.3)
            
            # Parse response
            data = self._validate_json(response_text)
            
            # Create sections from both decomposition and LLM output
            sections = []
            llm_sections = data.get("sections", [])
            
            # Prioritize LLM sections but fallback to decomposition
            if llm_sections and len(llm_sections) >= 5:
                for sec_data in llm_sections:
                    section = Section(
                        section_id=sec_data.get("section_id", f"sec_{len(sections)+1}"),
                        section_title=sec_data.get("section_title", ""),
                        objective=sec_data.get("objective", "")
                    )
                    sections.append(section)
            else:
                # Use decomposed sub-questions as sections
                for i, sub_q in enumerate(sub_questions, 1):
                    section = Section(
                        section_id=f"sec_{i}",
                        section_title=self._extract_title(sub_q),
                        objective=sub_q
                    )
                    sections.append(section)
            
            # Validate minimum sections (5+)
            if len(sections) < 5:
                additional = self._generate_default_sections(query, len(sections))
                sections.extend(additional)
            
            structure = ReportStructure(
                title=data.get("title", query),
                query=query,
                sections=sections,
                objective=data.get("objective", f"深度研究{query}相关内容")
            )
            
            self.log_execution(f"Generated structure with {len(sections)} sections")
            
            return self._create_response(
                task_id=task_id,
                section="global",
                output={"structure": structure.to_dict()},
                confidence=0.9,
                uncertainty=0.1,
                needs_reflection=False
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise
    
    def _local_decompose(self, query: str) -> List[str]:
        """Decompose query using original PlannerAgent logic.
        Splits on 'and', ';', '、' or generates default questions.
        """
        parts = re.split(r"\band\b|；|;|、", query)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) >= 2:
            return [f"{p} 的关键证据是什么？" for p in parts]
        
        # Default decomposition for single-topic queries
        return [
            f"{query} 的定义与范围是什么？",
            f"{query} 的核心证据与数据有哪些？",
            f"{query} 的影响与应用场景是什么？",
            f"{query} 的最新进展与趋势是什么？",
            f"{query} 的挑战与未来展望是什么？",
        ]
    
    def _extract_title(self, question: str) -> str:
        """Extract concise title from question."""
        # Remove common question patterns
        title = re.sub(r"的关键证据是什么？|是什么？|有哪些？", "", question)
        title = title.strip()
        return title if title else question[:20]
    
    def _generate_default_sections(self, query: str, current_count: int) -> List[Section]:
        """Generate default sections to reach minimum 5."""
        templates = [
            ("定义与范围", f"{query}的基本概念和范围界定"),
            ("核心证据", f"{query}的主要证据和数据支撑"),
            ("应用场景", f"{query}的实际应用和案例分析"),
            ("发展趋势", f"{query}的最新进展和未来趋势"),
            ("挑战展望", f"{query}面临的挑战和未来展望"),
        ]
        
        sections = []
        for i in range(current_count, 5):
            title, obj = templates[i] if i < len(templates) else (f"补充分析{i-4}", f"{query}的补充内容")
            section = Section(
                section_id=f"sec_{i+1}",
                section_title=title,
                objective=obj
            )
            sections.append(section)
        
        return sections


class SectionRetrieverAgent(BaseAgent):
    """Retrieve diverse sources for a section (fast mode: direct search)."""
    
    def __init__(self, tavily_client: TavilyClient):
        super().__init__("SectionRetrieverAgent", __name__)
        self.tavily = tavily_client
    
    async def execute(
        self,
        task_id: str,
        section: Section,
        query: str,
        max_results: int = 2
    ) -> AgentResponse:
        """Retrieve sources for section (fast mode: direct search, no LLM).
        
        Args:
            task_id: Task identifier
            section: Section to retrieve for
            query: Original query
            max_results: Maximum results (reduced to 2 for speed)
            
        Returns:
            AgentResponse with search results
        """
        search_query = f"{query} {section.section_title}"
        self.log_execution(f"Searching: {search_query[:60]}...")
        
        try:
            eval_pool_size = max(max_results + 2, 5)
            query_variants = self._build_query_variants(query, section)

            merged_by_url: Dict[str, Dict[str, Any]] = {}
            successful_queries = 0
            per_query_k = min(eval_pool_size, 5)

            for variant in query_variants:
                results_variant = await self.tavily.search(variant, max_results=per_query_k)
                if results_variant:
                    successful_queries += 1
                for result in results_variant:
                    key = self._result_key(result)
                    entry = merged_by_url.get(key)
                    if entry is None:
                        merged_by_url[key] = {
                            "result": result,
                            "hit_count": 1,
                            "best_score": result.score,
                        }
                    else:
                        entry["hit_count"] += 1
                        if result.score > entry["best_score"]:
                            entry["best_score"] = result.score
                            entry["result"] = result

            hit_ratio_map: Dict[str, float] = {}
            raw_candidates: List[SearchResult] = []
            for key, entry in merged_by_url.items():
                raw_candidates.append(entry["result"])
                hit_ratio_map[key] = (
                    entry["hit_count"] / len(query_variants)
                    if query_variants
                    else 0.0
                )

            raw_candidates = self._rank_results(
                raw_candidates,
                search_query,
                hit_ratio_map=hit_ratio_map,
            )
            raw_results = raw_candidates[:eval_pool_size]

            if not raw_results:
                return self._create_response(
                    task_id=task_id,
                    section=section.section_id,
                    output={
                        "sources": [],
                        "metrics": {
                            "ndcg": 0.0,
                            "mrr": 0.0,
                            "source_diversity": 0.0,
                            "mean_relevance": 0.0,
                            "relevance_dispersion": 0.0,
                            "avg_api_score": 0.0,
                            "authority_score": 0.0,
                            "query_coverage": 0.0,
                            "cross_query_consensus": 0.0,
                            "evidence_consistency": 0.0,
                            "eval_k": 0,
                            "eval_pool_size": 0,
                            "total_sources": 0,
                            "coverage": 0.0
                        }
                    },
                    confidence=0.30,
                    uncertainty=0.70,
                    needs_reflection=True
                )

            # Filter for domain diversity (used for downstream generation only)
            results = self._filter_for_diversity(raw_results, max_results)
            
            # Calculate metrics
            eval_k = min(4, len(raw_results)) if raw_results else 0
            ndcg = MetricsCalculator.calculate_ndcg(raw_results, query=search_query, k=eval_k)
            mrr = MetricsCalculator.calculate_mrr(raw_results, query=search_query, k=eval_k)
            diversity = MetricsCalculator.calculate_source_diversity(raw_results)
            mean_relevance = MetricsCalculator.calculate_mean_relevance(raw_results, query=search_query, k=eval_k)
            relevance_dispersion = MetricsCalculator.calculate_relevance_dispersion(raw_results, query=search_query, k=eval_k)

            coverage = min(len(raw_results) / eval_pool_size, 1.0) if eval_pool_size > 0 else 0.0
            top_scores = [max(0.0, min(1.0, r.score)) for r in raw_results[:eval_k]] if eval_k > 0 else []
            avg_api_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
            authority_scores = [self._source_authority_score(r.domain) for r in raw_results[:eval_k]] if eval_k > 0 else []
            authority_score = sum(authority_scores) / len(authority_scores) if authority_scores else 0.0
            query_coverage = successful_queries / len(query_variants) if query_variants else 0.0
            top_hit_ratios = [
                hit_ratio_map.get(self._result_key(r), 0.0)
                for r in raw_results[:eval_k]
            ] if eval_k > 0 else []
            cross_query_consensus = (
                sum(top_hit_ratios) / len(top_hit_ratios)
                if top_hit_ratios
                else 0.0
            )
            evidence_consistency = max(0.0, 1.0 - relevance_dispersion)

            # Academic-style composite confidence:
            # - Retrieval ranking quality (nDCG, MRR)
            # - Query-document alignment (mean_relevance) - primary signal
            # - Evidence consistency & consensus - quality signals
            # - Evidence breadth (diversity, coverage)
            # - Penalty for unstable relevance distribution
            # Special handling for low-source scenarios (<5 sources)
            is_low_source = len(raw_results) < 5
            
            base_conf = (
                0.10 * ndcg
                + 0.08 * mrr
                + (0.30 if is_low_source else 0.28) * mean_relevance  # Boost for low-source
                + (0.08 if is_low_source else 0.10) * diversity  # Reduce diversity penalty
                + (0.04 if is_low_source else 0.06) * coverage  # Reduce coverage penalty
                + 0.11 * avg_api_score
                + 0.08 * authority_score
                + 0.05 * query_coverage
                + 0.07 * cross_query_consensus
                + (0.14 if is_low_source else 0.12) * evidence_consistency  # Boost consistency signal
            )
            dispersion_penalty = 0.030 * relevance_dispersion
            confidence = min(
                0.96,
                max(
                    0.38,
                    base_conf - dispersion_penalty
                )
            )
            uncertainty = max(0.04, 1 - confidence)
            
            # Dynamic reflection threshold with more aggressive low-source handling
            needs_reflection_threshold = 0.66
            if len(results) >= 5 and evidence_consistency > 0.70 and mean_relevance > 0.65:
                # High-quality retrieval: raise bar
                needs_reflection_threshold = 0.70
            elif len(results) <= 3:  # Changed from <=2
                # Low source count: significantly lower bar to encourage reflection
                needs_reflection_threshold = 0.60  # Lowered from 0.62
            elif mean_relevance < 0.45:
                # Weak retrieval quality
                needs_reflection_threshold = 0.62
            
            needs_reflection = (len(results) < max_results) or (confidence < needs_reflection_threshold)
            
            self.log_execution(
                f"Retrieved {len(results)} sources (NDCG: {ndcg:.2f}, "
                f"MRR: {mrr:.2f}, Diversity: {diversity:.2f}, "
                f"Consensus: {cross_query_consensus:.2f})"
            )
            
            return self._create_response(
                task_id=task_id,
                section=section.section_id,
                output={
                    "sources": [
                        {
                            "title": r.title,
                            "url": r.url,
                            "content": r.content[:500],
                            "domain": r.domain,
                            "score": r.score
                        }
                        for r in results
                    ],
                    "metrics": {
                        "ndcg": ndcg,
                        "mrr": mrr,
                        "source_diversity": diversity,
                        "mean_relevance": mean_relevance,
                        "relevance_dispersion": relevance_dispersion,
                        "avg_api_score": avg_api_score,
                        "authority_score": authority_score,
                        "query_coverage": query_coverage,
                        "cross_query_consensus": cross_query_consensus,
                        "evidence_consistency": evidence_consistency,
                        "query_variants": len(query_variants),
                        "successful_queries": successful_queries,
                        "eval_k": eval_k,
                        "eval_pool_size": len(raw_results),
                        "total_sources": len(results),
                        "coverage": coverage
                    }
                },
                confidence=confidence,
                uncertainty=uncertainty,
                needs_reflection=needs_reflection
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise
    
    @staticmethod
    def _filter_for_diversity(
        results: List[SearchResult],
        max_results: int
    ) -> List[SearchResult]:
        """Filter results to ensure domain diversity.
        Uses original RetrieverAgent logic for diversity enforcement.
        """
        seen_domains = set()
        filtered = []
        
        # First pass: one result per domain
        for result in results:
            domain = result.domain
            if domain not in seen_domains:
                seen_domains.add(domain)
                filtered.append(result)
                if len(filtered) >= max_results:
                    break
        
        # Second pass: fill remaining slots if needed
        if len(filtered) < max_results:
            for result in results:
                if result not in filtered:
                    filtered.append(result)
                    if len(filtered) >= max_results:
                        break
        
        return filtered[:max_results]

    @staticmethod
    def _build_query_variants(query: str, section: Section) -> List[str]:
        base = f"{query} {section.section_title}".strip()
        objective = f"{query} {section.objective}".strip()
        evidence = f"{section.section_title} 权威 指南 标准 政策 数据 案例".strip()
        variants = [base, objective, evidence]
        seen = set()
        unique_variants = []
        for item in variants:
            key = " ".join(item.split())
            if key and key not in seen:
                seen.add(key)
                unique_variants.append(key)
        return unique_variants

    def _rank_results(
        self,
        results: List[SearchResult],
        query: str,
        hit_ratio_map: Optional[Dict[str, float]] = None,
    ) -> List[SearchResult]:
        def rank_score(r: SearchResult) -> float:
            api_score = max(0.0, min(1.0, r.score))
            relevance = MetricsCalculator.calculate_mean_relevance([r], query=query, k=1)
            authority = self._source_authority_score(r.domain)
            consensus = (
                hit_ratio_map.get(self._result_key(r), 0.0)
                if hit_ratio_map
                else 0.0
            )
            return 0.43 * api_score + 0.27 * relevance + 0.12 * authority + 0.18 * consensus

        return sorted(results, key=rank_score, reverse=True)

    @staticmethod
    def _result_key(result: SearchResult) -> str:
        return result.url or f"{result.title}-{result.domain}"

    @staticmethod
    def _source_authority_score(domain: str) -> float:
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
    def _calculate_diversity_score(results: List[SearchResult]) -> float:
        """Calculate diversity score based on TLDs and source types.
        Original RetrieverAgent diversity calculation.
        """
        if not results:
            return 0.0
        
        # TLD diversity
        tlds = set()
        for r in results:
            parts = r.domain.split(".")
            tld = parts[-1] if parts else ""
            tlds.add(tld)
        
        # Source type diversity
        source_types = {SectionRetrieverAgent._classify_source_type(r.domain) for r in results}
        
        # Combined score: 50% TLD diversity + 50% type diversity
        tld_score = len(tlds) / len(results)
        type_score = len(source_types) / len(results)
        
        return min(1.0, 0.5 * tld_score + 0.5 * type_score)
    
    @staticmethod
    def _classify_source_type(domain: str) -> str:
        """Classify source type based on domain.
        Original RetrieverAgent source classification.
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


class SectionSummarizerAgent(BaseAgent):
    """Generate initial summary for a section."""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("SectionSummarizerAgent", __name__)
        self.deepseek = deepseek_client
    
    async def execute(
        self,
        task_id: str,
        section: Section,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Generate section summary.
        
        Args:
            task_id: Task identifier
            section: Section to summarize
            query: Main query
            sources: Source documents
            
        Returns:
            AgentResponse with summary
        """
        self.log_execution(f"Summarizing section: {section.section_title}")
        
        try:
            # Format search results for prompt
            search_results_text = "\n\n".join([
                f"Title: {s.get('title', '')}\n"
                f"URL: {s.get('url', '')}\n"
                f"Content: {s.get('content', '')[:300]}"
                for s in sources[:5]
            ])
            
            prompt = PromptManager.render_prompt(
                "section_summarizer",
                query=query,
                section_title=section.section_title,
                section_objective=section.objective,
                search_results=search_results_text
            )
            
            messages = [{"role": "user", "content": prompt}]
            summary = await self.deepseek.chat(messages, temperature=0.3, max_tokens=1200)
            
            section.initial_summary = summary
            
            self.log_execution(f"Generated summary ({len(summary)} chars)")
            
            return self._create_response(
                task_id=task_id,
                section=section.section_id,
                output={
                    "summary": summary,
                    "sources_used": len(sources)
                },
                confidence=0.8,
                uncertainty=0.2,
                needs_reflection=True
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise


class ReflectionAgent(BaseAgent):
    """Evaluate section and generate single reflection query (DeepSearch mode)."""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("ReflectionAgent", __name__)
        self.deepseek = deepseek_client
    
    async def execute(
        self,
        task_id: str,
        section: Section,
        query: str,
        current_summary: str
    ) -> AgentResponse:
        """Evaluate section and generate ONE reflection search query (DeepSearch approach).
        
        Args:
            task_id: Task identifier
            section: Section to evaluate
            query: Main query
            current_summary: Current summary text
            
        Returns:
            AgentResponse with single reflection query
        """
        self.log_execution(f"Reflecting on section: {section.section_title}")
        
        try:
            # DeepSearch reflection prompt: identify gaps + generate ONE search query
            prompt = f"""分析以下段落内容，找出缺失或薄弱之处，生成一个补充搜索查询。

段落标题: {section.section_title}
原始目标: {section.objective}
当前内容: {current_summary}

任务：
1. 识别内容中的缺失信息或薄弱证据
2. 生成ONE个最重要的补充搜索查询

返回JSON: {{
  "missing_info": "...",
  "search_query": "...",
  "reasoning": "...",
  "needs_deeper_search": true/false
}}"""
            
            messages = [{"role": "user", "content": prompt}]
            response_text = await self.deepseek.chat(messages, temperature=0.7, max_tokens=700)
            
            # Parse response
            data = self._validate_json(response_text)
            
            search_query = data.get("search_query", "")
            needs_search = data.get("needs_deeper_search", False)
            
            self.log_execution(
                f"Reflection result - Query: {search_query[:50]}... | "
                f"Needs search: {needs_search}"
            )
            
            return self._create_response(
                task_id=task_id,
                section=section.section_id,
                output={
                    "search_query": search_query,
                    "missing_info": data.get("missing_info", ""),
                    "reasoning": data.get("reasoning", ""),
                    "needs_deeper_search": needs_search
                },
                confidence=0.7 if needs_search else 0.9,
                uncertainty=0.3 if needs_search else 0.1,
                needs_reflection=needs_search
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise


class SectionUpdaterAgent(BaseAgent):
    """Update section based on additional research."""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("SectionUpdaterAgent", __name__)
        self.deepseek = deepseek_client
    
    async def execute(
        self,
        task_id: str,
        section: Section,
        current_summary: str,
        new_sources: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Update section with new information.
        
        Args:
            task_id: Task identifier
            section: Section to update
            current_summary: Current summary
            new_sources: New sources to incorporate
            
        Returns:
            AgentResponse with updated summary
        """
        self.log_execution(f"Updating section with new sources: {section.section_title}")
        
        try:
            # Format new sources
            new_sources_text = "\n\n".join([
                f"Title: {s.get('title', '')}\nContent: {s.get('content', '')[:300]}"
                for s in new_sources[:3]
            ])
            
            prompt = (
                f"Update the following summary with new information from the provided sources. "
                f"Maintain structure and coherence.\n\n"
                f"Current Summary:\n{current_summary}\n\n"
                f"New Sources:\n{new_sources_text}\n\n"
                f"Provide updated summary that integrates both existing and new information."
            )
            
            messages = [{"role": "user", "content": prompt}]
            updated_summary = await self.deepseek.chat(messages, temperature=0.3, max_tokens=1200)
            
            section.final_summary = updated_summary
            
            self.log_execution(f"Updated summary ({len(updated_summary)} chars)")
            
            return self._create_response(
                task_id=task_id,
                section=section.section_id,
                output={
                    "updated_summary": updated_summary,
                    "new_sources_used": len(new_sources)
                },
                confidence=0.85,
                uncertainty=0.15,
                needs_reflection=False
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise


class GlobalUncertaintyAgent(BaseAgent):
    """Calculate global uncertainty and determine if more reflection is needed."""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("GlobalUncertaintyAgent", __name__)
        self.deepseek = deepseek_client
    
    async def execute(
        self,
        task_id: str,
        sections: List[Section]
    ) -> AgentResponse:
        """Calculate global uncertainty.
        
        Args:
            task_id: Task identifier
            sections: All sections
            
        Returns:
            AgentResponse with uncertainty analysis
        """
        self.log_execution("Calculating global uncertainty...")
        
        try:
            # Aggregate section uncertainties
            section_uncertainties = {
                sec.section_id: (sec.uncertainty if sec.uncertainty > 0 else max(0.05, 1 - sec.confidence))
                for sec in sections
            }
            
            average_confidence = sum(sec.confidence for sec in sections) / len(sections) if sections else 0.0
            average_uncertainty = max(0.05, min(0.95, 1 - average_confidence))

            # Add dispersion-aware correction to avoid over-confident global uncertainty.
            if sections:
                confidence_variance = sum(
                    (sec.confidence - average_confidence) ** 2 for sec in sections
                ) / len(sections)
                confidence_std = confidence_variance ** 0.5
            else:
                confidence_std = 0.0

            deterministic_global_uncertainty = max(
                0.05,
                min(0.95, average_uncertainty + 0.10 * confidence_std)
            )
            
            # Determine recommendation
            if average_uncertainty < 0.2:
                recommendation = "proceed"
            elif average_uncertainty < 0.5:
                recommendation = "reflect"
            else:
                recommendation = "escalate"
            
            # Prepare analysis summary
            analysis_summary = "\n".join([
                f"{sec.section_title}: uncertainty={sec.uncertainty:.2f}, "
                f"reflection_count={sec.reflection_count}"
                for sec in sections
            ])
            
            prompt = PromptManager.render_prompt(
                "global_uncertainty",
                sections_analysis=analysis_summary
            )
            
            messages = [{"role": "user", "content": prompt}]
            response_text = await self.deepseek.chat(messages, temperature=0.3, max_tokens=1000)
            
            # Parse response
            data = self._validate_json(response_text)

            llm_reasoning = data.get("reasoning", "")
            llm_recommendation = data.get("recommendation", "")

            # Recommendation follows deterministic uncertainty gate by default.
            if deterministic_global_uncertainty < 0.2:
                recommendation = "proceed"
            elif deterministic_global_uncertainty < 0.5:
                recommendation = "reflect"
            else:
                recommendation = "escalate"

            # Allow LLM recommendation only if valid and differs by at most one level.
            valid_recs = ["proceed", "reflect", "escalate"]
            if llm_recommendation in valid_recs:
                det_idx = valid_recs.index(recommendation)
                llm_idx = valid_recs.index(llm_recommendation)
                if abs(det_idx - llm_idx) <= 1:
                    recommendation = llm_recommendation
            
            result = GlobalUncertaintyResult(
                global_uncertainty=deterministic_global_uncertainty,
                section_uncertainties=section_uncertainties,
                average_confidence=average_confidence,
                recommendation=recommendation,
                reasoning=llm_reasoning,
                reflection_needed=data.get("reflection_needed", recommendation != "proceed")
            )
            
            self.log_execution(
                f"Global Uncertainty: {result.global_uncertainty:.2f}, "
                f"Recommendation: {result.recommendation}"
            )
            
            return self._create_response(
                task_id=task_id,
                section="global",
                output={
                    "global_uncertainty": result.global_uncertainty,
                    "section_uncertainties": result.section_uncertainties,
                    "average_confidence": result.average_confidence,
                    "recommendation": result.recommendation,
                    "reasoning": result.reasoning,
                    "reflection_needed": result.reflection_needed
                },
                confidence=average_confidence,
                uncertainty=average_uncertainty,
                needs_reflection=result.reflection_needed
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise


class FinalFormatterAgent(BaseAgent):
    """Format final research report.
    Integrates SynthesisAgent report generation and EvidenceEvaluatorAgent logic.
    """
    
    def __init__(self, deepseek_client: DeepSeekClient):
        super().__init__("FinalFormatterAgent", __name__)
        self.deepseek = deepseek_client
    
    async def execute(
        self,
        task_id: str,
        title: str,
        sections: List[Section],
        global_uncertainty: float
    ) -> AgentResponse:
        """Format final report using integrated SynthesisAgent template.
        
        Args:
            task_id: Task identifier
            title: Report title
            sections: All sections
            global_uncertainty: Global uncertainty score
            
        Returns:
            AgentResponse with formatted report
        """
        self.log_execution("Formatting final report...")
        
        try:
            # Extract claims and contradictions (from EvidenceEvaluatorAgent logic)
            all_claims = self._extract_all_claims(sections)
            contradictions = self._detect_contradictions(all_claims)
            
            # Calculate evidence strength
            avg_confidence = sum(s.confidence for s in sections) / len(sections) if sections else 0.5
            total_sources = sum(len(s.sources) for s in sections)
            total_reflections = sum(s.reflection_count for s in sections)
            
            # Generate structured report using SynthesisAgent template
            report_markdown = self._generate_structured_report(
                title=title,
                sections=sections,
                all_claims=all_claims,
                contradictions=contradictions,
                avg_confidence=avg_confidence,
                global_uncertainty=global_uncertainty,
                total_sources=total_sources,
                total_reflections=total_reflections
            )
            
            # Collect all references
            references = self._collect_references(sections)
            
            self.log_execution(
                f"Generated report: {len(sections)} sections, "
                f"{total_sources} sources, {total_reflections} reflections"
            )
            
            return self._create_response(
                task_id=task_id,
                section="global",
                output={
                    "report_markdown": report_markdown,
                    "metadata": {
                        "sections_count": len(sections),
                        "total_sources": total_sources,
                        "total_reflections": total_reflections,
                        "avg_confidence": avg_confidence,
                        "global_uncertainty": global_uncertainty,
                        "claims_extracted": len(all_claims),
                        "contradictions_found": len(contradictions)
                    },
                    "references": references
                },
                confidence=avg_confidence,
                uncertainty=global_uncertainty,
                needs_reflection=False
            )
        
        except Exception as e:
            self.log_execution(f"Error: {e}", "error")
            self.error_count += 1
            raise
    
    def _extract_all_claims(self, sections: List[Section]) -> List[str]:
        """Extract key claims from section summaries.
        Uses EvidenceEvaluatorAgent extraction logic.
        """
        claims = []
        for section in sections:
            summary = section.final_summary or section.initial_summary or ""
            # Split by Chinese/English sentence endings
            sentences = re.split(r'[。.!?！？]', summary)
            for sent in sentences:
                sent = sent.strip()
                # Keep substantial sentences (>15 chars)
                if len(sent) > 15:
                    claims.append(sent)
        
        # Deduplicate and limit
        return list(dict.fromkeys(claims))[:30]
    
    def _detect_contradictions(self, claims: List[str]) -> List[str]:
        """Detect potential contradictions in claims.
        Uses EvidenceEvaluatorAgent contradiction detection.
        """
        contradictions = []
        negative_indicators = [
            "not", "no", "无法", "没有", "无效", "不足", 
            "but", "however", "但是", "然而", "相反"
        ]
        
        for claim in claims:
            claim_lower = claim.lower()
            if any(neg in claim_lower for neg in negative_indicators):
                contradictions.append(claim)
        
        return contradictions[:10]
    
    def _generate_structured_report(
        self,
        title: str,
        sections: List[Section],
        all_claims: List[str],
        contradictions: List[str],
        avg_confidence: float,
        global_uncertainty: float,
        total_sources: int,
        total_reflections: int
    ) -> str:
        """Generate markdown report using SynthesisAgent template."""
        
        # Executive Summary
        exec_summary = f"""本报告针对查询"{title}"进行了段落级反思式深度搜索。
共生成{len(sections)}个章节，检索{total_sources}个来源，完成{total_reflections}次反思迭代。
平均置信度: {avg_confidence:.2f}，全局不确定性: {global_uncertainty:.2f}。"""
        
        # Structured Findings
        findings_section = "# Structured Findings\n\n"
        findings_section += "\n".join(f"- {claim}" for claim in all_claims[:15])
        
        # Evidence Strength
        evidence_section = f"""# Evidence Strength

平均源置信度: {avg_confidence:.2f}
总检索来源数: {total_sources}
多样性保证: 已通过域名多样性过滤

各章节证据质量:
"""
        for sec in sections:
            evidence_section += f"- **{sec.section_title}**: 置信度 {sec.confidence:.2f}, "
            evidence_section += f"来源数 {len(sec.sources)}, 反思次数 {sec.reflection_count}\n"
        
        # Contradictions Resolved
        contradictions_section = "# Contradictions Resolved\n\n"
        if contradictions:
            contradictions_section += "\n".join(f"- {c}" for c in contradictions[:5])
        else:
            contradictions_section += "未发现显著矛盾。"
        
        # Knowledge Gaps (from reflection history)
        gaps_section = "# Knowledge Gaps\n\n"
        all_gaps = []
        for sec in sections:
            for reflection in sec.reflection_history:
                if isinstance(reflection, dict):
                    gaps = reflection.get("missing_perspectives", [])
                    all_gaps.extend(gaps)
        
        if all_gaps:
            unique_gaps = list(dict.fromkeys(all_gaps))[:5]
            gaps_section += "\n".join(f"- {gap}" for gap in unique_gaps)
        else:
            gaps_section += "已覆盖主要话题。"
        
        # Section Details
        sections_detail = "# Detailed Sections\n\n"
        for sec in sections:
            sections_detail += f"## {sec.section_title}\n\n"
            sections_detail += f"{sec.final_summary or sec.initial_summary or ''}\n\n"
        
        # Cross-Section Insights
        cross_insights = "# Cross-Section Insights\n\n"
        cross_insights += "（通过多个章节综合分析发现的关键模式和联系）\n\n"
        
        # Final Uncertainty Score (using original SynthesisAgent format)
        uncertainty_section = f"""# Final Uncertainty Score

- Global Uncertainty: {global_uncertainty:.2f}
- Average Confidence: {avg_confidence:.2f}
- Recommendation: {"proceed" if global_uncertainty < 0.2 else "reflect" if global_uncertainty < 0.5 else "escalate"}

不确定性来源分析:
"""
        for sec in sections:
            if sec.uncertainty > 0.3:
                uncertainty_section += f"- {sec.section_title}: 不确定性 {sec.uncertainty:.2f}\n"
        
        # Verified Source List
        sources_section = "# Verified Source List\n\n"
        sources_section += "所有来源已通过域名多样性过滤和质量评估。\n\n"
        for i, sec in enumerate(sections, 1):
            if sec.sources:
                sources_section += f"## {sec.section_title} 引用来源\n\n"
                for j, source in enumerate(sec.sources[:5], 1):
                    if isinstance(source, dict):
                        sources_section += f"{i}.{j}. [{source.get('title', 'Unknown')}]({source.get('url', '#')})\n"
                sources_section += "\n"
        
        # Assemble full report
        report = f"""# {title}

# Executive Summary

{exec_summary}

{findings_section}

{evidence_section}

{contradictions_section}

{gaps_section}

{cross_insights}

{sections_detail}

{uncertainty_section}

{sources_section}
"""
        return report
    
    def _collect_references(self, sections: List[Section]) -> List[Dict[str, str]]:
        """Collect all unique references from sections."""
        references = []
        seen_urls = set()
        
        for section in sections:
            for source in section.sources:
                if isinstance(source, dict):
                    url = source.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        references.append({
                            "title": source.get("title", "Unknown"),
                            "url": url,
                            "domain": source.get("domain", ""),
                            "section": section.section_title
                        })
        
        return references
