import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import AgentOutput, SynthesisPayload, SystemState, EvaluationPayload, UncertaintyPayload
from agents.base_agent import BaseAgent
from utils.deepseek_client import DeepSeekClient


class SynthesisAgent(BaseAgent):
    def __init__(self, client: DeepSeekClient | None = None):
        super().__init__(role="synthesis", prompt_name="synthesis", client=client, temperature=0.4)

    async def run(
        self,
        state: SystemState,
        evaluations: list[EvaluationPayload],
        uncertainty: UncertaintyPayload | dict,
    ) -> AgentOutput:
        # 处理 uncertainty 可能是字典的情况
        uncertainty_dict = uncertainty.model_dump() if isinstance(uncertainty, UncertaintyPayload) else uncertainty
        
        if self.client:
            prompt = self.render_prompt(
                {"evaluations": [e.model_dump() for e in evaluations], "uncertainty": uncertainty_dict}
            )
            data = await self.client.chat_json(prompt, temperature=self.temperature)
            report = data.get("report_markdown", "")
        else:
            report = self._generate_markdown(state, evaluations, uncertainty_dict)

        payload = SynthesisPayload(report_markdown=report)
        
        # 处理 uncertainty 可能是字典或对象的情况
        if isinstance(uncertainty_dict, dict):
            global_unc = uncertainty_dict.get("global_uncertainty", 0.0)
        else:
            global_unc = getattr(uncertainty_dict, "global_uncertainty", 0.0)
        
        return AgentOutput(
            task_id=state.task_id,
            agent_role=self.role,
            output_payload=payload.model_dump(),
            confidence_score=max(0.0, 1 - global_unc),
            uncertainty_score=global_unc,
            needs_iteration=False,
        )

    def _generate_markdown(
        self, state: SystemState, evaluations: list[EvaluationPayload], uncertainty: dict
    ) -> str:
        findings = []
        contradictions = []
        for e in evaluations:
            findings.extend(e.claims[:5])
            contradictions.extend(e.contradictions[:3])

        missing_topics = uncertainty.get("missing_topics", []) if isinstance(uncertainty, dict) else []

        report = f"""# Executive Summary
本报告针对查询"{state.query}"进行了系统性的多智能体深度搜索。共分解为{len(state.sub_questions)}个子问题，完成{state.loop_count}轮迭代。

# Structured Findings
{chr(10).join(f"- {f}" for f in findings[:10])}

# Evidence Strength
平均源置信度: {sum(e.source_confidence for e in evaluations) / len(evaluations):.2f}

# Contradictions Resolved
{chr(10).join(f"- {c}" for c in contradictions[:5]) if contradictions else "未发现显著矛盾。"}

# Knowledge Gaps
{chr(10).join(f"- {t}" for t in missing_topics[:5]) if missing_topics else "已覆盖主要话题。"}

# Final Uncertainty Score
- Global Uncertainty: {uncertainty.get('global_uncertainty', 0):.2f}
- Conflict Rate: {uncertainty.get('conflict_rate', 0):.2f}
- Info Gap Score: {uncertainty.get('info_gap_score', 0):.2f}

# Verified Source List
参见检索结果（已通过域名多样性过滤）。
"""
        return report
