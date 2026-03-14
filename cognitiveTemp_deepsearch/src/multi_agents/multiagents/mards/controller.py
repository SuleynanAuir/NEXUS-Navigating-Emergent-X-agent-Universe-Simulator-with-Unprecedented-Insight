import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional

from agents import (
    PlannerAgent,
    RetrieverAgent,
    EvidenceEvaluatorAgent,
    ReflectionAgent,
    DebateAgent,
    UncertaintyAgent,
    SynthesisAgent,
)
from schemas import SystemState, EvaluationPayload, PlannerPayload, RetrievalPayload
from utils.deepseek_client import DeepSeekClient
from utils.tavily_client import TavilyClient
from utils.logger import setup_logger

logger = setup_logger()


class Controller:
    def __init__(self, deepseek_client: Optional[DeepSeekClient] = None, tavily_client: Optional[TavilyClient] = None):
        self.deepseek = deepseek_client
        self.tavily = tavily_client or TavilyClient()
        self.planner = PlannerAgent(client=self.deepseek)
        self.retriever = RetrieverAgent(client=self.tavily)
        self.evaluator = EvidenceEvaluatorAgent(client=self.deepseek)
        self.reflector = ReflectionAgent(client=self.deepseek)
        self.debater = DebateAgent(client=self.deepseek)
        self.uncertainty = UncertaintyAgent(client=self.deepseek)
        self.synthesizer = SynthesisAgent(client=self.deepseek)

    async def run(self, query: str, enable_debate: bool = False) -> SystemState:
        task_id = str(uuid.uuid4())
        state = SystemState(task_id=task_id, query=query)
        logger.info(f"[{task_id}] Starting MARDS workflow for query: {query}")

        # 1. Planner
        planner_output = await self.planner.run(state)
        planner_payload = PlannerPayload(**planner_output.output_payload)
        state.sub_questions = planner_payload.sub_questions
        logger.info(f"[{task_id}] Decomposed into {len(state.sub_questions)} sub-questions")
        self._save_state(state, "01_planner")

        # 2. For each sub-question
        for idx, sq in enumerate(state.sub_questions):
            logger.info(f"[{task_id}] Processing sub-question {idx+1}/{len(state.sub_questions)}: {sq}")
            await self._process_subquestion(state, sq, enable_debate)

        # 4. Uncertainty Quantification
        evaluations = [EvaluationPayload(**e) for e in state.evaluations.values()]
        unc_output = await self.uncertainty.run(state, evaluations, state.reflection)
        state.uncertainty = unc_output.output_payload
        logger.info(f"[{task_id}] Global uncertainty: {state.uncertainty['global_uncertainty']:.2f}")
        self._save_state(state, "04_uncertainty")

        # 5. Termination check
        if state.uncertainty["global_uncertainty"] >= 0.2 and state.loop_count < 3:
            logger.info(f"[{task_id}] Uncertainty still high, iterating...")
            state.loop_count += 1
            # 处理 reflection 可能是字典或对象的情况
            missing_topics = state.reflection.get("missing_topics", []) if isinstance(state.reflection, dict) else getattr(state.reflection, "missing_topics", [])
            for missing in missing_topics[:2]:
                await self._process_subquestion(state, missing, enable_debate)

        # 6. Synthesis
        synth_output = await self.synthesizer.run(state, evaluations, state.uncertainty)
        state.synthesis = synth_output.output_payload
        logger.info(f"[{task_id}] Synthesis completed")
        self._save_state(state, "06_synthesis")

        return state

    async def _process_subquestion(self, state: SystemState, query: str, enable_debate: bool):
        # a. Retrieve
        retr_output = await self.retriever.run(state, query)
        retr_payload = RetrievalPayload(**retr_output.output_payload)
        state.retrievals[query] = retr_payload.model_dump()

        # b. Evaluate
        eval_output = await self.evaluator.run(state, retr_payload)
        state.evaluations[query] = eval_output.output_payload

        # c. Reflect
        eval_payload = EvaluationPayload(**state.evaluations[query])
        refl_output = await self.reflector.run(state, eval_payload)
        state.reflection = refl_output.output_payload

        # 3. Optional Debate
        if enable_debate and eval_payload.contradictions:
            debate_output = await self.debater.run(state, query, eval_payload.contradictions)
            state.debate = debate_output.output_payload

    def _save_state(self, state: SystemState, stage: str):
        runs_dir = Path("runs")
        runs_dir.mkdir(exist_ok=True)
        file_path = runs_dir / f"{state.task_id}_{stage}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved state to {file_path}")
