# 消融实验详细说明

本文档给出 `experiment/` 中 Markdown 补充策略消融实验的完整说明：实验目标、变量设计、评估口径、两轮结果、现象解释与结论建议。

---

## 1. 实验目标

在固定 Step1/Step2 输入的前提下，评估不同 Markdown 补充策略对 Step3 量化表现的影响，重点回答：

1. Markdown 补充是否显著提升 Step3 总体效果（`step3_eis`）？
2. 收益主要来自哪些维度（`kg_quality`、`report_actionability`、`insight_quality` 等）？
3. 完整补充（`full_markdown`）是否明显优于轻量补充（如 `short_excerpt`）？
4. 哪些策略会带来副作用（如报告质量、洞察质量回退）？

---

## 2. 实验变量与控制

### 2.1 对照组与实验组

- 基线（Control）：`without_markdown`
- 实验变体（Treatment）：
  - `full_markdown`：完整补充材料
  - `short_excerpt`：短摘录
  - `plain_text`：去格式纯文本
  - `action_only`：仅行动建议
  - `title_only`：仅标题结构

### 2.2 控制变量

以下要素在同轮实验中保持一致：

- Step1 摘要输入与 Step2 输出
- 量化脚本与指标口径
- 评分聚合方式（同一 `pipeline_quant_monitor.py` + `finalize`）

> 因此差异主要由“Markdown 补充策略本身”引入。

---

## 3. 评估口径

### 3.1 主指标

- `step3_eis`：Step3 综合分（越高越好）
- `overall_risk`：总体风险（越低越好）
- `step3_eis_delta`：相对基线的 EIS 增量
- `risk_improvement`：相对基线的风险改善（正数为改善）

### 3.2 关键维度

- `retrieval_quality`
- `kg_quality`
- `multi_agent_quality`
- `simulation_quality`
- `insight_quality`
- 补充观察：`report_actionability`、`report_quality`、`markdown_supplement_signal`

### 3.3 Gate 视角

关注质量门槛是否新增通过（如 `kg_ge_0_60`），用于判断是否跨过“可用阈值”。

---

## 4. 数据来源

### 4.1 轮次 A：Gap Boost 对照（当前打开报告）

- 文件：`experiment/report/step3_runtime_dual_experiment/20260318_gap_boost_v6_actionability/step3_markdown_comparison.md`
- 结论类型：`without_markdown` vs `with_markdown` 双对照

### 4.2 轮次 B：多变体消融汇总（最新完整消融）

- 文件：`experiment/report/step3_runtime_dual_experiment/20260319_005606_oneclick_dual/ablation_summary/markdown_ablation_summary.json`
- 配套：`.../markdown_ablation_summary.md`

---

## 5. 结果（一）：双对照结果（轮次 A）

### 5.1 总体收益

- `step3_eis`: `0.559870 -> 0.692262`
- 增量：`+0.132392`（`+23.65%`）
- `overall_risk`：下降 `0.077215`（`-16.50%`）

这说明在该轮配置下，Markdown 补充对总体质量和风险均有显著正向影响。

### 5.2 核心五维变化

- `retrieval_quality`: `+0.054227`（`+6.29%`）
- `kg_quality`: `+0.358761`（`+101.91%`，最大收益）
- `multi_agent_quality`: `+0.063265`（`+12.06%`）
- `simulation_quality`: `+0.054227`（`+8.68%`）
- `insight_quality`: `+0.055346`（`+9.82%`）

### 5.3 Gate 变化

新增通过 3 项：

- `insight_ge_0_60`: `False -> True`
- `kg_ge_0_60`: `False -> True`
- `multi_agent_ge_0_55`: `False -> True`

无丢失 gate，说明不是“以偏概全”的单点提升。

### 5.4 正负变化并存

- 主要正向：`kg_quality`、`graph_density_proxy`、`report_evidence_quality`、`interaction_coherence`
- 主要回退：`novelty`、`report_coherence`（幅度较小）

含义：补充材料强化了结构化与证据链，但可能轻微牺牲文本新颖性与部分表达流畅性。

---

## 6. 结果（二）：多变体消融排名（轮次 B）

### 6.1 基线

- `without_markdown`
- `step3_eis = 0.578436`
- `overall_risk = 0.330836`

### 6.2 变体排名（按 `step3_eis_delta`）

| 排名 | 变体 | step3_eis | step3_eis_delta | risk_improvement |
|---|---|---:|---:|---:|
| 1 | full_markdown | 0.668377 | +0.089941 | +0.018905 |
| 2 | short_excerpt | 0.668250 | +0.089814 | +0.018818 |
| 3 | plain_text | 0.662291 | +0.083855 | +0.018285 |
| 4 | action_only | 0.648907 | +0.070471 | +0.003320 |
| 5 | title_only | 0.642758 | +0.064322 | +0.003451 |

### 6.3 最佳变体与关键信号

- `best_variant = full_markdown`
- 但 `short_excerpt` 与 `full_markdown` 几乎持平（差值约 `0.000127`）

这表明“高信息密度的精简材料”已可复现绝大部分收益。

### 6.4 各变体特征

- `full_markdown`：全面提升，`report_actionability` 与 `kg_quality` 同时显著上升
- `short_excerpt`：效果几乎等同 full，成本更低
- `plain_text`：总体仍有增益，但 `insight_quality` 略回退
- `action_only`：行动性提升明显，但综合收益不及 full/short
- `title_only`：结构信号不足，`report_actionability` 出现明显负增量

### 6.5 Gate 结果

所有变体都新增通过：

- `kg_ge_0_60`

说明即便轻量补充也能帮助跨过关键 KG 门槛。

---

## 7. 现象解释（针对消融结论）

1. **收益核心来自 KG 与行动性**
   - 多轮结果都显示 `kg_quality` 是最大增益项；
   - `report_actionability` 在 full/short/action 变体中也普遍提高。

2. **“信息密度”比“篇幅长度”更关键**
   - `short_excerpt` 接近 `full_markdown`，说明关键信息覆盖比长文本更重要。

3. **纯结构提示不足以支撑高质量决策**
   - `title_only` 虽改善部分图谱相关信号，但在行动性和报告质量上存在明显短板。

4. **有可能出现局部 trade-off**
   - 如 `novelty`、`report_coherence` 等小幅回退，需要在真实场景中平衡“可执行性 vs 表达多样性”。

---

## 8. 最终结论（可直接引用）

- Markdown 补充策略对 Step3 具有稳定正向作用：**EIS 上升、风险下降、KG 质量显著提升**。
- 在效果与成本平衡上，`short_excerpt` 是当前最具性价比的策略。
- 若目标是追求上限效果，优先 `full_markdown`；若目标是低成本近似最优，优先 `short_excerpt`。
- `title_only` 不建议单独作为策略；至少应补充行动建议与证据句。

---

## 9. 建议后续实验（面向下一轮消融）

1. **长度敏感性消融**：按 20/40/80 行切分摘要，寻找最小有效信息量。
2. **结构-证据-行动三因子正交消融**：分别开关三类内容，定位贡献占比。
3. **稳定性检验**：跨主题重复实验，统计排名稳定度（如 Top-1 命中率）。
4. **回退修复实验**：针对 `novelty`/`coherence` 回退引入后处理模板，验证是否可“保收益降副作用”。
