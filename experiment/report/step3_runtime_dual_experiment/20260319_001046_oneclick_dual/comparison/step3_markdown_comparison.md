# Step3 Markdown 补充材料对比实验报告

- 生成时间: 2026-03-19T00:12:19
- 无 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_001046_oneclick_dual/without/pipeline_metrics.json`
- 有 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_001046_oneclick_dual/with/pipeline_metrics.json`
- 聚焦指标数量（Step3 + KG）: `72`

## 1) Markdown 优势总览

- `Markdown Advantage Index` = `24.110` （越高表示综合净收益越强）
- 有利指标数/总数: `35`/`110` (31.82%)
- 净收益（方向校正后）: `+1.142037`，风险改善: `+0.018916`
- Gate 变化: 新增通过 `1`，丢失通过 `0`

## 2) EIS 对比

- `step2_eis`: 无补充=0.387161, 有补充=0.387161
- `step3_eis`: 无补充=0.578379, 有补充=0.668279
- `delta_eis`: 无补充=0.191218, 有补充=0.281118
- `step3_eis` 变化: +0.089900 (+15.54%)

## 3) 核心五维指标对比（沿用原有量化指标）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| retrieval_quality | 0.861962 | 0.875276 | +0.013314 | +1.54% |
| kg_quality | 0.352050 | 0.671098 | +0.319048 | +90.63% |
| multi_agent_quality | 0.670078 | 0.685610 | +0.015532 | +2.32% |
| simulation_quality | 0.624924 | 0.638238 | +0.013314 | +2.13% |
| insight_quality | 0.510359 | 0.522216 | +0.011857 | +2.32% |

## 4) 变化幅度最大的指标（Top 15）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| kg_quality | 0.352050 | 0.671098 | +0.319048 | +90.63% |
| markdown_supplement_signal | 0.000000 | 0.259151 | +0.259151 | +100.00% |
| report_structure_quality | 0.500000 | 0.250000 | -0.250000 | -50.00% |
| report_actionability | 0.500000 | 0.693813 | +0.193813 | +38.76% |
| graph_density_proxy | 0.503080 | 0.614788 | +0.111708 | +22.20% |
| relation_consistency | 0.721739 | 0.771830 | +0.050091 | +6.94% |
| report_query_alignment | 0.055394 | 0.098667 | +0.043273 | +78.12% |
| agent_query_relevance | 0.500000 | 0.531065 | +0.031065 | +6.21% |
| interaction_coherence | 0.061187 | 0.090033 | +0.028846 | +47.14% |
| kg_risk | 0.378261 | 0.353853 | -0.024408 | -6.45% |
| agent_disagreement_risk | 0.111111 | 0.088922 | -0.022189 | -19.97% |
| agent_bridge_coherence | 0.641900 | 0.664089 | +0.022189 | +3.46% |
| claim_structurality | 0.156522 | 0.178711 | +0.022189 | +14.18% |
| confidence_signal | 0.000000 | 0.019970 | +0.019970 | +100.00% |
| canyon_interaction_risk | 0.387763 | 0.370011 | -0.017751 | -4.58% |

## 5) 差异高亮（正向收益 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| kg_quality | higher_better | 0.352050 | 0.671098 | +0.319048 | +0.319048 |
| markdown_supplement_signal | higher_better | 0.000000 | 0.259151 | +0.259151 | +0.259151 |
| report_actionability | higher_better | 0.500000 | 0.693813 | +0.193813 | +0.193813 |
| graph_density_proxy | higher_better | 0.503080 | 0.614788 | +0.111708 | +0.111708 |
| relation_consistency | higher_better | 0.721739 | 0.771830 | +0.050091 | +0.050091 |
| report_query_alignment | higher_better | 0.055394 | 0.098667 | +0.043273 | +0.043273 |
| agent_query_relevance | higher_better | 0.500000 | 0.531065 | +0.031065 | +0.031065 |
| interaction_coherence | higher_better | 0.061187 | 0.090033 | +0.028846 | +0.028846 |
| kg_risk | lower_better | 0.378261 | 0.353853 | +0.024408 | -0.024408 |
| agent_disagreement_risk | lower_better | 0.111111 | 0.088922 | +0.022189 | -0.022189 |

## 6) 差异高亮（负向回退 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| report_structure_quality | higher_better | 0.500000 | 0.250000 | -0.250000 | -0.250000 |
| report_coherence | higher_better | 0.681818 | 0.669228 | -0.012591 | -0.012591 |
| report_length_score | higher_better | 0.020000 | 0.007500 | -0.012500 | -0.012500 |
| novelty | higher_better | 0.990201 | 0.979956 | -0.010245 | -0.010245 |
| insight_quality_agentd | higher_better | 0.619256 | 0.616388 | -0.002869 | -0.002869 |

## 7) 主题收益分组

| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |
|---|---:|---:|---:|---:|---:|
| knowledge_graph | 24 | 8 | 0 | +0.529498 | +0.022062 |
| multi_agent | 23 | 10 | 0 | +0.194156 | +0.008442 |
| simulation | 17 | 7 | 0 | +0.108727 | +0.006396 |
| insight_report | 18 | 6 | 4 | -0.004874 | -0.000271 |

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
- `overall_risk` 变化: -0.018916 (-5.72%)
