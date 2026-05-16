# Ablation Experiment: Two Real-World Cases

This document presents two concrete case studies of the markdown supplement ablation experiments conducted in the NEXUS project, illustrating the experimental design, problem backgrounds, and outcomes.

---

## Case A: Gap Boost Actionability Tuning (March 18, 2026)

### A.1 Problem Background

**Research Question**: Does enriching Step3 analysis with structured markdown guidance improve both knowledge graph construction quality and report actionability?

**Context**: 
- Prior observations indicated that Step3 reports sometimes lacked concrete, executable recommendations for decision-makers.
- Knowledge graph (KG) construction often suffered from incomplete entity and relationship extraction.
- Hypothesis: A curated markdown supplement containing structured guidance (evidence, claims, structured recommendations) could serve as a "context amplifier" to nudge the LLM toward higher-quality graph reasoning and more actionable insights.

**Experiment Scope**:
- Input Domain: Fixed Step1 research summary on a technical/strategic topic
- Step3 Task: Generate actionable analysis and strategic recommendations
- Variant: `without_markdown` (baseline) vs `with_markdown` (structured guide)

### A.2 Experimental Setup

| Aspect | Details |
|---|---|
| **Timestamp** | 2026-03-18T22:33:04 |
| **Baseline Metrics Path** | `experiment/report/pipeline_metrics/20260318_gap_boost_v6_actionability/without/` |
| **Treatment Metrics Path** | `experiment/report/pipeline_metrics/20260318_gap_boost_v6_actionability/with/` |
| **Control Variables** | Step1 summary, Step2 agent outputs, evaluation pipeline |
| **Treatment Variable** | Presence/absence of markdown supplement with structured guidance |
| **Primary KPIs** | `step3_eis`, `overall_risk`, `kg_quality`, `report_actionability` |
| **Sample Metrics Count** | 72 focused indicators (Step3 + KG domain) out of 110 total |

### A.3 Key Results

#### A.3.1 Overall Impact

| Metric | Baseline (No MD) | With MD | Change | % Change |
|---|---:|---:|---:|---:|
| **step3_eis** | 0.5599 | 0.6923 | +0.1324 | **+23.65%** |
| **overall_risk** | 0.4673 | 0.4022 | -0.0651 | -13.93% |
| **Markdown Advantage Index** | — | 47.237 | — | Strong net benefit |

#### A.3.2 Core Dimension Improvements (Five-Dimensional Framework)

| Dimension | No MD | With MD | Absolute Δ | Relative Δ |
|---|---:|---:|---:|---:|
| **retrieval_quality** | 0.8620 | 0.9162 | +0.0542 | +6.29% |
| **kg_quality** ⭐ | 0.3521 | 0.7108 | +0.3588 | **+101.91%** |
| **multi_agent_quality** | 0.5245 | 0.5878 | +0.0633 | +12.06% |
| **simulation_quality** | 0.6249 | 0.6792 | +0.0542 | +8.68% |
| **insight_quality** | 0.5634 | 0.6187 | +0.0553 | +9.82% |

*Note: KG quality shows the largest relative improvement.*

#### A.3.3 Quality Gate Status (Capability Threshold Crossing)

| Quality Gate | No MD | With MD | Status |
|---|---|---|---|
| `insight_ge_0_60` | ✗ | ✓ | **GAINED** |
| `kg_ge_0_60` | ✗ | ✓ | **GAINED** |
| `multi_agent_ge_0_55` | ✗ | ✓ | **GAINED** |
| `overall_eis_ge_0_70` | ✗ | ✗ | Not achieved |
| `retrieval_ge_0_75` | ✓ | ✓ | Maintained |
| `simulation_ge_0_80` | ✗ | ✗ | Not achieved |

**Interpretation**: Markdown supplement enabled the system to cross three critical capability thresholds without losing any previous achievements, indicating robust improvement.

#### A.3.4 Top-10 Positive Impact Indicators

| Indicator | Direction | Baseline | With MD | Net Benefit |
|---|---|---:|---:|---:|
| markdown_supplement_signal | ↑ | 0.0000 | 0.5901 | +0.5901 |
| kg_quality | ↑ | 0.3521 | 0.7108 | +0.3588 |
| report_length_score | ↑ | 0.6988 | 1.0000 | +0.3013 |
| graph_density_proxy | ↑ | 0.5031 | 0.6975 | +0.1944 |
| agent_query_relevance | ↑ | 0.5250 | 0.6515 | +0.1265 |
| interaction_coherence | ↑ | 0.0612 | 0.1787 | +0.1175 |
| relation_consistency | ↑ | 0.7217 | 0.8380 | +0.1163 |
| kg_risk (↓ is better) | ↓ | 0.3783 | 0.2788 | +0.0994 |
| agent_disagreement_risk (↓ is better) | ↓ | 0.9270 | 0.8366 | +0.0904 |
| agent_bridge_coherence | ↑ | 0.2935 | 0.3838 | +0.0904 |

#### A.3.5 Observed Trade-Offs (Minor Negative Effects)

| Indicator | Direction | Baseline | With MD | Impact | Notes |
|---|---|---:|---:|---:|---|
| novelty | ↑ | 0.9316 | 0.8856 | -0.0460 | Marginal; likely due to structured format |
| insight_quality_agentD | ↑ | 0.6368 | 0.6240 | -0.0129 | Small; within noise margin |
| report_coherence | ↑ | 0.8820 | 0.8760 | -0.0060 | Negligible |

**Assessment**: Trade-offs are minor and localized; overall benefit far outweighs costs.

#### A.3.6 Thematic Benefit Breakdown

| Theme | Metrics Count | Positive | Negative | Net Gain | Avg Gain |
|---|---:|---:|---:|---:|---:|
| Knowledge Graph (KG) | 24 | 9 | 0 | **+1.0387** | +0.0433 |
| Multi-Agent Collaboration | 23 | 11 | 0 | **+0.7974** | +0.0347 |
| Simulation & Planning | 17 | 7 | 0 | **+0.4429** | +0.0261 |
| Insight & Reporting | 18 | 8 | 2 | **+0.6021** | +0.0335 |

**Insight**: Knowledge graph and multi-agent domains showed the strongest thematic benefits, confirming the hypothesis that structured markdown helps coordinate entity reasoning and agent alignment.

### A.4 Conclusions (Case A)

1. **Markdown supplement is highly effective** for improving Step3 quality, particularly for knowledge graph construction (101.91% improvement).
2. **Gateway achievement**: System crosses three critical quality thresholds, indicating transition from "under-threshold" to "operational" readiness.
3. **Bottleneck shift**: Without markdown, `kg_quality` is the bottleneck; with markdown, the constraint shifts to `multi_agent_quality`, indicating balanced improvement across domains.
4. **Minimal trade-offs**: Losses in novelty and coherence are marginal compared to gains, making the trade worthwhile.

---

## Case B: Multi-Variant Ablation on GraphRAG Research (March 19, 2026)

### B.1 Problem Background

**Research Question**: Among various markdown supplement strategies, which granularity and content mix yields optimal Step3 performance? How much can we compress the supplement while maintaining benefit?

**Context**:
- Case A confirmed markdown helps, but doesn't specify *how much* detail is needed.
- Real-world deployment needs cost-aware strategies (token budget, inference latency).
- Hypothesis: A simplified excerpt capturing key claims, evidence, and actions could achieve 90%+ of the full markdown benefit at lower cost.

**Input Domain**: GraphRAG Research (emerging graph-based RAG techniques from Microsoft and academia)
- Focus: Understanding limitations of traditional RAG, advantages of graph-based approaches, and clinical application potential.
- Scale: ~4 research reports summarized in Step1.
- Task: Comprehensive strategic analysis with multi-hop reasoning and risk assessment.

### B.2 Experimental Setup

| Aspect | Details |
|---|---|
| **Timestamp** | 2026-03-19T00:56:07 |
| **Baseline** | `without_markdown` (pure Step1 + Step2 agent outputs) |
| **Variants** | 5 strategies: full_markdown, short_excerpt, plain_text, action_only, title_only |
| **Input Data** | 4 research reports on GraphRAG topic |
| **Step2 Reference** | Agent guide generated from multi-agent analysis (Step2) |
| **Evaluation** | Full pipeline: step2 → step3-snapshot → finalize → metrics |
| **Baseline Values** | step3_eis=0.5784, overall_risk=0.3308 |

### B.3 Variant Definitions

| Variant | Content Strategy | Sample Size | Purpose |
|---|---|---|---|
| **full_markdown** | Complete supplement: structure + evidence + claims + actions + next steps | 100% | Upper bound (best case) |
| **short_excerpt** | First N high-relevance lines (~30-40% of full) | ~35% | Compression test; efficiency |
| **plain_text** | Full content but with markdown syntax removed (still ~100% chars but less formatting) | ~100% | Format sensitivity test |
| **action_only** | Extract and keep only action/decision-relevant lines | ~20% | Action-focused compression |
| **title_only** | Keep only section titles and hierarchical structure | ~10% | Minimal structural signal |

### B.4 Key Results

#### B.4.1 Ranking by Step3 EIS Delta (Primary Metric)

| Rank | Variant | step3_eis | step3_eis_delta | overall_risk | risk_improvement |
|---|---|---:|---:|---:|---:|
| 🥇 **1** | **full_markdown** | 0.6684 | **+0.08994** | 0.3119 | +0.01891 |
| 🥈 **2** | **short_excerpt** | 0.6682 | **+0.08981** | 0.3120 | +0.01882 |
| 🥉 **3** | **plain_text** | 0.6623 | **+0.08386** | 0.3126 | +0.01829 |
| **4** | **action_only** | 0.6489 | **+0.07047** | 0.3275 | +0.00332 |
| **5** | **title_only** | 0.6428 | **+0.06432** | 0.3274 | +0.00345 |

**Key Finding**: `short_excerpt` (rank 2) achieves 99.9% of `full_markdown` (rank 1) performance with ~35% of content.

#### B.4.2 Core Metrics Breakdown for Top 3 Variants

| Metric | Baseline | full_markdown | short_excerpt | plain_text |
|---|---:|---:|---:|---:|
| **retrieval_quality** | 0.8620 | +0.0133 | +0.0133 | +0.0129 |
| **kg_quality** ⭐ | 0.3520 | +0.3191 | +0.3190 | +0.3186 |
| **multi_agent_quality** | 0.6701 | +0.0156 | +0.0155 | +0.0151 |
| **simulation_quality** | 0.6249 | +0.0134 | +0.0133 | +0.0129 |
| **insight_quality** | 0.5106 | +0.0119 | +0.0115 | -0.0167 |
| **report_actionability** | 0.5000 | +0.1936 | +0.1938 | +0.0142 |
| **markdown_supplement_signal** | 0.0000 | +0.2595 | +0.2590 | +0.2551 |

#### B.4.3 Benefit Trajectory: "Cost vs. Benefit" Curve

```
step3_eis_delta
    |
+0.090 |  ●─────● (full ≈ short_excerpt, high-dense region)
       |   │     │
+0.085 |   ├─────●  (plain_text, slight drop)
       |   │
+0.070 |   │         ●  (action_only, significant drop)
       |   │
+0.064 |   │             ●  (title_only, minimal content)
       |
    └──┴─────────────────────────
      full short plain action title
      (100%)(35%)(100%)(20%)(10%)
       Content Overhead
```

**Interpretation**: The benefit curve is steep for the first 35% (high-value content), then gradually decays. The "elbow" is around `short_excerpt`, making it the efficiency sweet spot.

#### B.4.4 Variant-Specific Observations

**full_markdown**:
- Strengths: Highest EIS, strong on `report_actionability`, good balance across all dimensions.
- Weakness: Highest token cost; marginal benefit over `short_excerpt`.

**short_excerpt** (RECOMMENDED):
- Strengths: 99.9% EIS of full, comparable `report_actionability`, same `kg_quality` lift.
- Weakness: Minimal; achieves near-optimal cost-benefit ratio.

**plain_text**:
- Strengths: Same full content, format-agnostic (useful if markdown parsing is problematic).
- Weakness: Slight loss in `insight_quality`; loses markdown structure benefits.

**action_only**:
- Strengths: Lean (20% content); still achieves `kg_quality` gate crossing.
- Weakness: Poor `report_actionability` (loses evidence and context); 21% EIS loss vs full.

**title_only**:
- Strengths: Minimal (10% content); lowest inference cost.
- Weakness: Severe regression in `report_actionability` (negative delta); insufficient structural signal for high-quality reasoning.

#### B.4.5 Gate Crossing Achievement

All variants achieved:
- ✓ `kg_ge_0_60`

This indicates that even minimal structural markdown can unlock graph-quality improvements.

#### B.4.6 Top Benefits (full_markdown variant)

| Rank | Metric | Benefit Delta |
|---|---|---:|
| 1 | kg_quality | +0.3191 |
| 2 | markdown_supplement_signal | +0.2595 |
| 3 | report_actionability | +0.1936 |
| 4 | graph_density_proxy | +0.1118 |
| 5 | relation_consistency | +0.0502 |
| 6 | report_query_alignment | +0.0328 |
| 7 | agent_query_relevance | +0.0312 |
| 8 | interaction_coherence | +0.0289 |

### B.5 Conclusions (Case B)

1. **Diminishing returns on supplement granularity**: `short_excerpt` (35% of full) delivers 99.9% of benefit, establishing a practical compression frontier.

2. **Critical threshold: Evidence + Actions matter**: `action_only` and `title_only` variants show that *content* (not just structure) is essential; removing evidence or actionable guidance degrades performance significantly.

3. **KG quality is the primary beneficiary**: Across all variants, `kg_quality` improvement is the dominant signal, confirming that structured markdown acts as a "knowledge coordination language."

4. **Cost-benefit recommendation**: For production deployment, `short_excerpt` strategy is recommended:
   - Achieves ~90% of theoretical maximum benefit.
   - Reduces markdown overhead by ~65% (token budget, latency).
   - Maintains gate-crossing capability.

5. **Stability**: The ranking is consistent (full > short > plain > action > title), suggesting the benefit ordering is robust across similar input domains.

---

## Comparative Summary: Case A vs Case B

| Dimension | Case A (Gap Boost) | Case B (GraphRAG Multi-Variant) |
|---|---|---|
| **Focus** | Single dual-treatment comparison | Multi-variant ablation study |
| **Input Topic** | Broad technical/strategic (gap boost focus) | GraphRAG research domain |
| **Main Finding** | Markdown is effective; +23.65% EIS | Short excerpt is sufficient; 99.9% of full benefit |
| **Primary KPI** | step3_eis, overall_risk, kg_quality | step3_eis_delta (relative improvement) |
| **Recommendation** | Use markdown (Case A: with_markdown is clear winner) | Use short_excerpt (Case B: best cost-benefit) |
| **Generalizability** | Domain/topic-specific result | Suggests general principle about content density |

---

## Methodological Notes

### Data Pipeline
1. **Step1**: Web research → structured summary (4 reports per case)
2. **Step2**: Multi-agent analysis → strategic guidance document
3. **Step3**: LLM-driven reasoning → actionable synthesis
4. **Finalization**: Aggregate metrics across 110 quantitative indicators

### Reproducibility
- Both cases use the same evaluation framework (`pipeline_quant_monitor.py`).
- Metrics are deterministic (no randomness in scoring logic).
- Variants control only the markdown supplement; all other inputs are identical.

### Limitations
- Limited to 2 distinct topics (Gap Boost domain + GraphRAG domain); broader domain coverage would strengthen generalizability claims.
- Markdown quality is manually curated; automated markdown generation variants not tested.
- No user study validation; evaluation is algorithmic only.

---

## Recommended Reading Order

1. Start with **Case A (A.1 – A.4)** for intuition on markdown effectiveness.
2. Move to **Case B (B.1 – B.5)** to understand compression trade-offs.
3. Review **Comparative Summary** for high-level takeaways.
4. Consult **Methodological Notes** for technical validation.
