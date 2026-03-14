"""
研究指标数据模型
定义所有指标的数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


@dataclass
class TimeMetrics:
    """时间消耗指标"""
    total_time: float = 0.0  # 总耗费时间（秒）
    structure_generation_time: float = 0.0  # 报告结构生成时间
    search_time: float = 0.0  # 搜索总耗费时间
    summary_time: float = 0.0  # 总结耗费时间
    reflection_time: float = 0.0  # 反思耗费时间
    report_generation_time: float = 0.0  # 最终报告生成时间
    
    # 按段落的时间消耗
    paragraph_times: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_time": round(self.total_time, 2),
            "structure_generation_time": round(self.structure_generation_time, 2),
            "search_time": round(self.search_time, 2),
            "summary_time": round(self.summary_time, 2),
            "reflection_time": round(self.reflection_time, 2),
            "report_generation_time": round(self.report_generation_time, 2),
            "paragraph_times": {k: round(v, 2) for k, v in self.paragraph_times.items()}
        }


@dataclass
class TokenMetrics:
    """Token消耗指标"""
    total_tokens: int = 0  # 总token数
    total_cost_usd: float = 0.0  # 总成本（美元）
    total_cost_rmb: float = 0.0  # 总成本（人民币）
    
    # 按模型统计
    deepseek_tokens: int = 0
    deepseek_cost_usd: float = 0.0
    openai_tokens: int = 0
    openai_cost_usd: float = 0.0
    
    # 按操作统计
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    exchange_rate: float = 7.0  # USD to RMB
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_cost_rmb": round(self.total_cost_rmb, 2),
            "deepseek_tokens": self.deepseek_tokens,
            "deepseek_cost_usd": round(self.deepseek_cost_usd, 4),
            "openai_tokens": self.openai_tokens,
            "openai_cost_usd": round(self.openai_cost_usd, 4),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens
        }


@dataclass
class SearchQualityMetrics:
    """搜索质量详细指标"""
    # 基础指标
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    mrr: float = 0.0  # Mean Reciprocal Rank
    
    # Precision指标
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    
    # 其他指标
    map_score: float = 0.0  # Mean Average Precision
    bpref: float = 0.0  # Binary Preference
    dcg: float = 0.0  # Discounted Cumulative Gain
    avg_relevance: float = 0.0  # 平均相关性
    
    # 来源多样性
    unique_sources: int = 0  # 唯一来源数量
    source_diversity: float = 0.0  # 来源多样性评分（0-1）
    
    # 覆盖率
    coverage_score: float = 0.0  # 覆盖率评分（主题覆盖范围）
    
    total_searches: int = 0  # 总搜索次数
    relevance_threshold: float = 0.12  # 本次实际使用的相关性阈值
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ndcg": round(self.ndcg, 4),
            "mrr": round(self.mrr, 4),
            "precision_at_1": round(self.precision_at_1, 4),
            "precision_at_3": round(self.precision_at_3, 4),
            "precision_at_5": round(self.precision_at_5, 4),
            "precision_at_10": round(self.precision_at_10, 4),
            "map_score": round(self.map_score, 4),
            "bpref": round(self.bpref, 4),
            "dcg": round(self.dcg, 4),
            "avg_relevance": round(self.avg_relevance, 4),
            "unique_sources": self.unique_sources,
            "source_diversity": round(self.source_diversity, 4),
            "coverage_score": round(self.coverage_score, 4),
            "total_searches": self.total_searches,
            "relevance_threshold": round(self.relevance_threshold, 4)
        }


@dataclass
class ResearchMetrics:
    """综合研究指标"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    query: str = ""
    
    # 基础统计
    total_sections: int = 0
    total_sources: int = 0
    total_reflections: int = 0
    
    # 详细指标
    time_metrics: TimeMetrics = field(default_factory=TimeMetrics)
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    search_quality: SearchQualityMetrics = field(default_factory=SearchQualityMetrics)
    
    # 整体评分
    overall_score: float = 0.0  # 综合评分（0-100）
    
    def calculate_overall_score(self) -> float:
        """计算综合评分"""
        weights = {
            "quality": 0.4,  # 搜索质量权重
            "efficiency": 0.3,  # 效率权重
            "coverage": 0.3  # 覆盖率权重
        }
        
        # 质量得分
        quality_score = (
            self.search_quality.ndcg * 100 +
            self.search_quality.avg_relevance * 100 +
            self.search_quality.source_diversity * 100
        ) / 3
        
        # 效率得分（反向，时间越短越好）
        max_time = 300  # 5分钟
        efficiency_score = max(0, 100 - (self.time_metrics.total_time / max_time) * 100)
        
        # 覆盖率得分
        coverage_score = self.search_quality.coverage_score * 100
        
        self.overall_score = (
            quality_score * weights["quality"] +
            efficiency_score * weights["efficiency"] +
            coverage_score * weights["coverage"]
        )
        
        return self.overall_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "query": self.query,
            "total_sections": self.total_sections,
            "total_sources": self.total_sources,
            "total_reflections": self.total_reflections,
            "time_metrics": self.time_metrics.to_dict(),
            "token_metrics": self.token_metrics.to_dict(),
            "search_quality": self.search_quality.to_dict(),
            "overall_score": round(self.overall_score, 2)
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class MetricsCollector:
    """指标收集器"""
    metrics: ResearchMetrics = field(default_factory=ResearchMetrics)
    
    # 时间记录点
    timing_records: Dict[str, float] = field(default_factory=dict)
    
    def start_timer(self, phase_name: str):
        """开始计时"""
        self.timing_records[f"{phase_name}_start"] = datetime.now().timestamp()
    
    def end_timer(self, phase_name: str) -> float:
        """结束计时并返回耗费时间"""
        start_key = f"{phase_name}_start"
        if start_key not in self.timing_records:
            return 0.0
        
        elapsed = datetime.now().timestamp() - self.timing_records[start_key]
        self.timing_records[f"{phase_name}_end"] = datetime.now().timestamp()
        self.timing_records[f"{phase_name}_elapsed"] = elapsed
        
        # 更新TimeMetrics中对应的字段
        if phase_name == "report_structure":
            self.metrics.time_metrics.structure_generation_time = elapsed
        elif phase_name == "search":
            self.metrics.time_metrics.search_time += elapsed
        elif phase_name == "summary":
            self.metrics.time_metrics.summary_time += elapsed
        elif phase_name == "reflection":
            self.metrics.time_metrics.reflection_time += elapsed
        elif phase_name == "report_generation":
            self.metrics.time_metrics.report_generation_time = elapsed
        
        return elapsed
    
    def add_token_usage(self, model: str, prompt_tokens: int, completion_tokens: int, 
                       cost_usd: float = 0.0):
        """添加token使用量"""
        total = prompt_tokens + completion_tokens
        self.metrics.token_metrics.total_tokens += total
        self.metrics.token_metrics.prompt_tokens += prompt_tokens
        self.metrics.token_metrics.completion_tokens += completion_tokens
        self.metrics.token_metrics.total_cost_usd += cost_usd
        self.metrics.token_metrics.total_cost_rmb = (
            self.metrics.token_metrics.total_cost_usd * 
            self.metrics.token_metrics.exchange_rate
        )
        
        if model.lower() == "deepseek":
            self.metrics.token_metrics.deepseek_tokens += total
            self.metrics.token_metrics.deepseek_cost_usd += cost_usd
        elif model.lower() == "openai":
            self.metrics.token_metrics.openai_tokens += total
            self.metrics.token_metrics.openai_cost_usd += cost_usd
    
    def add_search_metrics(self, quality_dict: Dict[str, Any]):
        """批量添加搜索质量指标"""
        if not quality_dict:
            return
        
        for key, value in quality_dict.items():
            if hasattr(self.metrics.search_quality, key):
                setattr(self.metrics.search_quality, key, value)
    
    def add_search_result(self, result_dict: Dict[str, Any]):
        """添加单个搜索结果（用于统计来源等）"""
        if not result_dict:
            return
        
        # 统计唯一来源
        source = result_dict.get("source", "")
        if source:
            if not hasattr(self, '_unique_sources'):
                self._unique_sources = set()
            self._unique_sources.add(source)
            self.metrics.search_quality.unique_sources = len(self._unique_sources)
    
    def finalize(self):
        """完成指标收集并计算综合评分"""
        # 计算总时间
        total_time = 0
        for key, value in self.timing_records.items():
            if key.endswith("_elapsed"):
                total_time += value
        self.metrics.time_metrics.total_time = total_time
        
        # 计算综合评分
        self.metrics.calculate_overall_score()
