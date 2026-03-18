# Step3 Markdown 补充材料对比实验报告

- 生成时间: 2026-03-19T00:22:03
- 无 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_002046_oneclick_dual/without/pipeline_metrics.json`
- 有 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_002046_oneclick_dual/with/pipeline_metrics.json`
- 聚焦指标数量（Step3 + KG）: `72`

## 1) Markdown 优势总览

- `Markdown Advantage Index` = `24.205` （越高表示综合净收益越强）
- 有利指标数/总数: `36`/`110` (32.73%)
- 净收益（方向校正后）: `+1.140976`，风险改善: `+0.016684`
- Gate 变化: 新增通过 `1`，丢失通过 `0`

## 2) EIS 对比

- `step2_eis`: 无补充=0.392441, 有补充=0.392441
- `step3_eis`: 无补充=0.585085, 有补充=0.675009
- `delta_eis`: 无补充=0.192644, 有补充=0.282568
- `step3_eis` 变化: +0.089924 (+15.37%)

## 3) 核心五维指标对比（沿用原有量化指标）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| retrieval_quality | 0.861962 | 0.875370 | +0.013408 | +1.56% |
| kg_quality | 0.352050 | 0.671218 | +0.319168 | +90.66% |
| multi_agent_quality | 0.696800 | 0.712443 | +0.015643 | +2.25% |
| simulation_quality | 0.624924 | 0.638333 | +0.013408 | +2.15% |
| insight_quality | 0.517166 | 0.528717 | +0.011550 | +2.23% |

## 4) 变化幅度最大的指标（Top 15）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| kg_quality | 0.352050 | 0.671218 | +0.319168 | +90.66% |
| markdown_supplement_signal | 0.000000 | 0.260152 | +0.260152 | +100.00% |
| report_structure_quality | 0.500000 | 0.250000 | -0.250000 | -50.00% |
| report_actionability | 0.500000 | 0.691673 | +0.191673 | +38.33% |
| graph_density_proxy | 0.503080 | 0.615038 | +0.111958 | +22.25% |
| relation_consistency | 0.721739 | 0.772030 | +0.050291 | +6.97% |
| agent_query_relevance | 0.500000 | 0.531286 | +0.031286 | +6.26% |
| interaction_coherence | 0.061187 | 0.090239 | +0.029052 | +47.48% |
| report_query_alignment | 0.055701 | 0.083379 | +0.027678 | +49.69% |
| kg_risk | 0.378261 | 0.353679 | -0.024582 | -6.50% |
| agent_bridge_coherence | 0.795451 | 0.817798 | +0.022347 | +2.81% |
| claim_structurality | 0.156522 | 0.178869 | +0.022347 | +14.28% |
| confidence_signal | 0.000000 | 0.020113 | +0.020113 | +100.00% |
| canyon_interaction_risk | 0.387763 | 0.369885 | -0.017878 | -4.61% |
| graph_reasoning_signal | 0.309096 | 0.326974 | +0.017878 | +5.78% |

## 5) 差异高亮（正向收益 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| kg_quality | higher_better | 0.352050 | 0.671218 | +0.319168 | +0.319168 |
| markdown_supplement_signal | higher_better | 0.000000 | 0.260152 | +0.260152 | +0.260152 |
| report_actionability | higher_better | 0.500000 | 0.691673 | +0.191673 | +0.191673 |
| graph_density_proxy | higher_better | 0.503080 | 0.615038 | +0.111958 | +0.111958 |
| relation_consistency | higher_better | 0.721739 | 0.772030 | +0.050291 | +0.050291 |
| agent_query_relevance | higher_better | 0.500000 | 0.531286 | +0.031286 | +0.031286 |
| interaction_coherence | higher_better | 0.061187 | 0.090239 | +0.029052 | +0.029052 |
| report_query_alignment | higher_better | 0.055701 | 0.083379 | +0.027678 | +0.027678 |
| kg_risk | lower_better | 0.378261 | 0.353679 | +0.024582 | -0.024582 |
| agent_bridge_coherence | higher_better | 0.795451 | 0.817798 | +0.022347 | +0.022347 |

## 6) 差异高亮（负向回退 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| report_structure_quality | higher_better | 0.500000 | 0.250000 | -0.250000 | -0.250000 |
| report_length_score | higher_better | 0.021875 | 0.008125 | -0.013750 | -0.013750 |
| novelty | higher_better | 0.989047 | 0.976668 | -0.012379 | -0.012379 |
| insight_quality_agentd | higher_better | 0.618933 | 0.615467 | -0.003466 | -0.003466 |

## 7) 主题收益分组

| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |
|---|---:|---:|---:|---:|---:|
| knowledge_graph | 24 | 8 | 0 | +0.530573 | +0.022107 |
| multi_agent | 23 | 10 | 0 | +0.183294 | +0.007969 |
| simulation | 17 | 7 | 0 | +0.109502 | +0.006441 |
| insight_report | 18 | 7 | 3 | +0.003901 | +0.000217 |

## 8) 质量门槛（quality_gates）对比

| Gate | 无 Markdown | 有 Markdown |
|---|---|---|
| insight_ge_0_60 | False | False |
| kg_ge_0_60 | False | True |
| multi_agent_ge_0_55 | True | True |
| overall_eis_ge_0_70 | False | False |
| retrieval_ge_0_75 | True | True |
| simulation_ge_0_80 | False | False |

## 9) 结论摘要

- `bottleneck_dimension` 无补充: `kg_quality`
- `bottleneck_dimension` 有补充: `insight_quality`
- `overall_risk` 变化: -0.016684 (-5.41%)
