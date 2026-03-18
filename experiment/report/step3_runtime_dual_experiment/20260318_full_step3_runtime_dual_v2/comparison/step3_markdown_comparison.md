# Step3 Markdown 补充材料对比实验报告

- 生成时间: 2026-03-18T16:27:58
- 无 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/pipeline_metrics/20260318_083051/pipeline_metrics.json`
- 有 Markdown 补充: `/Users/suleynan_suir/Desktop/NEXUS1/experiment/report/pipeline_metrics/20260318_122017/pipeline_metrics.json`
- 聚焦指标数量（Step3 + KG）: `69`

## 1) Markdown 优势总览

- `Markdown Advantage Index` = `67.018` （越高表示综合净收益越强）
- 有利指标数/总数: `80`/`106` (75.47%)
- 净收益（方向校正后）: `+249.645301`，风险改善: `+0.275738`
- Gate 变化: 新增通过 `2`，丢失通过 `0`

## 2) EIS 对比

- `step2_eis`: 无补充=0.339951, 有补充=0.355790
- `step3_eis`: 无补充=0.459323, 有补充=0.708265
- `delta_eis`: 无补充=0.119372, 有补充=0.352475
- `step3_eis` 变化: +0.248943 (+54.20%)

## 3) 核心五维指标对比（沿用原有量化指标）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| retrieval_quality | 0.844141 | 0.848947 | +0.004806 | +0.57% |
| kg_quality | 0.000000 | 0.983729 | +0.983729 | +100.00% |
| multi_agent_quality | 0.466817 | 0.517502 | +0.050685 | +10.86% |
| simulation_quality | 0.748589 | 0.620464 | -0.128125 | -17.12% |
| insight_quality | 0.448102 | 0.536989 | +0.088887 | +19.84% |

## 4) 变化幅度最大的指标（Top 15）

| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |
|---|---:|---:|---:|---:|
| graphrag_relation_count | 0.000000 | 137.000000 | +137.000000 | +100.00% |
| graphrag_entity_count | 0.000000 | 71.000000 | +71.000000 | +100.00% |
| claim_structurality | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| claim_support_ratio | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| confidence_signal | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| entity_coverage | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| evidence_balance | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| evidence_coverage | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| evidence_quality | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| graph_density_proxy | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| integrated_conf | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| interaction_density | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| interview_coverage | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| interview_diversity | 0.000000 | 1.000000 | +1.000000 | +100.00% |
| interview_quote_density | 0.000000 | 1.000000 | +1.000000 | +100.00% |

## 5) 差异高亮（正向收益 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| graphrag_relation_count | higher_better | 0.000000 | 137.000000 | +137.000000 | +137.000000 |
| graphrag_entity_count | higher_better | 0.000000 | 71.000000 | +71.000000 | +71.000000 |
| claim_structurality | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| claim_support_ratio | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| confidence_signal | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| entity_coverage | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| evidence_balance | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| evidence_coverage | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| evidence_quality | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |
| graph_density_proxy | higher_better | 0.000000 | 1.000000 | +1.000000 | +1.000000 |

## 6) 差异高亮（负向回退 Top 10）

| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |
|---|---|---:|---:|---:|---:|
| action_intensity | higher_better | 0.983333 | 0.116667 | -0.866667 | -0.866667 |
| actions_per_round | higher_better | 0.921875 | 0.145833 | -0.776042 | -0.776042 |
| action_balance | higher_better | 0.983051 | 0.457143 | -0.525908 | -0.525908 |
| total_actions | higher_better | 0.590000 | 0.070000 | -0.520000 | -0.520000 |
| simulation_stability | higher_better | 0.991525 | 0.720882 | -0.270643 | -0.270643 |
| insight_length | higher_better | 1.000000 | 0.730000 | -0.270000 | -0.270000 |
| simulation_quality | higher_better | 0.748589 | 0.620464 | -0.128125 | -0.128125 |
| evidence_per_claim | higher_better | 0.666667 | 0.547619 | -0.119048 | -0.119048 |
| novelty | higher_better | 0.934933 | 0.925627 | -0.009306 | -0.009306 |
| agent_diversity | higher_better | 0.973249 | 0.967154 | -0.006095 | -0.006095 |

## 7) 主题收益分组

| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |
|---|---:|---:|---:|---:|---:|
| knowledge_graph | 21 | 19 | 1 | +221.670333 | +10.555730 |
| multi_agent | 23 | 18 | 2 | +6.636301 | +0.288535 |
| simulation | 17 | 11 | 5 | +4.798400 | +0.282259 |
| insight_report | 18 | 14 | 1 | +4.515045 | +0.250836 |

## 8) 质量门槛（quality_gates）对比

| Gate | 无 Markdown | 有 Markdown |
|---|---|---|
| insight_ge_0_60 | False | False |
| kg_ge_0_60 | False | True |
| multi_agent_ge_0_55 | False | False |
| overall_eis_ge_0_70 | False | True |
| retrieval_ge_0_75 | True | True |
| simulation_ge_0_80 | False | False |

## 9) 结论摘要

- `bottleneck_dimension` 无补充: `kg_quality`
- `bottleneck_dimension` 有补充: `multi_agent_quality`
- `overall_risk` 变化: -0.275738 (-41.15%)
