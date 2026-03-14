from pathlib import Path
from typing import Dict, Any
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.deepseek_client import DeepSeekClient


class BaseAgent:
    def __init__(self, role: str, prompt_name: str, client: DeepSeekClient | None = None, temperature: float = 0.2):
        self.role = role
        self.prompt_name = prompt_name
        self.client = client
        self.temperature = temperature

    def load_prompt(self) -> str:
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / f"{self.prompt_name}.txt"
        return prompt_path.read_text(encoding="utf-8")

    def render_prompt(self, variables: Dict[str, Any]) -> str:
        template = self.load_prompt()
        return template.format(**variables)
