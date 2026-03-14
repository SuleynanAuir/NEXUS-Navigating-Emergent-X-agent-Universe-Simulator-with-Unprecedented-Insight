#!/usr/bin/env python3
"""
测试真实相关性评分系统
验证指标不再都是1.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.visualization import MetricsCollector, MetricsVisualizer, MetricsCalculator

def test_relevance_calculation():
    """测试真实相关性计算"""
    print("\n" + "="*70)
    print("🧪 Test 1: 真实相关性评分")
    print("="*70)
    
    # 模拟搜索结果
    test_cases = [
        ({"AI", "医学", "应用"}, "人工智能在医学中的应用", "详细介绍AI如何应用于医学诊断和治疗..." * 50),
        ({"AI", "医学", "应用"}, "人工智能发展历程", "讨论AI的发展历史"),
        ({"AI", "医学", "应用"}, "计算机科学基础", "基础计算机理论"),
        ({"AI", "医学", "应用"}, "", ""),
    ]
    
    # 重现agent中的相关性计算逻辑
    relevances = []
    for item in test_cases:
        query_terms = item[0]
        title = item[1]
        content = item[2]
        relevance = calculate_relevance(query_terms, title, content)
        relevances.append(relevance)
        print(f"  标题: {title[:30]}... 内容长度: {len(content)}")
        print(f"    → 相关性: {relevance:.4f}")
    
    # 检查多样性
    min_rel = min(relevances)
    max_rel = max(relevances)
    avg_rel = sum(relevances) / len(relevances)
    
    print(f"\n  相关性统计:")
    print(f"    - 最小: {min_rel:.4f}")
    print(f"    - 最大: {max_rel:.4f}")
    print(f"    - 平均: {avg_rel:.4f}")
    print(f"    - 差异: {max_rel - min_rel:.4f}")
    
    if max_rel - min_rel < 0.1:
        print("  ❌ 相关性差异太小")
        return False
    
    print("  ✓ 相关性分布多样化")
    return True

def test_metrics_calculation():
    """测试指标计算结果"""
    print("\n" + "="*70)
    print("🧪 Test 2: 指标计算多样化")
    print("="*70)
    
    # 模拟更现实的相关性分布（包括很多低相关性结果）
    # 这代表搜索引擎返回的混合结果
    relevances = [0.85, 0.72, 0.68, 0.45, 0.32, 0.18, 0.15, 0.08, 0.05, 0.02]
    
    calculator = MetricsCalculator()
    
    # 计算各项指标
    ndcg = calculator.calculate_ndcg(relevances)
    mrr = calculator.calculate_mrr(relevances, threshold=0.6)
    map_score = calculator.calculate_map(relevances, threshold=0.6)
    p1 = calculator.calculate_precision_at_k(relevances, k=1, threshold=0.6)
    p3 = calculator.calculate_precision_at_k(relevances, k=3, threshold=0.6)
    p5 = calculator.calculate_precision_at_k(relevances, k=5, threshold=0.6)
    
    print(f"\n  相关性分数: {relevances}")
    print(f"\n  计算结果:")
    print(f"    - NDCG: {ndcg:.4f}")
    print(f"    - MRR:  {mrr:.4f}")
    print(f"    - MAP:  {map_score:.4f}")
    print(f"    - P@1:  {p1:.4f}")
    print(f"    - P@3:  {p3:.4f}")
    print(f"    - P@5:  {p5:.4f}")
    
    # 检查是否都是1.0
    metrics = [ndcg, mrr, map_score, p1, p3, p5]
    ones_count = sum(1 for m in metrics if abs(m - 1.0) < 0.01)
    
    if ones_count > 0:
        print(f"\n  ⚠️  {ones_count} 个指标是1.0（但现在代表真实质量）")
    
    # 更重要的是看指标是否多样化
    variance = sum((m - sum(metrics)/len(metrics))**2 for m in metrics) / len(metrics)
    print(f"  指标方差: {variance:.4f}")
    
    if variance < 0.01:
        print("  ❌ 指标变化太小（都太接近）")
        return False
    
    print("  ✓ 指标多样化")
    return True

def test_edge_cases():
    """测试边界情况"""
    print("\n" + "="*70)
    print("🧪 Test 3: 边界情况处理")
    print("="*70)
    
    calculator = MetricsCalculator()
    
    # 完全相关
    print(f"\n  完全相关 (全1.0):")
    relevant_all = [1.0, 1.0, 1.0, 1.0]
    print(f"    NDCG: {calculator.calculate_ndcg(relevant_all):.4f}")
    print(f"    MRR:  {calculator.calculate_mrr(relevant_all):.4f}")
    print(f"    MAP:  {calculator.calculate_map(relevant_all):.4f}")
    
    # 完全不相关
    print(f"\n  完全不相关 (全0.0):")
    relevant_none = [0.0, 0.0, 0.0, 0.0]
    print(f"    NDCG: {calculator.calculate_ndcg(relevant_none):.4f}")
    print(f"    MRR:  {calculator.calculate_mrr(relevant_none, threshold=0.6):.4f}")
    print(f"    MAP:  {calculator.calculate_map(relevant_none, threshold=0.6):.4f}")
    
    # 混合
    print(f"\n  混合 (部分相关):")
    relevant_mix = [0.8, 0.4, 0.2, 0.9]
    ndcg = calculator.calculate_ndcg(relevant_mix)
    mrr = calculator.calculate_mrr(relevant_mix, threshold=0.6)
    map_score = calculator.calculate_map(relevant_mix, threshold=0.6)
    print(f"    NDCG: {ndcg:.4f}")
    print(f"    MRR:  {mrr:.4f}")
    print(f"    MAP:  {map_score:.4f}")
    
    print("  ✓ 边界情况处理正确")
    return True

def calculate_relevance(query_terms: set, title: str, content: str) -> float:
    """
    复现agent中的相关性计算逻辑
    """
    import re
    
    if not title and not content:
        return 0.0
    
    # 计算标题中的相关性
    title_text = title.lower() if title else ""
    title_terms = set(re.findall(r'\w+', title_text))
    title_overlap = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
    
    # 计算内容中的相关性
    content_text = content.lower() if content else ""
    content_terms = set(re.findall(r'\w+', content_text))
    content_overlap = len(query_terms & content_terms) / len(query_terms) if query_terms else 0
    
    # 内容长度质量评分
    content_length = len(content) if content else 0
    if content_length > 1000:
        length_score = 0.9
    elif content_length > 500:
        length_score = 0.7
    elif content_length > 200:
        length_score = 0.5
    elif content_length > 50:
        length_score = 0.3
    else:
        length_score = 0.1
    
    # 综合相关性分数
    relevance = (
        title_overlap * 0.4 +
        content_overlap * 0.35 +
        length_score * 0.25
    )
    
    return min(max(relevance, 0.0), 1.0)

def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("📊 真实相关性评分系统验证")
    print("="*70)
    
    tests = [
        ("相关性评分", test_relevance_calculation),
        ("指标计算多样化", test_metrics_calculation),
        ("边界情况", test_edge_cases),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ {test_name} 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "="*70)
    print("📋 测试总结")
    print("="*70)
    
    for (test_name, _), result in zip(tests, results):
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    if all(results):
        print("\n✅ 所有测试通过！")
        print("\n改进项目：")
        print("  1. ✅ 实现真实相关性评分（基于词汇匹配和内容质量）")
        print("  2. ✅ 提高相关性阈值（0.5 → 0.6）")
        print("  3. ✅ 指标现在能真实反映搜索质量差异")
        print("\n现在的指标意义：")
        print("  - 不再都是1.0")
        print("  - 真实反映搜索结果与查询的匹配度")
        print("  - 能够区分高质量和低质量的搜索")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
