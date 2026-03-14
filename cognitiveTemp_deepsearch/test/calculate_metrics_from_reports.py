#!/usr/bin/env python3
"""
从 streamlit_reports 生成的报告中计算量化指标

此脚本:
1. 加载 streamlit_reports 中所有的 JSON 状态文件
2. 提取搜索历史和相关性信息
3. 计算完整的学术指标
4. 生成对比分析和可视化
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import statistics

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.visualization.calculator import MetricsCalculator
from src.visualization.metrics_model import SearchQualityMetrics


class ReportMetricsAnalyzer:
    """分析 streamlit_reports 中的指标"""
    
    def __init__(self, reports_dir: str = None):
        """
        初始化分析器
        
        Args:
            reports_dir: 报告目录，默认为 streamlit_reports
        """
        if reports_dir is None:
            reports_dir = os.path.join(
                os.path.dirname(__file__), '..', 'streamlit_reports'
            )
        self.reports_dir = reports_dir
        self.reports = []
        self.metrics_results = {}
        self.calculator = MetricsCalculator()
        self.relevance_threshold = MetricsCalculator.DEFAULT_RELEVANCE_THRESHOLD
    
    def load_all_reports(self) -> List[Dict[str, Any]]:
        """加载所有状态 JSON 文件"""
        json_files = sorted(
            Path(self.reports_dir).glob('state_*.json'),
            reverse=True
        )
        
        print(f"📁 发现 {len(json_files)} 个报告文件")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.reports.append({
                        'file': json_file.name,
                        'path': str(json_file),
                        'data': state,
                        'query': state.get('query', 'Unknown'),
                    })
            except Exception as e:
                print(f"⚠️  加载失败: {json_file.name} - {e}")
        
        print(f"✅ 成功加载 {len(self.reports)} 个报告\n")
        return self.reports
    
    def extract_search_results(self, report_data: Dict) -> List[Dict]:
        """从报告数据中提取搜索结果"""
        results = []
        
        # 尝试从不同的数据结构中提取
        if 'paragraphs' in report_data:
            for para in report_data.get('paragraphs', []):
                if 'research' in para:
                    search_history = para['research'].get('search_history', [])
                    for item in search_history:
                        results.append({
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'source': item.get('source', ''),
                            'url': item.get('url', ''),
                        })
        
        # 如果找不到，尝试直接从根级别
        if not results and 'search_history' in report_data:
            results = report_data.get('search_history', [])
        
        return results
    
    def calculate_relevances(self, query: str, results: List[Dict]) -> List[float]:
        """计算结果与查询的相关性分数"""
        if not results:
            return []
        
        relevances = []
        query_tokens = set(query.lower().split())
        
        for result in results:
            title = result.get('title', '').lower()
            content = result.get('content', '').lower()
            
            # 标题匹配权重
            title_overlap = len(query_tokens & set(title.split()))
            title_score = min(title_overlap / len(query_tokens), 1.0) if query_tokens else 0
            
            # 内容匹配权重
            content_overlap = len(query_tokens & set(content.split()))
            content_score = min(content_overlap / len(query_tokens), 1.0) if query_tokens else 0
            
            # 长度质量（内容长度越长，质量越好）
            content_length = len(content.split())
            length_score = min(content_length / 100, 1.0)
            
            # 综合相关性: 标题 40% + 内容 35% + 长度 25%
            relevance = (title_score * 0.4 + content_score * 0.35 + length_score * 0.25)
            relevance = max(0.0, min(1.0, relevance))
            
            relevances.append(relevance)
        
        return relevances
    
    def analyze_report(self, report: Dict) -> Dict[str, Any]:
        """分析单个报告"""
        query = report['query']
        results = self.extract_search_results(report['data'])
        
        if not results:
            return {
                'status': 'no_data',
                'query': query,
                'message': '没有搜索结果数据',
            }
        
        relevances = self.calculate_relevances(query, results)
        
        # 计算各项指标
        metrics = {
            'status': 'success',
            'query': query,
            'file': report['file'],
            'total_results': len(results),
            'threshold_used': self.relevance_threshold,
            'relevant_count_06': sum(1 for r in relevances if r >= 0.6),
            'relevant_count_03': sum(1 for r in relevances if r >= 0.3),
            'relevant_count_threshold': sum(1 for r in relevances if r >= self.relevance_threshold),
            
            # NDCG
            'ndcg_10': self.calculator.calculate_ndcg(relevances, k=10),
            'ndcg_20': self.calculator.calculate_ndcg(relevances, k=20),
            
            # MRR
            'mrr': self.calculator.calculate_mrr(relevances, threshold=self.relevance_threshold),
            
            # MAP
            'map': self.calculator.calculate_map(relevances, threshold=self.relevance_threshold),
            
            # Precision@K
            'p_at_1': self.calculator.calculate_precision_at_k(relevances, k=1, threshold=self.relevance_threshold),
            'p_at_3': self.calculator.calculate_precision_at_k(relevances, k=3, threshold=self.relevance_threshold),
            'p_at_5': self.calculator.calculate_precision_at_k(relevances, k=5, threshold=self.relevance_threshold),
            'p_at_10': self.calculator.calculate_precision_at_k(relevances, k=10, threshold=self.relevance_threshold),
            
            # BPref
            'bpref': self.calculator.calculate_bpref(relevances, threshold=self.relevance_threshold),
            
            # 相关性统计
            'avg_relevance': statistics.mean(relevances) if relevances else 0,
            'median_relevance': statistics.median(relevances) if relevances else 0,
            'min_relevance': min(relevances) if relevances else 0,
            'max_relevance': max(relevances) if relevances else 0,
            'stdev_relevance': statistics.stdev(relevances) if len(relevances) > 1 else 0,
            
            # 覆盖率
            'coverage': 1.0,
        }
        
        return metrics
    
    def analyze_all(self) -> Dict[str, Dict]:
        """分析所有报告"""
        print("🔍 正在计算指标...\n")
        
        for i, report in enumerate(self.reports, 1):
            metrics = self.analyze_report(report)
            key = report['file']
            self.metrics_results[key] = metrics
            
            status_icon = "✅" if metrics['status'] == 'success' else "⚠️"
            query_short = report['query'][:40]
            print(f"{status_icon} [{i}/{len(self.reports)}] {query_short}...")
        
        return self.metrics_results
    
    def generate_summary(self) -> str:
        """生成摘要报告"""
        successful = [m for m in self.metrics_results.values() if m['status'] == 'success']
        
        if not successful:
            return "没有成功的报告"
        
        # 统计数据
        summary = []
        summary.append("=" * 80)
        summary.append("📊 指标汇总报告")
        summary.append("=" * 80)
        
        summary.append(f"\n📈 总体统计:")
        summary.append(f"  • 总报告数: {len(self.metrics_results)}")
        summary.append(f"  • 成功分析: {len(successful)}")
        summary.append(f"  • 失败: {len(self.metrics_results) - len(successful)}")
        
        # NDCG 统计
        ndcg_values = [m['ndcg_10'] for m in successful]
        summary.append(f"\n📍 NDCG@10:")
        summary.append(f"  • 平均: {statistics.mean(ndcg_values):.4f}")
        summary.append(f"  • 中位: {statistics.median(ndcg_values):.4f}")
        summary.append(f"  • 最小: {min(ndcg_values):.4f}")
        summary.append(f"  • 最大: {max(ndcg_values):.4f}")
        if len(ndcg_values) > 1:
            summary.append(f"  • 标差: {statistics.stdev(ndcg_values):.4f}")
        
        # MRR 统计
        mrr_values = [m['mrr'] for m in successful]
        summary.append(f"\n🎯 MRR (Mean Reciprocal Rank):")
        summary.append(f"  • 平均: {statistics.mean(mrr_values):.4f}")
        summary.append(f"  • 中位: {statistics.median(mrr_values):.4f}")
        summary.append(f"  • 最小: {min(mrr_values):.4f}")
        summary.append(f"  • 最大: {max(mrr_values):.4f}")
        
        # MAP 统计
        map_values = [m['map'] for m in successful]
        summary.append(f"\n📍 MAP (Mean Average Precision):")
        summary.append(f"  • 平均: {statistics.mean(map_values):.4f}")
        summary.append(f"  • 中位: {statistics.median(map_values):.4f}")
        summary.append(f"  • 最小: {min(map_values):.4f}")
        summary.append(f"  • 最大: {max(map_values):.4f}")
        
        # Precision@K
        p1_values = [m['p_at_1'] for m in successful]
        p3_values = [m['p_at_3'] for m in successful]
        p5_values = [m['p_at_5'] for m in successful]
        p10_values = [m['p_at_10'] for m in successful]
        
        summary.append(f"\n🎯 Precision@K (阈值{self.relevance_threshold:.2f}):")
        summary.append(f"  • P@1:  {statistics.mean(p1_values):.4f}")
        summary.append(f"  • P@3:  {statistics.mean(p3_values):.4f}")
        summary.append(f"  • P@5:  {statistics.mean(p5_values):.4f}")
        summary.append(f"  • P@10: {statistics.mean(p10_values):.4f}")
        
        # BPref
        bpref_values = [m['bpref'] for m in successful]
        summary.append(f"\n📊 BPref (Binary Preference):")
        summary.append(f"  • 平均: {statistics.mean(bpref_values):.4f}")
        summary.append(f"  • 中位: {statistics.median(bpref_values):.4f}")
        
        # 相关性分析
        avg_rel = statistics.mean([m['avg_relevance'] for m in successful])
        summary.append(f"\n🔍 相关性分析:")
        summary.append(f"  • 平均相关性: {avg_rel:.4f}")
        summary.append(f"  • 相关结果(≥0.6): {statistics.mean([m['relevant_count_06'] for m in successful]):.1f}")
        summary.append(f"  • 相关结果(≥0.3): {statistics.mean([m['relevant_count_03'] for m in successful]):.1f}")
        summary.append(
            f"  • 相关结果(≥{self.relevance_threshold:.2f}): "
            f"{statistics.mean([m['relevant_count_threshold'] for m in successful]):.1f}"
        )
        
        summary.append(f"\n{'='*80}\n")
        
        return "\n".join(summary)
    
    def generate_detailed_report(self) -> str:
        """生成详细报告"""
        report = []
        report.append("=" * 100)
        report.append("📋 详细指标分析")
        report.append("=" * 100)
        
        for i, (file, metrics) in enumerate(self.metrics_results.items(), 1):
            if metrics['status'] != 'success':
                report.append(f"\n⚠️  [{i}] {metrics['query']}")
                report.append(f"    状态: {metrics['message']}")
                continue
            
            query = metrics['query']
            report.append(f"\n✅ [{i}] {query}")
            report.append(f"    文件: {file}")
            report.append(f"    搜索结果数: {metrics['total_results']}")
            
            report.append(f"\n    排名质量指标:")
            report.append(f"      • NDCG@10:    {metrics['ndcg_10']:.4f}")
            report.append(f"      • NDCG@20:    {metrics['ndcg_20']:.4f}")
            report.append(f"      • MRR:        {metrics['mrr']:.4f}")
            report.append(f"      • MAP:        {metrics['map']:.4f}")
            report.append(f"      • BPref:      {metrics['bpref']:.4f}")
            
            report.append(f"\n    精度指标 (Precision@K, 阈值{self.relevance_threshold:.2f}):")
            report.append(f"      • P@1:        {metrics['p_at_1']:.4f}")
            report.append(f"      • P@3:        {metrics['p_at_3']:.4f}")
            report.append(f"      • P@5:        {metrics['p_at_5']:.4f}")
            report.append(f"      • P@10:       {metrics['p_at_10']:.4f}")
            
            report.append(f"\n    相关性分布:")
            report.append(f"      • 平均:       {metrics['avg_relevance']:.4f}")
            report.append(f"      • 中位:       {metrics['median_relevance']:.4f}")
            report.append(f"      • 范围:       [{metrics['min_relevance']:.4f}, {metrics['max_relevance']:.4f}]")
            report.append(f"      • 标差:       {metrics['stdev_relevance']:.4f}")
            report.append(f"      • 阈值:       {metrics['threshold_used']:.2f}")
            report.append(f"      • 相关(≥0.3): {metrics['relevant_count_03']}/{metrics['total_results']}")
            report.append(f"      • 相关(≥0.6): {metrics['relevant_count_06']}/{metrics['total_results']}")
            report.append(
                f"      • 相关(≥{self.relevance_threshold:.2f}): "
                f"{metrics['relevant_count_threshold']}/{metrics['total_results']}"
            )
        
        report.append(f"\n{'='*100}\n")
        return "\n".join(report)
    
    def save_results(self, output_dir: str = None) -> str:
        """保存结果到文件"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), 'metrics_reports')
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存为 JSON
        json_file = os.path.join(output_dir, f'metrics_{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics_results, f, ensure_ascii=False, indent=2)
        
        # 保存摘要
        summary = self.generate_summary()
        summary_file = os.path.join(output_dir, f'metrics_summary_{timestamp}.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        # 保存详细报告
        detailed = self.generate_detailed_report()
        detailed_file = os.path.join(output_dir, f'metrics_detailed_{timestamp}.txt')
        with open(detailed_file, 'w', encoding='utf-8') as f:
            f.write(detailed)
        
        print(f"\n💾 结果已保存:")
        print(f"  • JSON:    {json_file}")
        print(f"  • 摘要:    {summary_file}")
        print(f"  • 详细:    {detailed_file}")
        
        return output_dir


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 从 streamlit_reports 计算量化指标")
    print("="*80 + "\n")
    
    analyzer = ReportMetricsAnalyzer()
    
    # 1. 加载所有报告
    analyzer.load_all_reports()
    
    # 2. 分析所有报告
    analyzer.analyze_all()
    
    # 3. 打印摘要
    summary = analyzer.generate_summary()
    print(summary)
    
    # 4. 打印详细报告
    detailed = analyzer.generate_detailed_report()
    print(detailed)
    
    # 5. 保存结果
    analyzer.save_results()
    
    print("✅ 分析完成！")


if __name__ == "__main__":
    main()
