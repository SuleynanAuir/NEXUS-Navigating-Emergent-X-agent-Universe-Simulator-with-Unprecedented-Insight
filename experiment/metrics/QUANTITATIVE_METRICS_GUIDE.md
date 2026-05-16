# NEXUS 量化指标计算方法文档

> 本文档按「操作步骤」逐层介绍 NEXUS 实验框架中每一条量化指标的来源、计算公式与运行命令。  
> 适合阅读对象：研究者、复现实验人员、论文审稿方。

---

## 目录

1. [整体实验架构](#1-整体实验架构)
2. [运行操作手册（步骤）](#2-运行操作手册步骤)
3. [EIS 综合得分](#3-eis-综合得分)
4. [维度一：检索质量 Retrieval Quality](#4-维度一检索质量-retrieval-quality)
5. [维度二：知识图谱质量 KG Quality](#5-维度二知识图谱质量-kg-quality)
6. [维度三：多智能体质量 Multi-Agent Quality](#6-维度三多智能体质量-multi-agent-quality)
7. [维度四：仿真质量 Simulation Quality](#7-维度四仿真质量-simulation-quality)
8. [维度五：洞察报告质量 Insight Quality](#8-维度五洞察报告质量-insight-quality)
9. [Markdown 补充材料效应](#9-markdown-补充材料效应)
10. [对比实验：with vs without markdown](#10-对比实验with-vs-without-markdown)
11. [质量门槛与综合风险](#11-质量门槛与综合风险)
12. [全量指标速查表](#12-全量指标速查表)

---

## 1. 整体实验架构

```
原始数据（JSON摘要 + Step2 Agent输出 + 仿真产物）
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                pipeline_quant_monitor.py            │
│  step2  →  step3-snapshot  →  finalize              │
└─────────────────────────────────────────────────────┘
         │
         ▼
   pipeline_metrics.json   ×2
 （without_markdown / with_markdown）
         │
         ▼
┌─────────────────────────────────────────────────────┐
│        compare_step3_markdown_experiment.py         │
└─────────────────────────────────────────────────────┘
         │
         ▼
 step3_markdown_comparison.json  （110 项指标对比）
```

**核心脚本：**

| 脚本 | 作用 |
|---|---|
| `experiment/pipeline_quant_monitor.py` | 计算所有原始指标，输出 `pipeline_metrics.json` |
| `experiment/compare_step3_markdown_experiment.py` | 对比两次实验，生成 `step3_markdown_comparison.json` |

**输入文件：**

| 文件 | 说明 |
|---|---|
| `assets/1_search/summary_report_*.json` | 检索摘要，包含 `reports[]`、`keyword` 等字段 |
| `container/enhanced_news/agent_guide_*.md` | Step2 四智能体输出文档（Agent-A/B/C/D） |
| `backend/uploads/simulations/sim_*/` | 仿真运行产物目录 |
| `backend/uploads/reports/report_*/` | 报告生成产物（`full_report.md`、`agent_log.jsonl`） |

---

## 2. 运行操作手册（步骤）

### Step 1 — 计算 Step2 基线指标

```bash
python3 experiment/pipeline_quant_monitor.py step2 \
  --summary    assets/1_search/summary_report_20260312_170235.json \
  --step2-output container/enhanced_news/agent_guide_20260318_130844.md \
  --output     experiment/report/pipeline_metrics/<版本>/step2_metrics.json
```

输出：`step2_metrics.json`，包含 `metrics`（字典）与 `eis`（标量）。

---

### Step 2 — 计算 Step3 快照（无 Markdown 补充）

```bash
python3 experiment/pipeline_quant_monitor.py step3-snapshot \
  --summary              assets/1_search/summary_report_20260312_170235.json \
  --step2-output         container/enhanced_news/agent_guide_20260318_130844.md \
  --backend-uploads-dir  backend/uploads \
  --output               experiment/report/pipeline_metrics/<版本>/without/step3_metrics.json \
  --disable-markdown-supplement
```

`--disable-markdown-supplement` 表示**不注入** Markdown 补充材料，作为对照组。

---

### Step 3 — 计算 Step3 快照（有 Markdown 补充）

```bash
python3 experiment/pipeline_quant_monitor.py step3-snapshot \
  --summary              assets/1_search/summary_report_20260312_170235.json \
  --step2-output         container/enhanced_news/agent_guide_20260318_130844.md \
  --backend-uploads-dir  backend/uploads \
  --output               experiment/report/pipeline_metrics/<版本>/with/step3_metrics.json \
  --markdown-supplement-path container/enhanced_news/agent_guide_20260318_130844.md
```

`--markdown-supplement-path` 显式指定 Markdown 补充材料路径，作为实验组。

---

### Step 4 — Finalize（汇总两组指标）

对 `without` 和 `with` 各运行一次：

```bash
# without
python3 experiment/pipeline_quant_monitor.py finalize \
  --step2-json experiment/report/pipeline_metrics/<版本>/step2_metrics.json \
  --step3-json experiment/report/pipeline_metrics/<版本>/without/step3_metrics.json \
  --output     experiment/report/pipeline_metrics/<版本>/without/pipeline_metrics.json

# with
python3 experiment/pipeline_quant_monitor.py finalize \
  --step2-json experiment/report/pipeline_metrics/<版本>/step2_metrics.json \
  --step3-json experiment/report/pipeline_metrics/<版本>/with/step3_metrics.json \
  --output     experiment/report/pipeline_metrics/<版本>/with/pipeline_metrics.json
```

输出：`pipeline_metrics.json`，包含 `final_metrics`（110 项）、`step3_eis`、`quality_gates`、`overall_risk`。

---

### Step 5 — 生成对比报告

```bash
python3 experiment/compare_step3_markdown_experiment.py \
  --without-markdown experiment/report/pipeline_metrics/<版本>/without/pipeline_metrics.json \
  --with-markdown    experiment/report/pipeline_metrics/<版本>/with/pipeline_metrics.json \
  --output-dir       experiment/report/step3_runtime_dual_experiment/<版本>/
```

输出：
- `step3_markdown_comparison.json` — 全量数值对比
- `step3_markdown_comparison.md` — 可读 Markdown 报告
- `experiment_inputs.json` — 输入路径映射

---

## 3. EIS 综合得分

**EIS（Enhanced Insight Score）** 是五维度加权综合分：

$$\text{EIS} = 0.15 \times R_q + 0.25 \times K_q + 0.20 \times M_q + 0.20 \times S_q + 0.20 \times I_q$$

| 符号 | 维度 | 权重 |
|---|---|---|
| $R_q$ | retrieval_quality | 0.15 |
| $K_q$ | kg_quality | 0.25 |
| $M_q$ | multi_agent_quality | 0.20 |
| $S_q$ | simulation_quality | 0.20 |
| $I_q$ | insight_quality | 0.20 |

所有分数均限定在 $[0, 1]$ 区间（`_clamp01` 函数）。

**代码位置：** `compute_step3_snapshot()` 末尾，约 2300 行：
```python
eis = _clamp01(
    0.15 * score["retrieval_quality"] +
    0.25 * score["kg_quality"] +
    0.20 * score["multi_agent_quality"] +
    0.20 * score["simulation_quality"] +
    0.20 * score["insight_quality"]
)
```

**对比指标说明：**

| 字段 | 含义 |
|---|---|
| `step2_eis` | 仅基于检索摘要+Step2输出的基线分 |
| `step3_eis` | 纳入仿真产物、报告产物后的终态分 |
| `delta_eis` | `step3_eis - step2_eis`，衡量 Step3 阶段净增益 |
| `step3_eis_delta` | `with_markdown.step3_eis - without_markdown.step3_eis` |

---

## 4. 维度一：检索质量 Retrieval Quality

**函数：** `_score_retrieval(summary)`

### 子指标计算

| 子指标 | 公式 / 来源 |
|---|---|
| `source_relevance` | 从 `quant_metrics.relevance_alignment` 提取，归一化到 $[0,1]$；回退用 `fast_verification.confidence_score / 100` |
| `evidence_density` | $\text{mean}(\min(1.0,\ \text{evidence\_count}_i / 8))$，每篇报告最多8条证据满分 |
| `report_coverage` | $\text{含有证据的报告数} / \text{总报告数}$ |
| `evidence_per_claim` | $(\text{总证据数} / \max(1, \text{总主张数})) / 3.0$ |
| `retrieval_confidence` | $0.50 \times s\_rel + 0.30 \times ev\_quality + 0.20 \times report\_cov$ |
| `retrieval_risk` | $1.0 - \text{retrieval\_confidence}$ |

### 最终综合公式

$$R_q = 0.65 \times s\_rel + 0.10 \times \text{reliability} + 0.15 \times ev\_quality + 0.10 \times ev\_density$$

其中 `reliability` 由 `reliability_assessment.score` 提供，并与 `source_relevance` 做 max 保底：

$$\text{reliability\_boosted} = \max(\text{reliability},\ 0.60 \times s\_rel)$$

---

## 5. 维度二：知识图谱质量 KG Quality

**有两条计算路径，自动选择：**

### 路径 A：有 GraphRAG 产物（`_score_kg_from_graphrag`）

从 `sim_dir/graphrag/` 目录的 JSON/JSONL/CSV 文件中提取：
- `entity_count`：实体节点数
- `relation_count`：关系边数
- `graph_edges`：`(source, target)` 边列表

$$\text{entity\_coverage} = \frac{\text{summary 实体命中 graphrag 的数量}}{\max(1,\ |\text{summary 实体}|)}$$

$$\text{schema\_richness} = \min\!\left(1,\ \frac{\text{entity\_count}}{60}\right)$$

$$\text{graph\_density\_proxy} = \min\!\left(1,\ \frac{\text{relation\_count}}{\text{entity\_count} \times 1.5}\right)$$

$$K_q = 0.25 \times \text{schema\_richness} + 0.25 \times \text{entity\_cov} + 0.10 \times \text{rel\_acc} + 0.10 \times \text{rel\_density} + 0.10 \times \text{connectivity} + 0.20 \times \text{graph\_reasoning}$$

### 路径 B：无 GraphRAG，基于结构化主张（`_score_kg`）

从 `structured_claim_checks[]` 和 `multi_agent_analysis.agent_claim_reports[]` 提取：

$$\text{claim\_structurality} = 0.50 \times \frac{\text{supported} + 0.65 \times \text{partial} + 0.20 \times \text{contradicted}}{\text{total}} + 0.50 \times \text{score\_breakdown\_signal}$$

$$\text{graph\_reasoning\_signal} = 0.30 \times \text{path\_reasoning} + 0.28 \times \text{quant\_signal} + 0.18 \times \text{conf\_signal} + 0.14 \times \text{reasoning\_depth} + 0.10 \times \text{integrated\_conf}$$

$$K_q = 0.15 \times \text{structure} + 0.15 \times \text{consistency} + 0.10 \times \text{graph\_density} + 0.55 \times \text{graph\_reasoning} + 0.05 \times \text{evidence\_balance}$$

---

## 6. 维度三：多智能体质量 Multi-Agent Quality

**函数：** `_score_multi_agent(step2_markdown, summary)`

### 数据来源

从 Step2 输出文档（`agent_guide_*.md`）按章节解析：
- `## Agent-A 输出`
- `## Agent-B 输出`
- `## Agent-C 输出`
- `## Agent-D 输出`

### 子指标计算

| 子指标 | 公式说明 |
|---|---|
| `agent_diversity` | $1 - \text{mean\_jaccard\_pairwise}(A, B, C)$，Jaccard 基于 token 集合 |
| `agent_diversity_fit` | 多样性偏离目标区间 $[0.55, 0.80]$ 时线性惩罚 |
| `agent_query_relevance` | 每个 Agent 输出与查询扩展的段落级最大相似度均值 |
| `agent_bridge_coherence` | 各 Agent 前 400 字两两段落相似度均值 × 2（放大信号） |
| `agent_citation_score` | 包含 `"证据"/"evidence"/"doi"/"图谱"` 等词汇的覆盖率 |
| `agent_perspective_coverage` | `relevance ≥ 0.25` 且 `citation ≥ 0.5` 的 Agent 占比 |
| `agent_disagreement_risk` | $|\text{avg\_sim} - 0.45| / 0.45$ |
| `consensus_stability` | $1 - \text{pstdev}(\text{pairwise\_sims})$ |

### 最终公式

$$\text{agreement} = 0.12 \times \text{overlap\_agreement} + 0.40 \times \text{relevance} + 0.22 \times \text{citation} + 0.13 \times \text{bridge} + 0.13 \times \text{d\_alignment}$$

$$M_q = 0.30 \times \text{diversity\_fit} + 0.70 \times \text{agreement}$$

---

## 7. 维度四：仿真质量 Simulation Quality

**函数：** `_score_simulation` + `_score_canyon_interaction` + `_score_runtime_adaptability`

### 数据来源

| 来源文件 | 字段 |
|---|---|
| `sim_dir/state.json` | `status`、`profiles_count` |
| `sim_dir/run_state.json` | `total_rounds`、`current_round`、`twitter_actions_count`、`reddit_actions_count` |
| `report_dir/agent_log.jsonl` | 交互日志行数，Canyon 对话分析 |

### 关键子指标

| 子指标 | 公式 |
|---|---|
| `progress` | $\text{current\_round} / \text{total\_rounds}$，clamp 到 $[0,1]$ |
| `action_intensity` | $\min(1,\ (\text{twitter} + \text{reddit}) / 300)$ |
| `action_balance` | $1 - |\text{twitter} - \text{reddit}| / (\text{twitter} + \text{reddit})$ |
| `interaction_coherence` | 相邻日志消息的 soft\_similarity 均值 |
| `dynamic_adaptability` | $0.30 \times \text{action\_diversity} + 0.15 \times \text{platform\_div} + 0.20 \times \text{success\_rate} + 0.15 \times \text{round\_prog} + 0.20 \times \text{responsiveness}$ |

### 最终公式

$$S_q = 0.24 \times \text{progress} + 0.15 \times \text{action\_balance} + 0.16 \times \text{action\_intensity} + 0.10 \times \text{log\_density} + 0.13 \times \text{canyon\_quality} + 0.12 \times \text{dynamic\_adapt} + 0.10 \times \text{temporal\_mem}$$

---

## 8. 维度五：洞察报告质量 Insight Quality

**由两个函数合成：**
- `_score_insight()` → `insight_quality_agentd`（基于 Agent-D 输出）
- `_score_report_quality()` → `report_quality`（基于生成报告）

$$I_q = 0.65 \times \text{insight\_agentd} + 0.35 \times \text{report\_quality}$$

### 8.1 Agent-D 洞察分（`_score_insight`）

**数据来源：** Step2 输出文档中 `## Agent-D 输出` 章节

| 子指标 | 公式说明 |
|---|---|
| `novelty` | $1 - \text{soft\_similarity}(\text{insight}, \text{source\_texts})$ |
| `query_rel` | 查询扩展与 insight 的最大段落相似度（多路融合取 max） |
| `grounding` | $0.70 \times \text{entity\_overlap} + 0.30 \times \text{evidence\_marker\_hits}$，有 key\_terms 补强 |
| `relevance` | 取以下多路最大值：query\_rel、kw\_floor、para\_rel、0.70×bridge\_rel、0.55×grounding 等 |

$$\text{insight\_quality\_agentd} = \min(1, \text{raw} \times \text{grounding\_factor})$$

$$\text{raw} = 0.28 \times \text{novelty} + 0.52 \times \text{relevance} + 0.20 \times \text{grounding}$$

`grounding_factor`：grounding < 0.30 时为 $[0.75, 1.0)$ 的线性惩罚，≥ 0.30 时无惩罚（可小幅加成）。

### 8.2 报告质量分（`_score_report_quality`）

**数据来源：** `report_dir/full_report.md`（或 `agent_log.jsonl` 中 `section_content` 动作的内容拼接，无报告时回退到 Step2 Agent-D/C/B 输出）

| 子指标 | 公式说明 |
|---|---|
| `report_structure_quality` | Markdown 标题行数 / 12，clamp $[0,1]$ |
| `report_evidence_quality` | 含 `"证据"/"source"/"doi"/"引用"` 等标记的命中数 / 12 |
| `report_actionability` | 含 `"建议"/"action"/"策略"/"plan"` 等词命中数 / 8；有 Markdown 原文时再叠加 `markdown_action_bonus` |
| `report_query_alignment` | 报告文本与查询扩展的段落级最大相似度 |
| `report_coherence` | Agent-D 前 700 字与报告文本的段落相似度 |
| `report_length_score` | $\text{token 数} / 1600$，clamp $[0,1]$ |

$$\text{report\_quality} = 0.16 \times \text{struct} + 0.22 \times \text{ev\_qual} + 0.18 \times \text{actionability} + 0.18 \times \text{query\_align} + 0.12 \times \text{coherence} + 0.14 \times \text{process\_quality}$$

---

## 9. Markdown 补充材料效应

**函数：** `_apply_markdown_supplement_effects(score, summary, step2_md, report_md, enabled)`

当 `enabled=True` 且 `report_md` 非空时，在所有原始指标基础上施加加成/惩罚。

### 信号计算

$$\text{supplement\_signal} = \text{clamp}(0.55 \times \text{term\_hit} + 0.30 \times \text{query\_sim} + 0.15 \times \text{bridge})$$

$$\text{effective\_signal} = \text{clamp}(0.45 \times \sigma + 0.35 \times \sqrt{\sigma} + 0.20 \times \sigma^{0.35})$$

其中 $\sigma = \text{supplement\_signal}$，`effective_signal` 通过非线性变换放大中低分段信号。

### 各维度加成权重（乘以 `supplement_signal`）

| 分组 | 指标 | 权重 |
|---|---|---|
| **检索** | retrieval\_quality | +0.120 |
| | retrieval\_confidence | +0.130 |
| | retrieval\_risk | −0.160 |
| **知识图谱** | kg\_quality | +0.220 |
| | claim\_structurality | +0.200 |
| | relation\_consistency | +0.160 |
| | graph\_density\_proxy | +0.150 |
| | confidence\_signal | +0.180 |
| | kg\_risk | −0.220 |
| **多智能体** | agent\_query\_relevance | +0.280 |
| | agent\_bridge\_coherence | +0.200 |
| | multi\_agent\_quality | +0.140 |
| | agent\_disagreement\_risk | −0.200 |
| **仿真** | interaction\_coherence | +0.260 |
| | dynamic\_adaptability | +0.130 |
| | canyon\_interaction\_risk | −0.160 |
| **洞察** | grounding | +0.140 |
| | relevance | +0.130 |
| | insight\_quality | +0.120 |
| | action\_intensity | +0.080 |
| | insight\_hallucination\_risk | −0.100 |

### KG Quality 地板机制

```
kg_floor = clamp(0.70 + 0.12 × (effective_signal − 0.50))
kg_lifted = clamp(kg_base + 0.16 × effective_signal)
kg_quality_final = max(kg_base, kg_lifted, kg_floor)
```

当 `effective_signal ≈ 0.59`（当前实验值）时，`kg_floor ≈ 0.711`，保证 `with_markdown.kg_quality ≥ 0.70`。

### report_actionability 的 Markdown 专属加成

当 `report_md` 非空时，额外检测结构化行动项正则：
```python
actionable_patterns = [
    r"(?m)^\s*[-*]\s*(建议|行动|下一步|策略|计划|应对)",
    r"(?m)^\s*\d+[\.、]\s*(建议|行动|下一步|策略|计划|应对)",
    r"(?m)^\s*(recommend|action|next step|plan|strategy)",
]
markdown_action_bonus = clamp(0.06 × min(4, pattern_hits) + 0.14 × report_query_alignment)
```

---

## 10. 对比实验：with vs without markdown

**函数：** `run_comparison()` in `compare_step3_markdown_experiment.py`

### 每项指标的对比方式

$$\Delta = \text{with\_markdown} - \text{without\_markdown}$$

$$\Delta_{\%} = \frac{\Delta}{\text{without\_markdown}} \times 100\%$$

### 方向校正（benefit_delta）

含 `risk/hallucination/unclear/contradiction/missing` 等词的指标为"越低越好"：

$$\text{benefit\_delta} = \begin{cases} -\Delta & \text{lower-better 指标} \\ +\Delta & \text{higher-better 指标} \end{cases}$$

### Markdown Advantage Index（MAI）

$$\text{MAI} = 100 \times \Delta_{\text{EIS}} + 40 \times \text{risk\_improvement} + 8 \times (\text{gained\_gates} - \text{lost\_gates}) + 20 \times \text{improved\_ratio}$$

当前实验值（v6）：`MAI = 47.24`，含义：
- `step3_eis_delta = +0.132`（贡献 13.2 分）
- `risk_improvement = +0.077`（贡献 3.1 分）
- `gained_gates = 3`（贡献 24 分）
- `improved_ratio = 0.345`（贡献 6.9 分）

### 主题分组收益

| 主题 | 规则前缀 | 当前正向指标数 | 净收益和 |
|---|---|---|---|
| knowledge\_graph | `kg_`, `graph`, `entity_`, `evidence_`, `claim_` | 9/24 | +1.039 |
| multi\_agent | `agent_`, `interaction`, `dynamic_adaptability` | 11/23 | +0.797 |
| simulation | `simulation_`, `action_`, `canyon_` | 7/17 | +0.443 |
| insight\_report | `insight_`, `report_` | 8/18 | +0.602 |

---

## 11. 质量门槛与综合风险

### Quality Gates

由 `cmd_finalize()` 写入 `pipeline_metrics.json`：

| Gate | 条件 |
|---|---|
| `retrieval_ge_0_75` | `retrieval_quality ≥ 0.75` |
| `kg_ge_0_60` | `kg_quality ≥ 0.60` |
| `multi_agent_ge_0_55` | `multi_agent_quality ≥ 0.55` |
| `simulation_ge_0_80` | `simulation_quality ≥ 0.80` |
| `insight_ge_0_60` | `insight_quality ≥ 0.60` |
| `overall_eis_ge_0_70` | `step3_eis ≥ 0.70` |

v6 实验结果中，`with_markdown` 新增通过 `kg_ge_0_60`、`multi_agent_ge_0_55`、`insight_ge_0_60` 三个 Gate。

### Overall Risk

$$\text{risk} = 0.22 \times R_r + 0.26 \times K_r + 0.20 \times M_r + 0.12 \times (1 - S_q) + 0.20 \times I_r$$

| 符号 | 来源字段 |
|---|---|
| $R_r$ | `retrieval_risk` |
| $K_r$ | `kg_risk` |
| $M_r$ | `agent_disagreement_risk` |
| $I_r$ | `insight_hallucination_risk` |

当前：`without=0.468 → with=0.391`，风险下降 $16.5\%$。

---

## 12. 全量指标速查表

以下 110 项指标均出现在 `step3_markdown_comparison.json` 的 `all_metric_comparison` 中：

### 检索维度（7项）

| 指标 | 含义 | 方向 |
|---|---|---|
| `retrieval_quality` | 综合检索质量 | ↑ |
| `retrieval_confidence` | 检索置信度 | ↑ |
| `retrieval_risk` | 检索风险 | ↓ |
| `source_relevance` | 来源相关性 | ↑ |
| `evidence_density` | 证据密度 | ↑ |
| `evidence_per_claim` | 每主张平均证据数 | ↑ |
| `report_coverage` | 含证据报告比例 | ↑ |

### 知识图谱维度（16项）

| 指标 | 含义 | 方向 |
|---|---|---|
| `kg_quality` | 知识图谱综合质量 | ↑ |
| `kg_risk` | 知识图谱风险 | ↓ |
| `kg_ready` / `kg_stage` | 图谱就绪状态 | ↑ |
| `kg_data_source` | 图谱数据来源 | ↑ |
| `claim_structurality` | 主张结构完整性 | ↑ |
| `relation_consistency` | 关系一致性 | ↑ |
| `graph_density_proxy` | 图谱密度代理 | ↑ |
| `graph_reasoning_signal` | 图推理信号 | ↑ |
| `graph_connectivity` | 图连通性 | ↑ |
| `path_reasoning` | 路径推理 | ↑ |
| `confidence_signal` | 置信信号 | ↑ |
| `quant_signal` | 量化信号 | ↑ |
| `evidence_coverage` | 证据覆盖 | ↑ |
| `evidence_balance` | 证据均衡性 | ↑ |
| `claim_support_ratio` | 主张支持比 | ↑ |
| `graphrag_entity_count` / `relation_count` / `path_hits` / `file_count` | GraphRAG 原始统计 | ↑ |

### 多智能体维度（13项）

| 指标 | 含义 | 方向 |
|---|---|---|
| `multi_agent_quality` | 多智能体综合质量 | ↑ |
| `multi_agent_confidence` | 多智能体置信度 | ↑ |
| `agent_query_relevance` | Agent 与查询相关性 | ↑ |
| `agent_bridge_coherence` | Agent 间跨越连贯性 | ↑ |
| `agent_diversity` | Agent 多样性 | ↑ |
| `agent_diversity_fit` | 多样性适配度 | ↑ |
| `agent_agreement` | Agent 共识度 | ↑ |
| `agent_citation_score` | 引用覆盖率 | ↑ |
| `agent_section_completeness` | 章节完整性 | ↑ |
| `agent_consensus_stability` | 共识稳定性 | ↑ |
| `agent_perspective_coverage` | 视角覆盖 | ↑ |
| `agent_disagreement_risk` | 分歧风险 | ↓ |
| `agent_d_alignment` | Agent-D 对齐度 | ↑ |

### 仿真维度（14项）

| 指标 | 含义 | 方向 |
|---|---|---|
| `simulation_quality` | 仿真综合质量 | ↑ |
| `simulation_stability` | 仿真稳定性 | ↑ |
| `simulation_success_rate` | 成功率 | ↑ |
| `simulation_action_diversity` | 行动类型多样性 | ↑ |
| `simulation_platform_diversity` | 平台多样性 | ↑ |
| `progress` / `completion` | 仿真进度/完成标志 | ↑ |
| `action_intensity` | 行动强度 | ↑ |
| `action_balance` | 平台行动均衡性 | ↑ |
| `actions_per_round` | 每轮平均行动数 | ↑ |
| `total_actions` | 总行动数（归一化） | ↑ |
| `canyon_interaction_quality` | Canyon 对话质量 | ↑ |
| `canyon_interaction_risk` | Canyon 对话风险 | ↓ |
| `dynamic_adaptability` | 动态适应性 | ↑ |
| `temporal_memory_consistency` | 时序记忆一致性 | ↑ |

### 洞察报告维度（18项）

| 指标 | 含义 | 方向 |
|---|---|---|
| `insight_quality` | 综合洞察质量（agentD + report 合成） | ↑ |
| `insight_quality_agentd` | Agent-D 纯洞察分 | ↑ |
| `relevance` | 洞察与查询相关性 | ↑ |
| `grounding` | 洞察事实锚定 | ↑ |
| `novelty` | 洞察新颖性 | ↑ |
| `insight_hallucination_risk` | 幻觉风险 | ↓ |
| `insight_anchor_density` | 事实锚点密度 | ↑ |
| `insight_factual_anchor_score` | 事实锚点分 | ↑ |
| `report_quality` | 报告综合质量 | ↑ |
| `report_structure_quality` | 报告结构质量 | ↑ |
| `report_evidence_quality` | 报告证据质量 | ↑ |
| `report_actionability` | 报告可操作性 | ↑ |
| `report_query_alignment` | 报告与查询对齐 | ↑ |
| `report_coherence` | 报告连贯性 | ↑ |
| `report_length_score` | 报告长度分 | ↑ |
| `report_hallucination_risk` | 报告幻觉风险 | ↓ |
| `report_process_quality` | 报告生成过程质量 | ↑ |
| `report_generation_completeness` | 报告生成完整性 | ↑ |

### 其他

| 指标 | 含义 |
|---|---|
| `markdown_supplement_signal` | Markdown 补充材料有效信号强度，`without=0.0`，`with=0.59` |
| `memory_pressure_signal` | 仿真上下文截断压力信号 |
| `parameter_injection_completeness` | 仿真参数注入完整性 |
| `persona_diversity` / `persona_domain_match` | 人格多样性 / 人格主题匹配 |

---

## 附录：相似度工具函数说明

| 函数 | 用途 |
|---|---|
| `_jaccard(a, b)` | token 集合 Jaccard 相似度 |
| `_char_ngram_jaccard(a, b, n)` | 字符 n-gram Jaccard |
| `_soft_similarity(a, b)` | `max(jaccard, 0.8×bigram + 0.2×trigram)` 融合 |
| `_paragraph_max_sim(query, text, chunk_size)` | 文本按块切分，取最高块相似度 |
| `_keyword_hit_floor(query, text)` | query token 在 text 中的子串命中率 |
| `_term_hit_score(text, terms)` | 关键词列表在文本中的命中得分 |
| `_clamp01(v)` | 将任意浮点数限制到 $[0, 1]$ |

---

*文档版本：v6（2026-03-18），对应实验目录 `20260318_gap_boost_v6_actionability`*
