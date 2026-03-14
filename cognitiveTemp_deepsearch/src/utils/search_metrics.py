"""
搜索结果质量评估指标
实现学术标准的检索质量评估方法
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SearchMetrics:
    """搜索评估指标结果"""
    ndcg: float  # 归一化折损累积增益
    precision_at_k: Dict[int, float]  # Precision@K (K=1,3,5,10)
    mrr: float  # 平均倒数排名
    dcg: float  # 折损累积增益
    relevance_score: float  # 平均相关性分数
    total_results: int  # 结果总数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "ndcg": round(self.ndcg, 4),
            "precision_at_k": {k: round(v, 4) for k, v in self.precision_at_k.items()},
            "mrr": round(self.mrr, 4),
            "dcg": round(self.dcg, 4),
            "relevance_score": round(self.relevance_score, 4),
            "total_results": self.total_results
        }
    
    def __str__(self) -> str:
        """格式化输出"""
        return (
            f"Search Quality Metrics:\n"
            f"  NDCG: {self.ndcg:.4f}\n"
            f"  MRR: {self.mrr:.4f}\n"
            f"  Precision@1: {self.precision_at_k.get(1, 0):.4f}\n"
            f"  Precision@3: {self.precision_at_k.get(3, 0):.4f}\n"
            f"  Precision@5: {self.precision_at_k.get(5, 0):.4f}\n"
            f"  Avg Relevance: {self.relevance_score:.4f}\n"
            f"  Total Results: {self.total_results}"
        )


class SearchQualityEvaluator:
    """搜索质量评估器"""
    
    def __init__(self, relevance_threshold: float = 0.5):
        """
        初始化评估器
        
        Args:
            relevance_threshold: 相关性阈值，高于此值认为是相关结果
        """
        self.relevance_threshold = relevance_threshold
    
    def evaluate(
        self,
        results: List[Dict[str, Any]],
        score_key: str = "score",
        k_values: List[int] = [1, 3, 5, 10]
    ) -> SearchMetrics:
        """
        评估搜索结果质量
        
        Args:
            results: 搜索结果列表，每个结果包含score字段
            score_key: 分数字段名
            k_values: 计算Precision@K的K值列表
            
        Returns:
            SearchMetrics: 评估指标结果
        """
        if not results:
            return SearchMetrics(
                ndcg=0.0,
                precision_at_k={k: 0.0 for k in k_values},
                mrr=0.0,
                dcg=0.0,
                relevance_score=0.0,
                total_results=0
            )
        
        # 提取相关性分数
        scores = [r.get(score_key, 0.0) for r in results]
        
        # 计算各项指标
        ndcg = self._calculate_ndcg(scores)
        precision_at_k = self._calculate_precision_at_k(scores, k_values)
        mrr = self._calculate_mrr(scores)
        dcg = self._calculate_dcg(scores)
        avg_relevance = sum(scores) / len(scores) if scores else 0.0
        
        return SearchMetrics(
            ndcg=ndcg,
            precision_at_k=precision_at_k,
            mrr=mrr,
            dcg=dcg,
            relevance_score=avg_relevance,
            total_results=len(results)
        )
    
    def _calculate_dcg(self, scores: List[float], k: Optional[int] = None) -> float:
        """
        计算DCG (Discounted Cumulative Gain)
        DCG@k = Σ(rel_i / log2(i+1)) for i=1 to k
        
        Args:
            scores: 相关性分数列表
            k: 截断位置，None表示使用全部结果
            
        Returns:
            float: DCG值
        """
        if not scores:
            return 0.0
        
        k = k or len(scores)
        dcg = 0.0
        
        for i, score in enumerate(scores[:k], start=1):
            dcg += score / math.log2(i + 1)
        
        return dcg
    
    def _calculate_idcg(self, scores: List[float], k: Optional[int] = None) -> float:
        """
        计算IDCG (Ideal DCG)
        理想情况下的DCG，即分数按降序排列的DCG
        
        Args:
            scores: 相关性分数列表
            k: 截断位置
            
        Returns:
            float: IDCG值
        """
        if not scores:
            return 0.0
        
        # 按降序排列获得理想分数
        ideal_scores = sorted(scores, reverse=True)
        return self._calculate_dcg(ideal_scores, k)
    
    def _calculate_ndcg(self, scores: List[float], k: Optional[int] = None) -> float:
        """
        计算NDCG (Normalized DCG)
        NDCG = DCG / IDCG
        
        Args:
            scores: 相关性分数列表
            k: 截断位置
            
        Returns:
            float: NDCG值 (0-1之间)
        """
        if not scores:
            return 0.0
        
        dcg = self._calculate_dcg(scores, k)
        idcg = self._calculate_idcg(scores, k)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _calculate_precision_at_k(
        self,
        scores: List[float],
        k_values: List[int]
    ) -> Dict[int, float]:
        """
        计算Precision@K
        Precision@K = (前K个结果中相关结果数) / K
        
        Args:
            scores: 相关性分数列表
            k_values: K值列表
            
        Returns:
            Dict[int, float]: 各K值对应的Precision
        """
        precision = {}
        
        for k in k_values:
            if k > len(scores):
                # K超过结果数时，使用所有结果
                relevant_count = sum(1 for s in scores if s >= self.relevance_threshold)
                precision[k] = relevant_count / len(scores) if scores else 0.0
            else:
                # 计算前K个结果的精确率
                top_k_scores = scores[:k]
                relevant_count = sum(1 for s in top_k_scores if s >= self.relevance_threshold)
                precision[k] = relevant_count / k
        
        return precision
    
    def _calculate_mrr(self, scores: List[float]) -> float:
        """
        计算MRR (Mean Reciprocal Rank)
        MRR = 1 / rank_of_first_relevant_result
        
        Args:
            scores: 相关性分数列表
            
        Returns:
            float: MRR值
        """
        if not scores:
            return 0.0
        
        # 找到第一个相关结果的位置
        for i, score in enumerate(scores, start=1):
            if score >= self.relevance_threshold:
                return 1.0 / i
        
        # 如果没有相关结果
        return 0.0
    
    def compare_results(
        self,
        results_a: List[Dict[str, Any]],
        results_b: List[Dict[str, Any]],
        label_a: str = "A",
        label_b: str = "B"
    ) -> str:
        """
        比较两组搜索结果的质量
        
        Args:
            results_a: 第一组结果
            results_b: 第二组结果
            label_a: 第一组标签
            label_b: 第二组标签
            
        Returns:
            str: 比较报告
        """
        metrics_a = self.evaluate(results_a)
        metrics_b = self.evaluate(results_b)
        
        report = f"\n{'='*60}\n"
        report += f"Search Quality Comparison: {label_a} vs {label_b}\n"
        report += f"{'='*60}\n\n"
        
        report += f"{label_a} Results:\n{metrics_a}\n\n"
        report += f"{label_b} Results:\n{metrics_b}\n\n"
        
        # 计算改进
        report += f"{'='*60}\n"
        report += "Improvements:\n"
        report += f"{'='*60}\n"
        
        ndcg_diff = metrics_b.ndcg - metrics_a.ndcg
        report += f"NDCG: {ndcg_diff:+.4f} ({ndcg_diff/metrics_a.ndcg*100:+.2f}%)\n" if metrics_a.ndcg > 0 else f"NDCG: {ndcg_diff:+.4f}\n"
        
        mrr_diff = metrics_b.mrr - metrics_a.mrr
        report += f"MRR: {mrr_diff:+.4f} ({mrr_diff/metrics_a.mrr*100:+.2f}%)\n" if metrics_a.mrr > 0 else f"MRR: {mrr_diff:+.4f}\n"
        
        for k in [1, 3, 5]:
            p_a = metrics_a.precision_at_k.get(k, 0)
            p_b = metrics_b.precision_at_k.get(k, 0)
            p_diff = p_b - p_a
            report += f"Precision@{k}: {p_diff:+.4f} ({p_diff/p_a*100:+.2f}%)\n" if p_a > 0 else f"Precision@{k}: {p_diff:+.4f}\n"
        
        return report


def calculate_search_quality(
    results: List[Dict[str, Any]],
    score_key: str = "score",
    relevance_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    便捷函数：计算搜索结果质量指标
    
    Args:
        results: 搜索结果列表
        score_key: 分数字段名
        relevance_threshold: 相关性阈值
        
    Returns:
        Dict: 评估指标字典
    """
    evaluator = SearchQualityEvaluator(relevance_threshold)
    metrics = evaluator.evaluate(results, score_key)
    return metrics.to_dict()


if __name__ == "__main__":
    # 测试示例
    print("Testing Search Quality Metrics...\n")
    
    # 模拟搜索结果
    test_results = [
        {"title": "Result 1", "score": 0.95},
        {"title": "Result 2", "score": 0.85},
        {"title": "Result 3", "score": 0.75},
        {"title": "Result 4", "score": 0.60},
        {"title": "Result 5", "score": 0.45},
        {"title": "Result 6", "score": 0.30},
    ]
    
    evaluator = SearchQualityEvaluator(relevance_threshold=0.5)
    metrics = evaluator.evaluate(test_results)
    
    print(metrics)
    print("\n" + "="*60)
    print("Metrics as dict:")
    print(metrics.to_dict())
