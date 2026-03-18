# Markdown Ablation Summary

- generated_at: `2026-03-19T00:56:07`
- baseline: `without_markdown`
- variant_count: `5`

## Ranking by Step3 EIS

| variant | step3_eis | delta_vs_baseline | risk_improvement | report_actionability_delta | markdown_signal |
|---|---:|---:|---:|---:|---:|
| full_markdown | 0.668377 | +0.089941 | +0.018905 | +0.193621 | 0.259540 |
| short_excerpt | 0.668250 | +0.089814 | +0.018818 | +0.193813 | 0.258977 |
| plain_text | 0.662291 | +0.083855 | +0.018285 | +0.014214 | 0.255133 |
| action_only | 0.648907 | +0.070471 | +0.003320 | +0.180000 | 0.104867 |
| title_only | 0.642758 | +0.064322 | +0.003451 | -0.372333 | 0.110254 |

## Variant Details

### full_markdown

- `step3_eis_delta`: +0.089941
- `risk_improvement`: +0.018905
- `gained_gates`: kg_ge_0_60
- `report_actionability_delta`: +0.193621
- `kg_quality_delta`: +0.319095
- `insight_quality_delta`: +0.011898
- `top_benefits`: kg_quality (+0.3191), markdown_supplement_signal (+0.2595), report_actionability (+0.1936), graph_density_proxy (+0.1118), relation_consistency (+0.0502)

### short_excerpt

- `step3_eis_delta`: +0.089814
- `risk_improvement`: +0.018818
- `gained_gates`: kg_ge_0_60
- `report_actionability_delta`: +0.193813
- `kg_quality_delta`: +0.319027
- `insight_quality_delta`: +0.011502
- `top_benefits`: kg_quality (+0.3190), markdown_supplement_signal (+0.2590), report_actionability (+0.1938), graph_density_proxy (+0.1117), relation_consistency (+0.0501)

### plain_text

- `step3_eis_delta`: +0.083855
- `risk_improvement`: +0.018285
- `gained_gates`: kg_ge_0_60
- `report_actionability_delta`: +0.014214
- `kg_quality_delta`: +0.318566
- `insight_quality_delta`: -0.016658
- `top_benefits`: kg_quality (+0.3186), markdown_supplement_signal (+0.2551), graph_density_proxy (+0.1107), relation_consistency (+0.0493), report_query_alignment (+0.0371)

### action_only

- `step3_eis_delta`: +0.070471
- `risk_improvement`: +0.003320
- `gained_gates`: kg_ge_0_60
- `report_actionability_delta`: +0.180000
- `kg_quality_delta`: +0.300534
- `insight_quality_delta`: -0.029716
- `top_benefits`: kg_quality (+0.3005), report_actionability (+0.1800), markdown_supplement_signal (+0.1049), graph_density_proxy (+0.0731), relation_consistency (+0.0192)

### title_only

- `step3_eis_delta`: +0.064322
- `risk_improvement`: +0.003451
- `gained_gates`: kg_ge_0_60
- `report_actionability_delta`: -0.372333
- `kg_quality_delta`: +0.301180
- `insight_quality_delta`: -0.061986
- `top_benefits`: kg_quality (+0.3012), markdown_supplement_signal (+0.1103), graph_density_proxy (+0.0745), relation_consistency (+0.0203), agent_query_relevance (+0.0057)

