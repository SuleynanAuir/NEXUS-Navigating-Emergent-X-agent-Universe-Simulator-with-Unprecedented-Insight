from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


EPS = 1e-9


def _safe_div(numerator: float, denominator: float) -> float:
    if abs(denominator) < EPS:
        return 0.0
    return numerator / denominator


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _tokenize(text: str) -> List[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in (text or ""))
    return [tok for tok in cleaned.split() if tok]


def _cosine_sim_text(a: str, b: str) -> float:
    ta = Counter(_tokenize(a))
    tb = Counter(_tokenize(b))
    if not ta or not tb:
        return 0.0
    common = set(ta) & set(tb)
    dot = sum(ta[k] * tb[k] for k in common)
    na = math.sqrt(sum(v * v for v in ta.values()))
    nb = math.sqrt(sum(v * v for v in tb.values()))
    if na < EPS or nb < EPS:
        return 0.0
    return _clip01(dot / (na * nb))


def _avg_pairwise_similarity(texts: List[str]) -> float:
    n = len(texts)
    if n < 2:
        return 0.0
    sims: List[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            sims.append(_cosine_sim_text(texts[i], texts[j]))
    return sum(sims) / len(sims) if sims else 0.0


def _avg(values: Iterable[float]) -> float:
    vals = [v for v in values]
    return sum(vals) / len(vals) if vals else 0.0


def _std(values: List[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _build_adj(nodes: List[str], edges: List[Tuple[str, str]]) -> Dict[str, set]:
    adj = {node: set() for node in nodes}
    for u, v in edges:
        if u not in adj:
            adj[u] = set()
        if v not in adj:
            adj[v] = set()
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _largest_connected_component_ratio(nodes: List[str], edges: List[Tuple[str, str]]) -> float:
    if not nodes:
        return 0.0
    adj = _build_adj(nodes, edges)
    seen = set()
    largest = 0

    for node in nodes:
        if node in seen:
            continue
        stack = [node]
        size = 0
        seen.add(node)
        while stack:
            cur = stack.pop()
            size += 1
            for nxt in adj.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        largest = max(largest, size)

    return _safe_div(largest, len(nodes))


def _normalize_gain(gain: float) -> float:
    if gain <= 0:
        return 0.0
    return _clip01(gain / (1.0 + gain))


@dataclass
class DimensionScores:
    retrieval_quality: float
    kg_quality: float
    multi_agent_collaboration: float
    simulation_capability: float
    insight_quality: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "retrieval_quality": self.retrieval_quality,
            "kg_quality": self.kg_quality,
            "multi_agent_collaboration": self.multi_agent_collaboration,
            "simulation_capability": self.simulation_capability,
            "insight_quality": self.insight_quality,
        }


class EmergentMetricsEngine:
    """NEXUS experiment metrics engine covering 5 dimensions + EIS."""

    def evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        retrieval = self._eval_retrieval(payload.get("retrieval", []), payload.get("k", 10))
        kg = self._eval_kg(payload.get("kg", {}))
        multi_agent = self._eval_multi_agent(payload.get("multi_agent", {}))
        simulation = self._eval_simulation(payload.get("simulation", {}))
        insight = self._eval_insight(payload.get("insight", {}))

        dim = DimensionScores(
            retrieval_quality=_avg([
                retrieval["Recall@K"],
                retrieval["Precision@K"],
                retrieval["Diversity"],
            ]),
            kg_quality=_avg([
                kg["EntityCoverage"],
                kg["RelationAccuracy"],
                kg["GraphConnectivity"],
            ]),
            multi_agent_collaboration=_avg([
                multi_agent["AgentDiversity"],
                multi_agent["GainNormalized"],
                multi_agent["ConflictResolutionRate"],
            ]),
            simulation_capability=_avg([
                simulation["ScenarioDiversity"],
                simulation["PredictionConsistency"],
                simulation["CausalValidity"],
                simulation["TemporalCoherence"],
            ]),
            insight_quality=_avg([
                insight["Novelty"],
                insight["ReasoningDepth"],
                insight["ExpertScore"],
            ]),
        )

        eis_result = self._eval_eis(
            dim_scores=dim.to_dict(),
            baseline=payload.get("baselines", {}).get("best_baseline", {}),
            weights=payload.get("weights", {}),
        )

        return {
            "retrieval_metrics": retrieval,
            "kg_metrics": kg,
            "multi_agent_metrics": multi_agent,
            "simulation_metrics": simulation,
            "insight_metrics": insight,
            "dimension_scores": dim.to_dict(),
            "EIS": eis_result,
        }

    def _eval_retrieval(self, retrieval_cases: List[Dict[str, Any]], k: int) -> Dict[str, float]:
        recalls = []
        precisions = []
        diversities = []

        for case in retrieval_cases:
            top_k = [str(x) for x in (case.get("top_k_doc_ids", [])[:k])]
            gold = {str(x) for x in case.get("gold_doc_ids", [])}
            relevant = [doc_id for doc_id in top_k if doc_id in gold]

            # Recall: 相关文档 / 所有相关文档
            recall = _safe_div(len(relevant), max(1, len(gold)))
            # Precision: 相关文档 / 返回的文档
            precision = _safe_div(len(relevant), max(1, len(top_k)))

            # 多样性: 基于文本相似度
            texts = [str(x) for x in case.get("result_texts", [])]
            if len(texts) < 2:
                # 文本数量不足，无法评估多样性
                diversity = 0.0
            else:
                avg_sim = _avg_pairwise_similarity(texts)
                diversity = _clip01(1.0 - avg_sim)

            recalls.append(_clip01(recall))
            precisions.append(_clip01(precision))
            diversities.append(diversity)

        return {
            "Recall@K": _avg(recalls),
            "Precision@K": _avg(precisions),
            "Diversity": _avg(diversities),
        }

    def _eval_kg(self, kg_data: Dict[str, Any]) -> Dict[str, float]:
        # 实体覆盖: 提取的实体中有多少在黄金集中
        e_gold = {str(x) for x in kg_data.get("gold_entities", [])}
        e_graph = {str(x) for x in kg_data.get("graph_entities", [])}
        
        if not e_gold:
            coverage = 0.0
        else:
            coverage = _safe_div(len(e_gold & e_graph), len(e_gold))

        # 关系准确性: 正确的三元组占比
        triples = kg_data.get("triples", [])
        if not triples:
            relation_acc = 0.0
        else:
            correct = sum(1 for item in triples if item.get("is_correct") is True)
            relation_acc = _safe_div(correct, len(triples))

        # 图连通性: 最大连通分量占比
        nodes = [str(x) for x in kg_data.get("nodes", [])]
        edges = []
        for edge in kg_data.get("edges", []):
            if isinstance(edge, (list, tuple)) and len(edge) >= 2:
                u, v = str(edge[0]), str(edge[1])
                if u in nodes and v in nodes:
                    edges.append((u, v))

        if not nodes:
            connectivity = 0.0
        elif not edges:
            # 没有边, 如果有节点则孤立
            connectivity = _safe_div(1, len(nodes)) if nodes else 0.0
        else:
            connectivity = _largest_connected_component_ratio(nodes, edges)

        return {
            "EntityCoverage": _clip01(coverage),
            "RelationAccuracy": _clip01(relation_acc),
            "GraphConnectivity": _clip01(connectivity),
        }

    def _eval_multi_agent(self, multi_data: Dict[str, Any]) -> Dict[str, float]:
        cases = multi_data.get("cases", [])
        diversities = []
        gains = []
        resolutions = []

        for case in cases:
            # 多智能体多样性: 答案间的差异度
            answers = [str(x) for x in case.get("agent_answers", [])]
            if len(answers) < 2:
                diversities.append(0.0)
            else:
                avg_sim = _avg_pairwise_similarity(answers)
                diversities.append(_clip01(1.0 - avg_sim))

            # 增益计算: 必须有 p_single 和 p_multi
            p_single = float(case.get("p_single", 0.0) or 0.0)
            p_multi = float(case.get("p_multi", 0.0) or 0.0)
            
            if p_single < EPS:
                # p_single 为 0, 无法计算相对增益
                gain_raw = 0.0
            else:
                gain_raw = (p_multi - p_single) / p_single
            
            gains.append(_normalize_gain(gain_raw))

            # 冲突解决率: 已解决冲突 / 初始冲突
            total_conflicts = int(case.get("initial_conflicts", 0) or 0)
            resolved_conflicts = int(case.get("resolved_conflicts", 0) or 0)
            
            if total_conflicts == 0:
                resolutions.append(0.0)
            else:
                resolutions.append(_clip01(_safe_div(resolved_conflicts, total_conflicts)))

        return {
            "AgentDiversity": _avg(diversities),
            "GainNormalized": _avg(gains),
            "ConflictResolutionRate": _avg(resolutions),
        }

    def _eval_simulation(self, sim_data: Dict[str, Any]) -> Dict[str, float]:
        scenarios = sim_data.get("cases", [])
        scenario_diversities = []
        consistency_scores = []
        causal_validities = []
        temporal_scores = []

        for case in scenarios:
            # 场景多样性
            future_scenarios = [str(x) for x in case.get("future_scenarios", [])]
            if len(future_scenarios) < 2:
                scenario_diversities.append(0.0)
            else:
                avg_sim = _avg_pairwise_similarity(future_scenarios)
                scenario_diversities.append(_clip01(1.0 - avg_sim))

            # 预测一致性: 多次运行的数值稳定性
            runs = case.get("runs", [])
            if not runs:
                consistency_scores.append(0.0)
            else:
                numeric_columns: Dict[str, List[float]] = defaultdict(list)
                for run in runs:
                    for key, value in run.items():
                        if isinstance(value, (int, float)):
                            numeric_columns[key].append(float(value))
                
                if not numeric_columns:
                    consistency_scores.append(0.0)
                else:
                    stds = [_std(vals) for vals in numeric_columns.values() if vals]
                    if not stds:
                        consistency_scores.append(0.0)
                    else:
                        mean_std = _avg(stds)
                        consistency = _safe_div(1.0, 1.0 + mean_std)
                        consistency_scores.append(_clip01(consistency))

            # 因果有效性: 有效的因果边占比
            causal_edges = case.get("causal_edges", [])
            if not causal_edges:
                causal_validities.append(0.0)
            else:
                valid_edges = sum(1 for edge in causal_edges if edge.get("is_valid") is True)
                causal_validity = _safe_div(valid_edges, len(causal_edges))
                causal_validities.append(_clip01(causal_validity))

            # 时间连贯性: 专家标注的时间得分平均
            expert_temporal_scores = [
                float(x) for x in case.get("temporal_scores", [])
                if isinstance(x, (int, float))
            ]
            if not expert_temporal_scores:
                temporal_scores.append(0.0)
            else:
                avg_temporal = _avg(expert_temporal_scores)
                # 假设满分为 5
                temporal_scores.append(_clip01(avg_temporal / 5.0))

        return {
            "ScenarioDiversity": _avg(scenario_diversities),
            "PredictionConsistency": _avg(consistency_scores),
            "CausalValidity": _avg(causal_validities),
            "TemporalCoherence": _avg(temporal_scores),
        }

    def _eval_insight(self, insight_data: Dict[str, Any]) -> Dict[str, float]:
        outputs = insight_data.get("outputs", [])
        novelty_scores = []
        depth_scores = []
        expert_scores = []

        for item in outputs:
            # 新颖性: 与知识库的相似度越低越新
            text = str(item.get("text", ""))
            kb_texts = [str(x) for x in item.get("knowledge_base_texts", [])]
            
            if not kb_texts or not text:
                novelty_scores.append(0.0)
            else:
                sims = [_cosine_sim_text(text, kb) for kb in kb_texts]
                avg_kb_sim = _avg(sims)
                novelty = _clip01(1.0 - avg_kb_sim)
                novelty_scores.append(novelty)

            # 推理深度: 推理链长度和证据数量
            reasoning_chains = item.get("reasoning_chains", [])
            chain_lens = [len(chain) for chain in reasoning_chains if isinstance(chain, list)]
            
            evidence_counts = [
                float(x) for x in item.get("evidence_counts", [])
                if isinstance(x, (int, float))
            ]
            
            if not chain_lens or not evidence_counts:
                depth_scores.append(0.0)
            else:
                avg_chain_len = _avg([float(x) for x in chain_lens])
                avg_evidence = _avg(evidence_counts)
                # 推理链长度 (最多 5), 证据数量 (最多 5)
                depth = _clip01(0.5 * (avg_chain_len / 5.0) + 0.5 * (avg_evidence / 5.0))
                depth_scores.append(depth)

            # 专家评分: usefulness, innovation, logic 的平均 (满分 5)
            exp = item.get("expert_scores", {})
            usefulness = _avg([
                float(x) for x in exp.get("usefulness", [])
                if isinstance(x, (int, float))
            ])
            innovation = _avg([
                float(x) for x in exp.get("innovation", [])
                if isinstance(x, (int, float))
            ])
            logic = _avg([
                float(x) for x in exp.get("logic", [])
                if isinstance(x, (int, float))
            ])
            
            scores = [s for s in [usefulness, innovation, logic] if s > 0]
            if not scores:
                expert_scores.append(0.0)
            else:
                avg_expert = _avg(scores)
                expert_scores.append(_clip01(avg_expert / 5.0))

        return {
            "Novelty": _avg(novelty_scores),
            "ReasoningDepth": _avg(depth_scores),
            "ExpertScore": _avg(expert_scores),
        }

    def _eval_eis(
        self,
        dim_scores: Dict[str, float],
        baseline: Dict[str, float],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        all_dims = [
            "retrieval_quality",
            "kg_quality",
            "multi_agent_collaboration",
            "simulation_capability",
            "insight_quality",
        ]

        default_w = _safe_div(1.0, len(all_dims))
        dim_weights = {d: float(weights.get(d, default_w)) for d in all_dims}

        w_sum = sum(dim_weights.values())
        if w_sum > EPS:
            dim_weights = {k: v / w_sum for k, v in dim_weights.items()}

        improvements: Dict[str, float] = {}
        eis = 0.0
        for dim in all_dims:
            p_nexus = float(dim_scores.get(dim, 0.0))
            p_base = float(baseline.get(dim, 0.0))
            rel_gain = _safe_div((p_nexus - p_base), p_base) if p_base > EPS else 0.0
            improvements[dim] = rel_gain
            eis += dim_weights[dim] * rel_gain

        return {
            "score": eis,
            "weights": dim_weights,
            "relative_improvements": improvements,
        }


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
