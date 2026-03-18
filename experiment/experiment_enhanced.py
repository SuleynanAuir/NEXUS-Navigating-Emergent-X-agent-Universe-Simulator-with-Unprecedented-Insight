#!/usr/bin/env python3
"""
实验脚本：从数据到论文数据的完整流程
Experiment Pipeline: Data → Evaluation → Paper-Ready Results

运行方式：
    python3 experiment_enhanced.py --input payload.json --output results.json
    python3 experiment_enhanced.py --batch data/ --output batch_results.csv
    python3 experiment_enhanced.py --compare baseline.json nexus.json
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from self_supervised_metrics import EISCalculator, SimpleEmbedder
import numpy as np

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ============================================================================
# 第一部分：数据准备与验证
# ============================================================================

class DataPreparation:
    """数据准备和验证"""
    
    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证 payload 格式是否正确
        
        Returns:
            {
                'is_valid': bool,
                'issues': List[str],
                'warnings': List[str]
            }
        """
        issues = []
        warnings = []
        
        # 检查必需字段
        required_keys = ["retrieval", "kg", "multi_agent", "simulation", "insight"]
        for key in required_keys:
            if key not in payload:
                issues.append(f"Missing required field: {key}")
        
        # 检查检索数据
        if "retrieval" in payload:
            retrieval = payload["retrieval"]
            if not isinstance(retrieval, list) or not retrieval:
                warnings.append("retrieval is empty or not a list")
            else:
                case = retrieval[0]
                if not case.get("result_texts"):
                    warnings.append("retrieval: no result_texts")
        
        # 检查 KG 数据
        if "kg" in payload:
            kg = payload["kg"]
            if not kg.get("graph_entities"):
                warnings.append("kg: no graph_entities")
            if not kg.get("triples"):
                warnings.append("kg: no triples")
        
        # 检查多智能体数据
        if "multi_agent" in payload:
            ma = payload["multi_agent"]
            cases = ma.get("cases", [])
            if not cases:
                warnings.append("multi_agent: no cases")
            elif not cases[0].get("agent_answers"):
                warnings.append("multi_agent: no agent_answers")
        
        # 检查仿真数据
        if "simulation" in payload:
            sim = payload["simulation"]
            cases = sim.get("cases", [])
            if not cases:
                warnings.append("simulation: no cases")
            elif not cases[0].get("sequence"):
                warnings.append("simulation: no sequence")
        
        # 检查洞察数据
        if "insight" in payload:
            insight = payload["insight"]
            outputs = insight.get("outputs", [])
            if not outputs:
                warnings.append("insight: no outputs")
            elif not outputs[0].get("output"):
                warnings.append("insight: no output text")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }


# ============================================================================
# 第二部分：单系统评估
# ============================================================================

class SingleSystemEvaluation:
    """单个系统的详细评估"""
    
    def __init__(self):
        self.calculator = EISCalculator()
    
    def evaluate(
        self,
        query: str,
        payload: Dict[str, Any],
        system_name: str = "System"
    ) -> Dict[str, Any]:
        """
        评估单个系统
        """
        # 验证
        validation = DataPreparation.validate_payload(payload)
        
        if not validation['is_valid']:
            return {
                'system_name': system_name,
                'status': 'FAILED',
                'issues': validation['issues'],
                'warnings': validation['warnings']
            }
        
        # 计算
        result = self.calculator.evaluate_system(query, payload)
        
        return {
            'system_name': system_name,
            'status': 'SUCCESS',
            'warnings': validation['warnings'],
            'scores': {
                'retrieval': float(result.retrieval.score),
                'kg': float(result.kg.score),
                'multi_agent': float(result.multi_agent.score),
                'simulation': float(result.simulation.score),
                'insight': float(result.insight.score),
                'eis_absolute': float(result.eis_absolute),
            },
            'components': {
                'retrieval': result.retrieval.components,
                'kg': result.kg.components,
                'multi_agent': result.multi_agent.components,
                'simulation': result.simulation.components,
                'insight': result.insight.components,
            },
            'formulas': {
                'retrieval': result.retrieval.formula_name,
                'kg': result.kg.formula_name,
                'multi_agent': result.multi_agent.formula_name,
                'simulation': result.simulation.formula_name,
                'insight': result.insight.formula_name,
            }
        }


# ============================================================================
# 第三部分：对比评估
# ============================================================================

class ComparativeEvaluation:
    """两个或多个系统的对比"""
    
    def __init__(self):
        self.single_eval = SingleSystemEvaluation()
    
    def compare_systems(
        self,
        query: str,
        systems: Dict[str, Dict[str, Any]],  # {system_name: payload}
        baseline_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对比多个系统
        
        Args:
            query: 查询文本
            systems: {'System A': payload_a, 'System B': payload_b, ...}
            baseline_name: 哪个系统作为 baseline（用于计算相对改进）
        """
        
        # 评估所有系统
        results = {}
        for name, payload in systems.items():
            results[name] = self.single_eval.evaluate(query, payload, name)
        
        # 如果指定了 baseline，计算相对改进
        comparison = {
            'query': query,
            'systems': results,
            'comparison_table': {}
        }
        
        if baseline_name and baseline_name in results:
            baseline_result = results[baseline_name]
            
            if baseline_result['status'] == 'SUCCESS':
                baseline_scores = baseline_result['scores']
                
                for system_name, result in results.items():
                    if result['status'] == 'SUCCESS' and system_name != baseline_name:
                        improvements = {}
                        for metric in baseline_scores.keys():
                            if metric != 'eis_absolute':
                                baseline_val = baseline_scores[metric]
                                current_val = result['scores'][metric]
                                
                                if baseline_val > 0:
                                    improvement_pct = ((current_val - baseline_val) / baseline_val) * 100
                                else:
                                    improvement_pct = 0
                                
                                improvements[metric] = {
                                    'baseline': float(baseline_val),
                                    'current': float(current_val),
                                    'improvement': float(current_val - baseline_val),
                                    'improvement_pct': float(improvement_pct)
                                }
                        
                        comparison['comparison_table'][system_name] = improvements
        
        return comparison
    
    def generate_report(self, comparison: Dict[str, Any]) -> str:
        """
        生成文本格式的对比报告
        """
        report = []
        report.append("=" * 80)
        report.append("📊 系统对比评估报告")
        report.append("=" * 80)
        
        report.append(f"\n🔍 查询: {comparison['query']}\n")
        
        # 各系统得分
        report.append("各系统得分：\n")
        
        for system_name, result in comparison['systems'].items():
            if result['status'] == 'SUCCESS':
                report.append(f"{system_name}:")
                report.append(f"  Retrieval:    {result['scores']['retrieval']:.4f}")
                report.append(f"  KG Quality:   {result['scores']['kg']:.4f}")
                report.append(f"  Multi-Agent:  {result['scores']['multi_agent']:.4f}")
                report.append(f"  Simulation:   {result['scores']['simulation']:.4f}")
                report.append(f"  Insight:      {result['scores']['insight']:.4f}")
                report.append(f"  ┗ EIS (Absolute): {result['scores']['eis_absolute']:.4f}")
                report.append("")
        
        # 对比表
        if comparison['comparison_table']:
            report.append("\n📈 相对改进 (vs Baseline)：\n")
            report.append("| Metric          | Baseline | Current | Improvement | % Improvement |")
            report.append("|---|---|---|---|---|")
            
            for system_name, improvements in comparison['comparison_table'].items():
                report.append(f"\n{system_name}:")
                for metric, imp in improvements.items():
                    report.append(
                        f"  {metric:16} | {imp['baseline']:.4f} | "
                        f"{imp['current']:.4f} | {imp['improvement']:+.4f} | "
                        f"{imp['improvement_pct']:+.1f}%"
                    )
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


# ============================================================================
# 第四部分：批量实验
# ============================================================================

class BatchEvaluation:
    """批量评估多个查询-系统对"""
    
    def __init__(self):
        self.single_eval = SingleSystemEvaluation()
    
    def evaluate_directory(
        self,
        data_dir: str,
        output_csv: str = "batch_results.csv"
    ) -> Optional[Any]:
        """
        评估目录中的所有 JSON 文件
        
        数据格式：data_dir/
            query_1.json
            query_2.json
            ...
        
        每个文件格式：
            {
                "query": "...",
                "payload": {...}
            }
        """
        
        if not HAS_PANDAS:
            print("⚠️  pandas 不可用，使用 JSON 格式输出")
            results = []
        else:
            results = []
        
        for json_file in tqdm(sorted(Path(data_dir).glob("*.json"))):
            with open(json_file) as f:
                data = json.load(f)
            
            query = data.get("query", "")
            payload = data.get("payload", {})
            
            result = self.single_eval.evaluate(query, payload, str(json_file.stem))
            
            if result['status'] == 'SUCCESS':
                results.append({
                    'query': query[:50],
                    'file': json_file.name,
                    'retrieval': result['scores']['retrieval'],
                    'kg': result['scores']['kg'],
                    'multi_agent': result['scores']['multi_agent'],
                    'simulation': result['scores']['simulation'],
                    'insight': result['scores']['insight'],
                    'eis_absolute': result['scores']['eis_absolute'],
                })
        
        if HAS_PANDAS:
            df = pd.DataFrame(results)
            
            if output_csv:
                df.to_csv(output_csv, index=False)
                print(f"\n✅ 批量结果已保存: {output_csv}")
            
            return df
        else:
            # 以 JSON 格式保存
            if output_csv:
                output_json = output_csv.replace('.csv', '.json')
                with open(output_json, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n✅ 批量结果已保存: {output_json}")
            
            return results
    
    @staticmethod
    def summarize_results(results: Any) -> Dict[str, Any]:
        """
        统计汇总
        """
        if HAS_PANDAS and isinstance(results, pd.DataFrame):
            df = results
        else:
            # 如果是列表，转换为字典格式
            if isinstance(results, list):
                summary = {
                    'total_queries': len(results),
                    'metrics': {}
                }
                
                metrics = ['retrieval', 'kg', 'multi_agent', 'simulation', 'insight', 'eis_absolute']
                for metric in metrics:
                    values = [r[metric] for r in results if metric in r]
                    if values:
                        summary['metrics'][metric] = {
                            'mean': float(np.mean(values)),
                            'std': float(np.std(values)),
                            'min': float(np.min(values)),
                            'max': float(np.max(values)),
                            '25%': float(np.percentile(values, 25)),
                            '50%': float(np.percentile(values, 50)),
                            '75%': float(np.percentile(values, 75)),
                        }
                
                return summary
            return {}
        
        summary = {
            'total_queries': len(df),
            'metrics': {}
        }
        
        for metric in ['retrieval', 'kg', 'multi_agent', 'simulation', 'insight', 'eis_absolute']:
            summary['metrics'][metric] = {
                'mean': float(df[metric].mean()),
                'std': float(df[metric].std()),
                'min': float(df[metric].min()),
                'max': float(df[metric].max()),
                '25%': float(df[metric].quantile(0.25)),
                '50%': float(df[metric].quantile(0.50)),
                '75%': float(df[metric].quantile(0.75)),
            }
        
        return summary


# ============================================================================
# 第五部分：可视化
# ============================================================================

class Visualization:
    """结果可视化（如果有 matplotlib）"""
    
    @staticmethod
    def plot_single_system(result: Dict[str, Any], output_file: str = "system_eval.png"):
        """
        绘制单个系统的评分雷达图
        """
        if not HAS_MATPLOTLIB:
            print("⚠️  matplotlib 不可用，跳过可视化")
            return
        
        if result['status'] != 'SUCCESS':
            print(f"⚠️  {result['system_name']} 评估失败，无法绘制")
            return
        
        scores = result['scores']
        metrics = ['retrieval', 'kg', 'multi_agent', 'simulation', 'insight']
        values = [scores[m] for m in metrics]
        
        # 闭合图形
        values_plot = values + [values[0]]
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += [angles[0]]
        
        # 绘制
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, values_plot, 'o-', linewidth=2, label=result['system_name'])
        ax.fill(angles, values_plot, alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 1)
        ax.set_title(f"{result['system_name']} - Five Dimensions", size=16, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ 雷达图已保存: {output_file}")
        plt.close()
    
    @staticmethod
    def plot_comparison(
        comparison: Dict[str, Any],
        output_file: str = "comparison.png"
    ):
        """
        绘制系统对比柱状图
        """
        if not HAS_MATPLOTLIB:
            print("⚠️  matplotlib 不可用，跳过可视化")
            return
        
        systems = {}
        metrics = ['retrieval', 'kg', 'multi_agent', 'simulation', 'insight']
        
        for name, result in comparison['systems'].items():
            if result['status'] == 'SUCCESS':
                systems[name] = [result['scores'][m] for m in metrics]
        
        if not systems:
            print("⚠️  没有成功的系统可以对比")
            return
        
        if not HAS_PANDAS:
            print("⚠️  pandas 不可用，无法绘制对比图")
            return
        
        df_plot = pd.DataFrame(systems, index=metrics).T
        
        fig, ax = plt.subplots(figsize=(12, 6))
        df_plot.plot(kind='bar', ax=ax)
        
        ax.set_title("System Comparison - Five Dimensions", size=16)
        ax.set_ylabel("Score", size=12)
        ax.set_xlabel("System", size=12)
        ax.set_ylim(0, 1)
        ax.legend(title="Dimension", bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ 对比图已保存: {output_file}")
        plt.close()
    
    @staticmethod
    def plot_batch_distribution(
        results: Any,
        output_file: str = "distribution.png"
    ):
        """
        绘制批量结果的分布
        """
        if not HAS_MATPLOTLIB:
            print("⚠️  matplotlib 不可用，跳过可视化")
            return
        
        if not HAS_PANDAS:
            print("⚠️  pandas 不可用，无法绘制分布图")
            return
        
        df = results if isinstance(results, pd.DataFrame) else pd.DataFrame(results)
        
        metrics = ['retrieval', 'kg', 'multi_agent', 'simulation', 'insight', 'eis_absolute']
        
        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        axes = axes.flatten()
        
        for idx, metric in enumerate(metrics):
            if metric in df.columns:
                ax = axes[idx]
                df[metric].hist(bins=20, ax=ax, color='steelblue', edgecolor='black')
                ax.set_title(metric.replace('_', ' ').title())
                ax.set_xlabel('Score')
                ax.set_ylabel('Frequency')
                ax.set_xlim(0, 1)
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ 分布图已保存: {output_file}")
        plt.close()


# ============================================================================
# 第六部分：CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="NEXUS 自监督评估框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：

1. 评估单个系统：
   python3 experiment_enhanced.py --input payload.json

2. 对比两个系统：
   python3 experiment_enhanced.py --compare baseline.json nexus.json

3. 批量评估：
   python3 experiment_enhanced.py --batch data/ --output results.csv

4. 完整分析（含可视化）：
   python3 experiment_enhanced.py --input payload.json --plot --output result.json
        """
    )
    
    parser.add_argument('--query', type=str, default="What are the latest advances in quantum computing?",
                        help='查询文本')
    parser.add_argument('--input', type=str, help='输入 payload JSON 文件')
    parser.add_argument('--compare', type=str, nargs=2, metavar=('BASELINE', 'NEXUS'),
                        help='对比两个系统')
    parser.add_argument('--batch', type=str, help='批量评估目录')
    parser.add_argument('--output', type=str, help='输出文件 (JSON 或 CSV)')
    parser.add_argument('--plot', action='store_true', help='生成可视化')
    
    args = parser.parse_args()
    
    # ===== 场景 1：单个系统 =====
    if args.input:
        print("🔬 评估单个系统...")
        
        with open(args.input) as f:
            payload = json.load(f)
        
        evaluator = SingleSystemEvaluation()
        result = evaluator.evaluate(args.query, payload, Path(args.input).stem)
        
        # 打印结果
        if result['status'] == 'SUCCESS':
            print("\n✅ 评估成功！\n")
            print(f"检索质量：   {result['scores']['retrieval']:.4f}")
            print(f"KG 质量：    {result['scores']['kg']:.4f}")
            print(f"多智能体：   {result['scores']['multi_agent']:.4f}")
            print(f"仿真能力：   {result['scores']['simulation']:.4f}")
            print(f"洞察质量：   {result['scores']['insight']:.4f}")
            print(f"\nEIS (绝对)： {result['scores']['eis_absolute']:.4f}")
        else:
            print(f"\n❌ 评估失败: {result['issues']}")
            print(f"⚠️  警告: {result['warnings']}")
        
        # 保存结果
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✅ 结果已保存: {args.output}")
        
        # 绘图
        if args.plot:
            Visualization.plot_single_system(result)
    
    # ===== 场景 2：对比两个系统 =====
    elif args.compare:
        print("📊 对比两个系统...")
        
        with open(args.compare[0]) as f:
            baseline_payload = json.load(f)
        with open(args.compare[1]) as f:
            nexus_payload = json.load(f)
        
        comparator = ComparativeEvaluation()
        comparison = comparator.compare_systems(
            query=args.query,
            systems={
                'Baseline': baseline_payload,
                'NEXUS': nexus_payload
            },
            baseline_name='Baseline'
        )
        
        # 打印报告
        report = comparator.generate_report(comparison)
        print(report)
        
        # 保存
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(comparison, f, indent=2)
            print(f"\n✅ 对比结果已保存: {args.output}")
        
        # 绘图
        if args.plot:
            Visualization.plot_comparison(comparison)
    
    # ===== 场景 3：批量评估 =====
    elif args.batch:
        print("📈 批量评估...")
        
        batch_eval = BatchEvaluation()
        df = batch_eval.evaluate_directory(
            args.batch,
            output_csv=args.output or "batch_results.csv"
        )
        
        # 统计
        summary = batch_eval.summarize_results(df)
        print("\n📊 统计汇总：\n")
        
        for metric, stats in summary['metrics'].items():
            print(f"{metric}:")
            print(f"  Mean: {stats['mean']:.4f} ± {stats['std']:.4f}")
            print(f"  Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
            print()
        
        # 绘图
        if args.plot:
            Visualization.plot_batch_distribution(df)


if __name__ == "__main__":
    main()
