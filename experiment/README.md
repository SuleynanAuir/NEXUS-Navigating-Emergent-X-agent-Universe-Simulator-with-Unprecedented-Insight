# Experiment 指标体系说明

本目录的实验代码并不是只包含一套单一指标，而是由 **三层评估体系** 组成：

1. **经典五维主指标 + EIS 汇总**：用于统一衡量 NEXUS 在检索、知识图谱、多智能体、仿真、洞察五个维度上的表现。
2. **面向真实运行流水线的代理指标（proxy metrics）**：用于 Step2 / Step3 在线快照与运行后评估，强调“可从现有日志与产物自动计算”。
3. **面向 LLM 报告的自动评估指标**：用于比较不同模型生成的深度分析报告质量。

这份 README 的目标不是重复命令行说明，而是回答三个更重要的问题：

- 这些指标 **来自哪里**；
- 它们在本项目里 **如何被实现**；
- 哪些部分属于 **经典方法**，哪些部分属于 **项目化改写 / 工程代理定义**。

---

## 1. 指标体系总览

### 1.1 文件与职责映射

本目录中与量化指标直接相关的核心文件如下：

- `metrics_engine.py`：主实验指标引擎，定义五维指标与 `EIS` 汇总。
- `self_supervised_metrics.py`：论文化、自监督版本的五维指标体系，强调“无人工标注也可评估”。
- `pipeline_quant_monitor.py`：面向真实运行流程的 Step2 / Step3 自动量化监控器，是当前运行实验最常用的一套指标实现。
- `run_metrics.py`：对单个标准化输入执行主指标引擎计算。
- `llm_standalone_report_metrics.py`：针对 LLM 独立生成报告的 10 项自动评估指标。
- `llm_deep_analysis_report.py`：对 comparison 结果生成 LLM 深度分析，并用轻量质量分打分。
- `compare_step3_markdown_experiment.py`：对“有 / 无 markdown supplement”实验做增益比较与方向校正。

### 1.2 三类“出处”要区分开

为了专业地理解这些指标，建议把“出处”分成三类：

1. **经典学术来源**：例如 Precision / Recall、余弦相似度、最大连通分量、图密度、相对改进率等。
2. **方法论启发来源**：例如自监督评估、embedding coherence、基于结构一致性的代理评估。
3. **项目化工程定义**：例如 `markdown_advantage_index`、`report_process_quality`、`agent_bridge_coherence` 等，这些不是标准教科书指标，而是本项目为适配真实日志与产物而设计的可操作代理指标。

换句话说，本项目的指标体系是：

> **经典评价思想 + 自监督评估框架 + 面向工程日志的代理量化**

---

## 2. 五维主指标与 EIS 的出处

主指标最清晰的实现位于 `metrics_engine.py`，并在 `self_supervised_metrics.py` 中给出了更偏“论文表述”的版本。

五个核心维度为：

- `retrieval_quality`
- `kg_quality`
- `multi_agent_collaboration` / `multi_agent_quality`
- `simulation_capability` / `simulation_quality`
- `insight_quality`

最终汇总指标为：

- `EIS`（Emergent Insight Score）

### 2.1 EIS 的项目定义

在 `metrics_engine.py` 中，`EIS` 被定义为五维相对提升的加权和：

```text
EIS = Σ w_i * ((P_nexus_i - P_baseline_i) / P_baseline_i)
```

如果 baseline 缺失或为 0，则该维度相对提升按 0 处理，避免除零。

在 `pipeline_quant_monitor.py` 的在线快照实现中，`EIS` 则采用五维绝对分的加权组合：

```text
EIS = 0.15 * Retrieval
		+ 0.25 * KG
		+ 0.20 * MultiAgent
		+ 0.20 * Simulation
		+ 0.20 * Insight
```

### 2.2 EIS 的理论来源

`EIS` 不是一个通行的公共标准名词，而是本项目提出的 **综合性总指标**。它的理论来源主要有两类：

- **多指标综合评价**：即把多个子维度先标准化到 `[0,1]`，再进行加权聚合，这一思路广泛用于信息检索、推荐系统、知识图谱评测与多目标优化。
- **基线相对提升评估**：即用相对于 baseline 的 improvement 而不是绝对值作为“系统增益”的核心度量，这在系统论文、ablation study、A/B 实验中非常常见。

因此，`EIS` 的“出处”更准确地说是：

> **基于多维加权汇总与相对提升思想的项目综合指标，而非现成标准指标名。**

---

## 3. `metrics_engine.py`：经典五维主指标

`metrics_engine.py` 是本目录中最“标准化”的一套指标实现。它依赖结构化输入 payload，而不是运行时日志，因此更适合离线实验评估。

### 3.1 Retrieval Quality

实现位置：`EmergentMetricsEngine._eval_retrieval()`

由三个子项组成：

- `Recall@K`
- `Precision@K`
- `Diversity`

最终维度分：

```text
retrieval_quality = mean(Recall@K, Precision@K, Diversity)
```

#### 理论出处

- `Recall@K` 与 `Precision@K`：来自**经典信息检索（Information Retrieval, IR）评价体系**。
- `Diversity = 1 - avg_pairwise_similarity`：来自**结果去冗余 / 多样性检索**思想，核心是“结果之间越不相似，覆盖面越广”。

#### 本项目中的实现改写

- 相似度不是用 BM25、embedding API 或人工判断，而是用简单 token 级余弦相似度。
- 目的是保证 **零依赖、可重复、可离线运行**。

### 3.2 KG Quality

实现位置：`EmergentMetricsEngine._eval_kg()`

由三个子项组成：

- `EntityCoverage`
- `RelationAccuracy`
- `GraphConnectivity`

最终维度分：

```text
kg_quality = mean(EntityCoverage, RelationAccuracy, GraphConnectivity)
```

#### 理论出处

- `EntityCoverage`：来自 **抽取覆盖率 / schema coverage** 思想。
- `RelationAccuracy`：来自 **信息抽取与知识图谱构建** 中对三元组正确率的评估。
- `GraphConnectivity`：来自 **图论（Graph Theory）**，本质上是最大连通分量占比（Largest Connected Component Ratio）。

#### 本项目中的实现改写

- 这里的知识图谱质量不依赖外部 KG benchmark，而使用结构化 payload 中的实体、边、三元组正确性来直接计算。
- 强调的是 **图结构完整性 + 关系质量 + 可连接性**。

### 3.3 Multi-Agent Collaboration

实现位置：`EmergentMetricsEngine._eval_multi_agent()`

由三个子项组成：

- `AgentDiversity`
- `GainNormalized`
- `ConflictResolutionRate`

最终维度分：

```text
multi_agent_collaboration = mean(AgentDiversity, GainNormalized, ConflictResolutionRate)
```

#### 理论出处

- `AgentDiversity`：来自 **ensemble diversity / 多模型差异性** 思想。
- `GainNormalized`：来自 **相对性能提升** 的归一化写法。
- `ConflictResolutionRate`：来自 **协作式问题求解** 中的冲突消解能力衡量。

#### 本项目中的实现改写

- `gain = (p_multi - p_single) / p_single` 后再压缩到 `[0,1]`。
- 该维度的目标不是“智能体越一致越好”，而是“**有差异、但最终能形成收益并解决冲突**”。

### 3.4 Simulation Capability

实现位置：`EmergentMetricsEngine._eval_simulation()`

由四个子项组成：

- `ScenarioDiversity`
- `PredictionConsistency`
- `CausalValidity`
- `TemporalCoherence`

最终维度分：

```text
simulation_capability = mean(ScenarioDiversity, PredictionConsistency, CausalValidity, TemporalCoherence)
```

#### 理论出处

- `ScenarioDiversity`：来自 **情景规划 / scenario planning** 的覆盖性思路。
- `PredictionConsistency`：来自 **重复实验稳定性 / variance-based consistency** 思想。
- `CausalValidity`：来自 **因果图 / 因果边有效性** 的基本评价方法。
- `TemporalCoherence`：来自 **时序建模与事件链合理性** 评价。

#### 本项目中的实现改写

- `PredictionConsistency` 使用数值列的标准差变换为 `1 / (1 + mean_std)`。
- `TemporalCoherence` 允许人工给出 `temporal_scores`，再按 5 分制归一到 `[0,1]`。

### 3.5 Insight Quality

实现位置：`EmergentMetricsEngine._eval_insight()`

由三个子项组成：

- `Novelty`
- `ReasoningDepth`
- `ExpertScore`

最终维度分：

```text
insight_quality = mean(Novelty, ReasoningDepth, ExpertScore)
```

#### 理论出处

- `Novelty`：来自 **新颖性 / non-redundancy / information novelty** 评价。
- `ReasoningDepth`：来自 **推理链深度、证据链长度** 的启发式评估。
- `ExpertScore`：来自 **专家主观打分**，本质是人工评价接口。

#### 本项目中的实现改写

- `Novelty = 1 - avg_kb_similarity`，用文本相似度代替语义向量模型。
- `ReasoningDepth` 由 reasoning chain 长度和证据数共同定义。

---

## 4. `self_supervised_metrics.py`：自监督评估框架的出处

这个文件不是简单的代码实现，它本身就是一套“为什么没有人工标注也可以评估”的方法论说明。

### 4.1 方法论来源

该文件的核心思想是：

> **没有人工标注时，可以通过一致性、结构、对比、语义关联来构建可自动计算的代理评价。**

这种做法的学术归属通常可以放在以下脉络中理解：

- **Self-supervised / weakly supervised evaluation**
- **Structure-based evaluation**
- **Consistency-based evaluation**
- **Proxy metric design for LLM / multi-agent systems**

它不是复刻某一篇论文，而是将这些思想组合成了适合 NEXUS 的五维无监督评估框架。

### 4.2 该文件中的关键启发来源

#### 检索质量：query-doc 语义相关度

```text
R(q) = (1/k) Σ cos(Emb(q), Emb(d_i))
```

来源：**向量空间模型（Vector Space Model）与余弦相似度检索**。

#### KG Quality：结构 + 一致性 + Embedding Coherence

```text
KG = 0.3*C + 0.3*RC + 0.4*EC
```

其中：

- `C`：连通性
- `RC`：关系一致性
- `EC`：embedding coherence

特别是：

```text
EC = avg cos(h + r, t)
```

这明显借鉴了 **TransE 类知识图谱嵌入模型** 的直觉：关系可以理解为从 head 到 tail 的平移。

#### Multi-Agent Collaboration：多样性 + 一致性

```text
MAC = λ*D + (1-λ)*A
```

来源：

- **集成学习中的 diversity-accuracy tradeoff**
- **多主体系统中的 consensus / agreement 分析**

#### Simulation Capability：时间一致性 + 因果一致性

```text
SIM = 0.5*TC + 0.5*CC
```

来源：

- **事件序列合理性（temporal consistency）**
- **因果连贯性（causal coherence）**

#### Insight Quality：新颖性 + 相关性

```text
INSIGHT = 0.4*N + 0.6*R
```

来源：

- `N = 1 - cos(insight, input)`：新信息不应只是输入复述
- `R = cos(insight, query)`：新信息仍需紧扣原始问题

这是一个非常典型的 **novelty-relevance tradeoff** 设计。

### 4.3 为什么说它“专业”

因为它满足科研评估最关键的四个要求：

- 有明确公式；
- 每个分量都可自动计算；
- 不依赖人工标注；
- 可以解释为什么该分高 / 低。

同时也要明确：

> 这仍然是 **代理评估（proxy evaluation）**，不是人工黄金标准。

---

## 5. `pipeline_quant_monitor.py`：真实运行流程的代理指标出处

这是当前工程中最重要、也最“实战化”的指标文件。与 `metrics_engine.py` 相比，它并不要求严格结构化的实验 payload，而是从：

- `summary_report`
- `step2 markdown`
- `backend/uploads/simulations/*`
- `backend/uploads/reports/*`
- `agent_log.jsonl`
- `meta.json`

这些**实际产物**中自动抽取量化信号。

因此，这里的很多指标并不是标准教科书名词，而是 **工程代理量化定义**。

### 5.1 Retrieval 相关指标

实现位置：`_score_retrieval()`

核心输出：

- `retrieval_quality`
- `source_relevance`
- `evidence_density`
- `report_coverage`
- `evidence_per_claim`
- `retrieval_confidence`
- `retrieval_risk`

主公式：

```text
retrieval_quality =
		0.65 * source_relevance
	+ 0.10 * reliability_boosted
	+ 0.15 * ev_quality_signal
	+ 0.10 * evidence_density
```

#### 理论出处

- `source_relevance`：来自 IR 中的相关性评价。
- `evidence_density` / `evidence_per_claim`：来自事实核查与证据支持密度思想。
- `retrieval_confidence` / `retrieval_risk`：属于项目中的质量-风险对偶设计。

#### 工程含义

这里衡量的不只是“有没有检索到东西”，而是：

- 来源是否相关；
- 每条 claim 是否有支撑证据；
- 证据质量是否足够；
- 覆盖到多少报告。

### 5.2 KG 相关指标（Step3 在线版）

实现位置：`_score_kg_from_graphrag()` 与 `_score_kg()`

核心输出包括：

- `kg_quality`
- `entity_coverage`
- `relation_accuracy`
- `graph_connectivity`
- `graph_density_proxy`
- `path_reasoning`
- `graph_reasoning_signal`
- `kg_risk`

其中 `graphrag` 版本的主组合：

```text
kg_quality =
		0.25 * schema_richness
	+ 0.25 * entity_coverage
	+ 0.10 * relation_accuracy
	+ 0.10 * relation_density
	+ 0.10 * connectivity
	+ 0.20 * graph_reasoning_signal
```

而从 `structured_claim_checks` / `multi_agent_analysis` 提取的 Step2 版本则是：

```text
kg_quality =
		0.15 * structure_score
	+ 0.15 * consistency_score
	+ 0.10 * graph_density_proxy
	+ 0.55 * graph_reasoning_signal
	+ 0.05 * evidence_balance
```

#### 理论出处

- `entity_coverage`：覆盖率思想。
- `relation_accuracy`：关系正确率思想。
- `graph_connectivity`：最大连通分量、图连通性。
- `graph_density_proxy`：图密度代理。
- `path_reasoning`：多跳路径推理信号。
- `consistency_score`：一致性 / 矛盾惩罚。

#### 专业说明

这一套指标不是要“严格复刻知识图谱 benchmark”，而是评估：

- 是否形成了成规模的图结构；
- 图是否和任务主题相关；
- claim 是否能找到图与证据支撑；
- 图推理是否真正参与了分析。

### 5.3 Multi-Agent 相关指标

实现位置：`_score_multi_agent()`

核心输出：

- `multi_agent_quality`
- `agent_diversity`
- `agent_diversity_fit`
- `agent_agreement`
- `agent_query_relevance`
- `agent_citation_score`
- `agent_bridge_coherence`
- `agent_consensus_stability`
- `agent_perspective_coverage`
- `agent_disagreement_risk`
- `multi_agent_confidence`

主公式：

```text
agreement =
		0.12 * agreement_from_overlap
	+ 0.40 * relevance
	+ 0.22 * citation_score
	+ 0.13 * bridge_coherence
	+ 0.13 * agent_d_alignment

multi_agent_quality = 0.30 * diversity_fit + 0.70 * agreement
```

#### 理论出处

- `agent_diversity`：来自多样性分析。
- `agreement` / `consensus_stability`：来自共识与一致性分析。
- `citation_score`：来自 evidence-aware argumentation 思路。
- `perspective_coverage`：来自多视角覆盖的分析设计。

#### 为什么这里不是“越多样越好”

项目里用的是 `agent_diversity_fit` 而不是直接用 `agent_diversity` 做最终得分，因为：

- 多样性过低：说明不同 agent 只是重复；
- 多样性过高：说明系统可能失去共识；
- 最优状态是 **适中差异 + 有效整合**。

这非常符合多智能体系统评估中的常见实际判断标准。

### 5.4 Environment Preparation 指标

实现位置：`_score_environment_preparation()`

核心输出：

- `environment_preparation_quality`
- `persona_diversity`
- `persona_domain_match`
- `parameter_injection_completeness`
- `persona_artifact_coverage`

主公式：

```text
environment_preparation_quality =
		0.22 * entity_coverage
	+ 0.18 * relation_accuracy
	+ 0.15 * graph_connectivity
	+ 0.20 * persona_diversity
	+ 0.15 * persona_domain_match
	+ 0.10 * parameter_injection_completeness
```

#### 理论出处

这一部分主要是 **工程运行准备质量评估**，属于项目自定义代理指标。

它背后的专业逻辑是：

- 人设 / profile 是否充分；
- 参数是否被正确注入；
- persona 是否覆盖任务域；
- 这些准备工作是否与上游知识结构一致。

### 5.5 Insight 与 Report Quality 指标

实现位置：`_score_insight()`、`_score_report_quality()`

#### Insight Quality

主公式：

```text
insight_quality_raw = 0.28 * novelty + 0.52 * relevance + 0.20 * grounding
```

再乘以一个基于 grounding 的调节因子。

核心输出：

- `novelty`
- `relevance`
- `grounding`
- `insight_length`
- `insight_anchor_density`
- `insight_factual_anchor_score`
- `insight_hallucination_risk`

#### 理论出处

- `novelty`：来自信息新颖性评价。
- `relevance`：来自 query relevance。
- `grounding`：来自 LLM factual grounding / attribution 评价。
- `hallucination_risk`：来自反向 grounding 风险估计。

#### Report Quality

主公式：

```text
report_quality =
		0.16 * structure_quality
	+ 0.22 * report_evidence_quality
	+ 0.18 * report_actionability
	+ 0.18 * report_query_alignment
	+ 0.12 * report_coherence
	+ 0.14 * report_process_quality
```

核心输出：

- `report_structure_quality`
- `report_evidence_quality`
- `report_actionability`
- `report_query_alignment`
- `report_coherence`
- `report_process_quality`
- `report_hallucination_risk`

#### 理论出处

这一部分是 **LLM 报告质量评价** 与 **过程质量评价** 的混合代理指标。

其中：

- `structure_quality`：源自文档结构完整性评价；
- `evidence_quality`：源自 evidence-aware generation；
- `actionability`：源自管理咨询 / 决策支持类文本的可执行性评价；
- `query_alignment`：源自任务对齐；
- `coherence`：源自篇章连贯性；
- `process_quality`：是项目工程日志上的自定义指标。

### 5.6 Canyon Interaction / Deep Interaction 指标

这些指标用于评估 agent log 中的交互质量，例如：

- `dialogue_turns`
- `speaker_coverage`
- `interaction_reciprocity`
- `interaction_coherence`
- `interaction_density`

出处属于 **会话分析（conversation analysis）**、**多轮交互质量评估** 与 **系统日志过程分析** 的混合代理设计。

它们是本项目中非常有价值但明显属于 **工程化自定义指标** 的部分。

---

## 6. `llm_standalone_report_metrics.py`：LLM 报告 10 指标的出处

这是你当前多模型 benchmark 用得最多的一套指标。它的设计目标很明确：

> 不做人类主观打分，直接用文本、知识库和查询三者之间的关系来自动评估报告质量。

### 6.1 10 个指标及其出处

#### 1) `novelty`

```text
novelty = 1 - max_cosine(report, kb_docs)
```

来源：**新颖性 / 非冗余性评价**。

#### 2) `relevance`

```text
relevance = cosine(report, query)
```

来源：**任务相关性 / query alignment**。

#### 3) `grounding`

```text
grounding = supported_claims / total_claims
```

来源：**事实支撑率 / attribution / claim support**。

#### 4) `insight_length`

来源：**长度归一化评分**，属于工程代理指标。

它假定 700–2200 tokens 左右是较理想的深度分析长度区间。

#### 5) `insight_hallucination_risk`

```text
hallucination_risk = 1 - grounding
```

来源：**基于 grounding 的反向风险代理**。

#### 6) `report_structure_quality`

来源：**文档结构完整性**，通过“摘要 / 分析 / 预测 / 结论”等章节命中来计算。

#### 7) `report_coherence`

来源：**篇章连贯性**，用相邻段落的 TF-IDF 余弦相似度均值来近似。

#### 8) `report_actionability`

来源：**建议可执行性 / actionability**，基于行动词密度构建。

#### 9) `insight_anchor_density`

来源：**锚点密度（anchor density）**，衡量报告中有多少 token 与 query + KB 的核心术语重合。

#### 10) `insight_factual_anchor_score`

来源：**事实锚定评分**，衡量句子级内容能否在 KB 中找到近似支撑。

### 6.2 综合评分的出处

`run_benchmark()` 中将上述 10 个指标按权重组合为最终分数：

```text
score =
		0.10 * novelty
	+ 0.10 * relevance
	+ 0.20 * grounding
	+ 0.05 * insight_length
	+ 0.15 * (1 - hallucination_risk)
	+ 0.10 * structure_quality
	+ 0.10 * coherence
	+ 0.05 * actionability
	+ 0.075 * anchor_density
	+ 0.075 * factual_anchor
```

这是一个典型的 **项目加权综合质量分**，本质上不是公共 benchmark，而是本项目针对“深度分析报告”场景的自动评价函数。

### 6.3 为什么这套指标有意义

因为它实际上同时覆盖了四类问题：

- 是否相关；
- 是否新；
- 是否有依据；
- 是否写得像一份可用的分析报告。

---

## 7. `llm_deep_analysis_report.py`：深度分析报告质量分的出处

这个文件里有一套更轻量的质量评分函数：`_score_report_quality()`。

核心子项：

- `length_score`
- `section_score`
- `number_grounding_score`
- `structure_score`

最终：

```text
quality_score =
		0.20 * length_score
	+ 0.35 * section_score
	+ 0.30 * number_grounding_score
	+ 0.15 * structure_score
```

### 理论出处

这套分数主要服务于“多个模型谁更会写对比分析报告”的场景，因此强调：

- 篇幅是否足够；
- 是否覆盖关键章节；
- 是否引用了 comparison JSON 中的关键数字；
- Markdown 结构是否完整。

它的出处属于：

- **文档完整性评价**；
- **数值 grounding / evidence use**；
- **结构化写作质量代理评估**。

需要注意：

> 它不是通用文本质量指标，而是对“基于 comparison JSON 写分析报告”这一特定任务的定制质量分。

---

## 8. `compare_step3_markdown_experiment.py`：对比实验指标的出处

这个脚本做的不是重新计算底层指标，而是比较两份实验结果：

- `without_markdown`
- `with_markdown`

### 8.1 基础差分

对每个数值型指标：

```text
delta = with_markdown - without_markdown
relative_change_pct = delta / without_markdown * 100%
```

来源：**标准 A/B 实验差分分析**。

### 8.2 方向校正（benefit delta）

脚本显式识别“越低越好”的指标，如：

- `risk`
- `hallucination`
- `unclear`
- `contradiction`
- `missing`

然后做方向校正：

```text
benefit_delta = -delta   (如果该指标 lower is better)
benefit_delta =  delta   (否则)
```

来源：**成本型 / 效益型指标统一方向化处理**，这是多指标评价中的常见步骤。

### 8.3 Markdown Advantage Index

项目里还定义了一个工程总指标：

```text
markdown_advantage_index =
		step3_eis_delta * 100
	+ risk_improvement * 40
	+ (gained_gates - lost_gates) * 8
	+ improved_ratio * 20
```

这显然是一个 **项目自定义综合优势指数**，其设计目的不是学术标准化，而是帮助快速回答：

> “加不加 markdown supplement，整体上到底值不值？”

---

## 9. 哪些指标是“标准指标”，哪些是“项目定义”

### 9.1 近似标准 / 有明确经典来源的指标

- `Precision@K`
- `Recall@K`
- 余弦相似度 / TF-IDF 相似度
- 最大连通分量占比
- 图密度 / 节点-边密度代理
- 覆盖率（coverage）
- 关系正确率（relation accuracy）
- 时序一致性 / 因果一致性
- 相对改进率（relative improvement）

### 9.2 明确属于项目化代理定义的指标

- `retrieval_confidence`
- `retrieval_risk`
- `graph_reasoning_signal`
- `environment_preparation_quality`
- `agent_bridge_coherence`
- `agent_diversity_fit`
- `report_process_quality`
- `report_generation_completeness`
- `insight_anchor_density`
- `insight_factual_anchor_score`
- `markdown_advantage_index`

### 9.3 专业写法建议

如果你后续要写论文、技术报告或答辩，建议用下面这种表述：

> 本项目的量化评估体系由两部分组成：
> 一部分采用经典 IR / 图论 / 相似度分析中的通用指标；
> 另一部分采用面向真实系统运行日志设计的 proxy metrics，
> 用于在缺乏人工标注和统一 benchmark 的条件下进行自动化比较。

---

## 10. 使用边界与解释风险

为了避免误用，必须明确以下边界：

### 10.1 这些分数不是“真理值”

它们是 **代理评估**，适合做：

- 模型之间的相对比较；
- 同一流程不同版本的 A/B 对比；
- 系统迭代时的回归检测；
- 大规模实验中的自动筛选。

不适合直接替代：

- 专家盲评；
- 用户真实满意度；
- 严格事实核查 benchmark。

### 10.2 高 novelty 不一定等于高质量

在本项目中，`novelty` 越高表示与 KB 越不相似，但这可能意味着：

- 真正的新洞察；
- 也可能意味着 hallucination。

因此它必须和 `grounding`、`factual_anchor_score` 一起看。

### 10.3 多智能体 diversity 不宜单独看

`agent_diversity` 高并不自动代表系统更好。过高可能意味着 agent 彼此发散严重，无法收敛，因此项目里专门引入了 `agent_diversity_fit`。

### 10.4 报告质量分更适合比较，不适合绝对裁决

`report_quality`、`quality_score` 更适合做模型间横向比较，而不应被解释成“0.78 就一定是一份优秀报告”。

---

## 11. 推荐引用方式

如果你需要在文档或论文中引用本目录指标体系，建议按以下结构说明：

### 11.1 简短版

> We evaluate the system using a five-dimensional metric suite covering retrieval, knowledge graph construction, multi-agent collaboration, simulation capability, and insight quality. The final score (EIS) aggregates these dimensions either as relative improvements over a baseline or as weighted absolute scores in runtime monitoring.

### 11.2 强调无标注场景版

> Since no human-annotated ground truth is available for the full pipeline, we adopt a self-supervised and proxy-based evaluation framework. Classical metrics from information retrieval and graph analysis are combined with engineering proxy metrics derived from system logs, report structures, evidence density, and grounding signals.

### 11.3 强调 LLM 报告评测版

> For standalone LLM-generated reports, we use a ten-metric automated evaluation suite measuring novelty, relevance, grounding, length adequacy, hallucination risk, structure quality, coherence, actionability, anchor density, and factual anchoring.

---

## 12. 结论

本目录中的量化指标并不是来源单一的一套 benchmark，而是一个分层体系：

- `metrics_engine.py`：偏标准化、结构化输入的五维主指标；
- `self_supervised_metrics.py`：偏论文化、自监督解释框架；
- `pipeline_quant_monitor.py`：偏真实系统运行过程的工程代理指标；
- `llm_standalone_report_metrics.py`：偏 LLM 报告自动评估；
- `compare_step3_markdown_experiment.py`：偏 A/B 差分与收益汇总；
- `llm_deep_analysis_report.py`：偏写作质量排序。

如果只用一句话概括这些指标的“出处”，最准确的说法是：

> **它们建立在信息检索、图论、相似度计算、自监督评估和工程代理量化方法之上，并被项目化改造成适用于 NEXUS 全流程实验的自动评估体系。**

