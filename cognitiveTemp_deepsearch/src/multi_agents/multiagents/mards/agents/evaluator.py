import re
from typing import List
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, EvaluationPayload, RetrievalPayload, SystemState
from agents.base_agent import BaseAgent
from utils.deepseek_client import DeepSeekClient


class EvidenceEvaluatorAgent(BaseAgent):
    def __init__(self, client: DeepSeekClient | None = None):
        super().__init__(role="evaluator", prompt_name="evaluator", client=client, temperature=0.1)

    async def run(self, state: SystemState, retrieval: RetrievalPayload) -> AgentOutput:
        if self.client:
            prompt = self.render_prompt({"retrieval": retrieval.model_dump()})
            data = await self.client.chat_json(prompt, temperature=self.temperature)
            claims = data.get("claims", [])
            contradictions = data.get("contradictions", [])
        else:
            claims = self._extract_claims(retrieval)
            contradictions = self._detect_contradictions(claims)

        avg_conf = self._average_confidence(retrieval)
        payload = EvaluationPayload(claims=claims, contradictions=contradictions, source_confidence=avg_conf)
        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=avg_conf,
            uncertainty_score=max(0.0, 1 - avg_conf),
            needs_iteration=len(contradictions) > 0,
        )

    def _extract_claims(self, retrieval: RetrievalPayload) -> List[str]:
        claims = []
        for item in retrieval.results:
            sentences = re.split(r"[。.!?]", item.snippet)
            for s in sentences:
                s = s.strip()
                if len(s) > 12:
                    claims.append(s)
        return list(dict.fromkeys(claims))[:20]

    def _detect_contradictions(self, claims: List[str]) -> List[str]:
        contradictions = []
        for c in claims:
            if any(neg in c.lower() for neg in ["not", "no", "无法", "没有", "无效", "不足"]):
                contradictions.append(c)
        return contradictions[:10]

    def _average_confidence(self, retrieval: RetrievalPayload) -> float:
        if not retrieval.results:
            return 0.2
        return sum(r.score for r in retrieval.results) / len(retrieval.results)
