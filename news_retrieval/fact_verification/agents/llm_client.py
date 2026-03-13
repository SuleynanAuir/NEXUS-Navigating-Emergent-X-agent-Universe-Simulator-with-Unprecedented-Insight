import json
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


load_dotenv()


class LLMClient:
    """DeepSeek/OpenAI-compatible minimal client.

    Env:
    - DEEPSEEK_API_KEY or DEEP_SEEK_API_KEY
    - DEEPSEEK_BASE_URL (optional, default: https://api.deepseek.com)
    - DEEPSEEK_MODEL (optional, default: deepseek-chat)
    """

    def __init__(self) -> None:
        self.api_key = (
            os.getenv("DEEPSEEK_API_KEY", "").strip()
            or os.getenv("DEEP_SEEK_API_KEY", "").strip()
        )
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        try:
            self.timeout = max(8, min(120, int(str(os.getenv("DEEPSEEK_TIMEOUT", "22") or "22").strip())))
        except Exception:
            self.timeout = 22

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Optional[str]:
        if not self.enabled:
            return None
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": messages,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def json_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> Optional[Dict[str, Any]]:
        """调用 LLM 并强制解析为 JSON。优先使用 response_format=json_object。"""
        # 尝试带 response_format 的请求（DeepSeek 支持）
        raw = self._chat_json_mode(system_prompt, user_prompt, temperature)
        if raw is None:
            # 降级到普通 chat
            raw = self._chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
        if not raw:
            return None
        return self._parse_json_response(raw)

    def _chat_json_mode(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> Optional[str]:
        """使用 response_format=json_object 模式调用，强制输出纯 JSON。"""
        if not self.enabled:
            return None
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    @staticmethod
    def _parse_json_response(raw: str) -> Optional[Dict[str, Any]]:
        """多策略解析 LLM 返回的 JSON 字符串。"""
        raw = raw.strip()
        # 策略1：直接解析
        try:
            return json.loads(raw)
        except Exception:
            pass
        # 策略2：去掉 ```json ... ``` 代码块
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # 策略3：提取第一个 { ... } 块
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return None
