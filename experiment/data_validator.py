"""
数据验证模块：确保输入数据符合指标计算要求
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import json


class DataValidator:
    """验证指标计算所需的数据完整性和有效性"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_payload(self, payload: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        验证整个 payload 的数据质量
        
        返回: (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        self._validate_retrieval(payload.get("retrieval", []))
        self._validate_kg(payload.get("kg", {}))
        self._validate_multi_agent(payload.get("multi_agent", {}))
        self._validate_simulation(payload.get("simulation", {}))
        self._validate_insight(payload.get("insight", {}))
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_retrieval(self, retrieval_cases: List[Dict[str, Any]]) -> None:
        """验证检索质量指标数据"""
        if not retrieval_cases:
            self.warnings.append("retrieval 为空：无法计算检索质量指标")
            return
        
        for i, case in enumerate(retrieval_cases):
            case_id = f"retrieval[{i}]"
            
            # 必需字段
            if "gold_doc_ids" not in case or not case["gold_doc_ids"]:
                self.errors.append(f"{case_id}: 缺少 gold_doc_ids (标注的相关文档)")
            
            if "top_k_doc_ids" not in case or not case["top_k_doc_ids"]:
                self.errors.append(f"{case_id}: 缺少 top_k_doc_ids (检索结果)")
            
            # 可选但推荐
            if "result_texts" not in case or len(case.get("result_texts", [])) < 2:
                self.warnings.append(f"{case_id}: result_texts 不足 2 条，无法准确计算多样性")
            
            if "query_text" not in case:
                self.warnings.append(f"{case_id}: 缺少 query_text (便于追踪)")
    
    def _validate_kg(self, kg_data: Dict[str, Any]) -> None:
        """验证知识图谱质量指标数据"""
        # 实体覆盖率
        gold_entities = kg_data.get("gold_entities", [])
        if not gold_entities:
            self.errors.append("kg: 缺少 gold_entities (标注的标准实体集)")
        
        graph_entities = kg_data.get("graph_entities", [])
        if not graph_entities:
            self.warnings.append("kg: 缺少 graph_entities (提取的实体)")
        
        # 关系准确率
        triples = kg_data.get("triples", [])
        if not triples:
            self.warnings.append("kg: 缺少 triples，无法计算关系准确率")
        else:
            for i, triple in enumerate(triples):
                triple_id = f"kg.triples[{i}]"
                if "is_correct" not in triple:
                    self.errors.append(f"{triple_id}: 缺少 is_correct (标注)")
                if "head" not in triple or "rel" not in triple or "tail" not in triple:
                    self.errors.append(f"{triple_id}: 缺少 head/rel/tail 字段")
        
        # 图连通性
        nodes = kg_data.get("nodes", [])
        edges = kg_data.get("edges", [])
        if not nodes:
            self.warnings.append("kg: 缺少 nodes，无法计算图连通性")
        if not edges:
            self.warnings.append("kg: 缺少 edges，图可能是孤立节点")
    
    def _validate_multi_agent(self, multi_data: Dict[str, Any]) -> None:
        """验证多智能体协同指标数据"""
        cases = multi_data.get("cases", [])
        if not cases:
            self.warnings.append("multi_agent 为空：无法计算多智能体指标")
            return
        
        for i, case in enumerate(cases):
            case_id = f"multi_agent.cases[{i}]"
            
            # 多样性需要多个答案
            agent_answers = case.get("agent_answers", [])
            if len(agent_answers) < 2:
                self.warnings.append(f"{case_id}: agent_answers 少于 2 个，无法计算多样性")
            
            # 增益计算需要对比值
            p_single = case.get("p_single")
            p_multi = case.get("p_multi")
            if p_single is None or p_multi is None:
                self.errors.append(f"{case_id}: 缺少 p_single 或 p_multi (性能对比数据)")
            elif not (isinstance(p_single, (int, float)) and isinstance(p_multi, (int, float))):
                self.errors.append(f"{case_id}: p_single/p_multi 必须是数字")
            
            # 冲突解决需要计数
            initial_conflicts = case.get("initial_conflicts")
            resolved_conflicts = case.get("resolved_conflicts")
            if initial_conflicts is None or resolved_conflicts is None:
                self.errors.append(f"{case_id}: 缺少 initial_conflicts 或 resolved_conflicts")
            elif initial_conflicts == 0:
                self.warnings.append(f"{case_id}: initial_conflicts = 0，无冲突可解决")
    
    def _validate_simulation(self, sim_data: Dict[str, Any]) -> None:
        """验证仿真推演能力指标数据"""
        cases = sim_data.get("cases", [])
        if not cases:
            self.warnings.append("simulation 为空：无法计算仿真指标")
            return
        
        for i, case in enumerate(cases):
            case_id = f"simulation.cases[{i}]"
            
            # 场景多样性
            future_scenarios = case.get("future_scenarios", [])
            if len(future_scenarios) < 2:
                self.warnings.append(f"{case_id}: future_scenarios 少于 2 个，无法计算多样性")
            
            # 预测一致性
            runs = case.get("runs", [])
            if len(runs) < 2:
                self.warnings.append(f"{case_id}: runs 少于 2 次，无法计算一致性 (std 无意义)")
            else:
                # 检查数值字段
                has_numeric = False
                for run in runs:
                    for key, value in run.items():
                        if isinstance(value, (int, float)):
                            has_numeric = True
                            break
                if not has_numeric:
                    self.errors.append(f"{case_id}: runs 中没有数值字段，无法计算一致性")
            
            # 因果有效性
            causal_edges = case.get("causal_edges", [])
            if not causal_edges:
                self.warnings.append(f"{case_id}: 缺少 causal_edges")
            else:
                for j, edge in enumerate(causal_edges):
                    edge_id = f"{case_id}.causal_edges[{j}]"
                    if "is_valid" not in edge:
                        self.errors.append(f"{edge_id}: 缺少 is_valid (标注)")
            
            # 时间连贯性
            temporal_scores = case.get("temporal_scores", [])
            if not temporal_scores:
                self.warnings.append(f"{case_id}: 缺少 temporal_scores (专家评分)")
            else:
                for score in temporal_scores:
                    if not isinstance(score, (int, float)):
                        self.errors.append(f"{case_id}: temporal_scores 必须是数字列表")
                    elif not (1 <= score <= 5):
                        self.warnings.append(f"{case_id}: temporal_scores 应在 [1,5] 范围内")
    
    def _validate_insight(self, insight_data: Dict[str, Any]) -> None:
        """验证洞察质量指标数据"""
        outputs = insight_data.get("outputs", [])
        if not outputs:
            self.warnings.append("insight 为空：无法计算洞察质量指标")
            return
        
        for i, item in enumerate(outputs):
            item_id = f"insight.outputs[{i}]"
            
            # 新颖性
            text = item.get("text")
            if not text:
                self.errors.append(f"{item_id}: 缺少 text (报告文本)")
            
            kb_texts = item.get("knowledge_base_texts", [])
            if not kb_texts:
                self.warnings.append(f"{item_id}: 缺少 knowledge_base_texts，无法计算新颖性")
            
            # 推理深度
            reasoning_chains = item.get("reasoning_chains", [])
            if not reasoning_chains:
                self.warnings.append(f"{item_id}: 缺少 reasoning_chains")
            
            evidence_counts = item.get("evidence_counts", [])
            if not evidence_counts:
                self.warnings.append(f"{item_id}: 缺少 evidence_counts")
            
            # 专家评分
            expert_scores = item.get("expert_scores", {})
            usefulness = expert_scores.get("usefulness", [])
            innovation = expert_scores.get("innovation", [])
            logic = expert_scores.get("logic", [])
            
            if not (usefulness and innovation and logic):
                self.errors.append(
                    f"{item_id}: 缺少完整的 expert_scores "
                    "(需要 usefulness, innovation, logic)"
                )
            else:
                # 验证是否有至少 1-3 个专家评分
                if len(usefulness) == 0:
                    self.warnings.append(f"{item_id}: 没有专家评分数据")
                elif len(usefulness) < 3:
                    self.warnings.append(
                        f"{item_id}: 只有 {len(usefulness)} 个专家评分，"
                        "建议至少 3 个"
                    )


def print_validation_report(
    is_valid: bool,
    errors: List[str],
    warnings: List[str],
    verbose: bool = True
) -> str:
    """生成验证报告"""
    lines = []
    
    if is_valid:
        lines.append("✅ 数据验证通过！")
    else:
        lines.append("❌ 数据验证失败")
    
    if errors:
        lines.append(f"\n🔴 错误 ({len(errors)} 个)：")
        for err in errors:
            lines.append(f"  • {err}")
    
    if warnings:
        lines.append(f"\n🟡 警告 ({len(warnings)} 个)：")
        for warn in warnings:
            lines.append(f"  • {warn}")
    
    if not errors and not warnings:
        lines.append("\n无任何问题")
    
    report = "\n".join(lines)
    if verbose:
        print(report)
    return report


if __name__ == "__main__":
    # 测试数据
    test_payload = {
        "retrieval": [
            {
                "query_text": "test query",
                "gold_doc_ids": ["doc_1", "doc_2"],
                "top_k_doc_ids": ["doc_1", "doc_3"],
                "result_texts": ["text1", "text2"]
            }
        ],
        "kg": {
            "gold_entities": ["A", "B", "C"],
            "graph_entities": ["A", "B"],
            "triples": [
                {"head": "A", "rel": "rel1", "tail": "B", "is_correct": True}
            ],
            "nodes": ["A", "B"],
            "edges": [["A", "B"]]
        },
        "multi_agent": {
            "cases": [
                {
                    "agent_answers": ["ans1", "ans2"],
                    "p_single": 0.5,
                    "p_multi": 0.7,
                    "initial_conflicts": 1,
                    "resolved_conflicts": 1
                }
            ]
        },
        "simulation": {
            "cases": [
                {
                    "future_scenarios": ["s1", "s2", "s3"],
                    "runs": [
                        {"prob": 0.6},
                        {"prob": 0.65}
                    ],
                    "causal_edges": [{"edge": "A->B", "is_valid": True}],
                    "temporal_scores": [4, 4, 5]
                }
            ]
        },
        "insight": {
            "outputs": [
                {
                    "text": "report text",
                    "knowledge_base_texts": ["kb1", "kb2"],
                    "reasoning_chains": [["e1", "e2"]],
                    "evidence_counts": [2, 3],
                    "expert_scores": {
                        "usefulness": [4, 4, 4],
                        "innovation": [3, 3, 4],
                        "logic": [4, 4, 4]
                    }
                }
            ]
        }
    }
    
    validator = DataValidator()
    is_valid, errors, warnings = validator.validate_payload(test_payload)
    print_validation_report(is_valid, errors, warnings, verbose=True)
