#!/usr/bin/env python3
"""
从streamlit_reports中的实际报告数据验证指标计算的正确性
比对预期值范围和实际计算值
"""

import sys
import os
import json
import glob
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.visualization import MetricsCollector, MetricsCalculator, MetricsVisualizer
from src.state import State


@dataclass
class MetricsExpectation:
    """指标期望范围"""
    name: str
    expected_min: float
    expected_max: float
    typical_min: float
    typical_max: float
    
    def check(self, value: float) -> tuple[bool, str]:
        """检查值是否在合理范围内"""
        status = "✓" if self.expected_min <= value <= self.expected_max else "✗"
        in_typical = self.typical_min <= value <= self.typical_max
        typical_label = "典型" if in_typical else "非典型"
        
        return (self.expected_min <= value <= self.expected_max, 
                f"{status} {self.name}: {value:.4f} [{typical_label}]")


# 定义指标期望值（基于IR/NLP标准）
METRICS_EXPECTATIONS = {
    'ndcg': MetricsExpectation('NDCG@10', 0.0, 1.0, 0.5, 0.8),
    'mrr': MetricsExpectation('MRR', 0.0, 1.0, 0.2, 0.6),
    'map_score': MetricsExpectation('MAP', 0.0, 1.0, 0.2, 0.6),
    'bpref': MetricsExpectation('BPref', 0.0, 1.0, 0.3, 0.8),
    'precision_at_1': MetricsExpectation('P@1', 0.0, 1.0, 0.3, 0.9),
    'precision_at_3': MetricsExpectation('P@3', 0.0, 1.0, 0.3, 0.8),
    'precision_at_5': MetricsExpectation('P@5', 0.0, 1.0, 0.2, 0.6),
    'precision_at_10': MetricsExpectation('P@10', 0.0, 1.0, 0.1, 0.5),
    'avg_relevance': MetricsExpectation('平均相关性', 0.0, 1.0, 0.3, 0.7),
    'coverage_score': MetricsExpectation('覆盖率', 0.0, 1.0, 0.6, 1.0),
}


class MetricsValidator:
    """指标验证器"""
    
    def __init__(self, reports_dir: str):
        self.reports_dir = reports_dir
        self.json_files = glob.glob(os.path.join(reports_dir, 'state_*.json'))
        self.results = []
    
    def load_state_from_json(self, json_file: str) -> Optional[Dict[str, Any]]:
        """从JSON文件加载状态数据"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"❌ 加载失败: {json_file} - {e}")
            return None
    
    def validate_single_report(self, json_file: str) -> Dict[str, Any]:
        """验证单个报告的指标 - 从搜索历史重新计算"""
        filename = os.path.basename(json_file)
        print(f"\n{'='*70}")
        print(f"📊 验证: {filename}")
        print(f"{'='*70}")
        
        data = self.load_state_from_json(json_file)
        if not data:
            return None
        
        result = {
            'file': filename,
            'query': data.get('query', 'N/A'),
            'metrics': {},
            'validation_status': [],
            'issues': []
        }
        
        print(f"\n📈 基本信息:")
        print(f"  查询: {result['query']}")
        
        # 收集所有搜索结果
        all_searches = []
        paragraphs = data.get('paragraphs', [])
        
        for para_idx, paragraph in enumerate(paragraphs):
            research = paragraph.get('research', {})
            search_history = research.get('search_history', [])
            for search in search_history:
                all_searches.append({
                    'title': search.get('title', ''),
                    'content': search.get('content', ''),
                    'score': search.get('score', 0),
                    'url': search.get('url', '')
                })
        
        print(f"  段落数: {len(paragraphs)}")
        print(f"  搜索结果总数: {len(all_searches)}")
        
        if not all_searches:
            result['issues'].append("⚠️  没有搜索历史记录")
            return result
        
        # 计算相关性分数
        query_lower = result['query'].lower()
        relevances = self._calculate_relevances(query_lower, all_searches)
        
        print(f"\n📊 相关性分布:")
        print(f"  最小: {min(relevances):.4f}")
        print(f"  最大: {max(relevances):.4f}")
        print(f"  平均: {sum(relevances)/len(relevances):.4f}")
        print(f"  中位: {sorted(relevances)[len(relevances)//2]:.4f}")
        
        # 使用计算器计算指标
        calculator = MetricsCalculator()
        
        print(f"\n🎯 质量指标:")
        
        for metric_key, expectation in METRICS_EXPECTATIONS.items():
            if metric_key == 'ndcg':
                value = calculator.calculate_ndcg(relevances)
            elif metric_key == 'mrr':
                value = calculator.calculate_mrr(relevances, threshold=0.6)
            elif metric_key == 'map_score':
                value = calculator.calculate_map(relevances, threshold=0.6)
            elif metric_key == 'bpref':
                value = calculator.calculate_bpref(relevances, threshold=0.6)
            elif metric_key == 'precision_at_1':
                value = calculator.calculate_precision_at_k(relevances, k=1, threshold=0.6)
            elif metric_key == 'precision_at_3':
                value = calculator.calculate_precision_at_k(relevances, k=3, threshold=0.6)
            elif metric_key == 'precision_at_5':
                value = calculator.calculate_precision_at_k(relevances, k=5, threshold=0.6)
            elif metric_key == 'precision_at_10':
                value = calculator.calculate_precision_at_k(relevances, k=10, threshold=0.6)
            elif metric_key == 'avg_relevance':
                value = sum(relevances) / len(relevances) if relevances else 0
            elif metric_key == 'coverage_score':
                value = min(len(all_searches) / max(len(paragraphs) * 2, 1), 1.0)
            else:
                continue
            
            result['metrics'][metric_key] = value
            is_valid, message = expectation.check(value)
            print(f"  {message}")
            
            result['validation_status'].append({
                'metric': metric_key,
                'value': value,
                'valid': is_valid,
                'expected_range': (expectation.expected_min, expectation.expected_max)
            })
            
            if not is_valid:
                result['issues'].append(
                    f"❌ {metric_key} = {value:.4f} 超出期望范围 "
                    f"[{expectation.expected_min:.2f}, {expectation.expected_max:.2f}]"
                )
        
        return result
    
    def _calculate_relevances(self, query_lower: str, all_searches: List[Dict]) -> List[float]:
        """计算搜索结果的相关性分数"""
        import re
        
        query_terms = set(re.findall(r'\w+', query_lower))
        if not query_terms:
            return [0.5] * len(all_searches)
        
        relevances = []
        for search in all_searches:
            title = search.get('title', '').lower()
            content = search.get('content', '').lower()
            
            # 标题匹配
            title_terms = set(re.findall(r'\w+', title))
            title_overlap = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
            
            # 内容匹配
            content_terms = set(re.findall(r'\w+', content))
            content_overlap = len(query_terms & content_terms) / len(query_terms) if query_terms else 0
            
            # 内容长度质量
            content_length = len(content)
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
            
            # 综合相关性
            relevance = (
                title_overlap * 0.4 +
                content_overlap * 0.35 +
                length_score * 0.25
            )
            
            relevances.append(min(max(relevance, 0.0), 1.0))
        
        return relevances
    
    def validate_all_reports(self) -> List[Dict[str, Any]]:
        """验证所有报告"""
        print(f"\n{'='*70}")
        print(f"🔍 开始验证 {len(self.json_files)} 个报告")
        print(f"{'='*70}")
        
        for json_file in sorted(self.json_files):
            result = self.validate_single_report(json_file)
            if result:
                self.results.append(result)
        
        return self.results
    
    def generate_summary_report(self) -> str:
        """生成总结报告"""
        print(f"\n\n{'='*70}")
        print(f"📊 验证总结报告")
        print(f"{'='*70}")
        
        total_reports = len(self.results)
        valid_reports = sum(1 for r in self.results if not r['issues'])
        issue_count = sum(len(r['issues']) for r in self.results)
        
        print(f"\n📈 统计:")
        print(f"  总报告数: {total_reports}")
        print(f"  有效报告: {valid_reports}")
        print(f"  问题数: {issue_count}")
        print(f"  成功率: {valid_reports/total_reports*100:.1f}%" if total_reports > 0 else "  成功率: N/A")
        
        # 指标统计
        print(f"\n🎯 指标统计:")
        all_metrics = {}
        for result in self.results:
            for metric_key, value in result['metrics'].items():
                if metric_key not in all_metrics:
                    all_metrics[metric_key] = []
                all_metrics[metric_key].append(value)
        
        for metric_key, values in sorted(all_metrics.items()):
            if values:
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                print(f"  {metric_key}:")
                print(f"    平均: {avg:.4f}, 范围: [{min_val:.4f}, {max_val:.4f}]")
        
        # 列出所有问题
        if issue_count > 0:
            print(f"\n⚠️  发现的问题:")
            all_issues = []
            for result in self.results:
                if result['issues']:
                    for issue in result['issues']:
                        all_issues.append(f"  {result['file']}: {issue}")
            
            for issue in sorted(set(all_issues)):
                print(issue)
        
        # 建议
        print(f"\n💡 建议:")
        if valid_reports == total_reports:
            print("  ✅ 所有报告指标有效！")
        else:
            if any('超出范围' in issue for r in self.results for issue in r['issues']):
                print("  • 检查相关性计算逻辑是否正确")
                print("  • 验证阈值设置是否合理")
            if any('缺少' in issue for r in self.results for issue in r['issues']):
                print("  • 检查指标收集流程是否完整")
                print("  • 确保所有必需指标都被计算")
        
        return f"验证完成: {valid_reports}/{total_reports} 报告有效"


def main():
    """主函数"""
    # 找到streamlit_reports目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(project_root, 'streamlit_reports')
    
    if not os.path.exists(reports_dir):
        print(f"❌ 找不到reports目录: {reports_dir}")
        return 1
    
    print(f"\n🔍 报告目录: {reports_dir}")
    print(f"📂 JSON文件数: {len(glob.glob(os.path.join(reports_dir, 'state_*.json')))}")
    
    validator = MetricsValidator(reports_dir)
    validator.validate_all_reports()
    summary = validator.generate_summary_report()
    
    print(f"\n{'='*70}")
    print(f"✅ {summary}")
    print(f"{'='*70}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
