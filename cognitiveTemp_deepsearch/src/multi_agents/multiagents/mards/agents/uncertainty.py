import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, UncertaintyPayload, SystemState, EvaluationPayload, ReflectionPayload
from agents.base_agent import BaseAgent
from utils.deepseek_client import DeepSeekClient


class UncertaintyAgent(BaseAgent):
    def __init__(self, client: DeepSeekClient | None = None):
        super().__init__(role="uncertainty", prompt_name="uncertainty", client=client, temperature=0.1)

    async def run(
        self,
        state: SystemState,
        evaluations: list[EvaluationPayload],
        reflection: ReflectionPayload | dict,
    ) -> AgentOutput:
        # 处理字典或对象格式的 reflection
        if isinstance(reflection, dict):
            missing_topics = reflection.get("missing_topics", [])
        else:
            missing_topics = reflection.missing_topics if reflection else []
            
        conflict_rate = self._conflict_rate(evaluations)
        info_gap_score = self._info_gap_score(state.sub_questions, missing_topics)
        avg_unreliability = self._avg_unreliability(evaluations)

        global_uncertainty = min(1.0, 0.4 * conflict_rate + 0.3 * info_gap_score + 0.3 * avg_unreliability)
        needs_iteration = global_uncertainty >= 0.2

        payload = UncertaintyPayload(
            global_uncertainty=global_uncertainty,
            conflict_rate=conflict_rate,
            info_gap_score=info_gap_score,
            avg_source_unreliability=avg_unreliability,
            missing_topics=missing_topics,
        )

        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=max(0.0, 1 - global_uncertainty),
            uncertainty_score=global_uncertainty,
            needs_iteration=needs_iteration,
        )

    def _conflict_rate(self, evaluations: list[EvaluationPayload]) -> float:
        total_claims = sum(len(e.claims) for e in evaluations) or 1
        contradictions = sum(len(e.contradictions) for e in evaluations)
        return min(1.0, contradictions / total_claims)

    def _info_gap_score(self, sub_questions: list[str], missing_topics: list[str]) -> float:
        if not sub_questions:
            return 1.0
        return min(1.0, len(missing_topics) / len(sub_questions))

    def _avg_unreliability(self, evaluations: list[EvaluationPayload]) -> float:
        if not evaluations:
            return 1.0
        avg_conf = sum(e.source_confidence for e in evaluations) / len(evaluations)
        return min(1.0, 1 - avg_conf)
