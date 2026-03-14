import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, DebatePayload, SystemState
from agents.base_agent import BaseAgent
from utils.deepseek_client import DeepSeekClient


class DebateAgent(BaseAgent):
    def __init__(self, client: DeepSeekClient | None = None):
        super().__init__(role="debate", prompt_name="debate", client=client, temperature=0.7)

    async def run(self, state: SystemState, topic: str, contradictions: list[str]) -> AgentOutput:
        if self.client:
            prompt = self.render_prompt({"topic": topic, "contradictions": contradictions})
            data = await self.client.chat_json(prompt, temperature=self.temperature)
            resolution = data.get("resolution", "")
            remaining = data.get("remaining_disagreements", [])
        else:
            resolution = "基于现有证据形成暂时性折中结论，需进一步验证。"
            remaining = contradictions[:3]

        payload = DebatePayload(resolution=resolution, remaining_disagreements=remaining)
        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=0.5,
            uncertainty_score=0.5,
            needs_iteration=bool(remaining),
        )
