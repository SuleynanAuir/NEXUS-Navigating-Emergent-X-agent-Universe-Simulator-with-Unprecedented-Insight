from typing import List
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, ReflectionPayload, EvaluationPayload, SystemState
from agents.base_agent import BaseAgent
from utils.deepseek_client import DeepSeekClient


class ReflectionAgent(BaseAgent):
    def __init__(self, client: DeepSeekClient | None = None):
        super().__init__(role="reflection", prompt_name="reflection", client=client, temperature=0.4)

    async def run(self, state: SystemState, evaluation: EvaluationPayload) -> AgentOutput:
        if self.client:
            prompt = self.render_prompt({"evaluation": evaluation.model_dump()})
            data = await self.client.chat_json(prompt, temperature=self.temperature)
            contradictions = data.get("contradictions", [])
            follow_up = data.get("follow_up_queries", [])
            missing_topics = data.get("missing_topics", [])
            needs_iteration = data.get("needs_iteration", False)
        else:
            contradictions = evaluation.contradictions
            missing_topics = self._missing_topics(state.sub_questions, evaluation)
            follow_up = [f"补充证据：{t}" for t in missing_topics][:5]
            needs_iteration = bool(contradictions) or evaluation.source_confidence < 0.6

        payload = ReflectionPayload(
            contradictions=contradictions,
            follow_up_queries=follow_up,
            missing_topics=missing_topics,
            needs_iteration=needs_iteration,
        )

        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=0.6,
            uncertainty_score=0.4,
            needs_iteration=needs_iteration,
        )

    def _missing_topics(self, sub_questions: List[str], evaluation: EvaluationPayload) -> List[str]:
        missing = []
        for sq in sub_questions:
            if not any(sq[:6] in c for c in evaluation.claims):
                missing.append(sq)
        return missing
