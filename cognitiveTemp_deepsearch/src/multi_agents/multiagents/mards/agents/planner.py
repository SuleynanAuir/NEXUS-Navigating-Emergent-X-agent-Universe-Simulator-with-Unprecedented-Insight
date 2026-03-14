import re
import uuid
from typing import List
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, PlannerPayload, SystemState
from agents.base_agent import BaseAgent
from utils.deepseek_client import DeepSeekClient


class PlannerAgent(BaseAgent):
    def __init__(self, client: DeepSeekClient | None = None):
        super().__init__(role="planner", prompt_name="planner", client=client, temperature=0.1)

    async def run(self, state: SystemState) -> AgentOutput:
        if self.client:
            prompt = self.render_prompt({"query": state.query})
            data = await self.client.chat_json(prompt, temperature=self.temperature)
            sub_questions = data.get("sub_questions", [])
        else:
            sub_questions = self._local_decompose(state.query)

        payload = PlannerPayload(sub_questions=sub_questions)
        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=0.7,
            uncertainty_score=0.3,
            needs_iteration=False,
        )

    def _local_decompose(self, query: str) -> List[str]:
        parts = re.split(r"\band\b|；|;|、", query)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            return [f"{p} 的关键证据是什么？" for p in parts]
        return [
            f"{query} 的定义与范围是什么？",
            f"{query} 的核心证据与数据有哪些？",
            f"{query} 的影响与应用场景是什么？",
        ]
