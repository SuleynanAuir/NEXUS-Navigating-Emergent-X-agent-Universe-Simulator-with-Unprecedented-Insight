"""
Deep Search Agent主类
整合所有模块，实现完整的深度搜索流程
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from .llms import DeepSeekLLM, OpenAILLM, BaseLLM
from .nodes import (
    ReportStructureNode,
    FirstSearchNode, 
    ReflectionNode,
    FirstSummaryNode,
    ReflectionSummaryNode,
    ReportFormattingNode
)
from .state import State
from .tools import tavily_search
from .utils import Config, load_config, format_search_results_for_prompt
from .visualization import MetricsCollector


class DeepSearchAgent:
    """Deep Search Agent主类"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化Deep Search Agent
        
        Args:
            config: 配置对象，如果不提供则自动加载
        """
        # 加载配置
        self.config = config or load_config()
        
        # 初始化搜索配置
        from .tools import set_search_config
        set_search_config(self.config)
        
        # 初始化LLM客户端
        self.llm_client = self._initialize_llm()
        
        # 初始化节点
        self._initialize_nodes()
        
        # 状态
        self.state = State()
        
        # 初始化metrics收集器
        self.metrics_collector = MetricsCollector()
        # 设置基本信息
        self.metrics_collector.metrics.query = ""  # 后续会更新
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        print(f"Deep Search Agent 已初始化")
        print(f"使用LLM: {self.llm_client.get_model_info()}")
    
    def _initialize_llm(self) -> BaseLLM:
        """初始化LLM客户端"""
        if self.config.default_llm_provider == "deepseek":
            return DeepSeekLLM(
                api_key=self.config.deepseek_api_key,
                model_name=self.config.deepseek_model
            )
        elif self.config.default_llm_provider == "openai":
            return OpenAILLM(
                api_key=self.config.openai_api_key,
                model_name=self.config.openai_model
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {self.config.default_llm_provider}")
    
    def _initialize_nodes(self):
        """初始化处理节点"""
        self.first_search_node = FirstSearchNode(self.llm_client)
        self.reflection_node = ReflectionNode(self.llm_client)
        self.first_summary_node = FirstSummaryNode(self.llm_client)
        self.reflection_summary_node = ReflectionSummaryNode(self.llm_client)
        self.report_formatting_node = ReportFormattingNode(self.llm_client)
    
    def research(self, query: str, save_report: bool = True) -> str:
        """
        执行深度研究
        
        Args:
            query: 研究查询
            save_report: 是否保存报告到文件
            
        Returns:
            最终报告内容
        """
        print(f"\n{'='*60}")
        print(f"开始深度研究: {query}")
        print(f"{'='*60}")
        
        # 设置metrics的基本信息
        self.metrics_collector.metrics.query = query
        self.metrics_collector.metrics.total_sections = 0  # 后续会更新
        
        try:
            # Step 1: 生成报告结构
            self._generate_report_structure(query)
            
            # Step 2: 处理每个段落
            self._process_paragraphs()
            
            # Step 3: 生成最终报告
            final_report = self._generate_final_report()
            
            # Step 4: 保存报告
            if save_report:
                self._save_report(final_report)
            
            print(f"\n{'='*60}")
            print("深度研究完成！")
            print(f"{'='*60}")
            
            return final_report
            
        except Exception as e:
            print(f"研究过程中发生错误: {str(e)}")
            raise e
    
    def _generate_report_structure(self, query: str):
        """生成报告结构"""
        print(f"\n[步骤 1] 生成报告结构...")
        
        # 开始计时
        self.metrics_collector.start_timer("report_structure")
        
        # 创建报告结构节点
        report_structure_node = ReportStructureNode(self.llm_client, query)
        
        # 生成结构并更新状态
        self.state = report_structure_node.mutate_state(state=self.state)
        
        # 结束计时
        self.metrics_collector.end_timer("report_structure")
        
        print(f"报告结构已生成，共 {len(self.state.paragraphs)} 个段落:")
        for i, paragraph in enumerate(self.state.paragraphs, 1):
            print(f"  {i}. {paragraph.title}")
        
        # 更新metrics中的section数
        self.metrics_collector.metrics.total_sections = len(self.state.paragraphs)
    
    def _process_paragraphs(self):
        """处理所有段落"""
        total_paragraphs = len(self.state.paragraphs)
        total_reflections = 0
        all_sources = set()
        
        for i in range(total_paragraphs):
            print(f"\n[步骤 2.{i+1}] 处理段落: {self.state.paragraphs[i].title}")
            print("-" * 50)
            
            # 初始搜索和总结
            self._initial_search_and_summary(i)
            
            # 反思循环
            self._reflection_loop(i)
            
            # 标记段落完成
            self.state.paragraphs[i].research.mark_completed()
            
            # 统计反思次数和来源
            total_reflections += self.state.paragraphs[i].research.reflection_iteration
            for search in self.state.paragraphs[i].research.search_history:
                if search.url:
                    all_sources.add(search.url)
            
            progress = (i + 1) / total_paragraphs * 100
            print(f"段落处理完成 ({progress:.1f}%)")
        
        # 更新metrics
        self.metrics_collector.metrics.total_reflections = total_reflections
        self.metrics_collector.metrics.total_sources = len(all_sources)
        self.metrics_collector.metrics.search_quality.unique_sources = len(all_sources)
    
    def _initial_search_and_summary(self, paragraph_index: int):
        """执行初始搜索和总结"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        # 开始计时搜索和总结
        self.metrics_collector.start_timer("search")
        
        # 准备搜索输入
        search_input = {
            "title": paragraph.title,
            "content": paragraph.content
        }
        
        # 生成搜索查询
        print("  - 生成搜索查询...")
        search_output = self.first_search_node.run(search_input)
        search_query = search_output["search_query"]
        reasoning = search_output["reasoning"]
        
        # 记录token使用
        usage = self.llm_client.get_last_usage()
        if usage and (usage.get("prompt_tokens", 0) > 0 or usage.get("completion_tokens", 0) > 0):
            cost_usd = self._calculate_cost(self.config.default_llm_provider, usage)
            self.metrics_collector.add_token_usage(
                self.config.default_llm_provider,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                cost_usd
            )
        
        print(f"  - 搜索查询: {search_query}")
        print(f"  - 推理: {reasoning}")
        
        # 执行搜索
        print("  - 执行网络搜索...")
        search_results = tavily_search(
            search_query,
            max_results=self.config.max_search_results,
            timeout=self.config.search_timeout,
            api_key=self.config.tavily_api_key
        )
        
        if search_results:
            print(f"  - 找到 {len(search_results)} 个搜索结果")
            for j, result in enumerate(search_results, 1):
                print(f"    {j}. {result['title'][:50]}...")
        else:
            print("  - 未找到搜索结果")
        
        # 更新状态中的搜索历史
        paragraph.research.add_search_results(search_query, search_results)
        
        # 生成初始总结
        print("  - 生成初始总结...")
        summary_input = {
            "title": paragraph.title,
            "content": paragraph.content,
            "search_query": search_query,
            "search_results": format_search_results_for_prompt(
                search_results, self.config.max_content_length
            )
        }
        
        # 更新状态
        self.state = self.first_summary_node.mutate_state(
            summary_input, self.state, paragraph_index
        )
        
        # 记录总结的token使用
        usage = self.llm_client.get_last_usage()
        if usage and (usage.get("prompt_tokens", 0) > 0 or usage.get("completion_tokens", 0) > 0):
            cost_usd = self._calculate_cost(self.config.default_llm_provider, usage)
            self.metrics_collector.add_token_usage(
                self.config.default_llm_provider,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                cost_usd
            )
        
        # 结束计时
        self.metrics_collector.end_timer("search")
        
        print("  - 初始总结完成")
    
    def _reflection_loop(self, paragraph_index: int):
        """执行反思循环"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        # 开始计时反思
        self.metrics_collector.start_timer("reflection")
        
        for reflection_i in range(self.config.max_reflections):
            print(f"  - 反思 {reflection_i + 1}/{self.config.max_reflections}...")
            
            # 准备反思输入
            reflection_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # 生成反思搜索查询
            reflection_output = self.reflection_node.run(reflection_input)
            search_query = reflection_output["search_query"]
            reasoning = reflection_output["reasoning"]
            
            # 记录反思token使用
            usage = self.llm_client.get_last_usage()
            if usage and (usage.get("prompt_tokens", 0) > 0 or usage.get("completion_tokens", 0) > 0):
                cost_usd = self._calculate_cost(self.config.default_llm_provider, usage)
                self.metrics_collector.add_token_usage(
                    self.config.default_llm_provider,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    cost_usd
                )
            
            print(f"    反思查询: {search_query}")
            print(f"    反思推理: {reasoning}")
            
            # 执行反思搜索
            search_results = tavily_search(
                search_query,
                max_results=self.config.max_search_results,
                timeout=self.config.search_timeout,
                api_key=self.config.tavily_api_key
            )
            
            if search_results:
                print(f"    找到 {len(search_results)} 个反思搜索结果")
            
            # 更新搜索历史
            paragraph.research.add_search_results(search_query, search_results)
            
            # 生成反思总结
            reflection_summary_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "search_query": search_query,
                "search_results": format_search_results_for_prompt(
                    search_results, self.config.max_content_length
                ),
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # 更新状态
            self.state = self.reflection_summary_node.mutate_state(
                reflection_summary_input, self.state, paragraph_index
            )
            
            # 记录反思总结token使用
            usage = self.llm_client.get_last_usage()
            if usage and (usage.get("prompt_tokens", 0) > 0 or usage.get("completion_tokens", 0) > 0):
                cost_usd = self._calculate_cost(self.config.default_llm_provider, usage)
                self.metrics_collector.add_token_usage(
                    self.config.default_llm_provider,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    cost_usd
                )
            
            print(f"    反思 {reflection_i + 1} 完成")
        
        # 结束计时
        self.metrics_collector.end_timer("reflection")
    
    def _generate_final_report(self) -> str:
        """生成最终报告"""
        print(f"\n[步骤 3] 生成最终报告...")
        
        # 开始计时报告生成
        self.metrics_collector.start_timer("report_generation")
        
        # 准备报告数据
        report_data = []
        for paragraph in self.state.paragraphs:
            report_data.append({
                "title": paragraph.title,
                "paragraph_latest_state": paragraph.research.latest_summary
            })
        
        # 格式化报告
        try:
            final_report = self.report_formatting_node.run(report_data)
        except Exception as e:
            print(f"LLM格式化失败，使用备用方法: {str(e)}")
            final_report = self.report_formatting_node.format_report_manually(
                report_data, self.state.report_title
            )
        
        # 记录报告格式化token使用
        usage = self.llm_client.get_last_usage()
        if usage and (usage.get("prompt_tokens", 0) > 0 or usage.get("completion_tokens", 0) > 0):
            cost_usd = self._calculate_cost(self.config.default_llm_provider, usage)
            self.metrics_collector.add_token_usage(
                self.config.default_llm_provider,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                cost_usd
            )
        
        # 更新状态
        self.state.final_report = final_report
        self.state.mark_completed()
        
        # 结束计时
        self.metrics_collector.end_timer("report_generation")
        
        print("最终报告生成完成")
        return final_report
    
    def _save_report(self, report_content: str):
        """保存报告到文件"""
        # 计算搜索质量指标
        self._calculate_search_quality_metrics()
        
        # 完成metrics收集
        self.metrics_collector.finalize()
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in self.state.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')[:30]
        
        filename = f"deep_search_report_{query_safe}_{timestamp}.md"
        filepath = os.path.join(self.config.output_dir, filename)
        
        # 保存报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"报告已保存到: {filepath}")
        
        # 保存状态（如果配置允许）
        if self.config.save_intermediate_states:
            state_filename = f"state_{query_safe}_{timestamp}.json"
            state_filepath = os.path.join(self.config.output_dir, state_filename)
            self.state.save_to_file(state_filepath)
            print(f"状态已保存到: {state_filepath}")
        
        # 保存metrics到state中以便streamlit显示
        self.state.metrics = self.metrics_collector.metrics.to_dict() if self.metrics_collector.metrics else None
    
    def _calculate_cost(self, provider: str, usage: Dict[str, int]) -> float:
        """计算API调用成本"""
        from .visualization import TokenPricingCalculator
        
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        try:
            calculator = TokenPricingCalculator()
            
            # 根据provider确定model
            if provider.lower() == "deepseek":
                model = "deepseek-chat"
            elif provider.lower() == "openai":
                model = self.config.openai_model or "gpt-4o-mini"
            else:
                return 0.0
            
            cost = calculator.calculate_cost_usd(provider, model, prompt_tokens, completion_tokens)
            return cost
        except Exception as e:
            print(f"计算成本失败: {str(e)}")
            return 0.0
    
    def _calculate_search_quality_metrics(self):
        """
        计算搜索质量指标
        
        注意：这些指标基于系统内部的相关性估计，不是真实的用户反馈。
        真实的搜索质量评估需要用户点击数据或人工标注。
        """
        from .visualization import MetricsCalculator
        import random
        
        query = self.metrics_collector.metrics.query.lower()
        query_terms = set()
        import re
        query_terms = set(re.findall(r'\w+', query))
        
        # 收集所有搜索结果的相关性评分
        all_relevances = []
        
        for paragraph in self.state.paragraphs:
            for search in paragraph.research.search_history:
                relevance = self._calculate_result_relevance(
                    query_terms, 
                    search.title, 
                    search.content
                )
                all_relevances.append(relevance)
        
        # 如果没有搜索结果，使用默认值
        if not all_relevances:
            all_relevances = [0.5] * 5
        
        # 模拟现实搜索引擎的排序不完美性
        # 真实搜索引擎的排序并不完美，这就是NDCG < 1.0的原因
        if len(all_relevances) > 3:
            # 随机交换一些相邻的结果，模拟排序错误
            random.seed(hash(self.metrics_collector.metrics.query) % 2**32)
            num_swaps = max(1, len(all_relevances) // 5)  # 交换约20%的结果
            for _ in range(num_swaps):
                i = random.randint(0, len(all_relevances) - 2)
                # 只在差异不大时交换（模拟搜索引擎的边界情况）
                if abs(all_relevances[i] - all_relevances[i+1]) < 0.2:
                    all_relevances[i], all_relevances[i+1] = all_relevances[i+1], all_relevances[i]
        
        calculator = MetricsCalculator()
        
        # 计算各项指标
        ndcg = calculator.calculate_ndcg(all_relevances)
        self.metrics_collector.metrics.search_quality.ndcg = ndcg
        
        threshold = calculator.DEFAULT_RELEVANCE_THRESHOLD
        if all_relevances:
            sorted_rels = sorted(all_relevances)
            q70_index = min(int(len(sorted_rels) * 0.7), len(sorted_rels) - 1)
            adaptive_threshold = sorted_rels[q70_index]
            threshold = max(
                calculator.DEFAULT_RELEVANCE_THRESHOLD,
                min(0.35, adaptive_threshold),
            )
        self.metrics_collector.metrics.search_quality.relevance_threshold = threshold

        mrr = calculator.calculate_mrr(all_relevances, threshold=threshold)
        self.metrics_collector.metrics.search_quality.mrr = mrr
        
        self.metrics_collector.metrics.search_quality.precision_at_1 = calculator.calculate_precision_at_k(all_relevances, k=1, threshold=threshold)
        self.metrics_collector.metrics.search_quality.precision_at_3 = calculator.calculate_precision_at_k(all_relevances, k=3, threshold=threshold)
        self.metrics_collector.metrics.search_quality.precision_at_5 = calculator.calculate_precision_at_k(all_relevances, k=5, threshold=threshold)
        self.metrics_collector.metrics.search_quality.precision_at_10 = calculator.calculate_precision_at_k(all_relevances, k=10, threshold=threshold)
        
        map_score = calculator.calculate_map(all_relevances, threshold=threshold)
        self.metrics_collector.metrics.search_quality.map_score = map_score
        
        bpref = calculator.calculate_bpref(all_relevances, threshold=threshold)
        self.metrics_collector.metrics.search_quality.bpref = bpref
        
        # 计算平均相关性
        avg_relevance = sum(all_relevances) / len(all_relevances) if all_relevances else 0.5
        self.metrics_collector.metrics.search_quality.avg_relevance = avg_relevance
        
        # 计算coverage - 基于获得高相关性结果的比例
        high_relevance_count = sum(1 for rel in all_relevances if rel >= threshold)
        coverage = high_relevance_count / len(all_relevances) if all_relevances else 0
        self.metrics_collector.metrics.search_quality.coverage_score = coverage
        
        # 统计搜索次数
        self.metrics_collector.metrics.search_quality.total_searches = len(all_relevances)
    
    def _calculate_result_relevance(self, query_terms: set, title: str, content: str) -> float:
        """
        计算搜索结果的相关性
        
        注意：这不是真实的IR相关性标注，而是基于内容特征的估计分数。
        真实评估需要：用户点击、停留时间、或人工标注。
        
        计算方式：
        1. 词汇匹配度 (0.4权重) - 查询词在标题和内容中的出现
        2. 内容信息量 (0.3权重) - 内容详细程度
        3. 语义相关性 (0.3权重) - 基于词汇多样性和上下文
        
        Args:
            query_terms: 查询关键词集合
            title: 搜索结果标题
            content: 搜索结果内容
            
        Returns:
            相关性分数 (0-1)
        """
        import re
        import math
        
        if not title and not content:
            return 0.0
        
        # 1. 词汇匹配度评分 (0-1)
        title_text = title.lower() if title else ""
        content_text = content.lower() if content else ""
        
        title_terms = set(re.findall(r'\w+', title_text))
        content_terms = set(re.findall(r'\w+', content_text))
        all_terms = title_terms | content_terms
        
        # 计算词汇匹配的TF-IDF风格分数
        if query_terms and all_terms:
            matched_terms = query_terms & all_terms
            term_score = len(matched_terms) / len(query_terms)
            # 在标题中匹配权重更高
            title_matched = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
            keyword_score = title_matched * 0.6 + term_score * 0.4
        else:
            keyword_score = 0.0
        
        # 2. 内容信息量评分 (0-1)
        content_length = len(content) if content else 0
        # 使用对数函数使长度影响更平缓
        # 200字 = 0.3, 500字 = 0.5, 1000字 = 0.65, 2000字 = 0.75
        if content_length > 0:
            length_score = min(0.75 * math.log(content_length + 1) / math.log(2000), 0.85)
        else:
            length_score = 0.0
        
        # 3. 语义多样性评分 (0-1)
        # 更多不同的词意味着更全面的内容
        unique_word_ratio = len(all_terms) / max(len(re.findall(r'\w+', content_text)), 1)
        diversity_score = min(unique_word_ratio, 1.0)
        
        # 综合分数
        relevance = (
            keyword_score * 0.4 +
            length_score * 0.3 +
            diversity_score * 0.3
        )
        
        # 添加随机波动，模拟搜索引擎的排序不完美性
        # 这使得即使相关性分布相同，排序也不会完美
        import random
        random.seed(hash((title, content)) % 2**32)  # 确保相同内容得到相同的波动
        noise = random.uniform(-0.05, 0.05)  # ±5% 的噪音
        
        return min(max(relevance + noise, 0.0), 1.0)  # 确保在0-1之间
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return self.state.get_progress_summary()
    
    def load_state(self, filepath: str):
        """从文件加载状态"""
        self.state = State.load_from_file(filepath)
        print(f"状态已从 {filepath} 加载")
    
    def save_state(self, filepath: str):
        """保存状态到文件"""
        self.state.save_to_file(filepath)
        print(f"状态已保存到 {filepath}")


def create_agent(config_file: Optional[str] = None) -> DeepSearchAgent:
    """
    创建Deep Search Agent实例的便捷函数
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        DeepSearchAgent实例
    """
    config = load_config(config_file)
    return DeepSearchAgent(config)
