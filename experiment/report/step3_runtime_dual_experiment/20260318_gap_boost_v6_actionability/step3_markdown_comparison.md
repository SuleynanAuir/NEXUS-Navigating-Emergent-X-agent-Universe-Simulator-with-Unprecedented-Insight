# Step3 Markdown 补充材料对比实验报告

- 生成时间: 2026-03-18T22:33:04
- 无 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/pipeline_metrics/20260318_gap_boost_v6_actionability/without/pipeline_metrics.json`
- 有 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/pipeline_metrics/20260318_gap_boost_v6_actionability/with/pipeline_metrics.json`
- 聚焦指标数量（Step3 + KG）: `72`

## 1) Markdown 优势总览

- `Markdown Advantage Index` = `47.237` （越高表示综合净收益越强）
- 有利指标数/总数: `38`/`110` (34.55%)
- 净收益（方向校正后）: `+3.521409`，风险改善: `+0.077215`
- Gate 变化: 新增通过 `3`，丢失通过 `0`

## 2) EIS 对比

- `step2_eis`: 无补充=0.361564, 有补充=0.361564
- `step3_eis`: 无补充=0.559870, 有补充=0.692262
- `delta_eis`: 无补充=0.198306, 有补充=0.330698
- `step3_eis` 变化: +0.132392 (+23.65%)

## 3) 核心五维指标对比（沿用原有量化指标）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| retrieval_quality | 0.861962 | 0.916189 | +0.054227 | +6.29% |
| kg_quality | 0.352050 | 0.710811 | +0.358761 | +101.91% |
| multi_agent_quality | 0.524502 | 0.587767 | +0.063265 | +12.06% |
| simulation_quality | 0.624924 | 0.679151 | +0.054227 | +8.68% |
| insight_quality | 0.563390 | 0.618736 | +0.055346 | +9.82% |

## 4) 变化幅度最大的指标（Top 15）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| markdown_supplement_signal | 0.000000 | 0.590091 | +0.590091 | +100.00% |
| kg_quality | 0.352050 | 0.710811 | +0.358761 | +101.91% |
| report_length_score | 0.698750 | 1.000000 | +0.301250 | +43.11% |
| graph_density_proxy | 0.503080 | 0.697523 | +0.194443 | +38.65% |
| agent_query_relevance | 0.525000 | 0.651530 | +0.126530 | +24.10% |
| interaction_coherence | 0.061187 | 0.178679 | +0.117492 | +192.02% |
| relation_consistency | 0.721739 | 0.838018 | +0.116279 | +16.11% |
| kg_risk | 0.378261 | 0.278844 | -0.099417 | -26.28% |
| agent_disagreement_risk | 0.927009 | 0.836630 | -0.090379 | -9.75% |
| agent_bridge_coherence | 0.293456 | 0.383835 | +0.090379 | +30.80% |
| claim_structurality | 0.156522 | 0.246900 | +0.090379 | +57.74% |
| report_evidence_quality | 0.333333 | 0.416667 | +0.083333 | +25.00% |
| confidence_signal | 0.000000 | 0.081341 | +0.081341 | +100.00% |
| canyon_interaction_risk | 0.387763 | 0.315460 | -0.072303 | -18.65% |
| graph_reasoning_signal | 0.309096 | 0.381399 | +0.072303 | +23.39% |

## 5) 差异高亮（正向收益 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| markdown_supplement_signal | higher_better | 0.000000 | 0.590091 | +0.590091 | +0.590091 |
| kg_quality | higher_better | 0.352050 | 0.710811 | +0.358761 | +0.358761 |
| report_length_score | higher_better | 0.698750 | 1.000000 | +0.301250 | +0.301250 |
| graph_density_proxy | higher_better | 0.503080 | 0.697523 | +0.194443 | +0.194443 |
| agent_query_relevance | higher_better | 0.525000 | 0.651530 | +0.126530 | +0.126530 |
| interaction_coherence | higher_better | 0.061187 | 0.178679 | +0.117492 | +0.117492 |
| relation_consistency | higher_better | 0.721739 | 0.838018 | +0.116279 | +0.116279 |
| kg_risk | lower_better | 0.378261 | 0.278844 | +0.099417 | -0.099417 |
| agent_disagreement_risk | lower_better | 0.927009 | 0.836630 | +0.090379 | -0.090379 |
| agent_bridge_coherence | higher_better | 0.293456 | 0.383835 | +0.090379 | +0.090379 |

## 6) 差异高亮（负向回退 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| novelty | higher_better | 0.931598 | 0.885614 | -0.045984 | -0.045984 |
| insight_quality_agentd | higher_better | 0.636847 | 0.623972 | -0.012876 | -0.012876 |
| report_coherence | higher_better | 0.882046 | 0.876001 | -0.006044 | -0.006044 |

## 7) 主题收益分组

| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |
|---|---:|---:|---:|---:|---:|
| knowledge_graph | 24 | 9 | 0 | +1.038722 | +0.043280 |
| multi_agent | 23 | 11 | 0 | +0.797378 | +0.034669 |
| simulation | 17 | 7 | 0 | +0.442856 | +0.026050 |
| insight_report | 18 | 8 | 2 | +0.602136 | +0.033452 |

## 8) 质量门槛（quality_gates）对比

| Gate | 无 Markdown | 有 Markdown |
|---|---|---|
| insight_ge_0_60 | False | True |
| kg_ge_0_60 | False | True |
| multi_agent_ge_0_55 | False | True |
| overall_eis_ge_0_70 | False | False |
| retrieval_ge_0_75 | True | True |
| simulation_ge_0_80 | False | False |

## 9) 结论摘要

- `bottleneck_dimension` 无补充: `kg_quality`
- `bottleneck_dimension` 有补充: `multi_agent_quality`
- `overall_risk` 变化: -0.077215 (-16.50%)
