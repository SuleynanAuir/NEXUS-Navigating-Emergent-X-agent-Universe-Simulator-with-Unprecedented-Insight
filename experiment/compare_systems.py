"""
对标分析工具：比较多个系统的指标，生成对标报告
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import argparse


def load_metrics(path: str) -> Dict[str, Any]:
    """加载指标 JSON 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_systems(
    system_metrics: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    比较多个系统的指标
    
    Args:
        system_metrics: {system_name: metrics_dict}
    
    Returns:
        对标报告
    """
    report = {
        "systems": list(system_metrics.keys()),
        "comparison": {},
        "rankings": {},
        "insights": []
    }
    
    # 获取所有维度
    all_dims = [
        "retrieval_quality",
        "kg_quality",
        "multi_agent_collaboration",
        "simulation_capability",
        "insight_quality"
    ]
    
    # 按维度对比
    for dim in all_dims:
        scores = {}
        for system_name, metrics in system_metrics.items():
            score = metrics.get("dimension_scores", {}).get(dim, 0.0)
            scores[system_name] = score
        
        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        report["comparison"][dim] = scores
        report["rankings"][dim] = [
            {"rank": i+1, "system": name, "score": score}
            for i, (name, score) in enumerate(ranked)
        ]
    
    # EIS 对比
    eis_scores = {}
    for system_name, metrics in system_metrics.items():
        eis = metrics.get("EIS", {}).get("score", 0.0)
        eis_scores[system_name] = eis
    
    ranked_eis = sorted(eis_scores.items(), key=lambda x: x[1], reverse=True)
    report["rankings"]["EIS"] = [
        {"rank": i+1, "system": name, "score": score}
        for i, (name, score) in enumerate(ranked_eis)
    ]
    
    # 生成洞察
    report["insights"] = _generate_insights(system_metrics, report)
    
    return report


def _generate_insights(
    system_metrics: Dict[str, Dict[str, Any]],
    report: Dict[str, Any]
) -> List[str]:
    """生成对标洞察"""
    insights = []
    
    # 总体排名
    best_system = report["rankings"]["EIS"][0]["system"]
    insights.append(f"🏆 综合评分最高：{best_system}")
    
    # 维度洞察
    all_dims = [
        "retrieval_quality",
        "kg_quality",
        "multi_agent_collaboration",
        "simulation_capability",
        "insight_quality"
    ]
    
    for dim in all_dims:
        rankings = report["rankings"][dim]
        best = rankings[0]
        insights.append(
            f"🥇 {dim}: {best['system']} ({best['score']:.4f})"
        )
    
    # 差异分析
    systems = list(system_metrics.keys())
    if len(systems) >= 2:
        scores_by_system = report["comparison"]["retrieval_quality"]
        max_system = max(scores_by_system, key=scores_by_system.get)
        min_system = min(scores_by_system, key=scores_by_system.get)
        gap = scores_by_system[max_system] - scores_by_system[min_system]
        insights.append(
            f"📊 检索质量差距：{gap:.4f} "
            f"({max_system} vs {min_system})"
        )
    
    return insights


def print_comparison_report(report: Dict[str, Any]) -> None:
    """打印对标报告"""
    print("=" * 70)
    print("📊 多系统对标分析报告")
    print("=" * 70)
    
    print(f"\n参与对标的系统：{', '.join(report['systems'])}")
    
    # 维度对比表格
    print("\n" + "=" * 70)
    print("📈 维度对标结果")
    print("=" * 70)
    
    all_dims = [
        "retrieval_quality",
        "kg_quality",
        "multi_agent_collaboration",
        "simulation_capability",
        "insight_quality"
    ]
    
    # 打印表头
    header = "维度".ljust(20) + "".join(f"{sys:>12}" for sys in report["systems"])
    print(header)
    print("-" * len(header))
    
    # 打印数据行
    for dim in all_dims:
        scores = report["comparison"][dim]
        row = dim.ljust(20)
        for system in report["systems"]:
            score = scores.get(system, 0.0)
            row += f"{score:>12.4f}"
        print(row)
    
    # EIS 对比
    print("\n" + "=" * 70)
    print("🎯 综合评分 (EIS) 对比")
    print("=" * 70)
    
    for rank_item in report["rankings"]["EIS"]:
        rank = rank_item["rank"]
        system = rank_item["system"]
        score = rank_item["score"]
        medal = ["🥇", "🥈", "🥉"][rank-1] if rank <= 3 else f"{rank}️⃣"
        print(f"{medal} {rank}. {system:20} {score:.4f}")
    
    # 逐维度排名
    print("\n" + "=" * 70)
    print("🏅 逐维度排名")
    print("=" * 70)
    
    for dim in all_dims:
        print(f"\n{dim}:")
        for rank_item in report["rankings"][dim][:3]:
            rank = rank_item["rank"]
            system = rank_item["system"]
            score = rank_item["score"]
            medal = ["🥇", "🥈", "🥉"][rank-1]
            print(f"  {medal} {system:20} {score:.4f}")
    
    # 洞察
    print("\n" + "=" * 70)
    print("💡 关键洞察")
    print("=" * 70)
    for insight in report["insights"]:
        print(f"• {insight}")
    
    print("\n" + "=" * 70)


def save_comparison_report(report: Dict[str, Any], output_path: str) -> None:
    """保存对标报告为 JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 对标报告已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="多系统指标对标分析")
    parser.add_argument(
        "--metrics",
        nargs="+",
        required=True,
        help="指标 JSON 文件路径列表 (可选标签: path:label)"
    )
    parser.add_argument(
        "--output",
        default="comparison_report.json",
        help="输出报告路径"
    )
    args = parser.parse_args()
    
    # 加载指标
    system_metrics = {}
    for metric_spec in args.metrics:
        if ":" in metric_spec:
            path, label = metric_spec.split(":", 1)
            system_name = label
        else:
            path = metric_spec
            system_name = Path(path).stem
        
        print(f"正在加载 {system_name} 的指标... {path}")
        system_metrics[system_name] = load_metrics(path)
    
    # 执行对比
    report = compare_systems(system_metrics)
    
    # 打印报告
    print_comparison_report(report)
    
    # 保存报告
    save_comparison_report(report, args.output)


if __name__ == "__main__":
    main()
