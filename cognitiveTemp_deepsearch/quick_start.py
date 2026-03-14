#!/usr/bin/env python3
"""
快速开始指南：Research Metrics Dashboard
这个脚本演示如何使用集成的metrics系统
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.visualization import MetricsCollector, MetricsVisualizer, MetricsCalculator


def example_basic_metrics():
    """基础示例：创建和显示metrics"""
    print("\n" + "=" * 70)
    print("示例 1: 基础 Metrics 收集")
    print("=" * 70)
    
    # 创建收集器
    collector = MetricsCollector()
    
    # 设置基本信息
    collector.metrics.query = "AI发展趋势"
    collector.metrics.total_sections = 3
    collector.metrics.total_sources = 15
    collector.metrics.total_reflections = 3
    
    # 模拟计时
    collector.metrics.time_metrics.structure_generation_time = 5.2
    collector.metrics.time_metrics.search_time = 45.8
    collector.metrics.time_metrics.reflection_time = 32.5
    collector.metrics.time_metrics.report_generation_time = 8.3
    collector.metrics.time_metrics.total_time = 92.0  # 直接设置总时间
    
    # 模拟token
    collector.add_token_usage("deepseek", 3000, 2000, 0.084)  # $0.084
    
    # 模拟搜索质量
    relevances = [1, 1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.3, 0.1, 0]
    calculator = MetricsCalculator()
    collector.metrics.search_quality.ndcg = calculator.calculate_ndcg(relevances)
    collector.metrics.search_quality.mrr = calculator.calculate_mrr(relevances)
    collector.metrics.search_quality.avg_relevance = sum(relevances) / len(relevances)
    collector.metrics.search_quality.precision_at_1 = calculator.calculate_precision_at_k(relevances, k=1)
    collector.metrics.search_quality.precision_at_3 = calculator.calculate_precision_at_k(relevances, k=3)
    collector.metrics.search_quality.unique_sources = 15
    collector.metrics.search_quality.coverage_score = 0.85
    collector.metrics.search_quality.total_searches = len(relevances)
    
    # 最后调用finalize
    collector.finalize()
    
    # 显示结果
    print(f"\n📊 Metrics 摘要:")
    print(f"  查询: {collector.metrics.query}")
    print(f"  总章节: {collector.metrics.total_sections}")
    print(f"  总来源: {collector.metrics.total_sources}")
    print(f"  总时间: {collector.metrics.time_metrics.total_time:.2f}s")
    print(f"  总Token: {collector.metrics.token_metrics.total_tokens}")
    print(f"  总成本: ${collector.metrics.token_metrics.total_cost_usd:.4f}")
    print(f"  NDCG: {collector.metrics.search_quality.ndcg:.4f}")
    print(f"  综合评分: {collector.metrics.overall_score:.2f}/100")


def example_visualization():
    """示例 2: 生成和保存HTML仪表板"""
    print("\n" + "=" * 70)
    print("示例 2: 生成 HTML 可视化仪表板")
    print("=" * 70)
    
    # 创建完整的metrics
    collector = MetricsCollector()
    collector.metrics.query = "区块链技术应用"
    collector.metrics.total_sections = 4
    collector.metrics.total_sources = 20
    collector.metrics.total_reflections = 4
    
    # 详细的时间数据
    collector.metrics.time_metrics.structure_generation_time = 6.5
    collector.metrics.time_metrics.search_time = 52.3
    collector.metrics.time_metrics.reflection_time = 38.7
    collector.metrics.time_metrics.report_generation_time = 9.2
    
    # 详细的token数据
    collector.add_token_usage("deepseek", 3500, 2500, 0.098)
    collector.add_token_usage("deepseek", 2800, 1900, 0.078)
    
    # 详细的质量数据
    relevances = [1, 1, 0.95, 0.85, 0.75, 0.65, 0.5, 0.4, 0.2, 0.1, 0, 0]
    calculator = MetricsCalculator()
    
    collector.metrics.search_quality.ndcg = calculator.calculate_ndcg(relevances)
    collector.metrics.search_quality.mrr = calculator.calculate_mrr(relevances)
    collector.metrics.search_quality.map_score = calculator.calculate_map(relevances)
    collector.metrics.search_quality.precision_at_1 = calculator.calculate_precision_at_k(relevances, k=1)
    collector.metrics.search_quality.precision_at_3 = calculator.calculate_precision_at_k(relevances, k=3)
    collector.metrics.search_quality.precision_at_5 = calculator.calculate_precision_at_k(relevances, k=5)
    collector.metrics.search_quality.precision_at_10 = calculator.calculate_precision_at_k(relevances, k=10)
    collector.metrics.search_quality.avg_relevance = sum(relevances) / len(relevances)
    collector.metrics.search_quality.unique_sources = 20
    collector.metrics.search_quality.source_diversity = 0.88
    collector.metrics.search_quality.coverage_score = 0.92
    
    collector.finalize()
    
    # 生成HTML
    visualizer = MetricsVisualizer()
    html_dashboard = visualizer.generate_html_dashboard(collector.metrics, language="ZH")
    
    # 保存文件
    output_file = "metrics_dashboard.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_dashboard)
    
    print(f"\n✅ HTML仪表板已生成: {output_file}")
    print(f"   文件大小: {len(html_dashboard) / 1024:.1f} KB")
    print(f"   综合评分: {collector.metrics.overall_score:.2f}/100")
    print(f"\n💡 在浏览器中打开查看可视化仪表板")


def example_json_export():
    """示例 3: 导出为JSON格式"""
    print("\n" + "=" * 70)
    print("示例 3: 导出 Metrics 为 JSON")
    print("=" * 70)
    
    collector = MetricsCollector()
    collector.metrics.query = "深度学习应用"
    collector.metrics.total_sections = 2
    
    # 设置所有关键指标
    collector.metrics.time_metrics.structure_generation_time = 3.5
    collector.metrics.time_metrics.search_time = 28.7
    collector.metrics.time_metrics.reflection_time = 15.3
    collector.metrics.time_metrics.report_generation_time = 5.1
    
    collector.add_token_usage("deepseek", 2000, 1500, 0.049)
    
    # 添加搜索质量指标
    calculator = MetricsCalculator()
    relevances = [1, 0.95, 0.8, 0.7, 0.5]
    collector.metrics.search_quality.ndcg = calculator.calculate_ndcg(relevances)
    collector.metrics.search_quality.mrr = calculator.calculate_mrr(relevances)
    collector.metrics.search_quality.map_score = calculator.calculate_map(relevances)
    collector.metrics.search_quality.avg_relevance = sum(relevances) / len(relevances)
    collector.metrics.search_quality.unique_sources = 8
    collector.metrics.search_quality.coverage_score = 0.75
    collector.metrics.search_quality.total_searches = len(relevances)
    
    collector.finalize()
    
    # 导出JSON
    json_str = collector.metrics.to_json(indent=2)
    
    print("\n📄 JSON数据 (前500字符):")
    print(json_str[:500] + "...")
    
    # 保存到文件
    with open("metrics.json", "w", encoding="utf-8") as f:
        f.write(json_str)
    
    print(f"\n✅ JSON已保存到 metrics.json")


def example_cost_calculation():
    """示例 4: 成本计算"""
    print("\n" + "=" * 70)
    print("示例 4: Token 成本计算")
    print("=" * 70)
    
    from src.visualization import TokenPricingCalculator
    
    calc = TokenPricingCalculator()
    
    # 不同模型的成本对比
    models = [
        ("deepseek", "deepseek-chat"),
        ("openai", "gpt-4o-mini"),
        ("openai", "gpt-4o"),
    ]
    
    prompt_tokens = 10000
    completion_tokens = 5000
    
    print(f"\n📊 成本对比 ({prompt_tokens:,} prompt + {completion_tokens:,} completion):")
    print("-" * 70)
    
    for provider, model in models:
        cost_usd = calc.calculate_cost_usd(provider, model, prompt_tokens, completion_tokens)
        cost_rmb, _ = calc.calculate_cost(provider, model, prompt_tokens, completion_tokens, "CNY")
        print(f"  {provider:10} {model:20} ${cost_usd:8.4f}  ¥{cost_rmb:8.2f}")
    
    print("-" * 70)


def example_comparison():
    """示例 5: 多次研究对比"""
    print("\n" + "=" * 70)
    print("示例 5: 多次研究对比")
    print("=" * 70)
    
    queries = [
        ("AI趋势", 45.2, 3000),
        ("区块链", 52.8, 4200),
        ("量子计算", 38.5, 2800),
    ]
    
    print("\n📊 研究对比表:")
    print("-" * 70)
    print(f"{'查询':<15} {'耗时(s)':<12} {'Token':<10} {'预估成本':<12}")
    print("-" * 70)
    
    from src.visualization import TokenPricingCalculator
    calc = TokenPricingCalculator()
    
    for query, time, tokens in queries:
        cost = calc.calculate_cost_usd("deepseek", "deepseek-chat", tokens // 2, tokens // 2)
        print(f"{query:<15} {time:<12.1f} {tokens:<10} ${cost:<11.4f}")
    
    print("-" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 Research Metrics - 快速开始指南")
    print("=" * 70)
    
    try:
        # 运行所有示例
        example_basic_metrics()
        example_visualization()
        example_json_export()
        example_cost_calculation()
        example_comparison()
        
        print("\n" + "=" * 70)
        print("✅ 所有示例执行完成！")
        print("=" * 70)
        print("\n📚 生成的文件:")
        print("  • metrics_dashboard.html - 可视化仪表板")
        print("  • metrics.json - JSON数据")
        
        print("\n💡 下一步:")
        print("  1. 在浏览器中打开 metrics_dashboard.html")
        print("  2. 查看 METRICS_INTEGRATION.md 了解详细信息")
        print("  3. 运行 test_metrics.py 执行完整测试")
        print()
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
