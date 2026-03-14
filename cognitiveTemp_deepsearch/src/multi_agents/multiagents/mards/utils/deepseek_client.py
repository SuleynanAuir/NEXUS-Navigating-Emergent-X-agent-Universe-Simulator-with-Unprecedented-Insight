import json
import re
from typing import Any, Dict, Optional
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp

from config import settings


class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.model = model or settings.deepseek_model

    async def chat_json(self, prompt: str, temperature: float = 0.2, system: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        for attempt in range(settings.max_retries):
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.request_timeout)) as session:
                async with session.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    try:
                        return self._parse_json(content)
                    except ValueError:
                        if attempt == settings.max_retries - 1:
                            raise
                        payload["messages"] = [
                            {
                                "role": "user",
                                "content": f"请修复并仅输出合法JSON，不要包含解释。原内容: {content}",
                            }
                        ]
        raise ValueError("Failed to get valid JSON from DeepSeek")

    def _parse_json(self, text: str) -> Dict[str, Any]:
        cleaned = self._strip_markdown(text)
        cleaned = self._remove_trailing_commas(cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON") from exc

    def _strip_markdown(self, text: str) -> str:
        match = re.search(r"```json\s*(\{[\s\S]*\})\s*```", text)
        if match:
            return match.group(1)
        return text.strip()

    def _remove_trailing_commas(self, text: str) -> str:
        text = re.sub(r",\s*([}\]])", r"\1", text)
        return text
