from typing import List, Dict, Tuple
from copy import deepcopy
import time
import os
from search import search_news


class SearchTools:
    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str, int], Tuple[float, List[Dict]]] = {}
        self._ttl_seconds = 900
        self._max_cache_size = 256

    def _normalize_query(self, query: str) -> str:
        return " ".join((query or "").strip().lower().split())

    def _cached_search(self, kind: str, query: str, num_results: int) -> List[Dict]:
        norm_query = self._normalize_query(query)
        provider = (os.getenv("SEARCH_PROVIDER", "serpapi") or "serpapi").strip().lower()
        cache_key = (provider, kind, norm_query, num_results)
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached is not None:
            ts, value = cached
            if now - ts <= self._ttl_seconds:
                return deepcopy(value)
            self._cache.pop(cache_key, None)

        try:
            results = search_news(query, num_results, provider=provider)
        except TypeError as error:
            if "unexpected keyword argument 'provider'" in str(error):
                results = search_news(query, num_results)
            else:
                raise
        if results:
            if len(self._cache) >= self._max_cache_size:
                oldest_key = min(self._cache.items(), key=lambda item: item[1][0])[0]
                self._cache.pop(oldest_key, None)
            self._cache[cache_key] = (now, deepcopy(results))
        return results

    def web_search(self, query: str, num_results: int = 8) -> List[Dict]:
        return self._cached_search("web", query, num_results)

    def scholar_search(self, query: str, num_results: int = 5) -> List[Dict]:
        return self._cached_search("scholar", f"{query} site:arxiv.org OR site:semanticscholar.org", num_results)

    def trusted_kb_search(self, query: str, num_results: int = 5) -> List[Dict]:
        return self._cached_search("trusted", f"{query} site:.gov OR site:.edu OR site:who.int", num_results)
