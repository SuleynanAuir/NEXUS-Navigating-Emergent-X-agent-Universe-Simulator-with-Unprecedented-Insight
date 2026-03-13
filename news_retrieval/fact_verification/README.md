# Fact Verification 模块设计

本模块用于对“句子 / claim / `annotations.json` / 文档抽取陈述”进行自动化事实验证，目标不是给出武断结论，而是基于多源证据、来源质量、逻辑条件与前提约束，输出**可信度、置信度和透明的推理报告**。

核心目标：

- 高质量证据优先
- 少量低质量反例不过度拉低结论
- 避免过度泛化
- 先快筛，再深挖
- 多代理协作但不重复搜索
- UI 可追踪、可解释、可复核

## 新增：搜索与检验一体化流程（UI）

`fact_verification/ui/streamlit_app.py` 现按以下顺序工作：

1. 用户输入关键词搜索，并在每条搜索结果旁勾选是否用于后续报告。
2. 用户进入搜索结果页面浏览后，在 UI 中添加标记内容并点击“导出JSON”。
3. 标记内容会保存到 `hl_content/hl_content_*.json`（字段为 `hl_content`）。
4. 用户点击“完成浏览”后，系统仅对被勾选网页生成报告，并额外关注 `hl_content`。
5. 系统对每篇报告给出量化指标（置信度、等级、支持率、标记覆盖率、风险项数等），支持二次勾选并导出最终整合 JSON。

最终导出文件包含：`selected_reports`、每篇报告的 `fast_verification`、`quant_metrics`、以及 `hl_content_file` 路径。

## 1) 适用输入

系统支持以下输入形态：

- 单句陈述（sentence）
- 显式 claim 列表
- `annotations.json`（每条含 `text` + `url`）
- 文档中抽取出的 statement / finding / conclusion

统一进入 `Claim` 数据结构，至少包含：

```yaml
text: "待验证主张"
source_type: text|annotations|document
source_url: "可选，原始来源链接"
context: "上下文片段"
```

## 2) 设计原则

### 2.1 高置信证据优先

来源质量高的证据必须显著提高分数，例如：

- 同行评审论文
- 官方技术文档 / 标准规范
- 政府 / 国际组织 / 大学网站
- 权威数据库与可信知识库

推荐将来源分层：

| 层级 | 来源类型 | 基础权重 |
|---|---|---:|
| Tier A | peer-reviewed、官方文档、政府/高校 | 0.90 - 1.00 |
| Tier B | 知名技术媒体、专业研究博客、预印本 | 0.70 - 0.85 |
| Tier C | 普通媒体、聚合站、营销材料 | 0.45 - 0.65 |
| Tier D | 论坛、匿名内容、来源不明摘要 | 0.20 - 0.40 |

### 2.2 少量反证不应主导结论

如果存在多个独立高质量支持来源，而只有少量低质量反对证据，则最终置信度只应**温和下调**。只有当反证满足以下条件之一时，才应显著影响分数：

- 反证来自 Tier A / Tier B 高质量来源
- 反证直接击中 claim 核心，而非边缘细节
- 多个独立来源给出一致反驳

### 2.3 抑制过度泛化

系统应对以下表述自动提高审查强度：

- “all / always / never / every / universally”
- “在所有行业中都更优”
- “必然导致”“完全证明”“显著优于所有方法”

逻辑上需要将 claim 拆解为：

- 核心断言
- 适用范围
- 时间范围
- 比较基准
- 隐含条件

## 3) 两阶段验证架构

系统采用**加速验证流水线**：先做低成本快筛，再对不确定 claim 触发深度验证。

### Stage 1 — Fast Screening

目标：在低延迟下判断 claim 是否大概率属于：

- `well-supported`
- `weakly-supported`
- `unsupported`
- `uncertain`（进入 Stage 2）

输入后先做以下动作：

1. claim 标准化与轻量拆解
2. 生成 1~3 条短查询
3. 执行轻量 SerpApi 检索
4. 基于标题 / 摘要 / 域名做启发式打分
5. **新增：原文上下文对齐分析**（计算证据与原始文本的一致性）
6. **新增：语义深度评估**（评估证据的信息丰富度和关键词密度）
7. 输出初筛标签与是否需要深挖

建议快筛触发规则：

- 若 `高质量支持源 >= 2` 且 `高质量反证 = 0`，直接判为 `well-supported`
- 若 `无有效高质量来源` 且 `低质量来源居多`，判为 `unsupported`
- 若支持与反对混杂、或涉及绝对化表述，判为 `uncertain`

### Stage 2 — Deep Verification

仅对 `uncertain` 或高风险 claim 触发：

1. 多查询扩展
2. 多源深度检索
3. **增强版证据抽取**：融合上下文对齐和语义深度评分
4. stance 判别（支持/反驳）
5. 来源可信度校准
6. 逻辑一致性审查
7. 前提/边界条件识别
8. **增强版共识聚合**：权衡支持强度、多源多样性、官方数据信号、语义深度
9. 结构化报告生成

## 4) 多智能体协作设计

### 4.1 `ClaimExtractionAgent`

职责：

- 从句子、文档、`annotations.json` 中提取可验证 claim
- 合并重复 claim
- 提取范围词、时间词、比较对象
- 标注风险信号（绝对化、因果化、夸张表述）

输出：标准化 `Claim`

### 4.2 `FastEvidenceSearchAgent`

职责：

- 执行轻量 SerpApi 查询
- 优先拉取高价值域名结果
- 快速统计支持/反驳信号
- 给出初筛结论是否进入深度验证

关键要求：

- 只搜最必要的查询
- 复用缓存，避免后续代理重复搜索

### 4.3 `EvidenceRetrievalAgent`

职责：

- 从搜索结果中提取候选证据段落
- 判别 `support / contradict / neutral`
- 为每条证据计算相关性 `relevance`
- 标出证据是否直接击中 claim 核心

建议输出字段：

```yaml
quote: "证据摘录"
url: "来源"
source: "域名或出版物"
stance: support|contradict|neutral
relevance: 0-1
directness: 0-1
freshness: 0-1
```

### 4.4 `SourceCredibilityEvaluationAgent`

职责：

- 按来源层级计算基础可信度
- 评估是否独立来源（避免同源重复加权）
- 识别二手转述 vs 一手出处
- 结合出版类型、机构、时间新鲜度校准分数

特别注意：

- 多个转载页面不能等同于多个独立来源
- 原始论文、官方文档、标准文本应高于新闻转述

### 4.5 `LogicalConsistencyAgent`

职责：

- 检查 claim 是否存在范围外推、因果倒置、样本不足、指标偷换
- 判断 evidence 是否真能支持 claim，而非仅弱相关
- 输出逻辑限制条件

典型问题：

- 从“某任务更优”推到“所有任务更优”
- 从“相关性”推到“因果性”
- 从单一实验结果推到通用结论

### 4.6 `PreconditionsAnalysisAgent`

职责：

- 识别 claim 成立的必要前提
- 明确时间、数据集、评测指标、实验条件、适用对象
- 将“隐含假设”显式化

### 4.7 `ConsensusScoringAgent`

职责：

- 融合多代理输出
- 对支持与反证做非对称加权
- 生成最终 `confidence_score` 与 `verification_summary`

## 5) 高效协作与缓存策略

为避免冗余搜索，建议采用共享中间态：

```text
Claim
  -> normalized_queries
  -> search_cache
  -> evidence_pool
  -> credibility_map
  -> logic_findings
  -> premise_findings
  -> final_report
```

策略建议：

- 每个 claim 只执行一次基础检索
- 深度阶段基于已检索结果扩展，而非从零开始
- 按 URL 去重、按根域名聚类、按出处链路识别转载
- 为同一 claim 建立 session 级缓存

## 6) 置信度评分策略

最终分数范围为 `0-100`，建议拆为 5 个主维度：

- `source_credibility`：来源质量
- `support_strength`：支持证据强度
- `contradiction_impact`：反证影响度
- `logical_validity`：逻辑有效性
- `precondition_satisfaction`：前提满足度

### 6.1 评分直觉

- 强支持来自**独立的高可信来源**时，应显著加分
- 少量低可信反证只做轻微扣分
- 高可信直接反证应强扣分
- 逻辑泛化和缺失前提应降低上限分数

### 6.2 推荐计算方式

先定义：

- $S$：支持证据加权和
- $C$：反证证据加权和
- $L$：逻辑有效性
- $P$：前提满足度
- $I$：独立来源因子

其中每条证据的单条权重可定义为：

$$
w_i = credibility_i \times relevance_i \times directness_i \times independence_i
$$

支持和反证分别聚合：

$$
S = \sum w_i^{support}, \qquad C = \sum w_j^{contradict}
$$

为了避免少量弱反证过度影响，可使用**饱和型惩罚**：

$$
contradiction\_impact = \frac{C}{S + C + 1}
$$

而不是简单线性相减。

最终建议分数：

$$
confidence = 100 \times \Big(0.30\cdot source\_credibility +
0.30\cdot support\_strength +
0.15\cdot (1 - contradiction\_impact) +
0.15\cdot logical\_validity +
0.10\cdot precondition\_satisfaction\Big)
$$

### 6.3 结论分段与置信度等级系统（新增）

#### 6.3.1 六级置信度等级

系统采用细粒度的六级置信度等级划分，提供更精确的评估：

| 等级 | 分数范围 | 符号 | 描述 | 解释 |
|---:|---:|:---:|---|---|
| 完全支持 | 92-100 | ✅✅ | 有多个独立的高质量来源强有力支持，几乎没有反证 | 可以非常有信心地认为该主张是准确的 |
| 强烈支持 | 80-91.99 | ✅ | 有多个高质量来源支持，少量反证或低质量反证 | 可以有信心认为该主张是准确的 |
| 中等支持 | 65-79.99 | ⚠️ | 有适当的支持证据，但存在某些疑虑或有限的反证 | 需要进一步验证可能更有帮助 |
| 不确定 | 45-64.99 | ❓ | 支持和反驳证据混杂，或证据质量不清晰 | 主张的真伪尚不确定，需要深度分析 |
| 证据不足 | 30-44.99 | ❌ | 缺乏充分的支持证据，或有适度的反驳证据 | 根据可用信息，不足以支持该主张 |
| 强烈反驳 | 0-29.99 | ❌❌ | 有强有力的反证或缺乏任何支持 | 可以有信心认为该主张是不准确的 |

#### 6.3.2 新置信度计算权重

为大幅提升置信度评分的准确性和可靠性，新版本调整了权重分配：

$$
confidence = 100 \times \Big(
0.38 \cdot factuality 
+ 0.26 \cdot source\_credibility 
+ 0.20 \cdot evidence\_consistency 
+ 0.10 \cdot logical\_rigor 
+ 0.06 \cdot premise\_coverage
\Big)
$$

**权重变化说明：**
- **factuality (38%，↑ from 32%)**：事实性成为最重要维度，直接反映证据支持强度
- **source_credibility (26%，↓ from 24%)**：来源可信度权重略降，但融入证据强度信号
- **evidence_consistency (20%，保持)**：证据一致性保持稳定
- **logical_rigor (10%，保持)**：逻辑严密度保持稳定
- **premise_coverage (6%，↓ from 9%)**：前提覆盖度权重降低

#### 6.3.3 增强的事实性（Factuality）计算

新的 factuality 计算融合了多个维度：

$$
factuality = \min(1.0, 
  0.75 \cdot support\_ratio 
  + 0.15 \cdot avg\_evidence\_strength 
  + 0.12 \cdot support\_diversity 
  + official\_boost 
  + semantic\_boost 
  + context\_boost 
  + strength\_boost
)
$$

**新增维度说明：**
- **avg_evidence_strength (15%)**：平均证据强度 = relevance × context_alignment × semantic_depth
- **semantic_boost**：高语义深度（≥0.7）的支持证据额外加成 (max 0.08)
- **context_boost**：高上下文对齐（≥0.7）的支持证据额外加成 (max 0.06)
- **strength_boost**：高综合强度（≥0.75）的支持证据额外加成 (max 0.08)
- **official_boost**：官方来源（.gov/.edu等）额外加成 (max 0.12，↑ from 0.08)

## 6.4 新增：上下文对齐与语义深度优化

为进一步提升置信度评分的准确性和可靠性，系统新增两个关键维度：

### 6.4.1 上下文对齐度（Context Alignment）

**目的**：衡量证据是否与原始文本（annotations.json 中的 text）在语义空间中对齐。

**计算方式**：

```python
# 提取关键词集合（长度 > 2 字符）
claim_tokens = set(claim_text.split())
original_tokens = set(original_text.split())
evidence_tokens = set(evidence_quote.split())

# 计算三角对齐度
claim_original_overlap = len(claim_tokens & original_tokens) / max(1, len(claim_tokens | original_tokens))
evidence_overlap_with_original = len(evidence_tokens & original_tokens) / max(1, len(evidence_tokens | original_tokens))

context_alignment = (evidence_overlap_with_original + claim_original_overlap) / 2.0
```

**应用**：
- 高对齐度（≥ 0.7）的证据在计算支持强度时获得额外加权系数
- 低对齐度的证据作为补充参考，但权重降低
- 通过加权融合：`support_strength = sum(credibility × relevance × context_alignment for each evidence)`

### 6.4.2 语义深度（Semantic Depth）

**目的**：评估证据的信息丰富度——是否包含具体数据、统计信息、或结构化内容。

**计算方式**：

```python
# 三个分量：长度因子、关键词密度、信息丰富度
length_factor = min(1.0, len(evidence_tokens) / (len(claim_tokens) * 3))
keyword_density = len(claim_tokens & evidence_tokens) / len(claim_tokens)
info_richness = 1.0 if (has_numbers or "%" in evidence or "data" in evidence.lower()) else 0.8

semantic_depth = (length_factor * 0.3 + keyword_density * 0.5 + info_richness * 0.2)
```

**应用**：
- 高语义深度（≥ 0.7）的证据被视为质量更高的支持来源
- 在共识评分时，高深度支持证据的前提覆盖度额外加 0.1
- 自动识别"数据支撑型"证据并提升其在报告中的优先级

### 6.4.3 融合分数计算

新的综合置信度计算方式：

$$
confidence = 100 \times \Big(
0.32 \cdot factuality 
+ 0.24 \cdot source\_credibility 
+ 0.20 \cdot evidence\_consistency 
+ 0.15 \cdot logical\_rigor 
+ 0.09 \cdot premise\_coverage
\Big)
$$

其中 `factuality` 新增包含：

$$
factuality = \min(1.0, 
  0.68 \cdot support\_ratio 
  + 0.20 \cdot avg\_relevance 
  + 0.12 \cdot support\_diversity 
  + official\_boost 
  + semantic\_boost 
  + context\_boost
)
$$

- **semantic_boost**：`min(0.05, 0.015 × high_semantic_depth_count)`
- **context_boost**：`min(0.04, 0.01 × high_context_alignment_count)`

## 7) 快筛与深挖触发条件

建议 `FastEvidenceSearchAgent` 输出一个 `screening_decision`：

```yaml
screening_label: well-supported|weakly-supported|unsupported|uncertain
deep_verification_required: true|false
reasons:
  - "高质量支持源不足"
  - "出现绝对化范围词"
  - "存在高可信反证"
```

触发深挖的典型情况：

- claim 使用绝对化语言
- 支持证据与反证接近
- 高质量来源不足 2 个
- 来源集中在同一域名家族
- 证据只支持局部子命题而非完整 claim

## 8) 输出报告格式

每条验证结果应输出：

```yaml
Claim: "..."
Supporting Evidence:
  - quote: "..."
    source: "..."
    url: "..."
    credibility: 0-1
    relevance: 0-1
Contradicting Evidence:
  - quote: "..."
    source: "..."
    url: "..."
    credibility: 0-1
    relevance: 0-1
Source Credibility Analysis:
  source_tiers:
    tier_a: 2
    tier_b: 1
    tier_c: 1
  independence_notes:
    - "2 个结果为转载，不计作独立来源"
Logical Conditions:
  - "该结论仅在特定 benchmark 下成立"
Possible Preconditions:
  - "需要固定模型版本和数据集"
Confidence Score: 78
Verification Summary: "现有证据支持该主张在部分场景中成立，但不足以支持全称断言。"
```

同时建议输出：

- `reasoning_chain`
- `screening_label`
- `deep_verification_required`
- `trace`（查询、命中源数、是否启用 DeepSeek）

## 9) UI 设计

推荐继续使用 `Streamlit`，因为它与当前项目栈一致、适合可解释型验证工作流。

### 9.1 输入区

- 文本输入框
- 上传 `annotations.json`
- 文档 statement 导入入口（后续扩展）

### 9.2 操作区

- “开始验证”按钮
- `Fast Screening` / `Deep Verification` 状态标记
- 进度条与阶段提示
- SerpApi / DeepSeek 配置状态卡片

### 9.3 结果区

- 每条 claim 的置信度分数
- 支持证据 / 反证证据分栏
- 来源链接与来源等级
- 推理轨迹与逻辑条件
- 前提条件与限制说明
- 最终摘要

### 9.4 可视化建议

- 分数仪表盘或条形图
- 支持/反证来源数对比
- 来源层级分布图
- 深挖是否触发的流程视图

## 10) 与当前代码结构对齐

建议保留当前目录结构，并在现有实现上扩展：

```text
fact_verification/
  agents/
    claim_extractor.py
    search_agent.py
    evidence_retriever.py
    credibility_agent.py
    logic_agent.py
    premise_agent.py
    consensus_agent.py
    llm_client.py
  data/
    models.py
    trusted_sources.yaml
  retrieval/
    search_tools.py
  pipeline/
    orchestrator.py
  scoring/
    confidence.py
  evaluation/
    sample_cases.jsonl
  ui/
    streamlit_app.py
```

映射关系：

- `search_agent.py`：同时承担 `FastEvidenceSearchAgent` 与深挖查询扩展入口
- `evidence_retriever.py`：证据抽取、stance 判别、相关性排序
- `credibility_agent.py`：来源分层、独立性、可信度融合
- `logic_agent.py`：过度泛化、因果错误、范围问题
- `premise_agent.py`：必要前提与适用边界
- `consensus_agent.py`：反证非对称处理与最终评分
- `orchestrator.py`：Stage 1 / Stage 2 流程控制

## 11) DeepSeek 可选增强

DeepSeek 适合作为“增强器”，而不是唯一事实判断器。推荐用于：

- 查询扩展
- 证据与 claim 的 stance / relevance / rationale 判断
- 逻辑缺口识别
- 隐含前提补全
- 报告摘要生成

不建议直接让 LLM 单独决定结论；最终分数应由**证据与规则约束**驱动。

在项目根目录 `.env` 中配置：

```env
SERPAPI_API_KEY=your_serpapi_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

兼容写法：

```env
DEEP_SEEK_API_KEY=your_deepseek_api_key
```

## 12) 示例：避免过度泛化

输入主张：

> “GraphRAG 在所有行业中都优于传统 RAG。”

系统应输出如下判断思路：

1. 快筛识别到“所有行业中都”是全称断言
2. 初步检索发现部分文章支持“特定任务更优”，但不足以支撑全称命题
3. 深挖阶段检索 benchmark、论文、官方文档、技术分析
4. 逻辑代理指出：局部实验结论不能外推到所有行业
5. 前提代理指出：任务类型、数据结构、评估指标、模型版本均是必要条件
6. 共识代理给出：`mixed / weakly supported`

示例摘要：

> 现有证据支持 GraphRAG 在某些检索增强与知识结构化任务中优于传统 RAG，但没有足够高质量独立证据支持其在“所有行业”中普遍更优，因此应避免过度泛化。
