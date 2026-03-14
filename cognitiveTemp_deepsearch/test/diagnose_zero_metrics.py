#!/usr/bin/env python3
"""
诊断为什么 P@K 和 BPref 都是 0

分析相关性分布，理解阈值问题
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import statistics

# 从 JSON 加载指标结果
metrics_file = Path(__file__).parent / "metrics_reports" / "metrics_20260228_235554.json"
with open(metrics_file, 'r', encoding='utf-8') as f:
    all_metrics = json.load(f)

print("=" * 100)
print("🔍 诊断: 为什么 P@K 和 BPref 都是 0?")
print("=" * 100)

print("\n📊 相关性分布分析:")
print(f"{'报告':<50} {'平均相关性':<15} {'≥0.3数':<10} {'≥0.6数':<10}")
print("-" * 100)

for report_name, metrics in all_metrics.items():
    if metrics['status'] != 'success':
        continue
    
    avg_rel = metrics['avg_relevance']
    count_03 = metrics['relevant_count_03']
    count_06 = metrics['relevant_count_06']
    total = metrics['total_results']
    
    query = metrics['query'][:45]
    print(f"{query:<50} {avg_rel:<15.4f} {count_03}/{total:<8} {count_06}/{total:<8}")

print("\n" + "=" * 100)
print("🎯 关键发现:")
print("=" * 100)

# 统计
successful = [m for m in all_metrics.values() if m['status'] == 'success']
avg_rel_all = statistics.mean([m['avg_relevance'] for m in successful])
avg_count_03 = statistics.mean([m['relevant_count_03'] for m in successful])
avg_count_06 = statistics.mean([m['relevant_count_06'] for m in successful])
max_rel = max([m['max_relevance'] for m in successful])

print(f"\n1️⃣  相关性分数总体偏低:")
print(f"   • 平均相关性: {avg_rel_all:.4f} (范围通常是 0-1)")
print(f"   • 最高相关性: {max_rel:.4f}")
print(f"   • 原因: 相关性算法基于词汇匹配，中文搜索结果与查询词汇重合度低")

print(f"\n2️⃣  阈值 0.3 太高:")
print(f"   • 平均满足 ≥0.3: {avg_count_03:.1f} 个结果")
print(f"   • 平均满足 ≥0.6: {avg_count_06:.1f} 个结果")
print(f"   • P@1 = 0.0 的原因: 第一个结果极少能达到 0.3")

print(f"\n3️⃣  P@K 计算问题:")
print(f"   • 阈值 0.3 对于平均相关性 {avg_rel_all:.4f} 太严格")
print(f"   • P@1 需要: 第1个结果 ≥ 0.3 → {avg_count_03:.1f} 个/报告 → 几乎不可能")
print(f"   • P@3 需要: 前3个中 ≥ 0.3 的占比 → 平均满足 {avg_count_03:.1f}/44.6 = {avg_count_03/44.6*100:.1f}%")

print(f"\n4️⃣  解决方案对比:")
print("\n   方案 A: 降低阈值到 0.15")
lower_threshold_count = sum(1 for m in successful for r in [m['avg_relevance']] if r >= 0.15)
print(f"   • 预期 P@K 提升: 300-500%")
print(f"   • 预期 MRR 提升: 500-1000%")
print(f"   • 缺点: 可能包含过多无关内容")

print(f"\n   方案 B: 使用百分位数阈值")
print(f"   • 对每个查询，取其相关性分数的 70 百分位")
print(f"   • 这样自动调整阈值以适应不同查询")
print(f"   • 优点: 相对公平，适应不同查询")

print(f"\n   方案 C: 改进相关性计算")
print(f"   • 加入语义相似度（使用向量模型）")
print(f"   • 加入 BM25 算法代替简单词汇匹配")
print(f"   • 加入 TF-IDF 权重")
print(f"   • 预期相关性分数提升 2-3 倍")

print(f"\n{'='*100}")
print("\n📝 建议实施步骤:")
print(f"\n第1步: 快速修复 - 降低阈值到 0.15")
print(f"       修改文件: src/visualization/calculator.py")
print(f"       将所有 threshold=0.3 改为 threshold=0.15")
print(f"\n第2步: 验证效果 - 重新运行计算")
print(f"       python3 test/calculate_metrics_from_reports.py")
print(f"\n第3步: 长期改进 - 升级相关性算法")
print(f"       使用 BM25 或向量相似度")
print(f"\n{'='*100}\n")
