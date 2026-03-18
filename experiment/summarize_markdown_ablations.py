from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

CORE_METRICS = [
    "retrieval_quality",
    "kg_quality",
    "multi_agent_quality",
    "simulation_quality",
    "insight_quality",
    "report_actionability",
    "report_quality",
    "markdown_supplement_signal",
]

LOWER_BETTER = (
    "risk",
    "hallucination",
    "unclear",
    "contradiction",
    "missing",
    "penalty",
    "error",
    "timeout",
    "failure",
)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_lower_better(metric_name: str) -> bool:
    name = metric_name.lower()
    return any(token in name for token in LOWER_BETTER)


def _compute_benefit_delta(metric_name: str, baseline: float, target: float) -> float:
    delta = target - baseline
    return -delta if _is_lower_better(metric_name) else delta


def _collect_variant_summary(name: str, payload: Dict[str, Any], baseline_payload: Dict[str, Any]) -> Dict[str, Any]:
    final_metrics = payload.get("final_metrics") or {}
    baseline_metrics = baseline_payload.get("final_metrics") or {}

    step3_eis = _safe_float(payload.get("step3_eis", 0.0))
    baseline_step3_eis = _safe_float(baseline_payload.get("step3_eis", 0.0))
    overall_risk = _safe_float(payload.get("overall_risk", 0.0))
    baseline_overall_risk = _safe_float(baseline_payload.get("overall_risk", 0.0))

    core = {}
    for metric in CORE_METRICS:
        base = _safe_float(baseline_metrics.get(metric, 0.0))
        cur = _safe_float(final_metrics.get(metric, 0.0))
        core[metric] = {
            "baseline": base,
            "value": cur,
            "delta": cur - base,
            "benefit_delta": _compute_benefit_delta(metric, base, cur),
        }

    benefit_values: List[Tuple[str, float]] = []
    for metric, value in final_metrics.items():
        if not isinstance(value, (int, float)):
            continue
        base = _safe_float(baseline_metrics.get(metric, 0.0))
        benefit_values.append((metric, _compute_benefit_delta(metric, base, float(value))))

    benefit_values.sort(key=lambda item: item[1], reverse=True)

    quality_gates = payload.get("quality_gates") or {}
    baseline_gates = baseline_payload.get("quality_gates") or {}
    gained_gates = sorted(
        gate for gate, passed in quality_gates.items()
        if bool(passed) and not bool(baseline_gates.get(gate, False))
    )

    return {
        "variant": name,
        "step3_eis": step3_eis,
        "step3_eis_delta": step3_eis - baseline_step3_eis,
        "overall_risk": overall_risk,
        "risk_delta": overall_risk - baseline_overall_risk,
        "risk_improvement": baseline_overall_risk - overall_risk,
        "core_metrics": core,
        "gained_gates": gained_gates,
        "top_benefits": [
            {"metric": metric, "benefit_delta": benefit}
            for metric, benefit in benefit_values[:8]
            if benefit > 0
        ],
    }


def _build_markdown(result: Dict[str, Any]) -> str:
    baseline_name = result["baseline"]["name"]
    lines: List[str] = []
    lines.append("# Markdown Ablation Summary")
    lines.append("")
    lines.append(f"- generated_at: `{result['meta']['generated_at']}`")
    lines.append(f"- baseline: `{baseline_name}`")
    lines.append(f"- variant_count: `{len(result['variants'])}`")
    lines.append("")
    lines.append("## Ranking by Step3 EIS")
    lines.append("")
    lines.append("| variant | step3_eis | delta_vs_baseline | risk_improvement | report_actionability_delta | markdown_signal |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for item in result["rankings"]["by_step3_eis_delta"]:
        core = item["core_metrics"]
        lines.append(
            f"| {item['variant']} | {item['step3_eis']:.6f} | {item['step3_eis_delta']:+.6f} | {item['risk_improvement']:+.6f} | "
            f"{core['report_actionability']['delta']:+.6f} | {core['markdown_supplement_signal']['value']:.6f} |"
        )

    lines.append("")
    lines.append("## Variant Details")
    lines.append("")
    for item in result["variants"]:
        lines.append(f"### {item['variant']}")
        lines.append("")
        lines.append(f"- `step3_eis_delta`: {item['step3_eis_delta']:+.6f}")
        lines.append(f"- `risk_improvement`: {item['risk_improvement']:+.6f}")
        lines.append(f"- `gained_gates`: {', '.join(item['gained_gates']) if item['gained_gates'] else '无'}")
        lines.append(f"- `report_actionability_delta`: {item['core_metrics']['report_actionability']['delta']:+.6f}")
        lines.append(f"- `kg_quality_delta`: {item['core_metrics']['kg_quality']['delta']:+.6f}")
        lines.append(f"- `insight_quality_delta`: {item['core_metrics']['insight_quality']['delta']:+.6f}")
        top_benefits = item.get("top_benefits") or []
        if top_benefits:
            rendered = ", ".join(f"{row['metric']} ({row['benefit_delta']:+.4f})" for row in top_benefits[:5])
            lines.append(f"- `top_benefits`: {rendered}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize multiple markdown ablation pipeline_metrics results")
    parser.add_argument("--baseline-name", default="without_markdown")
    parser.add_argument("--baseline", required=True)
    parser.add_argument(
        "--variant",
        action="append",
        default=[],
        help="Format: name=/abs/path/to/pipeline_metrics.json ; can be passed multiple times",
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    baseline_path = Path(args.baseline).expanduser().resolve()
    baseline_payload = _load_json(baseline_path)

    variants: List[Dict[str, Any]] = []
    for raw in args.variant:
        if "=" not in raw:
            raise ValueError(f"Invalid --variant: {raw}")
        name, path_str = raw.split("=", 1)
        variant_path = Path(path_str).expanduser().resolve()
        payload = _load_json(variant_path)
        summary = _collect_variant_summary(name.strip(), payload, baseline_payload)
        summary["source"] = str(variant_path)
        variants.append(summary)

    variants.sort(key=lambda item: item["step3_eis_delta"], reverse=True)

    result = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "baseline_source": str(baseline_path),
        },
        "baseline": {
            "name": args.baseline_name,
            "step3_eis": _safe_float(baseline_payload.get("step3_eis", 0.0)),
            "overall_risk": _safe_float(baseline_payload.get("overall_risk", 0.0)),
        },
        "variants": variants,
        "rankings": {
            "by_step3_eis_delta": variants,
            "best_variant": variants[0]["variant"] if variants else "",
        },
    }

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "markdown_ablation_summary.json"
    md_path = output_dir / "markdown_ablation_summary.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(result), encoding="utf-8")

    print(f"[OK] ablation summary json: {json_path}")
    print(f"[OK] ablation summary markdown: {md_path}")
    if variants:
        print(f"[INFO] best variant: {variants[0]['variant']}")
        print(f"[INFO] best step3_eis_delta: {variants[0]['step3_eis_delta']:+.6f}")


if __name__ == "__main__":
    main()
