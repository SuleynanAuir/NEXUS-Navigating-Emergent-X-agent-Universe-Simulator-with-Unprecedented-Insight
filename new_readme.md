# NEXUS NEW README

## 🚀 项目定位：拒绝“正确废话”，做用户独享认知突破

NEXUS 不是通用问答模板引擎，而是面向**用户真实关注点**的认知推演系统：
- 不做“千人一面”的泛化分析
- 不给“看似正确但无决策价值”的空泛结论
- 通过用户关注锚点（Attention Anchors）驱动深度搜索、结构化建模与多视角推演，输出可行动洞见

---

## 1) 核心创新：从“信息回答”升级为“认知推演”

### 1.1 用户独享 Cognitive Map（反模板化）
**问题**：传统 RAG/通用 LLM 往往是“平均化答案”，忽略用户个体关注。

**NEXUS 机制**：
- 在图谱生成与模拟配置阶段注入用户先验：`focus_entities` / `focus_events`
- 将用户关注对象和事件直接写入本体与模拟提示，提升后续建模权重
- 形成面向单用户目标的认知图谱，而非公共模板图谱

**工程落点（仓库）**：
- `backend/app/api/graph.py`
- `backend/app/services/ontology_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `test_prior_settings.py`

**价值**：
- 从“泛泛而谈”转向“锚点驱动深挖”
- 显著提升分析贴合度与可解释性

---

### 1.2 高保真多源深度搜索（反单源重复）
**问题**：单源检索易信息偏置，重复内容高，结论脆弱。

**NEXUS 机制**：
- 引入压力驱动、段落级迭代反思（Iterative Reflection）
- 多 Agent 协作 + 不确定性量化 + 去噪重排序
- 在检索-反思-补证循环中不断提升事实保真度与一致性

**工程落点（仓库）**：
- `upairs_deepsearch_agents/`
- `cognitiveTemp_deepsearch/`

**价值**：
- 降低“信息冲突/幻觉”风险
- 提高证据完整性、可信度和时效性

---

### 1.3 不是静态预测，而是动态推演未来趋势
**问题**：传统分析多是静态快照，缺乏时序演化与群体互动。

**NEXUS 机制**：
- 构建 Digital Cognitive Twin（Canyon）
- 按现实行为规律（时段活跃、角色影响力、响应延迟）驱动多 Agent 交互
- 通过回合制仿真重建“事件-传播-反馈-再演化”链条

**工程落点（仓库）**：
- `backend/app/services/simulation_config_generator.py`
- `backend/scripts/run_parallel_simulation.py`

**价值**：
- 能看到趋势“如何形成”，而不只是“结果是什么”
- 适合风险预警、策略评估、政策影响研判

---

### 1.4 多角色多视角高保真模拟（反单视角）
NEXUS 将同一议题同时置于不同主体视角下进行推演：
- 政府与政策制定者（监管、治理、政策博弈）
- 企业与市场参与者（投资、竞争、品牌风险）
- 公众与社群舆论场（扩散、情绪、意见领袖）
- 研究者与专家网络（机制解释、证据框架、方法论）

**价值**：
- 从“单结论”升级为“多主体可对照决策空间”
- 更容易发现隐藏冲突、共识边界与拐点信号

---

## 2) 为什么 NEXUS 能避免“大众模板答案”

NEXUS 的关键不是“多跑几次模型”，而是**结构性机制改造**：
1. **锚点先验注入**：用户关注点进入本体和模拟全链路
2. **检索反思闭环**：不是一次检索，而是证据迭代优化
3. **不确定性约束**：让系统知道“哪里不确定，如何补证”
4. **仿真而非摘要**：通过角色行为演化，生成可推演的认知结果

因此 NEXUS 输出的是“用户上下文中的洞见”，而不是“互联网上的平均回答”。

---

## 3) 效率与成本：提速但不牺牲深度

> 下述指标为项目当前方案给出的工程目标/实测口径（可按你的实验环境复现验证）。

相较于原 mirofish 架构，NEXUS 的优化方向是：
- 背景知识先验 + 关注锚点聚焦，减少无效推理 token
- 优化智能体人格与职责分工，减少重复计算
- 双 LLM 通道（通用 + Boost）支持并行阶段提速

目标效果：
- 成本下降约 **40%~60%**（例如单次模拟从 `$5` 到 `$2~3`）
- 总时长缩短至约 **1/3**（例如从 `50` 分钟到 `18~20` 分钟）
- 在更少模拟轮次下保持分析质量（例如 `30` 次替代 `96` 次）

**工程落点（仓库）**：
- `.env` 中 `LLM_BOOST_API_KEY / LLM_BOOST_BASE_URL / LLM_BOOST_MODEL_NAME`
- `backend/scripts/run_parallel_simulation.py` 的双 LLM 选择逻辑

---

## 4) 关键能力总览（面向落地）

- **深度搜索高度贴合**：围绕用户锚点组织检索与证据
- **高保真知识建模**：图谱本体 + 关系约束 + 角色语义
- **动态未来推演**：时序仿真 + 多主体交互反馈
- **创新视角产出**：支持“jump outside of the box”的认知突破
- **资源受限可用**：通过加速配置获得高性价比深度分析

---

## 5) 快速使用（加速配置）

在项目根目录 `.env` 中可选配置：

```dotenv
LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL_NAME=...

# 可选：并行加速通道
LLM_BOOST_API_KEY=...
LLM_BOOST_BASE_URL=...
LLM_BOOST_MODEL_NAME=...
```

说明：
- 不使用加速通道时，可不配置 `LLM_BOOST_*`
- 使用并行模拟时，系统可根据配置切换通道以提升吞吐

---

## 6) 可选参考文献（Optional Material）

### 用户意图与个性化检索
- Farshidi et al. (2024), *Understanding user intent modeling for conversational recommender systems* (Springer Nature)
- Nguyen et al. (2018), *A Capsule Network‑based Embedding Model for Search Personalization* (arXiv)

### 迭代检索与意图驱动 GraphRAG
- Guo et al. (2025), *Beyond Static Retrieval: Opportunities and Pitfalls of Iterative Retrieval in GraphRAG* (arXiv)
- Zhu et al. (2025), *Conversational Intent‑Driven GraphRAG* (arXiv)

### 认知叙事与计算创造
- Zhong et al. (2023), *Beyond Sentiment: Cognitive and Narrative Open‑Ended Generation* (arXiv)
- Saunders (2012), *Towards Autonomous Creative Systems: A Computational Approach*, *Cognitive Computation*

---

## 7) 一句话总结

**NEXUS 的创新不在于“更会说”，而在于“更会理解你关心什么，并把真实世界多源信息转化为可推演、可决策的认知引擎”。**
