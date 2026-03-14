# UPARIS-DS: Uncertainty-Aware Paragraph-Level Iterative Reflective Deep Search Agents Collaboration

<!-- 项目基础信息 -->
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](./README.md)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](./LICENSE)
[![Framework](https://img.shields.io/badge/framework-Multi_Agent-purple.svg)](./README.md)
[![Async](https://img.shields.io/badge/async-asyncio+aiohttp-blueviolet.svg)](https://docs.python.org/3/library/asyncio.html)

[![LLM](https://img.shields.io/badge/LLM-DeepSeek-00d4ff.svg)](https://platform.deepseek.com/)
[![Search](https://img.shields.io/badge/search-Tavily-orange.svg)](https://tavily.com/)
[![Uncertainty](https://img.shields.io/badge/uncertainty-Quantified-lightblue.svg)](./DEMO_REPORT.md)
[![Metrics](https://img.shields.io/badge/metrics-NDCG_|_MRR-brightgreen.svg)](./DEMO_REPORT.md)

- Issue: [GitHub Issues](https://github.com/SuleynanAuir/UPAIRS-Agents/issues)
- Email: suleynanaiur@gmail.com

- Language: [中文文档](asserts/README_CN.md) | [English Documentation](asserts/README_EN.md)

- Time Update: 2026-03-01

## 📊 Demo Statistic Report
[![Full Demo Report](https://img.shields.io/badge/📊_查看完整演示报告-点击打开-brightgreen?style=for-the-badge)](asserts/DEMO_REPORT.md)

## 🎨  UPAIRS-Agents Architecture

UPARIS-DS 提出了一种基于压力驱动（Pressure-Driven）的段落级迭代反思搜索架构，其核心创新在于构建了五因子不确定性量化模型（5-Factor UQ Model）。该框架通过 8 个专业化 Agent 协同，利用语义熵与方差惩罚对证据权威性、时效性及一致性进行多维建模；并引入**动态反思压力机制(Dynamic Reflection Stress)**，依据不确定性阈值自适应分配检索预算与推理深度。结合**多样性去噪排序（Diversity Denoising）** 与 **跨维度置信度评估**，该系统有效解决了 RAG 中的信息冲突与幻觉问题，实现了具备高事实保真度（Factuality）与逻辑鲁棒性的长文本深度合成

---

<div align="center">



![MARDS v2 System Architecture](asserts/nano-banana-pro-9PAI8HRRN0BvYYEh1WSex.png)
**Figure 1: UPAIRS-DS Architecture**: *Agents Collaboration with Iterative Reflection & Uncertainty Quantify*

</div>

---


> *Prompt: "Artificial Intelligence Ethics (人工智能伦理)"*

| 指标 | 平均置信度 | 全局不确定性 | 反思循环次数 | 矛盾验证 | 权威来源数 | 源多样性 |
|------|---------|-----------|---------|---------|--------|--------|
| 结果 | **0.88** ✅ | **0.12** 🟢 | **×2** | 无显著矛盾 ✓ | **×31** | **0.94** 📊 |
| 评级 | 高质量 | 低风险 | 适中 | 已解决 | 充分 | 优秀 |

| 检索质量指标 | NDCG | MRR | 权威性评分 | 证据一致性 | 查询覆盖率 | 相关性 |
|---------|------|-----|----------|----------|----------|--------|
| 数值 | **0.96** 🎯 | **1.00** 🥇 | **0.76** 📋 | **0.94** ✅ | **1.00** 💯 | **0.35** 🔍 |
| 评级 | 极佳 | 完美 | 良好 | 高度一致 | 全覆盖 | 适中相关 |

🟢 优秀 (不确定性 < 0.20): 证据充分，结论可靠

🟡 良好 (不确定性 0.20-0.35): 主要结论可信，部分领域可深化

🔴 需改进 (不确定性 ≥ 0.35): 建议增加检索或重新规划

---

## 🔍 Core Innovations

**1.Innovation Tags**:

🔄 `段落级迭代反思` | 🎯 `反思压力模型` | 🧠 `智能体协作` | 📊 `不确定性量化` | ⚡ `智能预算分配` | 🎨 `源质量评分` | 🔍 `去噪重排序`

**2. Agent Types**:

| 序号 | Agent名称 | 核心机理 | 输入 | 输出 |
|-----|---------|--------|------|------|
| 1 | 🧭 结构规划 | 基于查询生成报告骨架，分解为子主题章节 | 用户查询 | 章节列表+关键问题 |
| 2 | 🔎 段落检索 | 通过Tavily多次查询+域名多样性过滤获取高质量来源 | 章节标题+关键问题 | 5-8个来源URL+摘要 |
| 3 | 📝 段落总结 | 信息融合、证据分类，生成结构化初始总结 | 来源内容 | 分层结构总结(600-1200词) |
| 4 | `🪞 反思评估` | 5-dim评估 (视角、证据、偏见、完整性、矛盾性) | 初始总结+来源列表 | 评估报告+改进建议+置信度 |
| 5 | `🛠️ 段落更新` | 根据反思结果进行补充检索和内容融合迭代优化 | 反思评估结果+补充来源 | 更新后的总结 |
| 6 | `🌐 全局不确定性` | 5因子权重模型计算全局不确定性，动态决定是否继续反思 | 所有章节评估指标 | 不确定性评分(0-1)+决策 |
| 7 | 📦 最终格式化 | 整合反思成果成专业Markdown报告(摘要+交叉见解+参考) | 全部优化章节+元数据 | 完整Markdown报告 |
| 8 | 🎛️ 控制编排 | 中央调度器，压力驱动反思循环，决定执行顺序和资源分配 | 用户参数+反思敏感度 | 完整工作流执行 |



---

## 🛠️ Core Technology Stack

`Python` · `asyncio` · `aiohttp` · `pydantic` · `LLM编排` · `Prompt Engineering` · `Tavily API` · `DeepSeek API` · `不确定性量化` · `NDCG/MRR评估` · `Conda` · `Shell自动化`

| 技术领域 | 本项目落地内容 | 实现方法 |
|---|---|---|
| 多智能体系统 | 8个专业化 Agent 协同流水线 | `controller_fast.py` 编止程序调度 + 不同业务特化 Agent 类 |
| 异步工程 | 章节级並发处理与控制重试 | `asyncio` + `aiohttp` + 指数退避策略（`backoff=2^n`） |
| 检索与排序 | 查询变体、源去噪、质量重排 | Tavily 多样本检索 + NDCG/MRR 量化评估 + 域名多样性过滤 |
| 反思决策 | 压力驱动的迭代反思机制 | `reflection_sensitivity` 业会决策模式 + 动态预算分配 |
| 质量度量 | 置信度/不确定性建模 + NDCG/MRR | `GlobalUncertaintyAgent` 5条权重分配公式 + 方差惩罚 |
| 工程交付 | 一键脚本、环境引导、确定性模式 | Conda 环境 + 专案模式（`--deterministic` flag） + JSON 中间产物


## 🧠 Algorithms Innovation

### 1. 反思压力模型 (Reflection Pressure Model)
**机制**: 根据各章节的*不确定性动态调整检索预算*
- 不确定性高(>0.35) → 自动触发额外反思循环
- 不确定性中(0.20-0.35) → 有条件反思
- 不确定性低(<0.20) → 直接进入格式化

### 2. 5因子不确定性量化 (Five-Factor Model)
| 因子 | 权重 | 说明 |
|------|------|------|
| 证据 | 0.30 (±0.02～0.05) | 来源权威性、多样性 |
| 完整 | 0.25 (±0.05～0.1) | 对章节目标覆盖率 |
| 多样 | 0.20 (±0.01～0.03) | 不同视角丰富程度 |
| 一致 | 0.15 (±0.03～0.05) | 跨来源信息一致性 |
| 时效 | 0.10 (±0.05～0.5) | 信息新鲜度 |

### 3. 多样性去噪排序 (Diversity Denoising)
- 域名多样性过滤 (目标0.94+)
- NDCG/MRR相关性评估
- 证据强度标注 [高/中/低]

### 4. 5维度反思评估
- 视角覆盖、证据强度、偏见风险、完整性、矛盾性


> ✅ 2026-03 更新：当前默认入口已切换到 `controller_fast.py`（`main.py` 内部已使用），以下“快速使用”与现有代码保持一致。

## 📦 Quick Start (Recommended)

### 1) 安装依赖

```bash
cd .
conda create -n multiAgents python=3.10 -y
conda activate multiAgents
pip install -r ./requirements.txt
```

### 2) 运行（请用模块方式）

```bash
cd .
python3 -m .main \
  --deepseek_key "<YOUR_DEEPSEEK_KEY>" \
  --tavily_key "<YOUR_TAVILY_KEY>" \
  --query "THINGS-TO-SEARCH" \
  --max_reflection_loops 1 \
  --log_level INFO
```

### 3) 输出位置

- 默认输出目录：`v2_paragraph_reflective/runs/`
- 结果文件：`<task_id>_final.json`

主要字段：
- `task_id`
- `query`
- `timestamp`
- `title`
- `report_markdown`
- `global_uncertainty`
- `sections_count`
- `status`

### 4) 常用参数（与 `main.py` 一致）

- `--deepseek_key`（必填）
- `--tavily_key`（必填）
- `--query`（必填）
- `--results_dir`（默认 `runs`）
- `--max_reflection_loops`（默认 `3`，Fast 模式建议 `1`）
- `--uncertainty_threshold`（默认 `0.2`）
- `--log_level`（`DEBUG|INFO|WARNING|ERROR`）
- `--deterministic`（可选开关）

### 5) 快速校验

```bash
cd .
python3 -m py_compile \
  v2_paragraph_reflective/clients.py \
  v2_paragraph_reflective/agents.py \
  v2_paragraph_reflective/controller_fast.py \
  v2_paragraph_reflective/main.py
```

### 6) 说明

- 本 README 下方历史内容保留用于参考；若与本节冲突，请以本节与代码实现为准。

---
## 🛠️ History

- **Multi-Agent Architecture**: 8 specialized agents for different research tasks
- **Paragraph-level Reflection**: Iterative refinement of each section with up to 3 reflection loops
- **Source Diversity**: Ensures diverse sources across domains
- **Uncertainty Quantification**: Calculates uncertainty scores (0-1 scale)
- **Evaluation Metrics**: NDCG, MRR, source diversity, reflection depth
- **Intermediate Results**: Saves all intermediate outputs for analysis
- **Asynchronous Execution**: Fully async architecture with retry logic
- **Structured Reports**: Comprehensive markdown reports with all required sections

## Architecture

### Agents

1. **StructurePlannerAgent**: Generates report structure with at least 5 sections
2. **SectionRetrieverAgent**: Retrieves 5-8 diverse sources per section using Tavily API
3. **SectionSummarizerAgent**: Creates initial structured summaries from search results
4. **ReflectionAgent**: Evaluates sections for gaps, weak evidence, and bias risks
5. **SectionUpdaterAgent**: Refines sections based on reflection results (max 3 loops)
6. **GlobalUncertaintyAgent**: Calculates overall uncertainty and provides recommendations
7. **FinalFormatterAgent**: Generates comprehensive final report
8. **MARDSController**: Orchestrates all agents in the workflow

### Workflow

```
User Query
    ↓
StructurePlannerAgent: Generate Report Structure (5+ sections)
    ↓
For each Section:
    ├─ SectionRetrieverAgent: Retrieve diverse sources
    ├─ SectionSummarizerAgent: Generate initial summary
    └─ Reflection Loop (Max 3 iterations):
       ├─ ReflectionAgent: Evaluate section
       ├─ If needs_deeper_search:
       │  ├─ Perform additional Tavily search
       │  └─ SectionUpdaterAgent: Update summary
       └─ Check loop counter
    ↓
GlobalUncertaintyAgent: Calculate global uncertainty
    ↓
If uncertainty < 0.2:
    Proceed to Final Formatting
Else:
    Recommend additional reflection
    ↓
FinalFormatterAgent: Generate comprehensive report
    ↓
Output: Markdown report with:
- Title
- Executive Summary
- Section 1-5 (with refined summaries)
- Cross-Section Insights
- Evidence Strength Overview
- Contradictions Resolution
- Knowledge Gaps
- Uncertainty Score
- References
```







### Python API

```python
import asyncio
from controller import MARDSController

async def main():
    controller = MARDSController(
        deepseek_key="sk-xxxxxxxxxxxxxxxx",
        tavily_key="tvly-xxxxxxxxxxxxxxx",
        results_dir="runs",
        max_reflection_loops=3,
        uncertainty_threshold=0.2
    )
    
    result = await controller.run(
        query="什么是量子计算？",
        enable_reflection=True,
        save_intermediate=True
    )
    
    print(result['report_markdown'])
    print(f"Uncertainty: {result['global_uncertainty']:.2%}")

asyncio.run(main())
```

## Output

### Result Structure

```json
{
  "task_id": "uuid",
  "query": "research query",
  "timestamp": "2024-03-01T10:00:00",
  "title": "Report Title",
  "report_markdown": "# Full Report...",
  "global_uncertainty": 0.15,
  "sections_count": 5,
  "total_sources": 40,
  "total_reflections": 8,
  "status": "completed"
}
```

### Report Sections

Each report contains:
- **Executive Summary**: High-level overview
- **Sections 1-5**: Detailed analysis per section
- **Cross-Section Insights**: Patterns and connections
- **Evidence Strength Overview**: Quality assessment
- **Contradictions**: Conflicting information resolution
- **Knowledge Gaps**: Areas needing further research
- **Uncertainty Score**: Overall uncertainty (0-1)
- **References**: Complete source list

## Metrics

### Per-Section Metrics

- **NDCG** (Normalized Discounted Cumulative Gain): Relevance ranking quality (0-1)
- **MRR** (Mean Reciprocal Rank): Quality of top result (0-1)
- **Source Diversity**: Percentage of unique domains (0-1)
- **Reflection Depth**: Number of reflection loops completed (0-1)

### Global Metrics

- **Global Uncertainty**: Overall research uncertainty (0-1)
- **Average Confidence**: Mean confidence across sections (0-1)
- **Reflection Efficiency**: Total reflections vs. sections

## Termination Conditions

### Per Section

- Maximum 3 reflection loops per section
- Stop reflection if no deeper search needed

### Global

- Calculate global uncertainty after all sections
- If `global_uncertainty < 0.2`: Proceed to formatting
- If `global_uncertainty >= 0.2`: Can trigger additional reflection

## Configuration

### Advanced Options

```python
controller = MARDSController(
    deepseek_key="...",
    tavily_key="...",
    results_dir="runs",           # Directory for saving results
    max_reflection_loops=3,       # Max loops per section
    uncertainty_threshold=0.2,    # Threshold for proceeding
    deterministic=True            # For reproducible results
)
```

### Prompt Customization

Prompts are loaded from `prompts/` directory:
- `structure_planner.txt`
- `section_summarizer.txt`
- `reflection.txt`
- `global_uncertainty.txt`

## Error Handling

- **Automatic Retries**: 3 attempts with exponential backoff (2^n seconds)
- **Timeout Handling**: 120s for DeepSeek, 60s for Tavily
- **Error Logging**: Comprehensive logging to file and console
- **Graceful Degradation**: Continues with partial results when possible

## Logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

### Log Levels

- `DEBUG`: Detailed execution flow
- `INFO`: Major steps and decisions
- `WARNING`: Retries, timeouts, partial failures
- `ERROR`: Critical failures

## Examples

### Example 1: Simple Query

```bash
python main.py \
  --deepseek_key "sk-123" \
  --tavily_key "tvly-456" \
  --query "What is blockchain?"
```

### Example 2: Deep Research with Custom Parameters

```bash
python main.py \
  --deepseek_key "sk-123" \
  --tavily_key "tvly-456" \
  --query "Climate change impacts on agriculture" \
  --max_reflection_loops 5 \
  --uncertainty_threshold 0.1 \
  --log_level DEBUG
```

### Example 3: Chinese Language Query

```bash
python main.py \
  --deepseek_key "sk-123" \
  --tavily_key "tvly-456" \
  --query "人工智能在医疗中的应用"
```

## Troubleshooting

### Issue: API Key Errors

```
APIException: DeepSeek API error: 401
```

**Solution**: Check API key validity and format

### Issue: Timeouts

```
APIException: DeepSeek API timeout
```

**Solution**: Check network connectivity, increase timeout (modify clients.py)

### Issue: Invalid JSON Response

```
MARDSException: Invalid JSON response
```

**Solution**: Check prompt format, DeepSeek model compatibility

## Performance Considerations

- **API Calls**: ~40-50 API calls per query (varies with reflection)
- **Execution Time**: 3-10 minutes depending on reflection depth
- **Memory**: ~500MB (includes search results caching)
- **Network**: Requires stable internet connection

## Future Enhancements

- [1] Multi-language support improvement
- [2] Real-time progress streaming
- [3] Web UI integration
- [4] Vector database for semantic search
- [5] Multi-modal research (images, PDFs)
- [6] Collaborative research workflows
- [7] Custom agent extensions

## API Keys

### DeepSeek API

1. Visit https://platform.deepseek.com/
2. Create account and project
3. Generate API key
4. Set budget limits

### Tavily API

1. Visit https://tavily.com/
2. Create account
3. Generate API key
4. Choose search tier

## License

Proprietary - DeepSearch Project

## Support

For issues and feature requests:
- Check logs in `mards.log`
- Review intermediate results in `runs/` directory
- Verify API key configuration

## Version

- **Current**: 2.0.0
- **Release Date**: 2024-03-01
- **Status**: Production Ready
