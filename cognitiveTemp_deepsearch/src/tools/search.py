"""
搜索工具实现
支持多种搜索引擎，主要使用Tavily搜索
支持搜索增强、优化和过滤功能
包含搜索结果质量评估
"""

import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from tavily import TavilyClient

# 导入搜索质量评估模块
try:
    from src.utils.search_metrics import SearchQualityEvaluator, calculate_search_quality
except ImportError:
    # 如果导入失败，使用占位符
    SearchQualityEvaluator = None
    calculate_search_quality = None


@dataclass
class SearchResult:
    """搜索结果数据类"""
    title: str
    url: str
    content: str
    score: Optional[float] = None
    source: Optional[str] = None
    published_date: Optional[str] = None
    credibility_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "published_date": self.published_date,
            "credibility_score": self.credibility_score
        }


class SearchEnhancer:
    """搜索增强器"""
    
    @staticmethod
    def expand_query(query: str, expansion_count: int = 3) -> List[str]:
        """
        扩展搜索查询
        生成相关的搜索变体
        
        Args:
            query: 原始查询
            expansion_count: 扩展数量
            
        Returns:
            查询列表
        """
        queries = [query]
        
        # 分词
        words = query.split()
        
        if expansion_count >= 1 and len(words) > 1:
            # 变体1：添加上下文词
            queries.append(f"{query} analysis")
        
        if expansion_count >= 2 and len(words) > 0:
            # 变体2：添加新闻关键词
            queries.append(f"latest {query}")
        
        if expansion_count >= 3:
            # 变体3：添加"是什么"相关查询
            queries.append(f"what is {query}")
        
        return queries[:1 + expansion_count]
    
    @staticmethod
    def calculate_content_quality_score(content: str) -> float:
        """
        计算内容质量分数
        基于内容长度、结构和信息密度
        
        Args:
            content: 内容文本
            
        Returns:
            质量分数（0.0-1.0）
        """
        if not content:
            return 0.0
        
        score = 0.0
        
        # 基于长度（0-0.3分）
        length = len(content)
        if length > 5000:
            score += 0.3
        elif length > 1000:
            score += 0.2
        elif length > 200:
            score += 0.1
        
        # 基于段落数（0-0.3分）
        paragraphs = len(content.split('\n\n'))
        if paragraphs > 5:
            score += 0.3
        elif paragraphs > 2:
            score += 0.2
        elif paragraphs > 0:
            score += 0.1
        
        # 基于信息密度（0-0.4分）
        sentences = len(re.split(r'[。.!?！？]', content))
        avg_sentence_length = length / max(sentences, 1)
        
        if 30 < avg_sentence_length < 150:
            score += 0.4
        elif avg_sentence_length > 20:
            score += 0.2
        
        return min(score, 1.0)
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        基于词汇重叠
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数（0.0-1.0）
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class TavilySearch:
    """Tavily搜索客户端封装"""
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Any] = None):
        """
        初始化Tavily搜索客户端
        
        Args:
            api_key: Tavily API密钥
            config: 配置对象（包含搜索增强参数）
        """
        if api_key is None:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise ValueError("Tavily API Key未找到！请设置TAVILY_API_KEY环境变量或在初始化时提供")
        
        self.client = TavilyClient(api_key=api_key)
        self.config = config
        self.enhancer = SearchEnhancer()
    
    def search(self, query: str, max_results: int = 5, include_raw_content: bool = True,
               timeout: int = 240, **kwargs) -> tuple[List[SearchResult], Optional[Dict[str, Any]]]:
        """
        执行搜索并返回结果和质量指标
        
        Args:
            query: 搜索查询
            max_results: 最大结果数量
            include_raw_content: 是否包含原始内容
            timeout: 超时时间（秒）
            **kwargs: 其他参数
            
        Returns:
            (搜索结果列表, 质量指标字典) 元组
        """
        try:
            # 调用Tavily API
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                timeout=timeout
            )
            
            # 解析结果
            results = []
            if 'results' in response:
                for item in response['results']:
                    # 计算内容质量分数
                    content = item.get('content', '')
                    quality_score = self.enhancer.calculate_content_quality_score(content)
                    
                    # 提取来源
                    url = item.get('url', '')
                    source = self._extract_domain(url)
                    
                    result = SearchResult(
                        title=item.get('title', ''),
                        url=url,
                        content=content,
                        score=item.get('score'),
                        source=source,
                        published_date=item.get('published_date'),
                        credibility_score=quality_score
                    )
                    results.append(result)
            
            # 应用过滤和优化
            results = self._apply_filters(results)
            results = self._deduplicate_results(results)
            results = self._sort_results(results)
            
            # 计算搜索质量指标
            quality_metrics = None
            if results and calculate_search_quality:
                quality_metrics = self._calculate_quality_metrics(results)
                print(f"\n🎯 搜索质量评估:")
                print(f"   NDCG: {quality_metrics.get('ndcg', 0):.4f}")
                print(f"   MRR: {quality_metrics.get('mrr', 0):.4f}")
                print(f"   P@3: {quality_metrics.get('precision_at_k', {}).get(3, 0):.4f}")
                print(f"   平均相关性: {quality_metrics.get('relevance_score', 0):.4f}")
            
            return results, quality_metrics
            
        except Exception as e:
            print(f"搜索错误: {str(e)}")
            return [], None
    
    def search_with_expansion(self, query: str, max_results: int = 5, 
                            expansion_count: int = 3, **kwargs) -> List[SearchResult]:
        """
        执行具有查询扩展的搜索
        
        Args:
            query: 搜索查询
            max_results: 每个查询的最大结果数
            expansion_count: 扩展查询数量
            **kwargs: 其他参数
            
        Returns:
            搜索结果列表
        """
        all_results = []
        queries = self.enhancer.expand_query(query, expansion_count)
        
        for expanded_query in queries:
            try:
                results = self.search(expanded_query, max_results=max_results, **kwargs)
                all_results.extend(results)
            except Exception as e:
                print(f"扩展查询 '{expanded_query}' 失败: {str(e)}")
        
        # 去重和重新排序
        all_results = self._deduplicate_results(all_results)
        all_results = self._sort_results(all_results)
        
        return all_results[:max_results]
    
    def _apply_filters(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        应用过滤器
        
        Args:
            results: 原始结果
            
        Returns:
            过滤后的结果
        """
        if not self.config:
            return results
        
        filtered = []
        
        for result in results:
            # 质量分数过滤
            if hasattr(self.config, 'min_content_quality_score'):
                min_score = self.config.min_content_quality_score
                if result.credibility_score and result.credibility_score < min_score:
                    continue
            
            # 日期过滤
            if hasattr(self.config, 'filter_by_date') and self.config.filter_by_date:
                if result.published_date:
                    try:
                        pub_date = datetime.fromisoformat(result.published_date.replace('Z', '+00:00'))
                        days_back = getattr(self.config, 'days_back', 90)
                        if datetime.now(pub_date.tzinfo) - pub_date > timedelta(days=days_back):
                            continue
                    except:
                        pass
            
            # 来源可信度过滤
            if hasattr(self.config, 'filter_by_source_credibility') and self.config.filter_by_source_credibility:
                min_credibility = getattr(self.config, 'min_source_credibility', 0.5)
                source_credibility = self._estimate_source_credibility(result.source)
                if source_credibility < min_credibility:
                    continue
            
            filtered.append(result)
        
        return filtered
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        去重结果
        
        Args:
            results: 结果列表
            
        Returns:
            去重后的结果
        """
        if not self.config:
            threshold = 0.7
        else:
            threshold = getattr(self.config, 'dedup_similarity_threshold', 0.7)
        
        deduped = []
        
        for result in results:
            is_duplicate = False
            
            for existing in deduped:
                similarity = self.enhancer.calculate_similarity(
                    result.content,
                    existing.content
                )
                
                if similarity > threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduped.append(result)
        
        return deduped
    
    def _sort_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        排序结果
        
        Args:
            results: 结果列表
            
        Returns:
            排序后的结果
        """
        if not self.config:
            mode = "relevance"
        else:
            mode = getattr(self.config, 'search_priority_mode', 'relevance')
        
        if mode == "relevance":
            # 按相关性排序（默认）
            return sorted(results, key=lambda r: r.score or 0, reverse=True)
        elif mode == "recency":
            # 按时效性排序
            return sorted(results, key=lambda r: r.published_date or '', reverse=True)
        elif mode == "authority":
            # 按权威性排序
            return sorted(results, key=lambda r: r.credibility_score or 0, reverse=True)
        else:
            return results
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or ""
        except:
            return ""
    
    @staticmethod
    def _estimate_source_credibility(source: Optional[str]) -> float:
        """
        估计来源可信度
        基于已知的可信来源
        
        Args:
            source: 来源域名
            
        Returns:
            可信度分数（0.0-1.0）
        """
        if not source:
            return 0.3
        
        # 高可信度来源
        high_credibility = {
            'bbc.com', 'reuters.com', 'apnews.com', 'theguardian.com',
            'nytimes.com', 'ft.com', 'economist.com', 'nature.com',
            'sciencedirect.com', 'arxiv.org'
        }
        
        # 中等可信度来源
        medium_credibility = {
            'wikipedia.org', 'techcrunch.com', 'theverge.com', 'medium.com'
        }
        
        source_lower = source.lower()
        
        if any(trusted in source_lower for trusted in high_credibility):
            return 0.9
        elif any(medium in source_lower for medium in medium_credibility):
            return 0.7
        else:
            return 0.5
    
    def _calculate_quality_metrics(self, results: List[SearchResult]) -> Dict[str, Any]:
        """
        计算搜索结果质量指标
        
        Args:
            results: 搜索结果列表
            
        Returns:
            质量指标字典
        """
        if not calculate_search_quality:
            return {}
        
        # 转换为字典格式
        results_dict = [r.to_dict() for r in results]
        
        # 使用credibility_score作为评估依据
        metrics = calculate_search_quality(
            results_dict,
            score_key='credibility_score',
            relevance_threshold=0.5
        )
        
        return metrics
    
    def evaluate_search_quality(
        self,
        results: List[SearchResult],
        verbose: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        详细评估搜索结果质量
        
        Args:
            results: 搜索结果列表
            verbose: 是否打印详细信息
            
        Returns:
            质量指标字典，如果评估失败则返回None
        """
        if not SearchQualityEvaluator:
            if verbose:
                print("⚠️ 搜索质量评估模块未加载")
            return None
        
        if not results:
            if verbose:
                print("⚠️ 没有搜索结果可以评估")
            return None
        
        try:
            evaluator = SearchQualityEvaluator(relevance_threshold=0.5)
            results_dict = [r.to_dict() for r in results]
            metrics = evaluator.evaluate(results_dict, score_key='credibility_score')
            
            if verbose:
                print("\n" + "="*60)
                print("📊 搜索结果质量评估报告")
                print("="*60)
                print(metrics)
                print("="*60 + "\n")
            
            return metrics.to_dict()
        
        except Exception as e:
            if verbose:
                print(f"❌ 质量评估失败: {str(e)}")
            return None


# 全局搜索客户端实例
_tavily_client = None
_client_config = None


def get_tavily_client(config: Optional[Any] = None) -> TavilySearch:
    """获取全局Tavily客户端实例"""
    global _tavily_client, _client_config
    if _tavily_client is None or (config and config != _client_config):
        _tavily_client = TavilySearch(config=config)
        _client_config = config
    return _tavily_client


def set_search_config(config: Any):
    """设置搜索配置"""
    global _tavily_client, _client_config
    _client_config = config
    _tavily_client = None  # 重置客户端以应用新配置


def tavily_search(query: str, max_results: int = 5, include_raw_content: bool = True, 
                  timeout: int = 240, api_key: Optional[str] = None, config: Optional[Any] = None,
                  enable_expansion: bool = False, expansion_count: int = 3) -> List[Dict[str, Any]]:
    """
    便捷的Tavily搜索函数
    
    Args:
        query: 搜索查询
        max_results: 最大结果数量
        include_raw_content: 是否包含原始内容
        timeout: 超时时间（秒）
        api_key: Tavily API密钥，如果提供则使用此密钥，否则使用全局客户端
        config: 配置对象
        enable_expansion: 是否启用查询扩展
        expansion_count: 查询扩展数量
        
    Returns:
        搜索结果字典列表，保持与原始代码兼容的格式
    """
    try:
        if api_key:
            # 使用提供的API密钥创建临时客户端
            client = TavilySearch(api_key, config=config)
        else:
            # 使用全局客户端
            if config:
                set_search_config(config)
            client = get_tavily_client(config)
        
        # 选择搜索方法
        if enable_expansion and hasattr(config, 'enable_search_expansion') and config.enable_search_expansion:
            expansion_count = getattr(config, 'search_query_expansion_count', expansion_count)
            search_result = client.search_with_expansion(query, max_results=max_results, expansion_count=expansion_count)
            # search_with_expansion 返回 List[SearchResult]，不返回 metrics
            if isinstance(search_result, tuple):
                results, _ = search_result
            else:
                results = search_result
        else:
            search_result = client.search(query, max_results=max_results, include_raw_content=include_raw_content, timeout=timeout)
            # search 返回 (List[SearchResult], Optional[Dict]) 元组
            if isinstance(search_result, tuple) and len(search_result) == 2:
                results, quality_metrics = search_result
            else:
                # 如果不是元组，说明是旧版本返回格式
                results = search_result if isinstance(search_result, list) else [search_result]
                quality_metrics = None
        
        # 转换为字典格式以保持兼容性
        if isinstance(results, list):
            return [result.to_dict() if hasattr(result, 'to_dict') else result for result in results]
        else:
            # 如果results不是列表，可能是单个结果
            return [results.to_dict() if hasattr(results, 'to_dict') else results]
        
    except Exception as e:
        print(f"搜索功能调用错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def test_search(query: str = "人工智能发展趋势 2025", max_results: int = 3):
    """
    测试搜索功能
    
    Args:
        query: 测试查询
        max_results: 最大结果数量
    """
    print(f"\n=== 测试Tavily搜索功能 ===")
    print(f"搜索查询: {query}")
    print(f"最大结果数: {max_results}")
    
    try:
        results = tavily_search(query, max_results=max_results)
        
        if results:
            print(f"\n找到 {len(results)} 个结果:")
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"标题: {result['title']}")
                print(f"链接: {result['url']}")
                print(f"内容摘要: {result['content'][:200]}...")
                if result.get('score'):
                    print(f"相关度评分: {result['score']}")
        else:
            print("未找到搜索结果")
            
    except Exception as e:
        print(f"搜索测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    test_search()
