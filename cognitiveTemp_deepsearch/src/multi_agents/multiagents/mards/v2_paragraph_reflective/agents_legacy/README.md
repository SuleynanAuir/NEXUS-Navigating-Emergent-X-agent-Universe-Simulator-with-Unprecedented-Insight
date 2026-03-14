# Original MARDS Agents - Reference Implementation

此目录包含从 `mards/agents/` 移植过来的原始agents实现，作为参考和代码复用库。

## 文件结构

```
agents/
├── __init__.py          # 导出所有agents
├── planner.py           # 问题分解agent
├── retriever.py         # 检索与多样性agent
├── evaluator.py         # 证据评估agent
├── debate.py            # 多视角辩论agent
├── reflection.py        # 全局反思agent
├── uncertainty.py       # 不确定性量化agent
└── synthesis.py         # 报告综合agent
```

## Agents说明

### 1. PlannerAgent (planner.py)
**原始功能**: 问题分解为3-5个子问题
**集成状态**: ✅ 已集成到 `../agents.py` 的 `StructurePlannerAgent`
**核心逻辑**:
- `local_decompose()`: 按"and/；/、"分割或生成默认问题
- 已在v2中增强为生成5+章节结构

### 2. RetrieverAgent (retriever.py)
**原始功能**: 检索结果多样性过滤和来源分类
**集成状态**: ✅ 已集成到 `../agents.py` 的 `SectionRetrieverAgent`
**核心逻辑**:
- `enforce_domain_diversity()`: 域名多样性过滤
- `diversity_score()`: TLD + source_type 综合评分
- `classify_source_type()`: academic/government/news/nonprofit/corporate分类

### 3. EvidenceEvaluatorAgent (evaluator.py)
**原始功能**: 从检索结果中提取声明和检测矛盾
**集成状态**: ✅ 已集成到 `../agents.py` 的 `FinalFormatterAgent`
**核心逻辑**:
- `extract_claims()`: 提取实质性句子作为声明
- `detect_contradictions()`: 检测包含否定词的矛盾
- `calculate_average_confidence()`: 计算平均置信度

### 4. DebateAgent (debate.py)
**原始功能**: 多视角辩论解决矛盾
**集成状态**: ⚠️ 暂未集成（v2暂不需要显式辩论阶段）
**核心逻辑**:
- `generate_fallback_resolution()`: 生成折中结论
- `extract_remaining_disagreements()`: 提取未解决分歧

### 5. OriginalReflectionAgent (reflection.py)
**原始功能**: 全局反思和迭代决策
**集成状态**: ⚠️ 部分逻辑保留，v2使用不同的章节级反思
**核心逻辑**:
- `identify_missing_topics()`: 识别未覆盖主题
- `should_iterate()`: 判断是否需要再次迭代
**v2差异**: v2的ReflectionAgent专注于单个章节的反思，而非全局决策

### 6. UncertaintyAgent (uncertainty.py)
**原始功能**: 全局不确定性量化
**集成状态**: ✅ 已集成到 `../agents.py` 的 `GlobalUncertaintyAgent`
**核心逻辑**:
- `calculate_conflict_rate()`: 矛盾率 = 矛盾数 / 总声明数
- `calculate_info_gap_score()`: 信息缺口 = 缺失主题数 / 子问题数
- `calculate_avg_unreliability()`: 平均不可靠性 = 1 - 平均置信度
- `calculate_global_uncertainty()`: 0.4*conflict + 0.3*gap + 0.3*unreliability

### 7. SynthesisAgent (synthesis.py)
**原始功能**: 生成结构化markdown报告
**集成状态**: ✅ 已集成到 `../agents.py` 的 `FinalFormatterAgent`
**核心逻辑**:
- `generate_markdown_report()`: 生成完整报告模板
- 包含: Executive Summary / Structured Findings / Evidence Strength
- Contradictions / Knowledge Gaps / Uncertainty Score

## 集成映射表

| 原始Agent | v2对应Agent | 集成方法 | 状态 |
|----------|------------|---------|------|
| PlannerAgent | StructurePlannerAgent | `_local_decompose()` | ✅ 完成 |
| RetrieverAgent | SectionRetrieverAgent | `_filter_for_diversity()`, `_classify_source_type()` | ✅ 完成 |
| EvidenceEvaluatorAgent | FinalFormatterAgent | `_extract_all_claims()`, `_detect_contradictions()` | ✅ 完成 |
| DebateAgent | - | 暂不需要 | ⏸️ 待定 |
| ReflectionAgent | ReflectionAgent (不同功能) | 逻辑保留但用途不同 | ⚠️ 部分 |
| UncertaintyAgent | GlobalUncertaintyAgent | conflict/gap/unreliability计算 | ✅ 完成 |
| SynthesisAgent | FinalFormatterAgent | 报告模板 | ✅ 完成 |

## 使用方式

### 作为参考库
```python
from v2_paragraph_reflective.agents import (
    PlannerAgent,
    RetrieverAgent,
    EvidenceEvaluatorAgent,
    UncertaintyAgent,
    SynthesisAgent
)

# 使用原始逻辑
planner = PlannerAgent()
sub_questions = planner.local_decompose("什么是量子计算")

# 或直接调用静态方法
diversity_score = RetrieverAgent.diversity_score(search_results)
```

### 在v2 agents中调用
v2的agents已经内置了这些逻辑，无需显式导入：
```python
# 在 v2_paragraph_reflective/agents.py 中
class StructurePlannerAgent(BaseAgent):
    def _local_decompose(self, query: str):
        # 使用原始PlannerAgent的逻辑
        parts = re.split(r"\band\b|；|;|、", query)
        ...
```

## 代码维护

- ✅ **已完成**: 核心逻辑已提取为静态方法或工具函数
- ⚙️ **进行中**: 测试v2集成效果
- 📋 **待办**: 考虑是否需要DebateAgent功能

## 相关文档

- `../INTEGRATION_GUIDE.md`: 详细的整合指南
- `../agents.py`: v2 agents实现（包含集成后的逻辑）
- `../../agents/`: 原始agents目录（保持不变作为备份）
