# Step3 Markdown 补充材料对比实验报告

- 生成时间: 2026-03-19T00:56:07
- 无 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_005606_oneclick_dual/without/pipeline_metrics.json`
- 有 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_005606_oneclick_dual/with/pipeline_metrics.json`
- 聚焦指标数量（Step3 + KG）: `72`

## 1) Markdown 优势总览

- `Markdown Advantage Index` = `24.114` （越高表示综合净收益越强）
- 有利指标数/总数: `35`/`110` (31.82%)
- 净收益（方向校正后）: `+1.142719`，风险改善: `+0.018905`
- Gate 变化: 新增通过 `1`，丢失通过 `0`

## 2) EIS 对比

- `step2_eis`: 无补充=0.387072, 有补充=0.387072
- `step3_eis`: 无补充=0.578436, 有补充=0.668377
- `delta_eis`: 无补充=0.191363, 有补充=0.281305
- `step3_eis` 变化: +0.089941 (+15.55%)

## 3) 核心五维指标对比（沿用原有量化指标）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| retrieval_quality | 0.861962 | 0.875312 | +0.013350 | +1.55% |
| kg_quality | 0.352050 | 0.671145 | +0.319095 | +90.64% |
| multi_agent_quality | 0.670084 | 0.685659 | +0.015576 | +2.32% |
| simulation_quality | 0.624924 | 0.638275 | +0.013350 | +2.14% |
| insight_quality | 0.510637 | 0.522535 | +0.011898 | +2.33% |

## 4) 变化幅度最大的指标（Top 15）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| kg_quality | 0.352050 | 0.671145 | +0.319095 | +90.64% |
| markdown_supplement_signal | 0.000000 | 0.259540 | +0.259540 | +100.00% |
| report_structure_quality | 0.500000 | 0.250000 | -0.250000 | -50.00% |
| report_actionability | 0.500000 | 0.693621 | +0.193621 | +38.72% |
| graph_density_proxy | 0.503080 | 0.614885 | +0.111805 | +22.22% |
| relation_consistency | 0.721739 | 0.771908 | +0.050169 | +6.95% |
| report_query_alignment | 0.064444 | 0.097294 | +0.032850 | +50.97% |
| agent_query_relevance | 0.500000 | 0.531151 | +0.031151 | +6.23% |
| interaction_coherence | 0.061187 | 0.090113 | +0.028926 | +47.27% |
| kg_risk | 0.378261 | 0.353785 | -0.024476 | -6.47% |
| agent_disagreement_risk | 0.111111 | 0.088860 | -0.022251 | -20.03% |
| claim_structurality | 0.156522 | 0.178773 | +0.022251 | +14.22% |
| agent_bridge_coherence | 0.641230 | 0.663480 | +0.022251 | +3.47% |
| confidence_signal | 0.000000 | 0.020026 | +0.020026 | +100.00% |
| retrieval_risk | 0.139826 | 0.122025 | -0.017801 | -12.73% |

## 5) 差异高亮（正向收益 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| kg_quality | higher_better | 0.352050 | 0.671145 | +0.319095 | +0.319095 |
| markdown_supplement_signal | higher_better | 0.000000 | 0.259540 | +0.259540 | +0.259540 |
| report_actionability | higher_better | 0.500000 | 0.693621 | +0.193621 | +0.193621 |
| graph_density_proxy | higher_better | 0.503080 | 0.614885 | +0.111805 | +0.111805 |
| relation_consistency | higher_better | 0.721739 | 0.771908 | +0.050169 | +0.050169 |
| report_query_alignment | higher_better | 0.064444 | 0.097294 | +0.032850 | +0.032850 |
| agent_query_relevance | higher_better | 0.500000 | 0.531151 | +0.031151 | +0.031151 |
| interaction_coherence | higher_better | 0.061187 | 0.090113 | +0.028926 | +0.028926 |
| kg_risk | lower_better | 0.378261 | 0.353785 | +0.024476 | -0.024476 |
| agent_disagreement_risk | lower_better | 0.111111 | 0.088860 | +0.022251 | -0.022251 |

## 6) 差异高亮（负向回退 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| report_structure_quality | higher_better | 0.500000 | 0.250000 | -0.250000 | -0.250000 |
| report_length_score | higher_better | 0.020000 | 0.007500 | -0.012500 | -0.012500 |
| novelty | higher_better | 0.988594 | 0.979887 | -0.008708 | -0.008708 |
| report_coherence | higher_better | 0.681818 | 0.678595 | -0.003223 | -0.003223 |
| insight_quality_agentd | higher_better | 0.618806 | 0.616368 | -0.002438 | -0.002438 |

## 7) 主题收益分组

| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |
|---|---:|---:|---:|---:|---:|
| knowledge_graph | 24 | 8 | 0 | +0.529916 | +0.022080 |
| multi_agent | 23 | 10 | 0 | +0.194694 | +0.008465 |
| simulation | 17 | 7 | 0 | +0.109029 | +0.006413 |
| insight_report | 18 | 6 | 4 | -0.007498 | -0.000417 |

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
- `overall_risk` 变化: -0.018905 (-5.71%)
