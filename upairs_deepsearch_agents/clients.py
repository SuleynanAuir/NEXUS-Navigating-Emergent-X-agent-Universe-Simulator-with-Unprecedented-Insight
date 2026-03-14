"""
API clients for DeepSeek and Tavily services.
"""

import aiohttp
import asyncio
import json
import logging
import math
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import random
from collections import Counter

from v2_paragraph_reflective.schema import SearchResult, APIException

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Client for DeepSeek API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        """Initialize DeepSeek client.
        
        Args:
            api_key: DeepSeek API key
            base_url: API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.call_count = 0
        self.error_count = 0
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        model: str = "deepseek-chat"
    ) -> str:
        """Call DeepSeek chat API.
        
        Args:
            messages: List of messages
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            model: Model name
            
        Returns:
            Response text
        """
        if not self.session:
            raise APIException("Session not initialized. Use 'async with' context.")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        retries = 3
        for attempt in range(retries):
            try:
                self.call_count += 1
                async with self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status != 200:
                        error_data = await resp.text()
                        logger.error(f"DeepSeek API error: {error_data}")
                        if attempt < retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        self.error_count += 1
                        raise APIException(f"DeepSeek API error: {resp.status}")
                    
                    data = await resp.json()
                    response_text = data["choices"][0]["message"]["content"]
                    logger.debug(f"DeepSeek response: {len(response_text)} chars")
                    return response_text
            
            except asyncio.TimeoutError:
                logger.warning(f"DeepSeek timeout, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.error_count += 1
                    raise APIException("DeepSeek API timeout")
            except Exception as e:
                logger.error(f"DeepSeek error: {e}")
                self.error_count += 1
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise APIException(f"DeepSeek API error: {e}")


class TavilyClient:
    """Client for Tavily Search API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.tavily.com"):
        """Initialize Tavily client.
        
        Args:
            api_key: Tavily API key
            base_url: API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.call_count = 0
        self.error_count = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search(
        self,
        query: str,
        max_results: int = 8,
        include_answer: bool = True
    ) -> List[SearchResult]:
        """Search using Tavily API.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            include_answer: Include answer from Tavily
            
        Returns:
            List of SearchResult objects
        """
        if not self.session:
            raise APIException("Session not initialized. Use 'async with' context.")
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": True
        }
        
        retries = 4
        retryable_status = {429, 500, 502, 503, 504}
        for attempt in range(retries):
            try:
                self.call_count += 1
                async with self.session.post(
                    f"{self.base_url}/search",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        error_data = await resp.text()
                        logger.error(f"Tavily API error: {error_data}")
                        if resp.status in retryable_status and attempt < retries - 1:
                            wait_s = min(8, 1.5 ** attempt) + random.uniform(0.0, 0.8)
                            await asyncio.sleep(wait_s)
                            continue
                        self.error_count += 1
                        if resp.status in retryable_status:
                            logger.warning("Tavily hard failure after retries, fallback to empty results")
                            return []
                        raise APIException(f"Tavily API error: {resp.status}")
                    
                    data = await resp.json(content_type=None)
                    results = []
                    
                    for item in data.get("results", []):
                        domain = self._extract_domain(item.get("url", ""))
                        result = SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            content=item.get("content", ""),
                            domain=domain,
                            score=item.get("score", 0.0)
                        )
                        results.append(result)
                    
                    logger.debug(f"Tavily search returned {len(results)} results")
                    if not results and attempt < retries - 1:
                        wait_s = min(8, 1.5 ** attempt) + random.uniform(0.0, 0.8)
                        await asyncio.sleep(wait_s)
                        continue
                    return results
            
            except asyncio.TimeoutError:
                wait_s = min(8, 1.5 ** attempt) + random.uniform(0.0, 0.8)
                logger.warning(f"Tavily timeout, attempt {attempt + 1}/{retries}, waiting {wait_s:.1f}s...")
                if attempt < retries - 1:
                    await asyncio.sleep(wait_s)
                else:
                    self.error_count += 1
                    logger.warning("Tavily timeout after retries, fallback to empty results")
                    return []
            except aiohttp.ClientError as e:
                logger.error(f"Tavily error: {e}")
                self.error_count += 1
                if attempt < retries - 1:
                    wait_s = min(8, 1.5 ** attempt) + random.uniform(0.0, 0.8)
                    await asyncio.sleep(wait_s)
                else:
                    logger.warning("Tavily client error after retries, fallback to empty results")
                    return []
            except Exception as e:
                logger.error(f"Tavily unexpected error: {e}")
                self.error_count += 1
                if attempt < retries - 1:
                    wait_s = min(8, 1.5 ** attempt) + random.uniform(0.0, 0.8)
                    await asyncio.sleep(wait_s)
                else:
                    logger.warning("Tavily unexpected error after retries, fallback to empty results")
                    return []

        return []
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or ""
        except:
            return ""


class MetricsCalculator:
    """Calculate evaluation metrics for search results."""

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text for lexical overlap (supports Chinese + English)."""
        if not text:
            return []
        text_lower = text.lower()
        latin_tokens = re.findall(r"[A-Za-z0-9_]+", text_lower)
        cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text_lower)
        cjk_chars = re.findall(r"[\u4e00-\u9fff]", text_lower)

        cjk_bigrams = []
        for chunk in cjk_chunks:
            if len(chunk) == 2:
                cjk_bigrams.append(chunk)
            elif len(chunk) > 2:
                cjk_bigrams.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))

        tokens = latin_tokens + cjk_chars + cjk_bigrams
        return [t for t in tokens if t.strip()]

    @staticmethod
    def _jaccard_similarity(a_tokens: List[str], b_tokens: List[str]) -> float:
        """Compute Jaccard similarity between token sets."""
        if not a_tokens or not b_tokens:
            return 0.0
        a_set, b_set = set(a_tokens), set(b_tokens)
        union = a_set | b_set
        if not union:
            return 0.0
        return len(a_set & b_set) / len(union)

    @staticmethod
    def _cosine_similarity(a_tokens: List[str], b_tokens: List[str]) -> float:
        """Compute cosine similarity from token-frequency vectors."""
        if not a_tokens or not b_tokens:
            return 0.0
        a_cnt, b_cnt = Counter(a_tokens), Counter(b_tokens)
        terms = set(a_cnt.keys()) | set(b_cnt.keys())
        dot = sum(a_cnt[t] * b_cnt[t] for t in terms)
        a_norm = math.sqrt(sum(v * v for v in a_cnt.values()))
        b_norm = math.sqrt(sum(v * v for v in b_cnt.values()))
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return dot / (a_norm * b_norm)

    @staticmethod
    def _proxy_relevance(query: str, result: SearchResult) -> float:
        """Compute proxy relevance in [0,1] from lexical evidence only.

        Keep relevance labeling independent from retrieval model scores
        to avoid evaluation leakage.
        """
        query_tokens = MetricsCalculator._tokenize(query)
        doc_tokens = MetricsCalculator._tokenize(f"{result.title} {result.content[:500]}")
        jac = MetricsCalculator._jaccard_similarity(query_tokens, doc_tokens)
        cos = MetricsCalculator._cosine_similarity(query_tokens, doc_tokens)
        return max(0.0, min(1.0, 0.4 * jac + 0.6 * cos))

    @staticmethod
    def _graded_relevance(query: str, result: SearchResult) -> int:
        """Map proxy relevance to graded relevance {0,1,2,3}."""
        rel = MetricsCalculator._proxy_relevance(query, result)
        if rel >= 0.55:
            return 3
        if rel >= 0.40:
            return 2
        if rel >= 0.25:
            return 1
        return 0
    
    @staticmethod
    def calculate_ndcg(
        results: List[SearchResult],
        query: str,
        k: Optional[int] = None,
        ideal_order: Optional[List[int]] = None
    ) -> float:
        """Calculate nDCG@k using graded relevance (academic definition).

        DCG@k = Σ((2^rel_i - 1) / log2(i + 2))
        nDCG@k = DCG@k / IDCG@k

        Args:
            results: Ranked search results
            query: User query for proxy relevance labeling
            k: Cutoff rank (defaults to len(results))
            ideal_order: Optional ideal permutation indices

        Returns:
            nDCG@k in [0,1]
        """
        if not results:
            return 0.0

        cutoff = min(k or len(results), len(results))
        rels = [MetricsCalculator._graded_relevance(query, r) for r in results[:cutoff]]

        dcg = sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(rels))

        if ideal_order and len(ideal_order) >= cutoff:
            ideal_rels = [rels[idx] for idx in ideal_order[:cutoff] if 0 <= idx < len(rels)]
            if len(ideal_rels) < cutoff:
                ideal_rels = sorted(rels, reverse=True)
        else:
            ideal_rels = sorted(rels, reverse=True)

        idcg = sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(ideal_rels))
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def calculate_mrr(
        results: List[SearchResult],
        query: str,
        k: Optional[int] = None,
        relevant_grade_threshold: int = 1
    ) -> float:
        """Calculate MRR@k with binary relevance converted from graded labels.

        MRR@k = 1 / rank(first relevant), if any relevant doc appears in top-k.

        Args:
            results: Ranked search results
            query: User query for proxy relevance labeling
            k: Cutoff rank (defaults to len(results))
            relevant_grade_threshold: graded relevance threshold for "relevant"

        Returns:
            MRR@k in [0,1]
        """
        if not results:
            return 0.0

        cutoff = min(k or len(results), len(results))
        for i, result in enumerate(results[:cutoff]):
            grade = MetricsCalculator._graded_relevance(query, result)
            if grade >= relevant_grade_threshold:
                return 1.0 / (i + 1)
        return 0.0
    
    @staticmethod
    def calculate_source_diversity(results: List[SearchResult]) -> float:
        """Calculate normalized source diversity with entropy + novelty.

        Diversity = 0.5 * H_norm(domain) + 0.5 * AvgPairwiseNovelty(title)
        where H_norm is Shannon entropy normalized to [0,1].
        """
        if not results:
            return 0.0

        total = len(results)
        domain_count: Dict[str, int] = {}
        for r in results:
            key = r.domain or "unknown"
            domain_count[key] = domain_count.get(key, 0) + 1

        probs = [count / total for count in domain_count.values()]
        entropy = -sum(p * math.log(p, 2) for p in probs if p > 0)
        max_entropy = math.log(total, 2) if total > 1 else 1.0
        domain_entropy_norm = entropy / max_entropy if max_entropy > 0 else 0.0

        docs = [MetricsCalculator._tokenize(f"{r.title} {r.content[:300]}") for r in results]
        if total <= 1:
            novelty = 0.0
        else:
            pair_scores: List[float] = []
            for i in range(total):
                for j in range(i + 1, total):
                    sim = MetricsCalculator._jaccard_similarity(docs[i], docs[j])
                    pair_scores.append(1.0 - sim)
            novelty = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0

        return max(0.0, min(1.0, 0.5 * domain_entropy_norm + 0.5 * novelty))

    @staticmethod
    def calculate_mean_relevance(
        results: List[SearchResult],
        query: str,
        k: Optional[int] = None
    ) -> float:
        """Calculate mean proxy relevance for top-k results."""
        if not results:
            return 0.0
        cutoff = min(k or len(results), len(results))
        rels = [MetricsCalculator._proxy_relevance(query, r) for r in results[:cutoff]]
        return sum(rels) / len(rels) if rels else 0.0

    @staticmethod
    def calculate_relevance_dispersion(
        results: List[SearchResult],
        query: str,
        k: Optional[int] = None
    ) -> float:
        """Calculate normalized relevance dispersion (std-like) for top-k."""
        if not results:
            return 0.0
        cutoff = min(k or len(results), len(results))
        rels = [MetricsCalculator._proxy_relevance(query, r) for r in results[:cutoff]]
        if len(rels) <= 1:
            return 0.0
        mean_rel = sum(rels) / len(rels)
        variance = sum((x - mean_rel) ** 2 for x in rels) / len(rels)
        std = math.sqrt(variance)
        return max(0.0, min(1.0, std / 0.5))
    
    @staticmethod
    def calculate_reflection_depth(reflection_count: int, max_reflections: int = 3) -> float:
        """Calculate reflection depth score.
        
        Args:
            reflection_count: Number of reflection loops executed
            max_reflections: Maximum allowed reflections
            
        Returns:
            Depth score (0-1)
        """
        return min(reflection_count / max_reflections, 1.0)
