"""
Controller Agent (Orchestrator for MARDS)

Workflow:
1. Call Planner
2. For each sub-question:
    a. Retrieve
    b. Evaluate Evidence
    c. Reflect
    d. If requires_additional_retrieval == true:
            repeat (max 3 loops)
3. Optional Debate Phase
4. Uncertainty Quantification
5. If recommend_termination == false:
        return to reflection
6. Call Synthesis Agent

Constraints:
- Maximum 3 recursive loops per question
- Stop if global_uncertainty < 0.2
- Maintain strict JSON communication
- No context leakage between roles
"""

import json
import logging
from typing import List, Dict, Any, Optional

from .planner_agent import PlannerAgent
from .retriever_agent import RetrieverAgent
from .evaluator_agent import EvidenceEvaluatorAgent
from .critical_reflection_agent import CriticalReflectionAgent
from .debate_agent import DebateAgent
from .uncertainty_quantifier_agent import UncertaintyQuantifierAgent
from .synthesis_agent import SynthesisAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ControllerAgent:
    """
    Orchestrator for Multi-Agent Research Deep Search (MARDS)
    """
    def __init__(self, model: str = "gpt-4"):
        self.planner = PlannerAgent(model=model)
        self.retriever = RetrieverAgent(model=model)
        self.evaluator = EvidenceEvaluatorAgent(model=model)
        self.reflector = CriticalReflectionAgent(model=model)
        self.debater = DebateAgent(model=model)
        self.uncertainty = UncertaintyQuantifierAgent(model=model)
        self.synthesizer = SynthesisAgent(model=model)
        self.max_loops = 3
        logger.info("ControllerAgent initialized.")

    def run(self, query: str, debate_phase: bool = False) -> Dict:
        """
        Run full MARDS workflow for a research query.
        Returns strict JSON output.
        """
        # 1. Planner
        decomposition = self.planner.decompose(query)
        sub_questions = decomposition.sub_questions
        all_results = []
        for sq in sub_questions:
            loop_count = 0
            requires_additional_retrieval = True
            evidence_sources = []
            evaluation = None
            reflection = None
            while requires_additional_retrieval and loop_count < self.max_loops:
                # 2a. Retrieve
                retrieval_result = self.retriever.retrieve(sq.text)
                evidence_sources = retrieval_result.results
                # 2b. Evaluate
                evaluation = self.evaluator.evaluate(evidence_sources)
                # 2c. Reflect
                reflection = self.reflector.reflect(evaluation.claims, evidence_sources)
                # 2d. Check if more retrieval needed
                requires_additional_retrieval = getattr(reflection, "requires_additional_retrieval", False)
                loop_count += 1
            # 3. Optional Debate
            debate_result = None
            if debate_phase:
                debate_result = self.debater.debate(sq.text, evidence_sources)
            # 4. Uncertainty Quantification
            uncertainty_result = self.uncertainty.quantify(
                analysis_id=sq.id if hasattr(sq, "id") else sq.text,
                evidence_sources=[es.to_dict() if hasattr(es, "to_dict") else es for es in evidence_sources],
                claims=evaluation.claims if evaluation else [],
            )
            # 5. If recommend_termination == false, return to reflection
            if not uncertainty_result.recommend_termination and loop_count < self.max_loops:
                reflection = self.reflector.reflect(evaluation.claims, evidence_sources)
            # 6. Collect results
            all_results.append({
                "sub_question": sq.text,
                "retrieval": [es.to_dict() if hasattr(es, "to_dict") else es for es in evidence_sources],
                "evaluation": evaluation.to_dict() if evaluation else {},
                "reflection": reflection.to_dict() if reflection else {},
                "debate": debate_result.to_dict() if debate_result else {},
                "uncertainty": uncertainty_result.to_dict(),
            })
            # Stop if global_uncertainty < 0.2
            if uncertainty_result.global_uncertainty < 0.2:
                logger.info(f"Early stop: global_uncertainty={uncertainty_result.global_uncertainty}")
                break
        # 7. Synthesis Agent
        synthesis_input = self._prepare_synthesis_input(all_results)
        synthesis_report = self.synthesizer.synthesize(**synthesis_input)
        # Strict JSON output
        return {
            "decomposition": decomposition.to_dict(),
            "sub_question_results": all_results,
            "synthesis_report": synthesis_report.to_dict(),
        }

    def _prepare_synthesis_input(self, all_results: List[Dict]) -> Dict:
        """
        Prepare input for SynthesisAgent from all sub-question results.
        """
        background = "本报告基于多智能体协作系统自动生成，涵盖多个子问题的深度检索与评估。"
        findings = []
        evidence_strength = ""
        contradictions = []
        limitations = []
        future_research = []
        confidence_assessment = ""
        uncertainty_highlight = []
        fact_vs_inference = {"facts": [], "inferences": []}
        for res in all_results:
            findings.extend(res.get("evaluation", {}).get("claims", []))
            evidence_strength = res.get("evaluation", {}).get("overall_strength_score", "")
            contradictions.extend(res.get("evaluation", {}).get("contradictions", []))
            limitations.extend(res.get("reflection", {}).get("missing_perspectives", []))
            future_research.extend(res.get("reflection", {}).get("counterfactual_questions", []))
            confidence_assessment = res.get("uncertainty", {}).get("confidence_level", "")
            uncertainty_highlight.extend(res.get("uncertainty", {}).get("uncertainty_sources", []))
            fact_vs_inference = res.get("reflection", {}).get("fact_vs_inference", fact_vs_inference)
        return {
            "background": background,
            "findings": findings,
            "evidence_strength": evidence_strength,
            "contradictions": contradictions,
            "limitations": limitations,
            "future_research": future_research,
            "confidence_assessment": confidence_assessment,
            "uncertainty_highlight": uncertainty_highlight,
            "fact_vs_inference": fact_vs_inference,
        }

def create_controller_agent(model: str = "gpt-4") -> ControllerAgent:
    """工厂函数，创建Controller Agent"""
    return ControllerAgent(model=model)
