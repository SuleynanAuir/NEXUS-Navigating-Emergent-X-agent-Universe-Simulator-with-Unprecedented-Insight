#!/usr/bin/env python3
"""
Pre-flight checks for DeepSearch Agent Streamlit app
验证metrics系统的完整性和正确性
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.visualization import (
    MetricsCollector, 
    MetricsVisualizer, 
    MetricsCalculator,
    TokenPricingCalculator
)

def check_imports():
    """检查所有必要的导入"""
    print("✓ 所有Python模块导入成功")
    return True

def check_metrics_collector():
    """检查MetricsCollector功能"""
    try:
        collector = MetricsCollector()
        assert hasattr(collector, 'metrics')
        assert hasattr(collector, 'start_timer')
        assert hasattr(collector, 'end_timer')
        assert hasattr(collector, 'add_token_usage')
        assert hasattr(collector, 'finalize')
        print("✓ MetricsCollector工作正常")
        return True
    except Exception as e:
        print(f"✗ MetricsCollector错误: {e}")
        return False

def check_metrics_calculator():
    """检查MetricsCalculator功能"""
    try:
        calculator = MetricsCalculator()
        test_relevances = [1, 0.9, 0.8, 0.7, 0.6]
        
        ndcg = calculator.calculate_ndcg(test_relevances)
        assert 0 <= ndcg <= 1, f"NDCG应在0-1之间，得到{ndcg}"
        
        mrr = calculator.calculate_mrr(test_relevances)
        assert 0 <= mrr <= 1, f"MRR应在0-1之间，得到{mrr}"
        
        map_score = calculator.calculate_map(test_relevances)
        assert 0 <= map_score <= 1, f"MAP应在0-1之间，得到{map_score}"
        
        print("✓ MetricsCalculator工作正常")
        return True
    except Exception as e:
        print(f"✗ MetricsCalculator错误: {e}")
        return False

def check_token_pricing():
    """检查TokenPricingCalculator功能"""
    try:
        calc = TokenPricingCalculator()
        
        # 测试DeepSeek
        cost_ds = calc.calculate_cost_usd("deepseek", "deepseek-chat", 1000, 500)
        assert cost_ds > 0, "DeepSeek成本应大于0"
        
        # 测试OpenAI
        cost_oa = calc.calculate_cost_usd("openai", "gpt-4o-mini", 1000, 500)
        assert cost_oa > 0, "OpenAI成本应大于0"
        
        # 测试多币种
        cost_cny, currency = calc.calculate_cost("deepseek", "deepseek-chat", 1000, 500, "CNY")
        assert currency == "CNY", f"货币应为CNY，得到{currency}"
        assert cost_cny > 0, "CNY成本应大于0"
        
        print("✓ TokenPricingCalculator工作正常")
        return True
    except Exception as e:
        print(f"✗ TokenPricingCalculator错误: {e}")
        return False

def check_metrics_visualizer():
    """检查MetricsVisualizer功能"""
    try:
        visualizer = MetricsVisualizer()
        
        # 创建测试metrics
        collector = MetricsCollector()
        collector.metrics.query = "Test Query"
        collector.metrics.total_sections = 2
        collector.metrics.search_quality.ndcg = 0.85
        collector.metrics.search_quality.mrr = 0.90
        collector.metrics.token_metrics.total_tokens = 1000
        collector.metrics.token_metrics.total_cost_usd = 0.05
        
        # 生成HTML
        html = visualizer.generate_html_dashboard(collector.metrics, language="ZH")
        assert isinstance(html, str), "HTML应为字符串"
        assert len(html) > 1000, "HTML应有足够的内容"
        # 检查关键元素（可能是HTML片段而不是完整文档）
        assert "research-metrics-dashboard" in html or "NDCG" in html or "ndcg" in html, "HTML应包含metrics内容"
        
        print("✓ MetricsVisualizer工作正常")
        return True
    except Exception as e:
        print(f"✗ MetricsVisualizer错误: {e}")
        return False

def check_complete_workflow():
    """检查完整工作流"""
    try:
        # 创建collector
        collector = MetricsCollector()
        
        # 设置基本信息
        collector.metrics.query = "测试查询"
        collector.metrics.total_sections = 2
        collector.metrics.total_sources = 5
        
        # 模拟时间
        collector.start_timer("test1")
        import time
        time.sleep(0.1)
        elapsed = collector.end_timer("test1")
        assert elapsed > 0, "计时器应记录正数"
        
        # 模拟token
        collector.add_token_usage("deepseek", 1000, 500, 0.042)
        assert collector.metrics.token_metrics.total_tokens == 1500
        
        # 模拟质量指标
        relevances = [1, 0.9, 0.8, 0.7, 0.6]
        calc = MetricsCalculator()
        collector.metrics.search_quality.ndcg = calc.calculate_ndcg(relevances)
        collector.metrics.search_quality.avg_relevance = sum(relevances) / len(relevances)
        
        # 完成
        collector.finalize()
        assert collector.metrics.overall_score > 0
        
        # 生成可视化
        visualizer = MetricsVisualizer()
        html = visualizer.generate_html_dashboard(collector.metrics, language="ZH")
        assert len(html) > 1000
        
        print("✓ 完整工作流验证通过")
        return True
    except Exception as e:
        print(f"✗ 完整工作流错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有检查"""
    print("\n" + "=" * 70)
    print("🔍 DeepSearch Agent - Metrics 系统预检查")
    print("=" * 70)
    print()
    
    checks = [
        ("Python模块导入", check_imports),
        ("MetricsCollector", check_metrics_collector),
        ("MetricsCalculator", check_metrics_calculator),
        ("TokenPricingCalculator", check_token_pricing),
        ("MetricsVisualizer", check_metrics_visualizer),
        ("完整工作流", check_complete_workflow),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"✗ {name}检查失败: {e}")
            results.append(False)
    
    print()
    print("=" * 70)
    if all(results):
        print(f"✅ 所有检查通过！({len(results)}/{len(results)})")
        print("=" * 70)
        print()
        print("您现在可以安全启动Streamlit应用：")
        print("  ./run_streamlit.sh")
        print()
        return 0
    else:
        passed = sum(results)
        total = len(results)
        print(f"❌ 部分检查失败 ({passed}/{total})")
        print("=" * 70)
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
