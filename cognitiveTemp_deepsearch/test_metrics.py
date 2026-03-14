#!/usr/bin/env python3
"""
测试脚本：验证metrics收集、计算和可视化的完整流程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.visualization import (
    MetricsCollector, MetricsVisualizer, MetricsCalculator,
    TokenPricingCalculator, ResearchMetrics
)
from datetime import datetime


def test_metrics_collection():
    """测试metrics收集"""
    print("=" * 60)
    print("测试 1: Metrics 收集")
    print("=" * 60)
    
    collector = MetricsCollector()
    
    # 模拟计时
    collector.start_timer("report_structure")
    import time
    time.sleep(0.1)
    collector.end_timer("report_structure")
    
    collector.start_timer("search")
    time.sleep(0.2)
    collector.end_timer("search")
    
    collector.start_timer("reflection")
    time.sleep(0.15)
    collector.end_timer("reflection")
    
    print(f"✅ 报告结构耗时: {collector.metrics.time_metrics.structure_generation_time:.2f}s")
    print(f"✅ 搜索耗时: {collector.metrics.time_metrics.search_time:.2f}s")
    print(f"✅ 反思耗时: {collector.metrics.time_metrics.reflection_time:.2f}s")
    print()


def test_token_calculation():
    """测试token计算"""
    print("=" * 60)
    print("测试 2: Token 计算")
    print("=" * 60)
    
    collector = MetricsCollector()
    
    # 添加DeepSeek token使用
    collector.add_token_usage("deepseek", prompt_tokens=500, completion_tokens=300, cost_usd=0.0112)
    collector.add_token_usage("deepseek", prompt_tokens=800, completion_tokens=400, cost_usd=0.0168)
    
    # 添加OpenAI token使用
    collector.add_token_usage("openai", prompt_tokens=200, completion_tokens=150, cost_usd=0.0015)
    
    print(f"✅ 总Token数: {collector.metrics.token_metrics.total_tokens}")
    print(f"✅ DeepSeek Token: {collector.metrics.token_metrics.deepseek_tokens}")
    print(f"✅ OpenAI Token: {collector.metrics.token_metrics.openai_tokens}")
    print(f"✅ 总成本(USD): ${collector.metrics.token_metrics.total_cost_usd:.4f}")
    print(f"✅ 总成本(RMB): ¥{collector.metrics.token_metrics.total_cost_rmb:.2f}")
    print()


def test_search_quality_metrics():
    """测试搜索质量指标"""
    print("=" * 60)
    print("测试 3: 搜索质量指标计算")
    print("=" * 60)
    
    calculator = MetricsCalculator()
    
    # 模拟相关性评分（1=高相关，0=不相关）
    relevances = [1, 1, 0.8, 0.6, 0.4, 0.2, 0, 0, 0, 0]
    
    ndcg = calculator.calculate_ndcg(relevances)
    mrr = calculator.calculate_mrr(relevances)
    map_score = calculator.calculate_map(relevances)
    bpref = calculator.calculate_bpref(relevances)
    
    p_at_1 = calculator.calculate_precision_at_k(relevances, k=1)
    p_at_3 = calculator.calculate_precision_at_k(relevances, k=3)
    p_at_5 = calculator.calculate_precision_at_k(relevances, k=5)
    p_at_10 = calculator.calculate_precision_at_k(relevances, k=10)
    
    print(f"✅ NDCG: {ndcg:.4f}")
    print(f"✅ MRR: {mrr:.4f}")
    print(f"✅ MAP: {map_score:.4f}")
    print(f"✅ BPref: {bpref:.4f}")
    print(f"✅ Precision@1: {p_at_1:.4f}")
    print(f"✅ Precision@3: {p_at_3:.4f}")
    print(f"✅ Precision@5: {p_at_5:.4f}")
    print(f"✅ Precision@10: {p_at_10:.4f}")
    print()


def test_token_pricing():
    """测试token定价"""
    print("=" * 60)
    print("测试 4: Token 定价")
    print("=" * 60)
    
    calculator = TokenPricingCalculator()
    
    # 测试DeepSeek
    cost_deepseek = calculator.calculate_cost_usd("deepseek", "deepseek-chat", 1000, 500)
    print(f"✅ DeepSeek (1000 prompt + 500 completion): ${cost_deepseek:.4f}")
    
    # 测试OpenAI
    cost_openai = calculator.calculate_cost_usd("openai", "gpt-4o-mini", 1000, 500)
    print(f"✅ OpenAI gpt-4o-mini (1000 prompt + 500 completion): ${cost_openai:.4f}")
    
    # 测试多币种
    cost_rmb, currency_rmb = calculator.calculate_cost("deepseek", "deepseek-chat", 1000, 500, "CNY")
    print(f"✅ DeepSeek in {currency_rmb}: {cost_rmb:.2f}")
    
    print()


def test_metrics_visualization():
    """测试metrics可视化"""
    print("=" * 60)
    print("测试 5: Metrics 可视化")
    print("=" * 60)
    
    # 创建完整的metrics对象
    collector = MetricsCollector()
    collector.metrics.query = "AI development trends 2026"
    collector.metrics.total_sections = 3
    collector.metrics.total_sources = 12
    collector.metrics.total_reflections = 3
    
    # 添加时间指标
    collector.metrics.time_metrics.structure_generation_time = 5.2
    collector.metrics.time_metrics.search_time = 45.8
    collector.metrics.time_metrics.reflection_time = 32.5
    collector.metrics.time_metrics.report_generation_time = 8.3
    collector.metrics.time_metrics.total_time = 91.8
    
    # 添加token指标
    collector.metrics.token_metrics.total_tokens = 8500
    collector.metrics.token_metrics.prompt_tokens = 5200
    collector.metrics.token_metrics.completion_tokens = 3300
    collector.metrics.token_metrics.deepseek_tokens = 5000
    collector.metrics.token_metrics.deepseek_cost_usd = 0.14
    collector.metrics.token_metrics.total_cost_usd = 0.14
    collector.metrics.token_metrics.total_cost_rmb = 0.98
    
    # 添加搜索质量指标
    relevances = [1, 1, 0.8, 0.6, 0.4, 0.2, 0.1, 0.05, 0, 0, 0, 0]
    calculator = MetricsCalculator()
    
    collector.metrics.search_quality.ndcg = calculator.calculate_ndcg(relevances)
    collector.metrics.search_quality.mrr = calculator.calculate_mrr(relevances)
    collector.metrics.search_quality.map_score = calculator.calculate_map(relevances)
    collector.metrics.search_quality.bpref = calculator.calculate_bpref(relevances)
    collector.metrics.search_quality.precision_at_1 = calculator.calculate_precision_at_k(relevances, k=1)
    collector.metrics.search_quality.precision_at_3 = calculator.calculate_precision_at_k(relevances, k=3)
    collector.metrics.search_quality.precision_at_5 = calculator.calculate_precision_at_k(relevances, k=5)
    collector.metrics.search_quality.precision_at_10 = calculator.calculate_precision_at_k(relevances, k=10)
    collector.metrics.search_quality.avg_relevance = sum(relevances) / len(relevances)
    collector.metrics.search_quality.unique_sources = 12
    collector.metrics.search_quality.source_diversity = 0.85
    collector.metrics.search_quality.coverage_score = 0.90
    collector.metrics.search_quality.total_searches = len(relevances)
    
    # 计算综合评分
    collector.metrics.calculate_overall_score()
    
    # 生成HTML
    visualizer = MetricsVisualizer()
    html_dashboard = visualizer.generate_html_dashboard(collector.metrics, language="ZH")
    
    # 保存HTML
    output_file = "/tmp/metrics_test.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_dashboard)
    
    print(f"✅ Metrics Dashboard HTML 已生成: {output_file}")
    print(f"✅ 总体评分: {collector.metrics.overall_score:.2f}/100")
    print()


def test_complete_workflow():
    """测试完整工作流"""
    print("=" * 60)
    print("测试 6: 完整工作流")
    print("=" * 60)
    
    collector = MetricsCollector()
    collector.metrics.query = "Test Query"
    
    # 模拟完整流程
    collector.start_timer("report_structure")
    import time
    time.sleep(0.05)
    elapsed = collector.end_timer("report_structure")
    print(f"✅ 报告结构: {elapsed:.3f}s")
    
    collector.start_timer("search")
    time.sleep(0.1)
    elapsed = collector.end_timer("search")
    print(f"✅ 搜索: {elapsed:.3f}s")
    
    collector.add_token_usage("deepseek", 1000, 500, 0.021)
    print(f"✅ Token已记录")
    
    collector.finalize()
    
    # 输出JSON
    import json
    metrics_json = collector.metrics.to_json()
    print(f"✅ Metrics JSON 生成成功 ({len(metrics_json)} 字节)")
    
    # 验证数据
    metrics_dict = json.loads(metrics_json)
    assert metrics_dict["query"] == "Test Query"
    assert metrics_dict["time_metrics"]["total_time"] > 0
    assert metrics_dict["token_metrics"]["total_tokens"] == 1500
    print("✅ 数据验证通过")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Deep Search Agent - Metrics 完整测试套件")
    print("=" * 60 + "\n")
    
    try:
        test_metrics_collection()
        test_token_calculation()
        test_search_quality_metrics()
        test_token_pricing()
        test_metrics_visualization()
        test_complete_workflow()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
