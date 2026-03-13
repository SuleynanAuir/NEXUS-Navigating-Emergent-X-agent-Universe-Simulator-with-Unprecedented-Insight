from typing import Dict, List, Any
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from ..retrieval.search_tools import SearchTools
from .llm_client import LLMClient


class SearchAgent:
    def __init__(self) -> None:
        self.tools = SearchTools()
        self.llm = LLMClient()

    DOMAIN_PRIOR = {
        ".gov": 0.35,
        ".edu": 0.3,
        "arxiv.org": 0.3,
        "semanticscholar.org": 0.28,
        "nature.com": 0.28,
        "science.org": 0.26,
        "ieee.org": 0.26,
        "acm.org": 0.26,
    }

    def _expand_queries(self, claim_text: str, mode: str = "fast") -> List[str]:
        compact_claim = " ".join(claim_text.split())
        head_phrase = " ".join(compact_claim.split()[:10])

        queries = [compact_claim]
        if head_phrase and head_phrase != compact_claim:
            queries.append(f'"{head_phrase}"')
        queries.append(f"{claim_text} evidence")
        queries.append(f"{claim_text} benchmark OR study")

        if self.llm.enabled and mode == "deep":
            result = self.llm.json_call(
                "你是检索查询扩展助手。输出 JSON：{\"queries\":[...]}，仅输出JSON。",
                f"为下面陈述生成3条高相关检索查询，优先学术与权威来源：\n{claim_text}",
            )
            if result and isinstance(result.get("queries"), list):
                queries.extend(str(item) for item in result["queries"][:3])

        deduped = []
        for query in queries:
            query = query.strip()
            if query and query not in deduped:
                deduped.append(query)
        return deduped[:6 if mode == "deep" else 4]

    def _relevance_score(self, claim_text: str, item: dict, bucket: str) -> float:
        claim_tokens = [token for token in claim_text.lower().split() if token.strip()]
        title = str(item.get("title", "")).lower()
        snippet = str(item.get("snippet", "")).lower()
        text = f"{title} {snippet}"
        overlap = sum(1 for token in claim_tokens if token in text)
        lexical = overlap / max(1, len(claim_tokens))

        host = urlparse(str(item.get("url", ""))).netloc.lower()
        prior = 0.1
        for key, bonus in self.DOMAIN_PRIOR.items():
            if key in host or host.endswith(key):
                prior = max(prior, bonus)

        bucket_bonus = 0.2 if bucket == "trusted" else (0.16 if bucket == "scholar" else 0.08)
        return round(min(1.0, 0.62 * lexical + 0.25 * prior + bucket_bonus), 4)

    def _rank_and_diversify(self, claim_text: str, items: List[dict], cap: int, bucket: str) -> List[dict]:
        scored = []
        for item in items:
            ranked = dict(item)
            ranked["search_score"] = self._relevance_score(claim_text, item, bucket)
            scored.append(ranked)

        scored.sort(key=lambda item: item.get("search_score", 0.0), reverse=True)

        host_quota = 2 if bucket == "web" else 3
        host_counts: Dict[str, int] = {}
        output: List[dict] = []
        for item in scored:
            host = urlparse(str(item.get("url", ""))).netloc.lower() or "unknown"
            count = host_counts.get(host, 0)
            if count >= host_quota:
                continue
            host_counts[host] = count + 1
            output.append(item)
            if len(output) >= cap:
                break
        return output

    def run(self, claim_text: str, mode: str = "fast") -> Dict[str, Any]:
        queries = self._expand_queries(claim_text, mode=mode)

        web_results: List[dict] = []
        scholar_results: List[dict] = []
        trusted_results: List[dict] = []

        if mode == "deep":
            query_limit = 4
            web_n, scholar_n, trusted_n = 8, 6, 6
            web_cap, scholar_cap, trusted_cap = 24, 16, 16
        else:
            query_limit = 2
            web_n, scholar_n, trusted_n = 4, 3, 3
            web_cap, scholar_cap, trusted_cap = 10, 8, 8

        query_batch = queries[:query_limit]

        def _search_one(query: str) -> Dict[str, List[dict]]:
            return {
                "web": self.tools.web_search(query, web_n),
                "scholar": self.tools.scholar_search(query, scholar_n),
                "trusted": self.tools.trusted_kb_search(query, trusted_n),
            }

        max_workers = 4 if mode == "deep" else 2
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(_search_one, query_batch):
                web_results.extend(result.get("web", []))
                scholar_results.extend(result.get("scholar", []))
                trusted_results.extend(result.get("trusted", []))

        def dedupe(items: List[dict]) -> List[dict]:
            seen = set()
            output: List[dict] = []
            for item in items:
                url = item.get("url", "")
                key = url or f"{item.get('title','')}|{item.get('snippet','')}"
                if key in seen:
                    continue
                seen.add(key)
                output.append(item)
            return output

        web_deduped = dedupe(web_results)
        scholar_deduped = dedupe(scholar_results)
        trusted_deduped = dedupe(trusted_results)

        return {
            "web": self._rank_and_diversify(claim_text, web_deduped, web_cap, "web"),
            "scholar": self._rank_and_diversify(claim_text, scholar_deduped, scholar_cap, "scholar"),
            "trusted": self._rank_and_diversify(claim_text, trusted_deduped, trusted_cap, "trusted"),
            "queries": queries,
            "llm_enabled": self.llm.enabled and mode == "deep",
            "mode": mode,
        }
