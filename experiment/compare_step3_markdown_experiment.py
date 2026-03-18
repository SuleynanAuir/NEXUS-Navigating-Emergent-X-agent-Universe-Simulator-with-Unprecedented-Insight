from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from llm_deep_analysis_report import generate_llm_deep_analysis, generate_llm_multi_model_benchmark


CORE_DIMENSIONS = [
    "retrieval_quality",
    "kg_quality",
    "multi_agent_quality",
    "simulation_quality",
    "insight_quality",
]

LOWER_BETTER_KEYWORDS = (
    "risk",
    "hallucination",
    "unclear",
    "contradiction",
    "missing",
    "penalty",
    "error",
    "latency",
    "timeout",
    "failure",
)

THEME_RULES = {
    "knowledge_graph": (
        "kg_",
        "graph",
        "graphrag",
        "entity_",
        "evidence_",
        "claim_",
        "confidence_signal",
        "integrated_conf",
    ),
    "multi_agent": (
        "agent_",
        "multi_agent",
        "interaction",
        "dialogue",
        "deep_interaction",
        "dynamic_adaptability",
    ),
    "simulation": (
        "simulation_",
        "action_",
        "actions_",
        "round",
        "canyon_",
    ),
    "insight_report": (
        "insight_",
        "report_",
        "summary_",
    ),
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _collect_numeric_metrics(final_metrics: Dict[str, Any]) -> Dict[str, float]:
    numeric: Dict[str, float] = {}
    for key, value in final_metrics.items():
        if isinstance(value, (int, float)):
            numeric[key] = float(value)
    return numeric


def _compute_metric_diff(
    without_md_metrics: Dict[str, float],
    with_md_metrics: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    keys = sorted(set(without_md_metrics.keys()) | set(with_md_metrics.keys()))
    diffs: Dict[str, Dict[str, float]] = {}
    for key in keys:
        base = _safe_float(without_md_metrics.get(key, 0.0))
        target = _safe_float(with_md_metrics.get(key, 0.0))
        delta = target - base
        rel_change = (delta / base * 100.0) if abs(base) > 1e-12 else (100.0 if abs(target) > 1e-12 else 0.0)
        diffs[key] = {
            "without_markdown": base,
            "with_markdown": target,
            "delta": delta,
            "relative_change_pct": rel_change,
        }
    return diffs


def _compute_dimension_summary(metric_diff: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for dim in CORE_DIMENSIONS:
        summary[dim] = metric_diff.get(
            dim,
            {
                "without_markdown": 0.0,
                "with_markdown": 0.0,
                "delta": 0.0,
                "relative_change_pct": 0.0,
            },
        )
    return summary


def _top_changed_metrics(metric_diff: Dict[str, Dict[str, float]], top_n: int = 15) -> List[Tuple[str, Dict[str, float]]]:
    ranked = sorted(metric_diff.items(), key=lambda item: abs(item[1]["delta"]), reverse=True)
    return ranked[:top_n]


def _is_lower_better(metric_name: str) -> bool:
    name = metric_name.lower()
    return any(keyword in name for keyword in LOWER_BETTER_KEYWORDS)


def _compute_benefit_directional_diff(
    metric_diff: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    directional: Dict[str, Dict[str, float]] = {}
    for metric_name, values in metric_diff.items():
        delta = _safe_float(values.get("delta", 0.0))
        lower_better = _is_lower_better(metric_name)
        benefit_delta = -delta if lower_better else delta
        directional[metric_name] = {
            **values,
            "benefit_delta": benefit_delta,
            "direction": "lower_better" if lower_better else "higher_better",
        }
    return directional


def _top_by_benefit(
    directional_diff: Dict[str, Dict[str, float]],
    top_n: int,
    positive: bool,
) -> List[Tuple[str, Dict[str, float]]]:
    if positive:
        candidates = [(k, v) for k, v in directional_diff.items() if _safe_float(v.get("benefit_delta", 0.0)) > 0]
        ranked = sorted(candidates, key=lambda item: item[1]["benefit_delta"], reverse=True)
    else:
        candidates = [(k, v) for k, v in directional_diff.items() if _safe_float(v.get("benefit_delta", 0.0)) < 0]
        ranked = sorted(candidates, key=lambda item: item[1]["benefit_delta"])
    return ranked[:top_n]


def _compute_theme_benefits(directional_diff: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    theme_summary: Dict[str, Dict[str, float]] = {}
    for theme_name, prefixes in THEME_RULES.items():
        theme_metrics = [
            values
            for metric_name, values in directional_diff.items()
            if any(prefix in metric_name for prefix in prefixes)
        ]
        if not theme_metrics:
            theme_summary[theme_name] = {
                "metrics_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "benefit_sum": 0.0,
                "benefit_mean": 0.0,
            }
            continue

        benefits = [_safe_float(item.get("benefit_delta", 0.0)) for item in theme_metrics]
        positive_count = sum(1 for value in benefits if value > 0)
        negative_count = sum(1 for value in benefits if value < 0)
        benefit_sum = sum(benefits)
        theme_summary[theme_name] = {
            "metrics_count": len(theme_metrics),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "benefit_sum": benefit_sum,
            "benefit_mean": (benefit_sum / len(theme_metrics)) if theme_metrics else 0.0,
        }
    return theme_summary


def _compute_advantage_overview(
    directional_diff: Dict[str, Dict[str, float]],
    quality_gate_comparison: Dict[str, Dict[str, bool]],
    step3_eis_delta: float,
    overall_risk_delta: float,
) -> Dict[str, float]:
    values = [_safe_float(item.get("benefit_delta", 0.0)) for item in directional_diff.values()]
    improved_count = sum(1 for value in values if value > 0)
    worsened_count = sum(1 for value in values if value < 0)
    unchanged_count = sum(1 for value in values if abs(value) <= 1e-12)

    gained_gates = [
        gate
        for gate, status in quality_gate_comparison.items()
        if not status.get("without_markdown", False) and status.get("with_markdown", False)
    ]
    lost_gates = [
        gate
        for gate, status in quality_gate_comparison.items()
        if status.get("without_markdown", False) and not status.get("with_markdown", False)
    ]

    risk_improvement = -overall_risk_delta
    net_benefit = sum(values)
    total = max(len(values), 1)
    benefit_ratio = improved_count / total
    markdown_advantage_index = (
        step3_eis_delta * 100.0
        + risk_improvement * 40.0
        + (len(gained_gates) - len(lost_gates)) * 8.0
        + benefit_ratio * 20.0
    )

    return {
        "improved_metrics": improved_count,
        "worsened_metrics": worsened_count,
        "unchanged_metrics": unchanged_count,
        "improved_ratio": benefit_ratio,
        "net_benefit": net_benefit,
        "gained_gates": len(gained_gates),
        "lost_gates": len(lost_gates),
        "risk_improvement": risk_improvement,
        "markdown_advantage_index": markdown_advantage_index,
    }


def _build_report_markdown(result: Dict[str, Any]) -> str:
    meta = result["meta"]
    eis = result["eis_comparison"]
    dimension = result["core_dimension_comparison"]
    top_changes = result["top_changed_metrics"]
    top_benefits = result["top_benefit_metrics"]
    top_tradeoffs = result["top_tradeoff_metrics"]
    theme_benefits = result["theme_benefits"]
    advantage = result["advantage_overview"]

    lines: List[str] = []
    lines.append("# Step3 Markdown 补充材料对比实验报告")
    lines.append("")
    lines.append(f"- 生成时间: {meta['generated_at']}")
    lines.append(f"- 无 Markdown 补充: `{meta['without_markdown_source']}`")
    lines.append(f"- 有 Markdown 补充: `{meta['with_markdown_source']}`")
    lines.append(f"- 聚焦指标数量（Step3 + KG）: `{meta['focused_metrics_count']}`")
    lines.append("")
    lines.append("## 1) Markdown 优势总览")
    lines.append("")
    lines.append(
        f"- `Markdown Advantage Index` = `{advantage['markdown_advantage_index']:.3f}` "
        f"（越高表示综合净收益越强）"
    )
    lines.append(
        f"- 有利指标数/总数: `{int(advantage['improved_metrics'])}`/`{int(advantage['improved_metrics'] + advantage['worsened_metrics'] + advantage['unchanged_metrics'])}` "
        f"({advantage['improved_ratio'] * 100:.2f}%)"
    )
    lines.append(
        f"- 净收益（方向校正后）: `{advantage['net_benefit']:+.6f}`，风险改善: `{advantage['risk_improvement']:+.6f}`"
    )
    lines.append(
        f"- Gate 变化: 新增通过 `{int(advantage['gained_gates'])}`，丢失通过 `{int(advantage['lost_gates'])}`"
    )
    lines.append("")
    lines.append("## 2) EIS 对比")
    lines.append("")
    lines.append(f"- `step2_eis`: 无补充={eis['step2_eis_without_markdown']:.6f}, 有补充={eis['step2_eis_with_markdown']:.6f}")
    lines.append(f"- `step3_eis`: 无补充={eis['step3_eis_without_markdown']:.6f}, 有补充={eis['step3_eis_with_markdown']:.6f}")
    lines.append(f"- `delta_eis`: 无补充={eis['delta_eis_without_markdown']:.6f}, 有补充={eis['delta_eis_with_markdown']:.6f}")
    lines.append(f"- `step3_eis` 变化: {eis['step3_eis_delta']:+.6f} ({eis['step3_eis_relative_change_pct']:+.2f}%)")
    lines.append("")
    lines.append("## 3) 核心五维指标对比（沿用原有量化指标）")
    lines.append("")
    lines.append("| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |")
    lines.append("|---|---:|---:|---:|---:|")
    for metric_name in CORE_DIMENSIONS:
        row = dimension.get(metric_name, {})
        lines.append(
            f"| {metric_name} | {row.get('without_markdown', 0.0):.6f} | {row.get('with_markdown', 0.0):.6f} | "
            f"{row.get('delta', 0.0):+.6f} | {row.get('relative_change_pct', 0.0):+.2f}% |"
        )

    lines.append("")
    lines.append("## 4) 变化幅度最大的指标（Top 15）")
    lines.append("")
    lines.append("| 指标 | 无 Markdown | 有 Markdown | 绝对变化 | 相对变化 |")
    lines.append("|---|---:|---:|---:|---:|")
    for item in top_changes:
        metric_name = str(item.get("metric", ""))
        lines.append(
            f"| {metric_name} | {item.get('without_markdown', 0.0):.6f} | {item.get('with_markdown', 0.0):.6f} | "
            f"{item.get('delta', 0.0):+.6f} | {item.get('relative_change_pct', 0.0):+.2f}% |"
        )

    lines.append("")
    lines.append("## 5) 差异高亮（正向收益 Top 10）")
    lines.append("")
    lines.append("| 指标 | 方向 | 无 Markdown | 有 Markdown | 收益增量 | 原始变化 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for item in top_benefits:
        lines.append(
            f"| {item.get('metric', '')} | {item.get('direction', '')} | {item.get('without_markdown', 0.0):.6f} | "
            f"{item.get('with_markdown', 0.0):.6f} | {item.get('benefit_delta', 0.0):+.6f} | {item.get('delta', 0.0):+.6f} |"
        )

    lines.append("")
    lines.append("## 6) 差异高亮（负向回退 Top 10）")
    lines.append("")
    lines.append("| 指标 | 方向 | 无 Markdown | 有 Markdown | 回退增量 | 原始变化 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for item in top_tradeoffs:
        lines.append(
            f"| {item.get('metric', '')} | {item.get('direction', '')} | {item.get('without_markdown', 0.0):.6f} | "
            f"{item.get('with_markdown', 0.0):.6f} | {item.get('benefit_delta', 0.0):+.6f} | {item.get('delta', 0.0):+.6f} |"
        )

    lines.append("")
    lines.append("## 7) 主题收益分组")
    lines.append("")
    lines.append("| 主题 | 指标数 | 正向数 | 负向数 | 净收益和 | 平均收益 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for theme_name, theme in theme_benefits.items():
        lines.append(
            f"| {theme_name} | {int(theme.get('metrics_count', 0))} | {int(theme.get('positive_count', 0))} | "
            f"{int(theme.get('negative_count', 0))} | {theme.get('benefit_sum', 0.0):+.6f} | {theme.get('benefit_mean', 0.0):+.6f} |"
        )

    lines.append("")
    lines.append("## 8) 质量门槛（quality_gates）对比")
    lines.append("")
    lines.append("| Gate | 无 Markdown | 有 Markdown |")
    lines.append("|---|---|---|")
    for key, gate_values in result["quality_gate_comparison"].items():
        lines.append(f"| {key} | {gate_values['without_markdown']} | {gate_values['with_markdown']} |")

    lines.append("")
    lines.append("## 9) 结论摘要")
    lines.append("")
    lines.append(f"- `bottleneck_dimension` 无补充: `{result['bottleneck_comparison']['without_markdown']}`")
    lines.append(f"- `bottleneck_dimension` 有补充: `{result['bottleneck_comparison']['with_markdown']}`")
    lines.append(
        f"- `overall_risk` 变化: {result['overall_risk_comparison']['delta']:+.6f} "
        f"({result['overall_risk_comparison']['relative_change_pct']:+.2f}%)"
    )

    return "\n".join(lines) + "\n"


def run_comparison(without_markdown_path: Path, with_markdown_path: Path) -> Dict[str, Any]:
    without_payload = _load_json(without_markdown_path)
    with_payload = _load_json(with_markdown_path)

    without_final = _collect_numeric_metrics(without_payload.get("final_metrics", {}))
    with_final = _collect_numeric_metrics(with_payload.get("final_metrics", {}))

    metric_diff = _compute_metric_diff(without_final, with_final)
    directional_diff = _compute_benefit_directional_diff(metric_diff)
    core_dimension_comparison = _compute_dimension_summary(metric_diff)

    without_step3_eis = _safe_float(without_payload.get("step3_eis", 0.0))
    with_step3_eis = _safe_float(with_payload.get("step3_eis", 0.0))
    eis_delta = with_step3_eis - without_step3_eis
    eis_rel = (eis_delta / without_step3_eis * 100.0) if abs(without_step3_eis) > 1e-12 else (100.0 if abs(with_step3_eis) > 1e-12 else 0.0)

    quality_gate_keys = sorted(
        set((without_payload.get("quality_gates") or {}).keys()) | set((with_payload.get("quality_gates") or {}).keys())
    )
    quality_gate_comparison = {
        key: {
            "without_markdown": bool((without_payload.get("quality_gates") or {}).get(key, False)),
            "with_markdown": bool((with_payload.get("quality_gates") or {}).get(key, False)),
        }
        for key in quality_gate_keys
    }

    without_risk = _safe_float(without_payload.get("overall_risk", 0.0))
    with_risk = _safe_float(with_payload.get("overall_risk", 0.0))
    risk_delta = with_risk - without_risk
    risk_rel = (risk_delta / without_risk * 100.0) if abs(without_risk) > 1e-12 else (100.0 if abs(with_risk) > 1e-12 else 0.0)
    top_benefits = _top_by_benefit(directional_diff, top_n=10, positive=True)
    top_tradeoffs = _top_by_benefit(directional_diff, top_n=10, positive=False)
    theme_benefits = _compute_theme_benefits(directional_diff)
    advantage_overview = _compute_advantage_overview(
        directional_diff,
        quality_gate_comparison,
        step3_eis_delta=eis_delta,
        overall_risk_delta=risk_delta,
    )
    focus_names = (
        "kg_",
        "graph",
        "graphrag",
        "entity_",
        "evidence_",
        "claim_",
        "confidence_signal",
        "integrated_conf",
        "agent_",
        "multi_agent",
        "simulation_",
        "action_",
        "actions_",
        "canyon_",
        "dialogue",
        "insight_",
        "report_",
        "summary_",
        "interaction",
        "dynamic_adaptability",
        "deep_interaction",
    )
    focused_metrics_count = sum(
        1 for metric_name in metric_diff.keys() if any(prefix in metric_name for prefix in focus_names)
    )

    return {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "without_markdown_source": str(without_markdown_path),
            "with_markdown_source": str(with_markdown_path),
            "metrics_count": len(metric_diff),
            "focused_metrics_count": focused_metrics_count,
        },
        "eis_comparison": {
            "step2_eis_without_markdown": _safe_float(without_payload.get("step2_eis", 0.0)),
            "step2_eis_with_markdown": _safe_float(with_payload.get("step2_eis", 0.0)),
            "step3_eis_without_markdown": without_step3_eis,
            "step3_eis_with_markdown": with_step3_eis,
            "delta_eis_without_markdown": _safe_float(without_payload.get("delta_eis", 0.0)),
            "delta_eis_with_markdown": _safe_float(with_payload.get("delta_eis", 0.0)),
            "step3_eis_delta": eis_delta,
            "step3_eis_relative_change_pct": eis_rel,
        },
        "core_dimension_comparison": core_dimension_comparison,
        "all_metric_comparison": metric_diff,
        "top_changed_metrics": [
            {
                "metric": name,
                **values,
            }
            for name, values in _top_changed_metrics(metric_diff, top_n=15)
        ],
        "top_benefit_metrics": [
            {
                "metric": name,
                **values,
            }
            for name, values in top_benefits
        ],
        "top_tradeoff_metrics": [
            {
                "metric": name,
                **values,
            }
            for name, values in top_tradeoffs
        ],
        "theme_benefits": theme_benefits,
        "advantage_overview": advantage_overview,
        "quality_gate_comparison": quality_gate_comparison,
        "bottleneck_comparison": {
            "without_markdown": without_payload.get("bottleneck_dimension"),
            "with_markdown": with_payload.get("bottleneck_dimension"),
        },
        "overall_risk_comparison": {
            "without_markdown": without_risk,
            "with_markdown": with_risk,
            "delta": risk_delta,
            "relative_change_pct": risk_rel,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Step3 markdown supplement comparison experiment")
    parser.add_argument("--without-markdown", required=True, help="path to pipeline_metrics.json without markdown supplement")
    parser.add_argument("--with-markdown", required=True, help="path to pipeline_metrics.json with markdown supplement")
    parser.add_argument("--output-dir", required=True, help="output experiment folder")
    parser.add_argument("--enable-llm-deep-analysis", action="store_true", help="Generate extra LLM-only deep analysis markdown")
    parser.add_argument("--llm-provider", default="auto", choices=["auto", "openai", "deepseek"], help="Provider for LLM deep analysis")
    parser.add_argument("--llm-model", default="", help="Override model for deep analysis")
    parser.add_argument("--llm-temperature", type=float, default=0.2, help="LLM temperature")
    parser.add_argument("--llm-max-tokens", type=int, default=1800, help="LLM max tokens")
    parser.add_argument("--llm-timeout", type=int, default=60, help="LLM timeout seconds")
    parser.add_argument("--enable-llm-benchmark", action="store_true", help="Benchmark multiple models for deep analysis quality")
    parser.add_argument("--llm-benchmark-provider", default="", choices=["", "openai", "deepseek"], help="Provider used for benchmark models")
    parser.add_argument("--llm-benchmark-models", default="", help="Comma-separated model list for benchmark")
    args = parser.parse_args()

    without_path = Path(args.without_markdown).expanduser().resolve()
    with_path = Path(args.with_markdown).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_comparison(without_path, with_path)

    json_path = output_dir / "step3_markdown_comparison.json"
    md_path = output_dir / "step3_markdown_comparison.md"
    llm_md_path = output_dir / "step3_markdown_llm_deep_analysis.md"
    llm_meta_path = output_dir / "step3_markdown_llm_deep_analysis.meta.json"
    llm_benchmark_json_path = output_dir / "step3_markdown_llm_model_benchmark.json"
    llm_benchmark_md_path = output_dir / "step3_markdown_llm_model_benchmark.md"
    source_map_path = output_dir / "experiment_inputs.json"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_report_markdown(result), encoding="utf-8")

    llm_meta: Dict[str, Any] = {
        "success": False,
        "reason": "llm deep analysis disabled",
    }
    if args.enable_llm_deep_analysis:
        llm_meta = generate_llm_deep_analysis(
            result,
            llm_md_path,
            llm_meta_path,
            provider=args.llm_provider,
            model=args.llm_model,
            temperature=args.llm_temperature,
            max_tokens=args.llm_max_tokens,
            timeout_sec=args.llm_timeout,
        )

    benchmark_result: Dict[str, Any] = {}
    if args.enable_llm_benchmark:
        models = [item.strip() for item in args.llm_benchmark_models.split(",") if item.strip()]
        if not models:
            models = [args.llm_model] if args.llm_model.strip() else []
        benchmark_provider = args.llm_benchmark_provider.strip() or (args.llm_provider if args.llm_provider != "auto" else "openai")
        benchmark_result = generate_llm_multi_model_benchmark(
            result,
            output_dir,
            provider=benchmark_provider,
            models=models,
            temperature=args.llm_temperature,
            max_tokens=args.llm_max_tokens,
            timeout_sec=args.llm_timeout,
        )

    source_map_path.write_text(
        json.dumps(
            {
                "without_markdown": str(without_path),
                "with_markdown": str(with_path),
                "output_json": str(json_path),
                "output_markdown": str(md_path),
                "output_llm_deep_analysis_markdown": str(llm_md_path) if args.enable_llm_deep_analysis else "",
                "output_llm_deep_analysis_meta": str(llm_meta_path) if args.enable_llm_deep_analysis else "",
                "llm_deep_analysis_enabled": bool(args.enable_llm_deep_analysis),
                "llm_deep_analysis_success": bool(llm_meta.get("success", False)) if args.enable_llm_deep_analysis else False,
                "llm_benchmark_enabled": bool(args.enable_llm_benchmark),
                "llm_benchmark_models": [item.strip() for item in args.llm_benchmark_models.split(",") if item.strip()],
                "output_llm_benchmark_json": str(llm_benchmark_json_path) if args.enable_llm_benchmark else "",
                "output_llm_benchmark_markdown": str(llm_benchmark_md_path) if args.enable_llm_benchmark else "",
                "llm_benchmark_best_model": benchmark_result.get("best_model", "") if args.enable_llm_benchmark else "",
                "llm_benchmark_best_quality_score": benchmark_result.get("best_quality_score", 0.0) if args.enable_llm_benchmark else 0.0,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[OK] comparison json: {json_path}")
    print(f"[OK] comparison markdown: {md_path}")
    if args.enable_llm_deep_analysis:
        print(f"[OK] llm deep analysis markdown: {llm_md_path}")
        print(f"[OK] llm deep analysis meta: {llm_meta_path}")
        print(f"[INFO] llm deep analysis success: {bool(llm_meta.get('success', False))}")
    if args.enable_llm_benchmark:
        print(f"[OK] llm benchmark json: {llm_benchmark_json_path}")
        print(f"[OK] llm benchmark markdown: {llm_benchmark_md_path}")
        print(f"[INFO] llm benchmark best model: {benchmark_result.get('best_model')}")
    print(f"[OK] input mapping: {source_map_path}")


if __name__ == "__main__":
    main()
