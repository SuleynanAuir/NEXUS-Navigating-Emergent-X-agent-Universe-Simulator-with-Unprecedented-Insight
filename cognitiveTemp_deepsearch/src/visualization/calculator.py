"""
指标计算模块
计算各种学术性指标
"""

from typing import List, Dict, Any, Optional
from .metrics_model import SearchQualityMetrics
import math


class MetricsCalculator:
    """指标计算器"""

    DEFAULT_RELEVANCE_THRESHOLD = 0.12
    
    @staticmethod
    def calculate_ndcg(relevances: List[float], k: int = 10) -> float:
        """
        计算NDCG (Normalized Discounted Cumulative Gain)
        
        Args:
            relevances: 相关性分数列表 (0-1之间)
            k: 考虑的排名位置
            
        Returns:
            NDCG值 (0-1)
        """
        if not relevances:
            return 0.0
        
        # 计算DCG
        dcg = sum((rel / math.log2(idx + 2)) for idx, rel in enumerate(relevances[:k]))
        
        # 计算IDCG (理想DCG)
        ideal_relevances = sorted(relevances, reverse=True)[:k]
        idcg = sum((rel / math.log2(idx + 2)) for idx, rel in enumerate(ideal_relevances))
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    @staticmethod
    def calculate_mrr(
        relevances: List[float],
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> float:
        """
        计算MRR (Mean Reciprocal Rank)
        
        Args:
            relevances: 相关性分数列表
            threshold: 相关性阈值（默认0.12，基于全量报告分布校准）
            
        Returns:
            MRR值 (0-1)
        """
        for idx, rel in enumerate(relevances, 1):
            if rel >= threshold:
                return 1.0 / idx
        return 0.0
    
    @staticmethod
    def calculate_precision_at_k(
        relevances: List[float],
        k: int = 3,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> float:
        """
        计算P@k (Precision at k)
        
        Args:
            relevances: 相关性分数列表
            k: 考虑的排名位置
            threshold: 相关性阈值（默认0.12）
            
        Returns:
            P@k值 (0-1)
        """
        if k <= 0 or not relevances:
            return 0.0
        
        relevant_count = sum(1 for rel in relevances[:k] if rel >= threshold)
        return relevant_count / k
    
    @staticmethod
    def calculate_map(
        relevances: List[float],
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> float:
        """
        计算MAP (Mean Average Precision)
        
        Args:
            relevances: 相关性分数列表
            threshold: 相关性阈值（默认0.12）
            
        Returns:
            MAP值 (0-1)
        """
        if not relevances:
            return 0.0
        
        precisions = []
        relevant_count = 0
        
        for idx, rel in enumerate(relevances, 1):
            if rel >= threshold:
                relevant_count += 1
                precisions.append(relevant_count / idx)
        
        if not precisions:
            return 0.0
        
        return sum(precisions) / len(precisions)
    
    @staticmethod
    def calculate_bpref(
        relevances: List[float],
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> float:
        """
        计算BPref (Binary Preference)
        用于评估排序质量，不依赖于非相关文档的完整列表
        
        Args:
            relevances: 相关性分数列表
            threshold: 相关性阈值（默认0.12）
            
        Returns:
            BPref值 (0-1)
        """
        if not relevances:
            return 0.0
        
        relevant_count = sum(1 for rel in relevances if rel >= threshold)
        if relevant_count == 0:
            return 0.0
        
        # 对每个相关文档，计算它排在多少非相关文档之前
        score = 0.0
        non_relevant_count = 0
        
        for rel in relevances:
            if rel >= threshold:
                # 相关文档
                score += 1 - (min(relevant_count, non_relevant_count) / relevant_count)
            else:
                # 非相关文档
                non_relevant_count += 1
        
        return score / relevant_count if relevant_count > 0 else 0.0
    
    @staticmethod
    def calculate_dcg(relevances: List[float], k: int = 10) -> float:
        """
        计算DCG (Discounted Cumulative Gain)
        
        Args:
            relevances: 相关性分数列表
            k: 考虑的排名位置
            
        Returns:
            DCG值
        """
        if not relevances:
            return 0.0
        
        return sum((rel / math.log2(idx + 2)) for idx, rel in enumerate(relevances[:k]))
    
    @staticmethod
    def calculate_source_diversity(sources: List[str]) -> float:
        """
        计算来源多样性
        基于不同来源的比例
        
        Args:
            sources: 来源域名列表
            
        Returns:
            多样性评分 (0-1)
        """
        if not sources:
            return 0.0
        
        unique_sources = len(set(sources))
        total_sources = len(sources)
        
        # 使用熵来计算多样性
        if unique_sources <= 1:
            return 0.0
        
        # 计算每个来源的出现频率
        source_counts = {}
        for source in sources:
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Shannon熵
        entropy = 0.0
        for count in source_counts.values():
            p = count / total_sources
            entropy -= p * math.log2(p) if p > 0 else 0
        
        # 标准化到0-1
        max_entropy = math.log2(unique_sources)
        if max_entropy == 0:
            return 0.0
        
        return entropy / max_entropy
    
    @staticmethod
    def calculate_coverage_score(topics_covered: List[str], total_topics: int) -> float:
        """
        计算覆盖率评分
        
        Args:
            topics_covered: 覆盖的主题列表
            total_topics: 总主题数
            
        Returns:
            覆盖率评分 (0-1)
        """
        if total_topics == 0:
            return 0.0
        
        unique_topics = len(set(topics_covered))
        return min(1.0, unique_topics / total_topics)
    
    @staticmethod
    def aggregate_metrics(all_relevances: List[List[float]], 
                         sources: List[str] = None,
                         topics: List[str] = None) -> SearchQualityMetrics:
        """
        聚合计算所有指标
        
        Args:
            all_relevances: 相关性分数的嵌套列表（每次搜索一个列表）
            sources: 来源列表
            topics: 主题列表
            
        Returns:
            SearchQualityMetrics对象
        """
        metrics = SearchQualityMetrics()
        
        # 如果有多次搜索，合并相关性分数
        if all_relevances and isinstance(all_relevances[0], list):
            combined_relevances = []
            for rel_list in all_relevances:
                combined_relevances.extend(rel_list)
        else:
            combined_relevances = all_relevances if all_relevances else []
        
        # 计算各项指标
        metrics.ndcg = MetricsCalculator.calculate_ndcg(combined_relevances)
        metrics.mrr = MetricsCalculator.calculate_mrr(combined_relevances)
        metrics.precision_at_1 = MetricsCalculator.calculate_precision_at_k(
            combined_relevances, k=1
        )
        metrics.precision_at_3 = MetricsCalculator.calculate_precision_at_k(
            combined_relevances, k=3
        )
        metrics.precision_at_5 = MetricsCalculator.calculate_precision_at_k(
            combined_relevances, k=5
        )
        metrics.precision_at_10 = MetricsCalculator.calculate_precision_at_k(
            combined_relevances, k=10
        )
        metrics.map_score = MetricsCalculator.calculate_map(combined_relevances)
        metrics.bpref = MetricsCalculator.calculate_bpref(combined_relevances)
        metrics.dcg = MetricsCalculator.calculate_dcg(combined_relevances)
        metrics.avg_relevance = (
            sum(combined_relevances) / len(combined_relevances) 
            if combined_relevances else 0.0
        )
        
        # 来源多样性
        if sources:
            metrics.unique_sources = len(set(sources))
            metrics.source_diversity = MetricsCalculator.calculate_source_diversity(sources)
        
        # 覆盖率
        if topics:
            metrics.coverage_score = MetricsCalculator.calculate_coverage_score(
                topics, len(set(topics))
            )
        
        metrics.total_searches = len(all_relevances) if isinstance(all_relevances[0] if all_relevances else [], list) else 1
        
        return metrics
