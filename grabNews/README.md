# 🛸 NEXUS ✨ — Networked Emergent X-agent Universe Simulator

> (1) `多搜索引擎检索`（Multi-Engine Retrieval）与`多智能体协同验证`（Multi-Agent Collaborative Verification） 的`实时新闻数据增强与事实核验工作流`（Real-time News Augmentation & Fact-Checking Pipeline）。系统通过自动化信息抓取、用户关注点语义标注以及多智能体交叉分析，实现对热点信息的 真实性评估、时效性验证与逻辑一致性检验，从而生成高可信度的增强数据。
   - 时效性 + 信息广度控制
   - 人机协同标注（关注点/疑问点）
   - 多智能体深度检验逻辑链：Claim Extraction → Evidence Retrieval → Credibility Assessment → Logic Analysis → Premise Coverage → Consensus Synthesis）
   - 面向预测引擎的数据准备（结构化报告 + 置信度评分 + 风险提示）

> (2) 设计并实现 基于 `GraphRAG 与 Multi-Agent System 的预测现实世界 Predictive Simulation Engine`。系统通过持续提取现实世界的关键种子信号（如突发新闻事件、舆论动态、与科研前沿），构建`高保真的数字孪生信息空间`（Digital Twin Information Space）。在该环境中，大规模具备`长期记忆机制、行为策略与社会交互能力`的智能体进行`持续演化`，通过复杂交互模拟宏观社会趋势与潜在事件演化路径。系统支持在宏观控制层动态注入外部变量，对不同情景进行模拟推演，从而为复杂系统的趋势预测与策略决策提供数据驱动的分析能力。
   - 高保真数学模拟世界
   - 长期记忆与社会交互智能体
   - 外部变量注入与情景模拟推演

目标： 为 新一代 AI 预测与决策支持系统（Next-generation AI Forecasting & Decision Intelligence Engine） 构建高质量现实世界信号源，提供 高相关性（High Relevance）、高可信度（High Credibility）以及可追溯性（Traceability） 的种子数据，为下游 GraphRAG 推理、智能体模拟以及预测模型训练 提供可靠的数据基础。

---

## 1. 项目定位

**NEXUS（Networked Emergent X-agent Universe Simulator）** 是一个面向“现实信号采集 → 结构化理解 → 深度核验 → 预测引擎供数”的一体化系统。

它聚焦于以下现实世界高价值信息：
- 突发新闻
- 政策草案与监管动态
- 金融与产业信号
- 跨媒体、跨地区、跨时效的事实线索

通过多搜索引擎 + 多 Agent 协作，NEXUS 将噪声新闻流转化为可供后续“平行数字世界构建”使用的高质量数据资产。

---

## 2. 核心能力

### 2.1 多搜索引擎驱动

- **国内源**：`bigmodel_web_search`（智谱搜索 API）、`baidu`
- **海外源**：`serpapi`、`brave`
- **兜底策略**：主源失败自动 fallback，降低单点不可用风险

### 2.2 时效与信息广度控制

- 支持多个时间维度：`一天` 到 `不限时间`
- 支持搜索广度扩展（建议搜索种子 `>=3`）
- 支持针对无直链结果的关键词扩展和关联链接补全

### 2.3 人机协同标注（重点/疑问）

- 用户可在浏览中标记：
   - `!` 关注点（高优先级）
   - `?` 疑问点（待核查）
- 支持手动标注与 Hypothesis 自动同步
- 标注用于引导 LLM 与 Agent 的注意力聚焦

### 2.4 多 Agent 深度检验

- Claim 抽取、证据检索、逻辑一致性、前提覆盖与可信度评估
- 支持快速模式与深度模式切换
- 输出结构化结论（支持率、置信度、风险项、证据摘录）

### 2.5 面向预测引擎的数据准备

输出数据可直接用于：
- 现实世界信号 seed 构建
- 时序事件图谱更新
- 平行数字世界场景初始化
- 下游预测模型的检索增强与校验增强

---

## 3. WebUI 工作流（搜索 → 标记 → 检验 → 导出）

主界面：`fact_verification/ui/streamlit_app.py`

### Step 1：搜索与浏览
- 输入主题关键词
- 选择搜索源与时效
- 获取候选新闻并浏览

### Step 2：标记管理
- 对网页内容添加 `!` / `?` 标记
- 同步 Hypothesis 标注（可选）
- 导出 `hl_content` 标注文件

### Step 3：生成评估
- 执行网页深度分析 + 事实检验
- 支持三种模式：
   - **极速模式**：最低延迟，适合快速筛选
   - **平衡模式**：默认推荐，速度与质量平衡
   - **深度模式**：多 Agent + 更完整验证，适合高价值主题

### Step 4：最终导出
- 选择保留报告
- 一键导出到 `summary_report/`
- 输出完整 JSON + 摘要文件（含 `page_summary` 与 `web_content`）

---

## 4. 系统架构概览

```text
[Multi Search Engines]
    ├─ BigModel / Baidu / SerpAPI / Brave
    ▼
[Candidate News + Link Enrichment]
    ▼
[Human Marking Layer]
    ├─ Focus Marks (!)
    └─ Question Marks (?)
    ▼
[NEXUS Multi-Agent Verification Pipeline]
    ├─ Claim Extractor
    ├─ Evidence Retriever
    ├─ Credibility Agent
    ├─ Logic Agent
    ├─ Premise Agent
    └─ Consensus Agent
    ▼
[Structured Reports + Confidence + Risks]
    ▼
[Prediction-Ready Seeds for Parallel Digital Worlds]
```

---

## 5. 目录结构（关键模块）

```text
fact_verification/
   agents/
      claim_extractor.py
      evidence_retriever.py
      credibility_agent.py
      logic_agent.py
      premise_agent.py
      consensus_agent.py
      webpage_report_agent.py
      llm_client.py
   pipeline/
      orchestrator.py
   retrieval/
      search_tools.py
   scoring/
      confidence.py
   ui/
      streamlit_app.py

hl_content/        # 标注导出
summary_report/    # 报告导出（完整JSON + 摘要）
search.py          # 搜索与链接补全
```

---

## 6. 环境准备

### 6.1 安装依赖

```bash
pip install -r requirements.txt
```

### 6.2 环境变量（示例）

请在 `.env` 中配置（**不要提交真实密钥到公开仓库**）：

```dotenv
# 搜索相关
SERPAPI_API_KEY=xxx
BIGMODEL_API_KEY=xxx
SEARCH_PROVIDER=bigmodel_web_search
SEARCH_RECENCY=oneWeek

# 标注同步（可选）
HYPOTHESIS_USERNAME=your_name
HYPOTHESIS_TOKEN=your_token

# LLM
DEEP_SEEK_API_KEY=xxx
WEB_REPORT_ENABLE_LLM=1
DEEPSEEK_TIMEOUT=22

# Step3 性能模式参数（可选）
STEP3_MAX_WORKERS=3
STEP3_SKIP_VERIFY=1
```

---

## 7. 启动方式

```bash
cd /Users/suleynan_suir/Desktop/grabNews
python3 -m streamlit run fact_verification/ui/streamlit_app.py --server.port 8502
```

浏览器访问：`http://127.0.0.1:8502`

---

## 8. 输出产物说明

### 8.1 标注文件
- 目录：`hl_content/`
- 内容：关键词、已选 URL、标注明细、时间戳

### 8.2 报告文件
- 目录：`summary_report/`
- `summary_report_<ts>.json`：完整结构化报告
- `summary_only_<ts>.md`：聚焦摘要与原文摘录

报告关键字段：
- `page_summary`
- `structured_claim_checks`
- `reliability_assessment`
- `multi_agent_analysis`（深度模式）
- `quant_metrics`（置信度、覆盖率、支持率等）

---

## 9. 典型应用场景

1. **政策冲击追踪**：快速收集政策草案相关新闻并做一致性核验  
2. **金融风险雷达**：融合跨源新闻信号，输出风险提示与证据链  
3. **技术趋势监测**：围绕 AI/产业议题持续生成可检索事实报告  
4. **预测引擎供数**：将真实世界信号转为结构化 seed 输入平行世界模拟

---

## 10. 质量与可信度原则

- **可追溯**：每条结论尽量对应证据片段
- **可解释**：输出支持/部分支持/不明确/矛盾等结构化状态
- **可扩展**：新搜索源、新 Agent、新评估策略可插拔
- **人机协同**：用户标注始终是分析焦点约束

---

## 11. 路线图（Roadmap）

- [ ] 加入事件图谱构建与实体关系演化追踪
- [ ] 增加跨语种新闻对齐与多地区语义归并
- [ ] 引入长期记忆层（主题级历史证据链）
- [ ] 面向预测引擎提供标准化 seed API
- [ ] 增强“场景推演”与“反事实模拟”能力

---

## 12. 致谢

NEXUS 旨在把“实时新闻抓取 + 多 Agent 事实处理 + 人机协同标注”连接为统一数据工程链路，为下一代 AI 预测系统提供可持续、可验证的数据底座。