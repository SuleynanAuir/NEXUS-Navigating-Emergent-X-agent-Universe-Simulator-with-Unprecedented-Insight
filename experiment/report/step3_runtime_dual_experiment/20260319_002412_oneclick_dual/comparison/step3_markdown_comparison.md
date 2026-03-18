# Step3 Markdown 补充材料对比实验报告

- 生成时间: 2026-03-19T00:25:11
- 无 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_002412_oneclick_dual/without/pipeline_metrics.json`
- 有 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/step3_runtime_dual_experiment/20260319_002412_oneclick_dual/with/pipeline_metrics.json`
- 聚焦指标数量（Step3 + KG）: `72`

## 1) Markdown 优势总览

- `Markdown Advantage Index` = `24.309` （越高表示综合净收益越强）
- 有利指标数/总数: `36`/`110` (32.73%)
- 净收益（方向校正后）: `+1.164785`，风险改善: `+0.019024`
- Gate 变化: 新增通过 `1`，丢失通过 `0`

## 2) EIS 对比

- `step2_eis`: 无补充=0.389431, 有补充=0.389431
- `step3_eis`: 无补充=0.580651, 有补充=0.670678
- `delta_eis`: 无补充=0.191219, 有补充=0.281246
- `step3_eis` 变化: +0.090027 (+15.50%)

## 3) 核心五维指标对比（沿用原有量化指标）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| retrieval_quality | 0.861962 | 0.875330 | +0.013368 | +1.55% |
| kg_quality | 0.352050 | 0.671167 | +0.319117 | +90.65% |
| multi_agent_quality | 0.681694 | 0.697290 | +0.015596 | +2.29% |
| simulation_quality | 0.624924 | 0.638292 | +0.013368 | +2.14% |
| insight_quality | 0.510102 | 0.522351 | +0.012249 | +2.40% |

## 4) 变化幅度最大的指标（Top 15）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| kg_quality | 0.352050 | 0.671167 | +0.319117 | +90.65% |
| markdown_supplement_signal | 0.000000 | 0.259723 | +0.259723 | +100.00% |
| report_structure_quality | 0.500000 | 0.250000 | -0.250000 | -50.00% |
| report_actionability | 0.500000 | 0.692727 | +0.192727 | +38.55% |
| graph_density_proxy | 0.503080 | 0.614931 | +0.111851 | +22.23% |
| relation_consistency | 0.721739 | 0.771945 | +0.050206 | +6.96% |
| report_query_alignment | 0.054037 | 0.090909 | +0.036872 | +68.23% |
| agent_query_relevance | 0.500000 | 0.531192 | +0.031192 | +6.24% |
| interaction_coherence | 0.061187 | 0.090151 | +0.028964 | +47.34% |
| kg_risk | 0.378261 | 0.353753 | -0.024508 | -6.48% |
| agent_disagreement_risk | 0.111111 | 0.088831 | -0.022280 | -20.05% |
| claim_structurality | 0.156522 | 0.178801 | +0.022280 | +14.23% |
| agent_bridge_coherence | 0.728007 | 0.750287 | +0.022280 | +3.06% |
| confidence_signal | 0.000000 | 0.020052 | +0.020052 | +100.00% |
| canyon_interaction_risk | 0.387763 | 0.369939 | -0.017824 | -4.60% |

## 5) 差异高亮（正向收益 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| kg_quality | higher_better | 0.352050 | 0.671167 | +0.319117 | +0.319117 |
| markdown_supplement_signal | higher_better | 0.000000 | 0.259723 | +0.259723 | +0.259723 |
| report_actionability | higher_better | 0.500000 | 0.692727 | +0.192727 | +0.192727 |
| graph_density_proxy | higher_better | 0.503080 | 0.614931 | +0.111851 | +0.111851 |
| relation_consistency | higher_better | 0.721739 | 0.771945 | +0.050206 | +0.050206 |
| report_query_alignment | higher_better | 0.054037 | 0.090909 | +0.036872 | +0.036872 |
| agent_query_relevance | higher_better | 0.500000 | 0.531192 | +0.031192 | +0.031192 |
| interaction_coherence | higher_better | 0.061187 | 0.090151 | +0.028964 | +0.028964 |
| kg_risk | lower_better | 0.378261 | 0.353753 | +0.024508 | -0.024508 |
| agent_disagreement_risk | lower_better | 0.111111 | 0.088831 | +0.022280 | -0.022280 |

## 6) 差异高亮（负向回退 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| report_structure_quality | higher_better | 0.500000 | 0.250000 | -0.250000 | -0.250000 |
| report_length_score | higher_better | 0.020000 | 0.007500 | -0.012500 | -0.012500 |
| novelty | higher_better | 0.989254 | 0.978176 | -0.011077 | -0.011077 |
| insight_quality_agentd | higher_better | 0.618991 | 0.615889 | -0.003102 | -0.003102 |

## 7) 主题收益分组

| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |
|---|---:|---:|---:|---:|---:|
| knowledge_graph | 24 | 8 | 0 | +0.530113 | +0.022088 |
| multi_agent | 23 | 10 | 0 | +0.194947 | +0.008476 |
| simulation | 17 | 7 | 0 | +0.109171 | +0.006422 |
| insight_report | 18 | 7 | 3 | +0.016107 | +0.000895 |

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
- `overall_risk` 变化: -0.019024 (-5.77%)
