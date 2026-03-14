from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp

from config import settings


class TavilyClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.tavily_api_key

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is required")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_raw_content": False,
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.request_timeout)) as session:
            async with session.post("https://api.tavily.com/search", json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("results", [])
