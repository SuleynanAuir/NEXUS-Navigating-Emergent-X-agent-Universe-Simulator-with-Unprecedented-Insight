from __future__ import annotations

import argparse
import json
from pathlib import Path

from metrics_engine import EmergentMetricsEngine, dump_json, load_json
from md_input_parser import parse_markdown_input
from data_validator import DataValidator, print_validation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="NEXUS experiment metrics runner")
    parser.add_argument("--input", required=True, help="Path to experiment input JSON or Markdown")
    parser.add_argument("--output", default="", help="Path to save metrics JSON")
    parser.add_argument("--validate-only", action="store_true", help="Only validate data, do not compute metrics")
    parser.add_argument("--skip-validation", action="store_true", help="Skip data validation")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # 解析输入
    if input_path.suffix.lower() == ".md":
        payload = parse_markdown_input(str(input_path))
    else:
        payload = load_json(str(input_path))
    
    # 验证数据
    if not args.skip_validation:
        validator = DataValidator()
        is_valid, errors, warnings = validator.validate_payload(payload)
        
        print("=" * 60)
        print("📊 数据验证报告")
        print("=" * 60)
        print_validation_report(is_valid, errors, warnings, verbose=True)
        print("=" * 60)
        
        if args.validate_only:
            return
        
        if not is_valid:
            print("\n⚠️  存在错误，仍然尝试计算指标（可能不准确）")
    
    # 计算指标
    engine = EmergentMetricsEngine()
    result = engine.evaluate(payload)

    print("\n=== 维度评分 ===")
    for key, value in result["dimension_scores"].items():
        print(f"{key}: {value:.4f}")

    print("\n=== 综合评分 (EIS) ===")
    print(f"score: {result['EIS']['score']:.4f}")
    
    print("\n=== 相对改进 ===")
    for dim, improvement in result['EIS']['relative_improvements'].items():
        print(f"{dim}: {improvement:.2%}")

    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_metrics.json")
    dump_json(str(output_path), result)
    print(f"\n✅ 指标已保存到: {output_path}")


if __name__ == "__main__":
    main()
