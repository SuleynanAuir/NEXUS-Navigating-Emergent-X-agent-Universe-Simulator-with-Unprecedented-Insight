# MARDS v2: Paragraph-level Iterative Reflective Deep Search Framework

A comprehensive multi-agent system for conducting deep, reflective research with structured section-wise processing, iterative reflection loops, and uncertainty quantification.

> ✅ 2026-03 更新：当前默认入口已切换到 `controller_fast.py`（`main.py` 内部已使用），以下“快速使用”与现有代码保持一致。

## 快速使用（当前推荐）

### 1) 安装依赖

```bash
cd /Users/suleynan_suir/Desktop/AIGC/project/option1-舆情分析/DeepSearch/DeepSearchAgent/src/multi_agents/multiagents/mards
pip install -r v2_paragraph_reflective/requirements.txt
```

### 2) 运行（请用模块方式）

```bash
cd /Users/suleynan_suir/Desktop/AIGC/project/option1-舆情分析/DeepSearch/DeepSearchAgent/src/multi_agents/multiagents/mards
python3 -m v2_paragraph_reflective.main \
  --deepseek_key "<YOUR_DEEPSEEK_KEY>" \
  --tavily_key "<YOUR_TAVILY_KEY>" \
  --query "人工智能伦理" \
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
cd /Users/suleynan_suir/Desktop/AIGC/project/option1-舆情分析/DeepSearch/DeepSearchAgent/src/multi_agents/multiagents/mards
python3 -m py_compile \
  v2_paragraph_reflective/clients.py \
  v2_paragraph_reflective/agents.py \
  v2_paragraph_reflective/controller_fast.py \
  v2_paragraph_reflective/main.py
```

### 6) 说明

- 本 README 下方历史内容保留用于参考；若与本节冲突，请以本节与代码实现为准。

## Features

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

## Installation

### Requirements

- Python 3.10+
- asyncio (built-in)
- aiohttp (for async HTTP)
- pydantic (for type validation)

### Setup

```bash
# Install dependencies
pip install aiohttp pydantic

# Clone repository
cd mards/v2_paragraph_reflective

# Set API keys
export DEEPSEEK_API_KEY="your-deepseek-key"
export TAVILY_API_KEY="your-tavily-key"
```

## Usage

### Command Line

```bash
python main.py \
  --deepseek_key "sk-xxxxxxxxxxxxxxxx" \
  --tavily_key "tvly-xxxxxxxxxxxxxxx" \
  --query "什么是量子计算？"

# Optional parameters
python main.py \
  --deepseek_key "sk-xxxxxxxxxxxxxxxx" \
  --tavily_key "tvly-xxxxxxxxxxxxxxx" \
  --query "气候变化的影响" \
  --max_reflection_loops 5 \
  --uncertainty_threshold 0.15 \
  --results_dir "./research_results" \
  --log_level DEBUG
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

- [ ] Multi-language support improvement
- [ ] Real-time progress streaming
- [ ] Web UI integration
- [ ] Vector database for semantic search
- [ ] Multi-modal research (images, PDFs)
- [ ] Collaborative research workflows
- [ ] Custom agent extensions

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
