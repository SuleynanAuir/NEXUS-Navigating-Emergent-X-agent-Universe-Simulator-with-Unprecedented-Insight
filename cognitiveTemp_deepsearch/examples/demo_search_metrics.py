"""
搜索质量评估演示脚本
展示如何使用搜索质量评估功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.search_metrics import SearchQualityEvaluator, calculate_search_quality


def demo_basic_metrics():
    """演示基础质量指标计算"""
    print("\n" + "="*80)
    print("📊 搜索质量评估演示 - 基础指标")
    print("="*80 + "\n")
    
    # 模拟两组搜索结果：优化前和优化后
    print("🔍 场景：比较搜索优化前后的效果\n")
    
    # 优化前：结果相关性分散
    results_before = [
        {"title": "相关度高的结果", "url": "https://example.com/1", "credibility_score": 0.85},
        {"title": "相关度中等的结果", "url": "https://example.com/2", "credibility_score": 0.65},
        {"title": "相关度低的结果", "url": "https://example.com/3", "credibility_score": 0.40},
        {"title": "不相关的结果", "url": "https://example.com/4", "credibility_score": 0.25},
        {"title": "相关度一般的结果", "url": "https://example.com/5", "credibility_score": 0.55},
    ]
    
    # 优化后：结果相关性更集中在前面
    results_after = [
        {"title": "高质量相关结果", "url": "https://example.com/1", "credibility_score": 0.95},
        {"title": "优质相关结果", "url": "https://example.com/2", "credibility_score": 0.88},
        {"title": "良好相关结果", "url": "https://example.com/3", "credibility_score": 0.78},
        {"title": "中等相关结果", "url": "https://example.com/4", "credibility_score": 0.62},
        {"title": "一般相关结果", "url": "https://example.com/5", "credibility_score": 0.48},
    ]
    
    # 创建评估器
    evaluator = SearchQualityEvaluator(relevance_threshold=0.5)
    
    # 评估优化前
    print("📉 优化前的搜索结果质量:")
    print("-" * 80)
    metrics_before = evaluator.evaluate(results_before, score_key='credibility_score')
    print(metrics_before)
    
    print("\n" + "="*80 + "\n")
    
    # 评估优化后
    print("📈 优化后的搜索结果质量:")
    print("-" * 80)
    metrics_after = evaluator.evaluate(results_after, score_key='credibility_score')
    print(metrics_after)
    
    # 对比报告
    print("\n" + "="*80)
    comparison = evaluator.compare_results(
        results_before,
        results_after,
        label_a="优化前",
        label_b="优化后"
    )
    print(comparison)


def demo_quality_interpretation():
    """演示各指标的含义和解读"""
    print("\n" + "="*80)
    print("📚 搜索质量指标解读")
    print("="*80 + "\n")
    
    explanations = {
        "NDCG (归一化折损累积增益)": {
            "说明": "考虑结果排序位置的质量指标，越高越好",
            "范围": "0.0 - 1.0",
            "解读": {
                "0.9-1.0": "优秀 - 最相关的结果排在最前面",
                "0.7-0.9": "良好 - 相关结果排序合理",
                "0.5-0.7": "中等 - 排序有优化空间",
                "<0.5": "较差 - 需要改进搜索算法"
            }
        },
        "MRR (平均倒数排名)": {
            "说明": "第一个相关结果出现的位置，越高越好",
            "范围": "0.0 - 1.0",
            "解读": {
                "1.0": "完美 - 第一个结果就是相关的",
                "0.5": "第二个结果是相关的",
                "0.33": "第三个结果是相关的",
                "0.0": "没有找到相关结果"
            }
        },
        "Precision@K": {
            "说明": "前K个结果中相关结果的比例",
            "范围": "0.0 - 1.0",
            "解读": {
                "P@1 = 1.0": "第一个结果相关",
                "P@3 = 0.67": "前3个中有2个相关",
                "P@5 = 0.6": "前5个中有3个相关",
                "P@10 = 0.5": "前10个中有5个相关"
            }
        },
        "平均相关性分数": {
            "说明": "所有结果的平均质量分数",
            "范围": "0.0 - 1.0",
            "解读": {
                ">0.7": "整体质量高",
                "0.5-0.7": "质量中等",
                "<0.5": "质量偏低"
            }
        }
    }
    
    for metric_name, info in explanations.items():
        print(f"📌 {metric_name}")
        print(f"   说明: {info['说明']}")
        print(f"   范围: {info['范围']}")
        print(f"   解读:")
        for level, desc in info['解读'].items():
            print(f"      • {level}: {desc}")
        print()


def demo_real_world_scenario():
    """演示真实场景应用"""
    print("\n" + "="*80)
    print("🌐 真实场景演示：新闻搜索质量评估")
    print("="*80 + "\n")
    
    # 模拟搜索"人工智能最新进展"的结果
    print("查询: '人工智能最新进展'\n")
    
    search_results = [
        {
            "title": "2024年AI重大突破：GPT-5发布",
            "url": "https://techcrunch.com/ai-breakthrough-2024",
            "credibility_score": 0.92,
            "source": "techcrunch.com"
        },
        {
            "title": "深度学习在医疗诊断中的应用",
            "url": "https://nature.com/ai-medical-diagnosis",
            "credibility_score": 0.88,
            "source": "nature.com"
        },
        {
            "title": "机器学习算法优化新方法",
            "url": "https://arxiv.org/ml-optimization",
            "credibility_score": 0.75,
            "source": "arxiv.org"
        },
        {
            "title": "AI在自动驾驶中的最新进展",
            "url": "https://medium.com/self-driving-ai",
            "credibility_score": 0.68,
            "source": "medium.com"
        },
        {
            "title": "人工智能入门教程",
            "url": "https://blog.example.com/ai-tutorial",
            "credibility_score": 0.45,
            "source": "blog.example.com"
        },
        {
            "title": "AI相关产品广告",
            "url": "https://ads.example.com/ai-product",
            "credibility_score": 0.20,
            "source": "ads.example.com"
        }
    ]
    
    # 评估质量
    evaluator = SearchQualityEvaluator(relevance_threshold=0.5)
    metrics = evaluator.evaluate(search_results, score_key='credibility_score')
    
    print("📊 搜索结果质量评估:")
    print("-" * 80)
    print(metrics)
    
    print("\n" + "="*80)
    print("💡 评估结论:")
    print("="*80)
    
    # 根据指标给出建议
    ndcg = metrics.ndcg
    mrr = metrics.mrr
    p_at_3 = metrics.precision_at_k.get(3, 0)
    
    if ndcg > 0.8 and mrr > 0.8:
        print("✅ 搜索质量优秀！")
        print("   - 最相关的结果排在前面")
        print("   - 用户能快速找到需要的信息")
    elif ndcg > 0.6:
        print("⚠️  搜索质量良好，有提升空间")
        print("   - 建议优化结果排序算法")
        print("   - 可以提高内容质量过滤标准")
    else:
        print("❌ 搜索质量需要改进")
        print("   - 建议启用搜索增强功能")
        print("   - 增加来源可信度过滤")
        print("   - 提高内容质量评分阈值")
    
    print(f"\n具体建议:")
    if mrr < 0.5:
        print(f"   • MRR={mrr:.2f}较低，建议优化结果排序，让最相关结果排在最前")
    if p_at_3 < 0.67:
        print(f"   • Precision@3={p_at_3:.2f}，建议提高前3个结果的相关性")
    if metrics.relevance_score < 0.6:
        print(f"   • 平均相关性={metrics.relevance_score:.2f}，建议提高整体结果质量")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🎯 Deep Search Agent - 搜索质量评估系统")
    print("="*80)
    
    # 运行各种演示
    demo_basic_metrics()
    demo_quality_interpretation()
    demo_real_world_scenario()
    
    print("\n" + "="*80)
    print("✨ 演示完成！")
    print("="*80 + "\n")
    
    print("💡 提示：")
    print("   在实际使用中，这些指标会自动集成到搜索流程中")
    print("   可以通过配置文件开启：ENABLE_QUALITY_METRICS = True")
    print("   搜索时会自动显示质量评估信息\n")


if __name__ == "__main__":
    main()
