from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = EXPERIMENT_DIR.parent


def _load_local_env_file() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        env_key = key.strip()
        env_value = value.strip().strip('"').strip("'")
        if env_key and env_key not in os.environ:
            os.environ[env_key] = env_value


def _apply_env_aliases() -> None:
    if not os.getenv("DEEPSEEK_API_KEY", "").strip():
        llm_api_key = os.getenv("LLM_API_KEY", "").strip()
        if llm_api_key:
            os.environ["DEEPSEEK_API_KEY"] = llm_api_key
    if not os.getenv("DEEPSEEK_BASE_URL", "").strip():
        llm_base_url = os.getenv("LLM_BASE_URL", "").strip()
        if llm_base_url:
            os.environ["DEEPSEEK_BASE_URL"] = llm_base_url
    if not os.getenv("DEEPSEEK_MODEL", "").strip():
        llm_model = os.getenv("LLM_MODEL_NAME", "").strip()
        if llm_model:
            os.environ["DEEPSEEK_MODEL"] = llm_model

    if not os.getenv("OPENAI_API_KEY", "").strip():
        boost_key = os.getenv("LLM_BOOST_API_KEY", "").strip()
        if boost_key:
            os.environ["OPENAI_API_KEY"] = boost_key
    if not os.getenv("OPENAI_BASE_URL", "").strip():
        boost_url = os.getenv("LLM_BOOST_BASE_URL", "").strip()
        if boost_url:
            os.environ["OPENAI_BASE_URL"] = boost_url
    if not os.getenv("OPENAI_MODEL", "").strip():
        boost_model = os.getenv("LLM_BOOST_MODEL_NAME", "").strip()
        if boost_model:
            os.environ["OPENAI_MODEL"] = boost_model

    # gemini/qwen 无专用 key 时，fallback 到 OPENAI_* (millionengine 统一兼容端点)
    _openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    _openai_base = os.getenv("OPENAI_BASE_URL", "").strip()
    if not os.getenv("GEMINI_API_KEY", "").strip() and _openai_key:
        os.environ["GEMINI_API_KEY"] = _openai_key
    if not os.getenv("GEMINI_BASE_URL", "").strip() and _openai_base:
        os.environ["GEMINI_BASE_URL"] = _openai_base
    if not os.getenv("QWEN_API_KEY", "").strip() and _openai_key:
        os.environ["QWEN_API_KEY"] = _openai_key
    if not os.getenv("QWEN_BASE_URL", "").strip() and _openai_base:
        os.environ["QWEN_BASE_URL"] = _openai_base


def _bootstrap_env() -> None:
    _load_local_env_file()
    _apply_env_aliases()


def _build_endpoint(base: str) -> str:
    raw = (base or "").strip()
    if not raw:
        return ""
    if raw.endswith("/chat/completions"):
        return raw
    if raw.endswith("/v1"):
        return f"{raw}/chat/completions"
    return f"{raw.rstrip('/')}/v1/chat/completions"


def _resolve_provider(provider: str) -> str:
    _bootstrap_env()
    p = (provider or "auto").strip().lower()
    if p in {"openai", "deepseek", "gemini", "qwen"}:
        return p

    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    if os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEP_SEEK_API_KEY", "").strip():
        return "deepseek"
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "gemini"
    if os.getenv("QWEN_API_KEY", "").strip():
        return "qwen"
    return ""


def _resolve_model(provider: str, model: str) -> str:
    _bootstrap_env()
    custom = (model or "").strip()
    if custom:
        return custom

    if provider == "openai":
        return os.getenv("LLM_DEEP_ANALYSIS_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip()
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    if provider == "qwen":
        return os.getenv("QWEN_MODEL", "qwen-max").strip()
    return os.getenv("LLM_DEEP_ANALYSIS_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")).strip()


def _resolve_key_and_endpoint(provider: str) -> Dict[str, str]:
    _bootstrap_env()
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        endpoint = _build_endpoint(os.getenv("OPENAI_BASE_URL", "https://api.openai.com"))
        return {"api_key": key, "endpoint": endpoint}

    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        base = os.getenv("GEMINI_BASE_URL", "").strip() or "https://generativelanguage.googleapis.com/v1beta/openai"
        return {"api_key": key, "endpoint": _build_endpoint(base)}

    if provider == "qwen":
        key = os.getenv("QWEN_API_KEY", "").strip()
        base = os.getenv("QWEN_BASE_URL", "").strip() or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return {"api_key": key, "endpoint": _build_endpoint(base)}

    # deepseek
    key = os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEP_SEEK_API_KEY", "").strip()
    endpoint = _build_endpoint(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    return {"api_key": key, "endpoint": endpoint}


def _call_chat_completions(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def _extract_content(chat_response: Dict[str, Any]) -> str:
    choices = chat_response.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            text = (item or {}).get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


def _sanitize_model_name(model: str) -> str:
    text = (model or "model").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "model"


def _extract_numeric_tokens(comparison_result: Dict[str, Any], limit: int = 40) -> List[str]:
    numbers: List[str] = []

    def _collect(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                _collect(item)
            return
        if isinstance(value, list):
            for item in value:
                _collect(item)
            return
        if isinstance(value, (int, float)):
            number = float(value)
            numbers.append(f"{number:.6f}")
            numbers.append(f"{number:.3f}")
            numbers.append(f"{number:.2f}")

    _collect(comparison_result)
    dedup: List[str] = []
    seen = set()
    for token in numbers:
        t = token.rstrip("0").rstrip(".") if "." in token else token
        if not t or t in seen:
            continue
        seen.add(t)
        dedup.append(t)
        if len(dedup) >= limit:
            break
    return dedup


def _score_report_quality(report_markdown: str, comparison_result: Dict[str, Any]) -> Dict[str, float]:
    text = (report_markdown or "").strip()
    if not text:
        return {
            "length_score": 0.0,
            "section_score": 0.0,
            "number_grounding_score": 0.0,
            "structure_score": 0.0,
            "quality_score": 0.0,
        }

    lower = text.lower()
    length = len(text)
    if length <= 200:
        length_score = 0.2
    elif length <= 800:
        length_score = 0.5
    elif length <= 4000:
        length_score = 1.0
    else:
        length_score = 0.8

    required_sections = [
        "结论",
        "eis",
        "gate",
        "kg",
        "多智能体",
        "仿真",
        "洞察",
        "trade-off",
        "实验",
        "上线",
    ]
    section_hits = sum(1 for section in required_sections if section in lower)
    section_score = section_hits / len(required_sections)

    source_numbers = _extract_numeric_tokens(comparison_result)
    if source_numbers:
        hits = sum(1 for token in source_numbers if token in text)
        number_grounding_score = min(1.0, hits / max(6, len(source_numbers) * 0.35))
    else:
        number_grounding_score = 0.0

    heading_count = sum(1 for line in text.splitlines() if line.strip().startswith("#"))
    bullet_count = sum(1 for line in text.splitlines() if line.strip().startswith(("- ", "* ", "1)")))
    structure_score = min(1.0, (heading_count / 6.0) * 0.5 + (bullet_count / 20.0) * 0.5)

    quality_score = (
        0.20 * length_score
        + 0.35 * section_score
        + 0.30 * number_grounding_score
        + 0.15 * structure_score
    )

    return {
        "length_score": round(length_score, 6),
        "section_score": round(section_score, 6),
        "number_grounding_score": round(number_grounding_score, 6),
        "structure_score": round(structure_score, 6),
        "quality_score": round(quality_score, 6),
    }


def _build_prompts(comparison_result: Dict[str, Any]) -> Dict[str, str]:
    system_prompt = (
        "你是资深实验评估专家。你只能基于用户提供的 JSON 数据进行分析，"
        "不得臆造不存在的数值。请输出结构化 Markdown，语言使用简体中文。"
    )
    user_prompt = (
        "请基于以下 Step3 Markdown A/B 对比 JSON 生成‘深度分析报告’。要求：\n"
        "1) 先给结论（是否支持引入 Markdown 补充）\n"
        "2) 拆解 5 个维度：EIS、Gate、KG、多智能体、仿真/洞察\n"
        "3) 给出收益-代价权衡（Trade-off）\n"
        "4) 给出下一轮实验设计建议（至少5条，可执行）\n"
        "5) 给出上线建议（灰度策略与监控项）\n"
        "6) 报告里必须引用具体数值并解释其意义\n\n"
        "以下是 JSON：\n"
        f"{json.dumps(comparison_result, ensure_ascii=False, indent=2)}"
    )
    return {"system": system_prompt, "user": user_prompt}


def generate_llm_deep_analysis(
    comparison_result: Dict[str, Any],
    output_markdown_path: Path,
    output_meta_path: Path,
    *,
    provider: str = "auto",
    model: str = "",
    temperature: float = 0.2,
    max_tokens: int = 1800,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    output_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    output_meta_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_provider = _resolve_provider(provider)
    if not resolved_provider:
        status = {
            "success": False,
            "reason": "No provider available; set OPENAI_API_KEY or DEEPSEEK_API_KEY",
            "provider": None,
            "model": None,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        output_markdown_path.write_text(
            "# LLM 深度分析报告\n\n"
            "- 状态: 未生成（未检测到可用 API Key）\n"
            "- 需要: `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`\n",
            encoding="utf-8",
        )
        output_meta_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        return status

    auth = _resolve_key_and_endpoint(resolved_provider)
    api_key = auth.get("api_key", "")
    endpoint = auth.get("endpoint", "")
    if not api_key or not endpoint:
        status = {
            "success": False,
            "reason": "Provider selected but API key or endpoint missing",
            "provider": resolved_provider,
            "model": None,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        output_markdown_path.write_text(
            "# LLM 深度分析报告\n\n"
            f"- 状态: 未生成（{status['reason']}）\n",
            encoding="utf-8",
        )
        output_meta_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        return status

    resolved_model = _resolve_model(resolved_provider, model)
    prompts = _build_prompts(comparison_result)

    try:
        response = _call_chat_completions(
            endpoint=endpoint,
            api_key=api_key,
            model=resolved_model,
            system_prompt=prompts["system"],
            user_prompt=prompts["user"],
            temperature=float(temperature),
            max_tokens=int(max_tokens),
            timeout_sec=int(timeout_sec),
        )
        content = _extract_content(response)
        if not content:
            raise RuntimeError("LLM returned empty content")

        output_markdown_path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
        quality = _score_report_quality(content, comparison_result)
        meta = {
            "success": True,
            "provider": resolved_provider,
            "model": resolved_model,
            "endpoint": endpoint,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "response_usage": response.get("usage", {}),
            "quality": quality,
        }
        output_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        status = {
            "success": False,
            "provider": resolved_provider,
            "model": resolved_model,
            "endpoint": endpoint,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "reason": str(exc),
        }
        output_markdown_path.write_text(
            "# LLM 深度分析报告\n\n"
            "- 状态: 生成失败\n"
            f"- 原因: `{status['reason']}`\n",
            encoding="utf-8",
        )
        output_meta_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        return status


def generate_llm_multi_model_benchmark(
    comparison_result: Dict[str, Any],
    output_dir: Path,
    *,
    provider: str = "openai",
    models: List[str] | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1800,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_list = [m.strip() for m in (models or []) if m.strip()]
    if not model_list:
        model_list = [
            os.getenv("OPENAI_MODEL", "gpt-4o"),
            "gpt-4o-mini",
        ]

    runs: List[Dict[str, Any]] = []
    for model_name in model_list:
        safe = _sanitize_model_name(model_name)
        md_path = output_dir / f"step3_markdown_llm_deep_analysis.{safe}.md"
        meta_path = output_dir / f"step3_markdown_llm_deep_analysis.{safe}.meta.json"
        meta = generate_llm_deep_analysis(
            comparison_result,
            md_path,
            meta_path,
            provider=provider,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_sec=timeout_sec,
        )
        quality_score = float(((meta.get("quality") or {}).get("quality_score", 0.0)) if meta.get("success") else 0.0)
        runs.append(
            {
                "model": model_name,
                "success": bool(meta.get("success", False)),
                "quality_score": quality_score,
                "markdown_path": str(md_path),
                "meta_path": str(meta_path),
                "reason": meta.get("reason", ""),
                "quality": meta.get("quality", {}),
            }
        )

    successful = [item for item in runs if item.get("success")]
    best = max(successful, key=lambda item: float(item.get("quality_score", 0.0))) if successful else None

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "provider": provider,
        "models": model_list,
        "runs": runs,
        "best_model": (best or {}).get("model"),
        "best_quality_score": (best or {}).get("quality_score", 0.0),
        "success_count": len(successful),
        "total_count": len(runs),
    }

    summary_json = output_dir / "step3_markdown_llm_model_benchmark.json"
    summary_md = output_dir / "step3_markdown_llm_model_benchmark.md"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# LLM 多模型深度分析质量对比",
        "",
        f"- 生成时间: {summary['generated_at']}",
        f"- provider: `{provider}`",
        f"- 成功数: `{summary['success_count']}/{summary['total_count']}`",
        f"- 最优模型: `{summary['best_model'] or 'N/A'}`",
        f"- 最优质量分: `{float(summary.get('best_quality_score', 0.0)):.6f}`",
        "",
        "| 模型 | 成功 | 质量分 | 长度分 | 章节分 | 数值落地分 | 结构分 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in runs:
        quality = item.get("quality") or {}
        lines.append(
            f"| {item.get('model', '')} | {item.get('success', False)} | {float(item.get('quality_score', 0.0)):.6f} | "
            f"{float(quality.get('length_score', 0.0)):.6f} | {float(quality.get('section_score', 0.0)):.6f} | "
            f"{float(quality.get('number_grounding_score', 0.0)):.6f} | {float(quality.get('structure_score', 0.0)):.6f} |"
        )
    lines.append("")
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    return {
        "summary_json": str(summary_json),
        "summary_markdown": str(summary_md),
        **summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM-only deep analysis report from comparison JSON")
    parser.add_argument("--comparison-json", required=True, help="Path to step3_markdown_comparison.json")
    parser.add_argument("--output-markdown", default="", help="Output markdown path")
    parser.add_argument("--output-meta", default="", help="Output metadata json path")
    parser.add_argument("--provider", default="auto", choices=["auto", "openai", "deepseek"], help="LLM provider")
    parser.add_argument("--model", default="", help="Override model")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--benchmark-models", default="", help="Comma-separated models for quality benchmark")
    parser.add_argument("--benchmark-provider", default="", choices=["", "openai", "deepseek"], help="Provider used in multi-model benchmark")
    parser.add_argument("--output-dir", default="", help="Output directory for benchmark artifacts")
    args = parser.parse_args()

    comparison_path = Path(args.comparison_json).expanduser().resolve()
    if args.output_markdown:
        output_markdown_path = Path(args.output_markdown).expanduser().resolve()
    else:
        output_markdown_path = comparison_path.parent / "step3_markdown_llm_deep_analysis.md"

    output_meta_path = Path(args.output_meta).expanduser().resolve() if args.output_meta else output_markdown_path.with_suffix(".meta.json")

    comparison_result = json.loads(comparison_path.read_text(encoding="utf-8"))
    single_meta = generate_llm_deep_analysis(
        comparison_result,
        output_markdown_path,
        output_meta_path,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_sec=args.timeout,
    )

    benchmark_result: Dict[str, Any] = {}
    if args.benchmark_models.strip():
        model_list = [item.strip() for item in args.benchmark_models.split(",") if item.strip()]
        benchmark_provider = args.benchmark_provider.strip() or (args.provider if args.provider != "auto" else "openai")
        benchmark_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else output_markdown_path.parent
        benchmark_result = generate_llm_multi_model_benchmark(
            comparison_result,
            benchmark_dir,
            provider=benchmark_provider,
            models=model_list,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_sec=args.timeout,
        )

    print(f"[OK] llm analysis markdown: {output_markdown_path}")
    print(f"[OK] llm analysis meta: {output_meta_path}")
    print(f"[INFO] llm analysis success: {bool(single_meta.get('success'))}")
    if benchmark_result:
        print(f"[OK] llm benchmark json: {benchmark_result.get('summary_json')}")
        print(f"[OK] llm benchmark markdown: {benchmark_result.get('summary_markdown')}")
        print(f"[INFO] llm benchmark best model: {benchmark_result.get('best_model')}")


if __name__ == "__main__":
    main()
