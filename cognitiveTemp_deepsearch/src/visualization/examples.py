"""
指标可视化使用示例
演示如何在DeepSearchAgent中集成指标收集和可视化
"""

from src.visualization import MetricsCollector, MetricsVisualizer, MetricsCalculator
from src.visualization.metrics_model import ResearchMetrics


def example_basic_usage():
    """基础使用示例"""
    # 1. 创建指标收集器
    collector = MetricsCollector()
    
    # 2. 记录各个阶段的执行时间
    collector.start_timer("report_structure")
    # ... 报告结构生成代码 ...
    structure_time = collector.end_timer("report_structure")
    print(f"报告结构生成耗时: {structure_time:.2f}s")
    
    collector.start_timer("search")
    # ... 搜索代码 ...
    search_time = collector.end_timer("search")
    print(f"搜索耗时: {search_time:.2f}s")
    
    # 3. 记录Token使用量和成本
    collector.add_token_usage(
        model="deepseek",
        prompt_tokens=1000,
        completion_tokens=500,
        cost_usd=0.003
    )
    
    # 4. 更新基础统计信息
    collector.metrics.query = "人工智能发展趋势"
    collector.metrics.total_sections = 5
    collector.metrics.total_sources = 45
    collector.metrics.total_reflections = 6
    
    # 5. 计算搜索质量指标
    # 假设我们有相关性分数列表
    relevances = [0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
    sources = ["github.com", "arxiv.org", "github.com", "medium.com", "arxiv.org", 
               "dev.to", "github.com", "arxiv.org", "medium.com", "stackexchange.com"]
    topics = ["neural networks", "transformers", "NLP", "computer vision", "reinforcement learning",
              "neural networks", "transformers", "NLP", "computer vision", "reinforcement learning"]
    
    quality_metrics = MetricsCalculator.aggregate_metrics(
        all_relevances=[relevances],
        sources=sources,
        topics=topics
    )
    
    collector.metrics.search_quality = quality_metrics
    
    # 6. 完成指标收集
    collector.finalize()
    
    # 7. 输出指标
    print("\n=== 综合评分 ===")
    print(f"综合评分: {collector.metrics.overall_score:.1f}/100")
    print(f"时间消耗: {collector.metrics.time_metrics.total_time:.2f}s")
    print(f"Token总数: {collector.metrics.token_metrics.total_tokens}")
    print(f"总成本: ${collector.metrics.token_metrics.total_cost_usd:.4f}")
    
    return collector.metrics


def example_html_generation():
    """HTML生成示例"""
    # 获取metrics
    metrics = example_basic_usage()
    
    # 生成HTML仪表板
    visualizer = MetricsVisualizer()
    html = visualizer.generate_html_dashboard(metrics, language="ZH")
    
    # 保存到文件
    with open("metrics_dashboard.html", "w", encoding="utf-8") as f:
        f.write(f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>研究指标仪表板</title>
</head>
<body style="margin: 0; padding: 20px; background: #f5f5f5;">
    <div style="max-width: 1200px; margin: 0 auto;">
        {html}
    </div>
</body>
</html>
""")
    
    print("HTML仪表板已保存到 metrics_dashboard.html")


def example_integration_with_agent():
    """与Agent集成的示例"""
    print("""
    # 在Agent中使用指标收集的方式:
    
    from src.visualization import MetricsCollector
    from src.agent import DeepSearchAgent
    
    # 在agent.py中添加:
    def __init__(self, config):
        super().__init__(config)
        self.metrics_collector = MetricsCollector()
        self.metrics_collector.metrics.query = config.query or ""
    
    # 在各个阶段记录时间:
    def _generate_report_structure(self, query: str):
        self.metrics_collector.start_timer("report_structure")
        # ... 原有代码 ...
        self.metrics_collector.end_timer("report_structure")
    
    # 在搜索后记录token和成本:
    def _initial_search_and_summary(self, index: int):
        # ... 搜索代码 ...
        self.metrics_collector.add_token_usage(
            model="deepseek",
            prompt_tokens=prompt_tokens_count,
            completion_tokens=completion_tokens_count,
            cost_usd=calculated_cost
        )
    
    # 在完成时生成报告:
    def get_metrics_html(self):
        self.metrics_collector.finalize()
        visualizer = MetricsVisualizer()
        return visualizer.generate_html_dashboard(
            self.metrics_collector.metrics,
            language=st.session_state.language
        )
    """)


def example_advanced_calculation():
    """高级计算示例"""
    print("\n=== 高级指标计算示例 ===")
    
    # 计算器
    calculator = MetricsCalculator()
    
    # 示例相关性分数
    relevances = [0.95, 0.90, 0.85, 0.75, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20]
    
    # 计算单个指标
    ndcg = calculator.calculate_ndcg(relevances, k=10)
    mrr = calculator.calculate_mrr(relevances, threshold=0.7)
    map_score = calculator.calculate_map(relevances, threshold=0.7)
    bpref = calculator.calculate_bpref(relevances, threshold=0.7)
    
    print(f"NDCG@10: {ndcg:.4f}")
    print(f"MRR (threshold=0.7): {mrr:.4f}")
    print(f"MAP (threshold=0.7): {map_score:.4f}")
    print(f"BPref (threshold=0.7): {bpref:.4f}")
    
    # 计算来源多样性
    sources = ["arxiv.org", "github.com", "medium.com", "arxiv.org", "github.com",
               "dev.to", "medium.com", "stackoverflow.com", "arxiv.org", "github.com"]
    diversity = calculator.calculate_source_diversity(sources)
    print(f"\n来源多样性: {diversity:.4f}")
    
    # 计算覆盖率
    topics = ["AI", "ML", "NLP", "CV", "RL", "AI", "ML", "NLP", "CV", "RL"]
    coverage = calculator.calculate_coverage_score(topics, len(set(topics)))
    print(f"覆盖率: {coverage:.4f}")


if __name__ == "__main__":
    print("=== 指标可视化使用示例 ===\n")
    
    # 运行基础示例
    print("1. 基础使用示例:")
    example_basic_usage()
    
    # 运行HTML生成示例
    print("\n2. HTML生成示例:")
    # example_html_generation()  # 取消注释以生成HTML文件
    
    # 显示集成提示
    print("\n3. Agent集成示例:")
    example_integration_with_agent()
    
    # 运行高级计算
    print("\n4. 高级计算示例:")
    example_advanced_calculation()
