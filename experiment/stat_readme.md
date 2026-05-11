# Experiment 量化指标计算说明（stat_readme）

本文档基于 `experiment/` 目录下当前代码实现整理，说明每个量化指标**如何计算**、**由哪些字段得到**、以及**最终如何汇总成 EIS**。


我们的量化指标主要分成五个维度：
R：搜索的检索质量（retrieval quality）
K：知识图谱质量（KG quality）
M：多智能体协作质量（multi-agent quality）
S：仿真能力（simulation quality）
I：洞察质量（insight quality）

## 搜索的检索质量（retrieval quality）：
传统的RAG重排rerank-topK算法，来计算 recall 和 precision. 然后多样性的话，women用的是 1-sim, sim的计算是结合三种相似度得到：【基于距离，方向，小模型权重映射】

## KG 维度的量化

运用 Zep API 的平台来计算的，用 Zep 分别将 Mirofish 和 Nexus 的建图结果来对比；

EntityCoverage 来代指本事件的实体命中率【那毕竟我们前面的深度搜索优化，搜索材料本身的关键词命中率就高】；

基于关系建立的量化指标是用图算法，深度优先搜索（DFS） 遍历图，找到最大连通分量（选出节点最多的那个），判断图的连通性（用python来计算）; 
- 但是，我们的 graph 通过 Zep 的算法加持，这个图会 real-time update, 图随时间变化的连通性，而原本mirofish是静态图，我们 NEXUS 的图是动态图，图的连通量会随模拟变化。

所以，对于动态图，我们 NEXUS 会用更多的指标来量化：
- 节点活跃度：被访问/检索次数（尤其关注重要接node被访问的次数）
- 边权变化：相关度分数变化 （类似weight，weight的调整能不能让重要的节点被访问更多次数？）
- LCC 占比：核心知识子图连通性
- GraphRAG检索到的向量信息能不能覆盖所有 query 信息

## Multi-Agent 多个Agent协作的维度：
每个agents回答的 1-sim 得到多样性指标，避免一个 agents 重复回答某一个答案【原作是会出现agent偷懒的问题，基于简单强化学习RL奖励函数的设计，会重复某一个action来“骗奖励”，但是我们设置了重复动作的惩罚，并且同一个回复的奖励有一个指数衰减】

## Simulation 维度：
结合上面 multiagent 协作的质量量化，内设置一个 voting 机制，idea发生变化趋同会导致 voting 往一个方向去发展，然后看 simulation 对于 voting 的收敛。同时 simulation 会加一个奖励函数，如果交互对话能够不跑题（内容前后sim），加分；跑题 or 答非所问扣分

## Insight Report 维度: 
- 传统对于一份report的量化指标：结构完整性指标 (结构标题、分段...) / 结论支持率 / 篇幅适宜度 / 语言质量 (语法错误数、句子复杂度、重复率)
- 【额外】新颖度：Novelty 与知识库相似度反向： 1-sim
- 【额外】深度分析：提取 LLMs 的思维链，思维链长度 + 对应的 evidence，融合起来计算；
- 幻觉：因为本身就有多协作 + 多验证，同时 GraphRAG 建图高质量也一定程度上降低了乱讲的概率

---

## 1. 指标体系总览

`experiment/` 里主要有三套量化口径：

1. `metrics_engine.py`（标准 5 维 + EIS，相对改进）
2. `pipeline_quant_monitor.py`（Step2/Step3 实验监控，含大量过程指标与风险门槛）
3. `self_supervised_metrics.py`（论文式自监督评估框架）

实际批量跑实验常见入口：
- `run_metrics.py`（调用 `EmergentMetricsEngine`）
- `pipeline_quant_monitor.py`（step2 / step3-snapshot / finalize）

---

## 2. 统一记号

设五个维度分别为：

- $R$：检索质量（retrieval quality）
- $K$：知识图谱质量（KG quality）
- $M$：多智能体协作质量（multi-agent quality）
- $S$：仿真能力（simulation quality）
- $I$：洞察质量（insight quality）

所有维度最终都被裁剪到 $[0,1]$（`_clamp01` / `_clip01`）。

---

## 3. `metrics_engine.py` 的指标计算（推荐作为“统一口径”）

文件：`experiment/metrics_engine.py`

### 3.1 Retrieval 维度

输入：`payload["retrieval"]`（每个 case 含 `top_k_doc_ids`, `gold_doc_ids`, `result_texts`）

- Recall@K:
$$
\text{Recall@K} = \frac{|\text{TopK} \cap \text{Gold}|}{|\text{Gold}|}
$$
- Precision@K:
$$
\text{Precision@K} = \frac{|\text{TopK} \cap \text{Gold}|}{|\text{TopK}|}
$$
- Diversity（文本两两相似度的反向）：
$$
\text{Diversity} = 1 - \operatorname{avg\_pairwise\_similarity}(\text{result\_texts})
$$

输出字段：`Recall@K`, `Precision@K`, `Diversity`

---

### 3.2 KG 维度

输入：`payload["kg"]`

- EntityCoverage:
$$
\text{EntityCoverage} = \frac{|E_{gold} \cap E_{graph}|}{|E_{gold}|}
$$
- RelationAccuracy:
$$
\text{RelationAccuracy} = \frac{\#\{\text{is\_correct}=True\}}{\#\text{triples}}
$$
- GraphConnectivity（最大连通分量占比）:
$$
\text{GraphConnectivity} = \frac{|\text{LCC}|}{|V|}
$$

输出字段：`EntityCoverage`, `RelationAccuracy`, `GraphConnectivity`

---

### 3.3 Multi-Agent 维度

输入：`payload["multi_agent"]["cases"]`

- AgentDiversity:
$$
\text{AgentDiversity} = 1 - \operatorname{avg\_pairwise\_similarity}(\text{agent\_answers})
$$
- GainNormalized：先算
$$
\text{gain\_raw} = \frac{p_{multi}-p_{single}}{p_{single}}
$$
再归一化
$$
\text{GainNormalized} = \frac{\max(0,\text{gain\_raw})}{1+\max(0,\text{gain\_raw})}
$$
- ConflictResolutionRate:
$$
\text{ConflictResolutionRate} = \frac{\text{resolved\_conflicts}}{\text{initial\_conflicts}}
$$

输出字段：`AgentDiversity`, `GainNormalized`, `ConflictResolutionRate`

---

### 3.4 Simulation 维度

输入：`payload["simulation"]["cases"]`

- ScenarioDiversity：
$$
1 - \operatorname{avg\_pairwise\_similarity}(\text{future\_scenarios})
$$
- PredictionConsistency：从多次 run 的数值列标准差构造
$$
\text{PredictionConsistency}=\frac{1}{1+\operatorname{mean\_std}}
$$
- CausalValidity：
$$
\frac{\#\{\text{is\_valid}=True\}}{\#\text{causal\_edges}}
$$
- TemporalCoherence：专家时间分（1~5）归一化到 0~1
$$
\text{TemporalCoherence}=\frac{\operatorname{mean}(\text{temporal\_scores})}{5}
$$

输出字段：`ScenarioDiversity`, `PredictionConsistency`, `CausalValidity`, `TemporalCoherence`

---

### 3.5 Insight 维度

输入：`payload["insight"]["outputs"]`

- Novelty（与知识库相似度反向）：
$$
\text{Novelty}=1-\operatorname{avg\_sim}(\text{text}, \text{knowledge\_base\_texts})
$$
- ReasoningDepth：
$$
0.5\cdot\frac{\text{avg\_chain\_len}}{5}+0.5\cdot\frac{\text{avg\_evidence}}{5}
$$
- ExpertScore：`usefulness/innovation/logic` 的均值，再除以 5

输出字段：`Novelty`, `ReasoningDepth`, `ExpertScore`

---

### 3.6 五维得分与 EIS

维度得分（`dimension_scores`）按子指标平均：

- RetrievalQuality = avg(Recall@K, Precision@K, Diversity)
- KGQuality = avg(EntityCoverage, RelationAccuracy, GraphConnectivity)
- MultiAgentQuality = avg(AgentDiversity, GainNormalized, ConflictResolutionRate)
- SimulationQuality = avg(ScenarioDiversity, PredictionConsistency, CausalValidity, TemporalCoherence)
- InsightQuality = avg(Novelty, ReasoningDepth, ExpertScore)

EIS（相对改进）定义为：
$$
\text{EIS}=\sum_d w_d\cdot\frac{P_d^{nexus}-P_d^{baseline}}{P_d^{baseline}}
$$
其中权重来自 `payload.weights`；若未提供则默认等权（每维 $0.2$，且会自动归一化）。

输出字段：
- `EIS.score`
- `EIS.weights`
- `EIS.relative_improvements`

---

## 4. `pipeline_quant_monitor.py` 的关键量化口径（Step2/Step3）

文件：`experiment/pipeline_quant_monitor.py`

这套更偏“工程实战监控”，除了五维主分，还会输出风险与门槛。

### 4.1 五维主分（Step2/Step3）

最终 EIS（step2/step3 一致）：
$$
\text{EIS}=0.15R+0.25K+0.20M+0.20S+0.20I
$$

#### Retrieval（`_score_retrieval`）
$$
R=0.65\cdot\text{source\_relevance}+0.10\cdot\text{reliability\_boosted}+0.15\cdot\text{ev\_quality}+0.10\cdot\text{evidence\_density}
$$
其中：
- `reliability_boosted = max(reliability_signal, 0.60 * source_relevance)`
- `retrieval_confidence = 0.50*source_relevance + 0.30*ev_quality + 0.20*report_coverage`
- `retrieval_risk = 1 - retrieval_confidence`

#### KG（`_score_kg`，无 GraphRAG fallback）
$$
K=0.15\cdot\text{structure}+0.15\cdot\text{consistency}+0.10\cdot\text{graph\_density}+0.55\cdot\text{graph\_reasoning}+0.05\cdot\text{evidence\_balance}
$$
`graph_reasoning` 子项：
$$
0.30\cdot\text{path}+0.28\cdot\text{quant}+0.18\cdot\text{conf}+0.14\cdot\text{reasoning\_depth}+0.10\cdot\text{integrated\_conf}
$$

#### Multi-Agent（`_score_multi_agent`）
$$
M=0.30\cdot\text{diversity\_fit}+0.70\cdot\text{agreement}
$$
$$
\text{agreement}=0.12\cdot\text{overlap\_agreement}+0.40\cdot\text{relevance}+0.22\cdot\text{citation}+0.13\cdot\text{bridge}+0.13\cdot\text{agentD\_align}
$$

#### Simulation（`_score_simulation`）
$$
S=0.24\cdot\text{progress}+0.15\cdot\text{action\_balance}+0.16\cdot\text{action\_intensity}+0.10\cdot\text{log\_density}+0.13\cdot\text{canyon}+0.12\cdot\text{dynamic\_adaptability}+0.10\cdot\text{temporal\_memory\_consistency}
$$

#### Insight（`_score_insight` + step3融合）
Agent-D 洞察先算：
$$
I_{agentd}=0.28\cdot\text{novelty}+0.52\cdot\text{relevance}+0.20\cdot\text{grounding}
$$
再做 grounding 因子修正；在 step3 中还会与报告质量融合：
$$
I=0.65\cdot I_{agentd}+0.35\cdot \text{report\_quality}
$$

---

### 4.2 Finalize 阶段：贡献、风险、门槛

`cmd_finalize` 会输出：

- `contributions`：
  - retrieval: `0.15 * retrieval_quality`
  - kg: `0.25 * kg_quality`
  - multi_agent: `0.20 * multi_agent_quality`
  - simulation: `0.20 * simulation_quality`
  - insight: `0.20 * insight_quality`

- `overall_risk`：
$$
0.22\cdot retrieval\_risk + 0.26\cdot kg\_risk + 0.20\cdot agent\_disagreement\_risk + 0.12\cdot (1-S) + 0.20\cdot insight\_hallucination\_risk
$$

- `quality_gates`：
  - retrieval ≥ 0.75
  - kg ≥ 0.60
  - multi_agent ≥ 0.55
  - simulation ≥ 0.80
  - insight ≥ 0.60
  - overall_eis ≥ 0.70

---

## 5. `self_supervised_metrics.py`（论文式自监督框架）

文件：`experiment/self_supervised_metrics.py`

这套是“可写论文的解释型框架”，与 `metrics_engine.py` 口径不同，但同样输出五维。

### 5.1 典型公式

- Retrieval：
$$
R(q)=\frac{1}{k}\sum_i \cos(Emb(q), Emb(d_i))
$$
并结合一致性项：
$$
R_{final}=0.7\cdot \text{semantic\_similarity}+0.3\cdot \text{consistency}
$$

- KG：
$$
K=0.3\cdot C+0.3\cdot RC+0.4\cdot EC
$$
其中 $C$ 为连通性，$RC$ 为关系一致性，$EC$ 为嵌入一致性。

- Multi-Agent：
$$
M=0.5\cdot D+0.5\cdot A
$$

- Simulation：
$$
S=0.5\cdot TC+0.5\cdot CC
$$

- Insight：
$$
I=0.4\cdot N+0.6\cdot R
$$

### 5.2 EIS（该文件中的实现）

权重固定：
- retrieval: 0.15
- kg: 0.25
- multi_agent: 0.20
- simulation: 0.20
- insight: 0.20

提供两种结果：
- `eis_absolute`：五维绝对加权分
- `eis_relative`：相对 baseline 的改进加权分（负改进先截断到 0）

---

## 6. 运行命令（可复现）

### 6.1 跑标准 5 维 + EIS（`metrics_engine.py`）

```bash
python3 experiment/run_metrics.py \
  --input experiment/examples/experiment_input_example.json \
  --output experiment/report/metrics_example.json
```

### 6.2 跑 Step2 / Step3 / Finalize（`pipeline_quant_monitor.py`）

```bash
python3 experiment/pipeline_quant_monitor.py step2 \
  --summary assets/1_search/summary_report_xxx.json \
  --step2-output container/enhanced_news/agent_guide_xxx.md \
  --output experiment/report/pipeline_metrics/step2_metrics.json

python3 experiment/pipeline_quant_monitor.py step3-snapshot \
  --summary assets/1_search/summary_report_xxx.json \
  --step2-output container/enhanced_news/agent_guide_xxx.md \
  --backend-uploads-dir backend/uploads \
  --output experiment/report/pipeline_metrics/step3_metrics.json

python3 experiment/pipeline_quant_monitor.py finalize \
  --step2-json experiment/report/pipeline_metrics/step2_metrics.json \
  --step3-json experiment/report/pipeline_metrics/step3_metrics.json \
  --output experiment/report/pipeline_metrics/pipeline_metrics.json
```

---

## 7. 结果解读建议

1. 先看 `quality_gates`：确认是否达标。  
2. 再看 `contributions`：定位 EIS 提升主要来源。  
3. 再看 `overall_risk` 和各风险子项：判断是否“高分但不稳”。  
4. 若要做系统对标，使用 `compare_systems.py` 对多个指标 JSON 统一排序。

---

## 8. 与现有文档关系

- 本文件：偏“统计口径速查 + 公式索引”。
- 详版说明可参考：`experiment/QUANTITATIVE_METRICS_GUIDE.md`。
