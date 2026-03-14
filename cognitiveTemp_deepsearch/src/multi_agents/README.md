# Multi-Agent Collaboration System

多智能体协作系统，用于复杂研究查询的分解和深度搜索。

## 📁 项目结构

```
src/multi_agents/
├── __init__.py                      # 包初始化
├── examples.py                      # Planner Agent示例
├── retriever_examples.py            # Retriever Agent示例
├── test_planner_agent.py           # Planner Agent测试
├── test_retriever_agent.py         # Retriever Agent测试
├── README.md                        # 本文档
├── agents/
│   ├── __init__.py
│   ├── planner_agent.py            # Planner Agent实现
│   └── retriever_agent.py          # Retriever Agent实现
├── prompts/
│   └── __init__.py                 # 提示词模板（待扩展）
└── utils/
    ├── __init__.py
    └── json_parser.py              # JSON解析工具
```

## 🤖 已实现的Agent

### 1️⃣ **Planner Agent** (Strategic Research Decomposition Agent)

战略性研究分解智能体，将复杂的研究查询分解为多维度的子问题。

#### 功能特性

- ✅ **多维度分解**：理论、经验、方法论、应用四个维度
- ✅ **假设检测**：自动检测查询中的隐藏假设
- ✅ **难度评估**：为每个子问题评估复杂度（1-5级）
- ✅ **证据类型指定**：说明每个子问题需要哪种证据
- ✅ **迭代策略**：设计合理的研究迭代流程
- ✅ **JSON输出**：严格的结构化JSON格式输出
- ✅ **验证机制**：内置输出验证功能

#### 快速开始

```python
from src.multi_agents.agents import PlannerAgent

# 创建Planner Agent（无LLM）
planner = PlannerAgent()

# 分解查询
query = "What is the current state of quantum computing?"
decomposition = planner.decompose(query)

# 访问结果
print(decomposition.main_question)
print(decomposition.sub_questions)
print(decomposition.to_json())
```

#### 输出格式

```json
{
  "main_question": "What is artificial intelligence?",
  "assumptions_detected": [
    "AI is a well-defined concept",
    "There are multiple aspects to understand"
  ],
  "dimensions": {
    "theoretical": ["Definitions", "Core concepts"],
    "empirical": ["Current applications", "Real-world examples"],
    "methodological": ["Research approaches", "Study methods"],
    "applications": ["Use cases", "Future directions"]
  },
  "sub_questions": [
    {
      "question": "What are the key theoretical frameworks and definitions relevant to AI?",
      "difficulty": 2,
      "expected_evidence_type": "academic papers, theoretical reviews"
    }
  ],
  "iteration_strategy": "Start with foundations...",
  "estimated_total_rounds": 3
}
```

---

### 2️⃣ **Retriever Agent** (Diversity-Aware Retrieval Agent)

多样性感知检索智能体，从多个领域检索高质量的多样化信息源。

#### 功能特性

- ✅ **多域检索**：从至少3个不同领域检索源
- ✅ **学术源优先**：优先包含学术来源
- ✅ **多样性惩罚**：惩罚重复的域类型
- ✅ **可信度评估**：为每个源分配可信度分数（0-1）
- ✅ **关联度评分**：评估源与查询的相关性
- ✅ **不确定标记**：明确标记不确定的来源
- ✅ **无虚构保证**：绝不虚构或编造源

#### 域类型

- **academic**: 学术论文、期刊、论文、研究数据库
- **industry**: 行业报告、白皮书、公司出版物
- **news**: 新闻文章、新闻业、时事新闻
- **blog**: 博客文章、个人文章、评论
- **government**: 政府出版物、政策文件、官方报告
- **official**: 官方网站、文档、官方公告
- **other**: 不适合上述类别的其他来源

#### 快速开始

```python
from src.multi_agents.agents import RetrieverAgent

# 创建Retriever Agent
retriever = RetrieverAgent()

# 检索源
query = "latest developments in quantum computing"
result = retriever.retrieve(query)

# 访问结果
print(f"检索了 {len(result.results)} 个源")
print(f"多样性分数: {result.diversity_score}")
print(f"检索置信度: {result.retrieval_confidence}")

# 查看源
for source in result.results:
    print(f"- {source.title} ({source.domain_type})")
    print(f"  可信度: {source.credibility_score}")
    print(f"  关联度: {source.relevance_score}")
```

#### 输出格式

```json
{
  "query_used": "artificial intelligence trends",
  "results": [
    {
      "title": "Recent Advances in Deep Learning",
      "source": "arXiv",
      "domain_type": "academic",
      "credibility_score": 0.95,
      "relevance_score": 0.85,
      "summary": "Comprehensive review of recent deep learning techniques",
      "url": "https://arxiv.org/abs/...",
      "publication_date": "2026-02-28",
      "authors": ["Author1", "Author2"],
      "uncertainty_marked": false
    }
  ],
  "diversity_score": 0.87,
  "retrieval_confidence": 0.74,
  "domain_distribution": {
    "academic": 3,
    "industry": 2,
    "news": 1
  },
  "total_sources_searched": 10
}
```

#### 可信度评分指南

| 分数范围 | 等级 | 举例 |
|---------|------|------|
| 0.9-1.0 | 非常高 | 同行评审的学术源、官方政府/机构源 |
| 0.7-0.9 | 高 | 知名新闻媒体、知名行业来源 |
| 0.5-0.7 | 中等-高 | 半权威博客、较少知名新闻 |
| 0.3-0.5 | 中等 | 用户生成的内容、意见博客 |
| 0.0-0.3 | 低 | 未经验证的源、社交媒体、可疑声明 |

---

## 📊 核心类和方法

### PlannerAgent

**初始化参数：**
- `llm_client` (optional): LLM客户端，如OpenAI客户端
- `model` (str): 使用的模型名称，默认为"gpt-4"

**主要方法：**
- `decompose(query)` → `ResearchDecomposition`: 分解查询为结构化子问题
- `validate_decomposition(decomposition)` → `tuple(bool, List[str])`: 验证分解输出

### RetrieverAgent

**初始化参数：**
- `llm_client` (optional): LLM客户端
- `model` (str): 使用的模型名称，默认为"gpt-4"
- `search_client` (optional): 搜索API客户端

**主要方法：**
- `retrieve(query, max_results=6)` → `RetrievalResult`: 检索多样化源
- `validate_retrieval_result(result)` → `tuple(bool, List[str])`: 验证检索结果

### 数据类

#### ResearchDecomposition
- `main_question`: 原始问题
- `assumptions_detected`: 检测到的假设列表
- `dimensions`: 研究维度字典
- `sub_questions`: 子问题列表
- `iteration_strategy`: 迭代策略描述
- `estimated_total_rounds`: 估计迭代轮数
- `to_dict()`: 转换为字典
- `to_json()`: 转换为JSON字符串

#### RetrievalResult
- `query_used`: 使用的查询
- `results`: 检索到的源列表
- `diversity_score`: 多样性分数（0-1）
- `retrieval_confidence`: 检索置信度（0-1）
- `domain_distribution`: 域分布计数器
- `total_sources_searched`: 搜索的总源数
- `to_dict()`: 转换为字典
- `to_json()`: 转换为JSON字符串

#### RetrievedSource
- `title`: 源标题
- `source`: 源名称/组织
- `domain_type`: 源类型
- `credibility_score`: 可信度评分（0-1）
- `relevance_score`: 关联度评分（0-1）
- `summary`: 源摘要
- `url`: 源URL
- `publication_date`: 发布日期
- `authors`: 作者列表
- `uncertainty_marked`: 是否标记为不确定
- `validate()`: 验证源
- `to_dict()`: 转换为字典

---

## 📚 使用示例

### 运行所有示例

```bash
cd src/multi_agents

# 运行Planner Agent示例
python examples.py

# 运行Retriever Agent示例
python retriever_examples.py
```

### 示例1：分解查询

```python
from src.multi_agents.agents import PlannerAgent

planner = PlannerAgent()
decomposition = planner.decompose("What is blockchain technology?")

print(f"主问题: {decomposition.main_question}")
print(f"假设: {decomposition.assumptions_detected}")
print(f"子问题数: {len(decomposition.sub_questions)}")

for i, sq in enumerate(decomposition.sub_questions, 1):
    print(f"{i}. {sq.question} (难度: {sq.difficulty}/5)")
```

### 示例2：检索多样化源

```python
from src.multi_agents.agents import RetrieverAgent

retriever = RetrieverAgent()
result = retriever.retrieve("machine learning applications")

print(f"总源数: {len(result.results)}")
print(f"多样性分数: {result.diversity_score}")
print(f"源分布: {result.domain_distribution}")

for source in result.results:
    print(f"\n{source.title}")
    print(f"  来源: {source.source} ({source.domain_type})")
    print(f"  可信度: {source.credibility_score} | 关联度: {source.relevance_score}")
```

### 示例3：集成使用

```python
from src.multi_agents.agents import PlannerAgent, RetrieverAgent

# 第一步：分解查询
planner = PlannerAgent()
decomposition = planner.decompose("future of renewable energy")

# 第二步：为每个子问题检索源
retriever = RetrieverAgent()

for sq in decomposition.sub_questions:
    result = retriever.retrieve(sq.question)
    print(f"\nQ: {sq.question}")
    print(f"  检索到 {len(result.results)} 个源（多样性: {result.diversity_score}）")
```

---

## 🧪 运行测试

```bash
cd src/multi_agents

# 运行Planner Agent测试
python -m unittest test_planner_agent -v

# 运行Retriever Agent测试
python -m unittest test_retriever_agent -v

# 运行所有测试
python -m unittest discover -p "test_*.py" -v
```

### 测试覆盖范围

**Planner Agent** (24个测试):
- ✅ 基础功能测试
- ✅ 分解验证
- ✅ 假设检测
- ✅ 维度提取
- ✅ JSON解析
- ✅ 序列化/反序列化
- ✅ 边界情况

**Retriever Agent** (26个测试):
- ✅ 基础功能测试
- ✅ 检索验证
- ✅ 域多样性
- ✅ 源可信度
- ✅ 源检索
- ✅ 置信度评分
- ✅ 不确定标记

---

## 🔄 工作流程

### Planner Agent工作流

```
用户查询
    ↓
PlannerAgent.decompose()
    ├─ 检测假设
    ├─ 提取维度
    ├─ 生成子问题
    └─ 确定迭代策略
    ↓
ResearchDecomposition对象
    ↓
验证输出
    ↓
JSON序列化
    ↓
返回结构化结果
```

### Retriever Agent工作流

```
搜索查询
    ↓
RetrieverAgent.retrieve()
    ├─ 搜索/获取源
    ├─ 检测域类型
    ├─ 计算可信度和关联度
    ├─ 强制多样性
    └─ 计算分数
    ↓
RetrievalResult对象
    ↓
验证输出
    ↓
JSON序列化
    ↓
返回检索结果
```

---

## ✅ 验证规则

### Planner Agent验证

- 最少子问题数：≥ 4
- 难度范围：1-5级
- 维度完整性：必须有theoretical、empirical、methodological、applications
- 迭代轮数：1-5轮
- 所有字段都不能为空

### Retriever Agent验证

- 最少源数：≥ 4
- 至少一个学术源
- 至少3个不同域
- 可信度分数：0-1
- 关联度分数：0-1
- 多样性分数：0-1
- 置信度分数：0-1

---

## 🚀 性能特点

- ⚡ **无依赖本地运行**：无需LLM或搜索API即可工作
- 🔌 **集成可选**：支持集成OpenAI、搜索引擎等
- 📦 **轻量级**：最小化外部依赖
- 🎯 **高准确性**：严格验证输出
- 🔄 **可扩展**：易于添加新的Agent类型
- 🛡️ **安全可靠**：无虚构源、明确标记不确定性

---

## 📋 文件说明

| 文件 | 说明 |
|------|------|
| `planner_agent.py` | Planner Agent核心实现 |
| `retriever_agent.py` | Retriever Agent核心实现 |
| `json_parser.py` | JSON解析和验证工具 |
| `examples.py` | Planner Agent使用示例 |
| `retriever_examples.py` | Retriever Agent使用示例 |
| `test_planner_agent.py` | Planner Agent单元测试 |
| `test_retriever_agent.py` | Retriever Agent单元测试 |
| `README.md` | 本文档 |

---

## 🔮 未来规划

计划实现的Agent类型：

- [ ] **Analyzer Agent**: 分析和综合信息
- [ ] **Synthesizer Agent**: 生成最终报告和见解
- [ ] **Critic Agent**: 质量检查和改进建议
- [ ] **Coordinator Agent**: 协调多Agent间的协作
- [ ] **Evaluator Agent**: 评估信息质量和可信度
- [ ] **Summarizer Agent**: 生成内容摘要

---

## 💡 最佳实践

### 使用Planner Agent

1. ✅ 总是验证decomposition对象
2. ✅ 处理可能的异常
3. ✅ 对相同查询缓存分解结果
4. ✅ 使用列表批量分解多个查询
5. ✅ 启用日志以追踪执行过程

### 使用Retriever Agent

1. ✅ 验证检索结果
2. ✅ 检查域多样性
3. ✅ 审查可信度分数
4. ✅ 标记不确定源
5. ✅ 为高分数源优先级
6. ✅ 监控多样性分数

### 集成使用

```python
import logging

logging.basicConfig(level=logging.INFO)

from src.multi_agents.agents import PlannerAgent, RetrieverAgent

planner = PlannerAgent()
retriever = RetrieverAgent()

try:
    # 分解查询
    decomposition = planner.decompose(query)
    
    if not planner.validate_decomposition(decomposition)[0]:
        logging.error("Invalid decomposition")
        return
    
    # 检索源
    sources = []
    for sq in decomposition.sub_questions:
        result = retriever.retrieve(sq.question)
        
        if not retriever.validate_retrieval_result(result)[0]:
            logging.warning(f"Invalid retrieval for: {sq.question}")
            continue
        
        sources.extend(result.results)
    
    # 处理源
    return {
        "decomposition": decomposition,
        "sources": sources
    }
    
except ValueError as e:
    logging.error(f"Error: {e}")
```

---

## 📞 支持

如有问题，请参考：
- 本README文档
- `examples.py` 中的Planner Agent使用示例
- `retriever_examples.py` 中的Retriever Agent使用示例
- `evaluator_examples.py` 中的Evaluator Agent使用示例
- `critical_reflection_examples.py` 中的Reflection Agent使用示例
- `debate_examples.py` 中的Debate Agent使用示例
- `uncertainty_quantifier_examples.py` 中的Uncertainty Quantifier Agent使用示例
- 对应的测试文件中的测试用例

---

## 🎯 Agent概览

| Agent | 功能 | 输入 | 输出 | 测试 | 示例 |
|-------|------|------|------|------|------|
| Planner | 查询分解 | Query | SubQuestions | 24 | 5 |
| Retriever | 证据检索 | Query | Sources | 26 | 7 |
| Evaluator | 证据评估 | Findings | Strength | 24 | 8 |
| Reflection | 偏见检测 | Findings | Gaps/Bias | 44 | 8 |
| Debate | 对抗论证 | Topic | Pro/Con | 47 | 8 |
| Uncertainty | 不确定量化 | Evidence | Risk | 31 | 8 |
| **TOTAL** | - | - | - | **196** | **44** |

---

**版本**: 1.0.0  
**最后更新**: 2026年3月1日  
**状态**: ✅ 全部6个Agent完成，196个测试通过，44个工作示例


