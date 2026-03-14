import uuid
from typing import List
from urllib.parse import urlparse
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, RetrievalItem, RetrievalPayload, SystemState
from agents.base_agent import BaseAgent
from utils.tavily_client import TavilyClient


class RetrieverAgent(BaseAgent):
    def __init__(self, client: TavilyClient):
        super().__init__(role="retriever", prompt_name="retriever", client=None, temperature=0.2)
        self.tavily = client

    async def run(self, state: SystemState, query: str) -> AgentOutput:
        results = await self.tavily.search(query, max_results=8)
        items = self._normalize_results(results)
        items = self._enforce_domain_diversity(items, min_count=5)
        diversity_score = self._diversity_score(items)

        payload = RetrievalPayload(query=query, results=items, diversity_score=diversity_score)
        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=min(1.0, 0.5 + diversity_score / 2),
            uncertainty_score=max(0.0, 1 - diversity_score),
            needs_iteration=len(items) < 5,
        )

    def _normalize_results(self, results: List[dict]) -> List[RetrievalItem]:
        normalized = []
        for r in results:
            url = r.get("url", "")
            domain = self._domain(url)
            source_type = self._source_type(domain)
            normalized.append(
                RetrievalItem(
                    title=r.get("title", ""),
                    url=url,
                    domain=domain,
                    source_type=source_type,
                    snippet=r.get("content", "") or r.get("snippet", ""),
                    score=min(1.0, max(0.0, r.get("score", 0.5))),
                )
            )
        return normalized

    def _enforce_domain_diversity(self, items: List[RetrievalItem], min_count: int) -> List[RetrievalItem]:
        seen = set()
        diverse = []
        for item in items:
            if item.domain not in seen:
                diverse.append(item)
                seen.add(item.domain)
            if len(diverse) >= min_count:
                break
        return diverse

    def _diversity_score(self, items: List[RetrievalItem]) -> float:
        if not items:
            return 0.0
        tlds = {self._tld(item.domain) for item in items}
        types = {item.source_type for item in items}
        return min(1.0, 0.5 * (len(tlds) / len(items)) + 0.5 * (len(types) / len(items)))

    def _domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    def _tld(self, domain: str) -> str:
        parts = domain.split(".")
        return parts[-1] if parts else ""

    def _source_type(self, domain: str) -> str:
        if domain.endswith(".edu") or ".ac." in domain:
            return "academic"
        if domain.endswith(".gov"):
            return "government"
        if "news" in domain or domain.endswith(".news"):
            return "news"
        if domain.endswith(".org"):
            return "nonprofit"
        return "corporate"
