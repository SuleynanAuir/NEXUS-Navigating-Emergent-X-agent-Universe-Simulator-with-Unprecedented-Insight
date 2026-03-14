#!/usr/bin/env python3
"""
完整集成测试：模拟真实的Agent运行流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.visualization import MetricsCollector, MetricsVisualizer, MetricsCalculator


def test_complete_workflow():
    """测试完整的metrics工作流程"""
    print("\n" + "=" * 80)
    print("🧪 完整集成测试：Research Metrics 端到端流程")
    print("=" * 80)
    
    # Step 1: 创建collector
    print("\n[Step 1] 创建 MetricsCollector...")
    collector = MetricsCollector()
    print("✅ Collector已创建")
    
    # Step 2: 设置基本信息
    print("\n[Step 2] 设置研究基本信息...")
    collector.metrics.query = "人工智能在医疗领域的应用"
    collector.metrics.total_sections = 4
    collector.metrics.total_sources = 24
    collector.metrics.total_reflections = 4
    print(f"  查询: {collector.metrics.query}")
    print(f"  章节: {collector.metrics.total_sections}")
    print(f"  来源: {collector.metrics.total_sources}")
    
    # Step 3: 模拟时间数据
    print("\n[Step 3] 记录各阶段耗时...")
    times = {
        "结构生成": 6.3,
        "初始搜索": 38.5,
        "反思迭代": 42.2,
        "报告生成": 7.8,
    }
    collector.metrics.time_metrics.structure_generation_time = times["结构生成"]
    collector.metrics.time_metrics.search_time = times["初始搜索"]
    collector.metrics.time_metrics.reflection_time = times["反思迭代"]
    collector.metrics.time_metrics.report_generation_time = times["报告生成"]
    
    for phase, duration in times.items():
        print(f"  {phase}: {duration:.1f}s")
    
    # Step 4: 记录token使用
    print("\n[Step 4] 记录Token使用...")
    collector.add_token_usage("deepseek", 4000, 3000, 0.112)  # 结构和初始搜索
    collector.add_token_usage("deepseek", 5200, 3800, 0.145)  # 反思
    collector.add_token_usage("deepseek", 2100, 1500, 0.057)  # 报告
    
    print(f"  总Token: {collector.metrics.token_metrics.total_tokens}")
    print(f"  总成本(USD): ${collector.metrics.token_metrics.total_cost_usd:.4f}")
    print(f"  总成本(RMB): ¥{collector.metrics.token_metrics.total_cost_rmb:.2f}")
    
    # Step 5: 计算搜索质量指标
    print("\n[Step 5] 计算搜索质量指标...")
    # 模拟24个搜索结果的相关性评分
    relevances = [
        1.0, 1.0, 0.95, 0.92,      # 最相关的4个
        0.85, 0.82, 0.80, 0.78,    # 较相关的4个
        0.72, 0.68, 0.65, 0.60,    # 中等相关的4个
        0.55, 0.50, 0.45, 0.40,    # 略相关的4个
        0.35, 0.30, 0.25, 0.20,    # 弱相关的4个
        0.15, 0.12, 0.08, 0.05,    # 极弱相关的4个
    ]
    
    calculator = MetricsCalculator()
    
    # 计算所有指标
    collector.metrics.search_quality.ndcg = calculator.calculate_ndcg(relevances, k=10)
    collector.metrics.search_quality.mrr = calculator.calculate_mrr(relevances, threshold=0.5)
    collector.metrics.search_quality.map_score = calculator.calculate_map(relevances)
    collector.metrics.search_quality.bpref = calculator.calculate_bpref(relevances)
    collector.metrics.search_quality.precision_at_1 = calculator.calculate_precision_at_k(relevances, k=1)
    collector.metrics.search_quality.precision_at_3 = calculator.calculate_precision_at_k(relevances, k=3)
    collector.metrics.search_quality.precision_at_5 = calculator.calculate_precision_at_k(relevances, k=5)
    collector.metrics.search_quality.precision_at_10 = calculator.calculate_precision_at_k(relevances, k=10)
    collector.metrics.search_quality.avg_relevance = sum(relevances) / len(relevances)
    collector.metrics.search_quality.unique_sources = 24
    collector.metrics.search_quality.source_diversity = 0.92
    collector.metrics.search_quality.coverage_score = 0.88
    collector.metrics.search_quality.total_searches = len(relevances)
    
    print(f"  NDCG@10: {collector.metrics.search_quality.ndcg:.4f}")
    print(f"  MRR: {collector.metrics.search_quality.mrr:.4f}")
    print(f"  MAP: {collector.metrics.search_quality.map_score:.4f}")
    print(f"  平均相关性: {collector.metrics.search_quality.avg_relevance:.4f}")
    print(f"  P@1: {collector.metrics.search_quality.precision_at_1:.4f}")
    print(f"  P@3: {collector.metrics.search_quality.precision_at_3:.4f}")
    print(f"  P@5: {collector.metrics.search_quality.precision_at_5:.4f}")
    print(f"  P@10: {collector.metrics.search_quality.precision_at_10:.4f}")
    
    # Step 6: 完成metrics收集
    print("\n[Step 6] 完成metrics收集...")
    collector.finalize()
    print(f"  综合评分: {collector.metrics.overall_score:.2f}/100")
    
    # Step 7: 生成可视化
    print("\n[Step 7] 生成HTML可视化仪表板...")
    visualizer = MetricsVisualizer()
    html_dashboard = visualizer.generate_html_dashboard(collector.metrics, language="ZH")
    
    with open("metrics_complete_test.html", "w", encoding="utf-8") as f:
        f.write(html_dashboard)
    print(f"✅ HTML已生成: metrics_complete_test.html ({len(html_dashboard) / 1024:.1f}KB)")
    
    # Step 8: 导出JSON
    print("\n[Step 8] 导出JSON数据...")
    json_data = collector.metrics.to_json()
    
    with open("metrics_complete_test.json", "w", encoding="utf-8") as f:
        f.write(json_data)
    print(f"✅ JSON已生成: metrics_complete_test.json ({len(json_data) / 1024:.1f}KB)")
    
    # Step 9: 验证所有指标
    print("\n[Step 9] 验证数据完整性...")
    checks = {
        "时间数据": collector.metrics.time_metrics.structure_generation_time > 0,
        "Token数据": collector.metrics.token_metrics.total_tokens > 0,
        "成本数据": collector.metrics.token_metrics.total_cost_usd > 0,
        "NDCG指标": collector.metrics.search_quality.ndcg > 0,
        "MRR指标": collector.metrics.search_quality.mrr > 0,
        "MAP指标": collector.metrics.search_quality.map_score > 0,
        "平均相关性": collector.metrics.search_quality.avg_relevance > 0,
        "源多样性": collector.metrics.search_quality.unique_sources > 0,
        "覆盖范围": collector.metrics.search_quality.coverage_score > 0,
        "综合评分": collector.metrics.overall_score > 0,
    }
    
    all_pass = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}: {result}")
        if not result:
            all_pass = False
    
    # 总结
    print("\n" + "=" * 80)
    if all_pass:
        print("✅ 所有测试通过！Metrics系统工作正常。")
    else:
        print("❌ 部分测试失败，请检查数据。")
    print("=" * 80)
    
    # 显示完整的metrics摘要
    print("\n📊 完整 Metrics 摘要:")
    print("-" * 80)
    print(f"查询: {collector.metrics.query}")
    print(f"\n⏱️ 时间消耗 (总计: {collector.metrics.time_metrics.total_time:.2f}s):")
    print(f"   • 结构生成: {collector.metrics.time_metrics.structure_generation_time:.1f}s")
    print(f"   • 搜索耗时: {collector.metrics.time_metrics.search_time:.1f}s")
    print(f"   • 反思耗时: {collector.metrics.time_metrics.reflection_time:.1f}s")
    print(f"   • 报告生成: {collector.metrics.time_metrics.report_generation_time:.1f}s")
    
    print(f"\n💰 成本统计 (总计: ${collector.metrics.token_metrics.total_cost_usd:.4f}):")
    print(f"   • 总Token: {collector.metrics.token_metrics.total_tokens:,}")
    print(f"   • USD成本: ${collector.metrics.token_metrics.total_cost_usd:.4f}")
    print(f"   • CNY成本: ¥{collector.metrics.token_metrics.total_cost_rmb:.2f}")
    
    print(f"\n🎯 搜索质量指标:")
    print(f"   • NDCG@10: {collector.metrics.search_quality.ndcg:.4f}")
    print(f"   • MRR: {collector.metrics.search_quality.mrr:.4f}")
    print(f"   • MAP: {collector.metrics.search_quality.map_score:.4f}")
    print(f"   • BPref: {collector.metrics.search_quality.bpref:.4f}")
    print(f"   • 平均相关性: {collector.metrics.search_quality.avg_relevance:.4f}")
    print(f"   • 源多样性: {collector.metrics.search_quality.source_diversity:.4f}")
    print(f"   • 覆盖范围: {collector.metrics.search_quality.coverage_score:.4f}")
    
    print(f"\n📈 资源统计:")
    print(f"   • 总章节: {collector.metrics.total_sections}")
    print(f"   • 总来源: {collector.metrics.total_sources}")
    print(f"   • 总反思: {collector.metrics.total_reflections}")
    
    print(f"\n⭐ 综合评分: {collector.metrics.overall_score:.2f}/100")
    print("-" * 80)


if __name__ == "__main__":
    try:
        test_complete_workflow()
        print("\n✨ 测试完成！您可以打开 metrics_complete_test.html 在浏览器查看可视化。\n")
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
