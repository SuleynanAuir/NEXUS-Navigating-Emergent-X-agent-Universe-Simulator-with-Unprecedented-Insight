from __future__ import annotations

import argparse
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _load_env_file() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _apply_env_aliases() -> None:
    # LLM_BOOST_* → OPENAI_* (millionengine 兼容端点)
    if not os.getenv("OPENAI_API_KEY", "").strip() and os.getenv("LLM_BOOST_API_KEY", "").strip():
        os.environ["OPENAI_API_KEY"] = os.getenv("LLM_BOOST_API_KEY", "").strip()
    if not os.getenv("OPENAI_BASE_URL", "").strip() and os.getenv("LLM_BOOST_BASE_URL", "").strip():
        os.environ["OPENAI_BASE_URL"] = os.getenv("LLM_BOOST_BASE_URL", "").strip()
    if not os.getenv("OPENAI_MODEL", "").strip() and os.getenv("LLM_BOOST_MODEL_NAME", "").strip():
        os.environ["OPENAI_MODEL"] = os.getenv("LLM_BOOST_MODEL_NAME", "").strip()

    # LLM_API_* → DEEPSEEK_*
    if not os.getenv("DEEPSEEK_API_KEY", "").strip() and os.getenv("LLM_API_KEY", "").strip():
        os.environ["DEEPSEEK_API_KEY"] = os.getenv("LLM_API_KEY", "").strip()
    if not os.getenv("DEEPSEEK_BASE_URL", "").strip() and os.getenv("LLM_BASE_URL", "").strip():
        os.environ["DEEPSEEK_BASE_URL"] = os.getenv("LLM_BASE_URL", "").strip()
    if not os.getenv("DEEPSEEK_MODEL", "").strip() and os.getenv("LLM_MODEL_NAME", "").strip():
        os.environ["DEEPSEEK_MODEL"] = os.getenv("LLM_MODEL_NAME", "").strip()

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
    _load_env_file()
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


def _resolve_key_endpoint_model(provider: str, model: str) -> Tuple[str, str, str]:
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        endpoint = _build_endpoint(os.getenv("OPENAI_BASE_URL", "https://api.openai.com"))
        model_name = (model or os.getenv("OPENAI_MODEL", "gpt-4o")).strip() or "gpt-4o"
        return api_key, endpoint, model_name

    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEP_SEEK_API_KEY", "").strip()
        endpoint = _build_endpoint(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        model_name = (model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")).strip() or "deepseek-chat"
        return api_key, endpoint, model_name

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        # GEMINI_BASE_URL 已由 alias 填为 millionengine；若仍空则用官方端点
        base = os.getenv("GEMINI_BASE_URL", "").strip() or "https://generativelanguage.googleapis.com/v1beta/openai"
        endpoint = _build_endpoint(base)
        model_name = (model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")).strip() or "gemini-2.0-flash"
        return api_key, endpoint, model_name

    # qwen
    api_key = os.getenv("QWEN_API_KEY", "").strip()
    # QWEN_BASE_URL 已由 alias 填为 millionengine；若仍空则用 DashScope
    base = os.getenv("QWEN_BASE_URL", "").strip() or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    endpoint = _build_endpoint(base)
    model_name = (model or os.getenv("QWEN_MODEL", "qwen-max")).strip() or "qwen-max"
    return api_key, endpoint, model_name


def _call_chat_completions(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_content(resp: Dict[str, Any]) -> str:
    choices = resp.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            text = (item or {}).get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]+", (text or "").lower())


def _split_paragraphs(text: str) -> List[str]:
    chunks = [c.strip() for c in re.split(r"\n\s*\n+", text or "") if c.strip()]
    return chunks


def _tfidf_vectors(texts: Sequence[str]) -> Tuple[List[Dict[str, float]], Dict[str, float]]:
    token_lists = [_tokenize(t) for t in texts]
    doc_freq: Counter = Counter()
    for tokens in token_lists:
        doc_freq.update(set(tokens))

    n_docs = max(len(texts), 1)
    idf: Dict[str, float] = {}
    for term, df in doc_freq.items():
        idf[term] = math.log((1 + n_docs) / (1 + df)) + 1.0

    vectors: List[Dict[str, float]] = []
    for tokens in token_lists:
        tf = Counter(tokens)
        total = max(sum(tf.values()), 1)
        vec: Dict[str, float] = {}
        for term, count in tf.items():
            vec[term] = (count / total) * idf.get(term, 1.0)
        vectors.append(vec)
    return vectors, idf


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _collect_kb_texts(paths: Sequence[Path], max_files: int = 100) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if text.strip():
                    out.append((str(path), text))
            except Exception:
                pass
            continue

        if not path.is_dir():
            continue

        for file_path in path.rglob("*"):
            if len(out) >= max_files:
                return out
            if not file_path.is_file() or file_path.suffix.lower() not in {".md", ".txt", ".json"}:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                if text.strip():
                    out.append((str(file_path), text))
            except Exception:
                continue
    return out


def _normalize_length_score(token_count: int, low: int = 700, high: int = 2200, hard_max: int = 4200) -> float:
    if token_count <= 0:
        return 0.0
    if token_count < low:
        return max(0.0, token_count / low)
    if token_count <= high:
        return 1.0
    if token_count >= hard_max:
        return 0.0
    return max(0.0, 1.0 - (token_count - high) / (hard_max - high))


def _extract_claims(report_text: str, max_claims: int = 20) -> List[str]:
    lines = [line.strip() for line in report_text.splitlines() if line.strip()]
    claim_like: List[str] = []
    for line in lines:
        if len(line) < 20:
            continue
        if line.startswith("#"):
            continue
        if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
            candidate = re.sub(r"^[-*\d\.\)\s]+", "", line).strip()
            if len(candidate) >= 20:
                claim_like.append(candidate)
        elif re.search(r"。|\.|；|;", line):
            claim_like.append(line)
        if len(claim_like) >= max_claims:
            break
    return claim_like[:max_claims]


def _sentence_similarity(a: str, b: str) -> float:
    vectors, _ = _tfidf_vectors([a, b])
    return _cosine(vectors[0], vectors[1])


def _section_presence_score(report_text: str) -> Tuple[float, Dict[str, bool]]:
    required = {
        "摘要": ["摘要", "summary", "执行摘要"],
        "分析": ["分析", "analysis", "现状"],
        "预测": ["预测", "趋势", "forecast", "展望"],
        "结论": ["结论", "conclusion"],
    }
    lower = report_text.lower()
    hits: Dict[str, bool] = {}
    for name, keys in required.items():
        hits[name] = any(k.lower() in lower for k in keys)
    score = sum(1 for v in hits.values() if v) / len(required)
    return score, hits


def _actionability_score(report_text: str) -> float:
    keywords = [
        "建议", "应当", "可以", "路线图", "下一步", "优先", "实施", "deploy", "recommend", "action", "milestone",
    ]
    lines = [line.strip() for line in report_text.splitlines() if line.strip()]
    actionable_lines = 0
    for line in lines:
        if any(k in line.lower() for k in keywords):
            actionable_lines += 1
    density = actionable_lines / max(len(lines), 1)
    return max(0.0, min(1.0, density * 8.0))


def _anchor_density(report_text: str, query: str, kb_texts: Sequence[str]) -> Tuple[float, int, int]:
    query_terms = [t for t in _tokenize(query) if len(t) >= 3]
    kb_counter: Counter = Counter()
    for text in kb_texts[:20]:
        kb_counter.update(t for t in _tokenize(text) if len(t) >= 4)
    kb_terms = [term for term, _ in kb_counter.most_common(50)]
    anchors = set(query_terms + kb_terms)

    report_tokens = _tokenize(report_text)
    if not report_tokens:
        return 0.0, 0, 0
    hits = sum(1 for token in report_tokens if token in anchors)
    density = hits / len(report_tokens)
    normalized = max(0.0, min(1.0, density / 0.22))
    return normalized, hits, len(report_tokens)


def _factual_anchor_score(report_text: str, kb_texts: Sequence[str], max_sentences: int = 30) -> Tuple[float, int, int]:
    if not kb_texts:
        return 0.0, 0, 0
    sentences = [s.strip() for s in re.split(r"[。！？!?.]\s*", report_text) if len(s.strip()) >= 16]
    sampled = sentences[:max_sentences]
    if not sampled:
        return 0.0, 0, 0

    kb_join = "\n".join(kb_texts[:30])
    supported = 0
    for sentence in sampled:
        sim = _sentence_similarity(sentence, kb_join)
        if sim >= 0.12:
            supported += 1
    score = supported / max(len(sampled), 1)
    return score, supported, len(sampled)


def compute_metrics(report_text: str, query: str, kb_docs: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    kb_texts = [text for _, text in kb_docs]
    corpus = [report_text, query] + kb_texts[:40]
    vectors, _ = _tfidf_vectors(corpus)
    report_vec = vectors[0]
    query_vec = vectors[1]
    kb_vecs = vectors[2:]

    max_kb_sim = max((_cosine(report_vec, kv) for kv in kb_vecs), default=0.0)
    novelty = max(0.0, min(1.0, 1.0 - max_kb_sim))

    relevance = _cosine(report_vec, query_vec)

    claims = _extract_claims(report_text)
    supported_claims = 0
    for claim in claims:
        if not kb_vecs:
            continue
        claim_vec, _ = _tfidf_vectors([claim, *kb_texts[:20]])
        support_sim = max((_cosine(claim_vec[0], claim_vec[idx]) for idx in range(1, len(claim_vec))), default=0.0)
        if support_sim >= 0.10:
            supported_claims += 1
    grounding = supported_claims / max(len(claims), 1)

    token_count = len(_tokenize(report_text))
    insight_length = _normalize_length_score(token_count)

    insight_hallucination_risk = max(0.0, min(1.0, 1.0 - grounding))

    report_structure_quality, section_hits = _section_presence_score(report_text)

    paragraphs = _split_paragraphs(report_text)
    if len(paragraphs) <= 1:
        report_coherence = 0.4
    else:
        sims = [_sentence_similarity(paragraphs[i], paragraphs[i + 1]) for i in range(len(paragraphs) - 1)]
        report_coherence = sum(sims) / len(sims)

    report_actionability = _actionability_score(report_text)

    insight_anchor_density, anchor_hits, total_tokens = _anchor_density(report_text, query, kb_texts)

    insight_factual_anchor_score, factual_supported, factual_total = _factual_anchor_score(report_text, kb_texts)

    return {
        "novelty": novelty,
        "relevance": relevance,
        "grounding": grounding,
        "insight_length": insight_length,
        "insight_hallucination_risk": insight_hallucination_risk,
        "report_structure_quality": report_structure_quality,
        "report_coherence": report_coherence,
        "report_actionability": report_actionability,
        "insight_anchor_density": insight_anchor_density,
        "insight_factual_anchor_score": insight_factual_anchor_score,
        "diagnostics": {
            "token_count": token_count,
            "claim_count": len(claims),
            "supported_claim_count": supported_claims,
            "section_hits": section_hits,
            "paragraph_count": len(paragraphs),
            "anchor_hits": anchor_hits,
            "total_tokens": total_tokens,
            "factual_supported_sentences": factual_supported,
            "factual_total_sentences": factual_total,
            "kb_doc_count": len(kb_docs),
        },
    }


def _write_markdown_summary(path: Path, payload: Dict[str, Any]) -> None:
    m = payload["metrics"]
    d = m.get("diagnostics", {})
    lines = [
        "# LLM 单独生成报告自动化指标评估",
        "",
        f"- 时间: {payload['meta']['generated_at']}",
        f"- provider/model: `{payload['meta']['provider']}` / `{payload['meta']['model']}`",
        f"- prompt: {payload['meta']['prompt']}",
        f"- KB 文档数: `{d.get('kb_doc_count', 0)}`",
        "",
        "## 指标结果",
        "",
        "| 指标 | 分数 |",
        "|---|---:|",
    ]
    for key in [
        "novelty",
        "relevance",
        "grounding",
        "insight_length",
        "insight_hallucination_risk",
        "report_structure_quality",
        "report_coherence",
        "report_actionability",
        "insight_anchor_density",
        "insight_factual_anchor_score",
    ]:
        lines.append(f"| {key} | {float(m.get(key, 0.0)):.6f} |")

    lines.extend(
        [
            "",
            "## 诊断信息",
            "",
            f"- token_count: `{d.get('token_count', 0)}`",
            f"- claim_support: `{d.get('supported_claim_count', 0)}/{d.get('claim_count', 0)}`",
            f"- factual_sentence_support: `{d.get('factual_supported_sentences', 0)}/{d.get('factual_total_sentences', 0)}`",
            f"- paragraph_count: `{d.get('paragraph_count', 0)}`",
            f"- anchor_hits: `{d.get('anchor_hits', 0)}/{d.get('total_tokens', 0)}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_once(
    prompt: str,
    output_dir: Path,
    provider: str,
    model: str,
    kb_paths: Sequence[Path],
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> Dict[str, Any]:
    _bootstrap_env()
    resolved_provider = _resolve_provider(provider)
    if not resolved_provider:
        raise RuntimeError("No provider available. Set OPENAI_API_KEY or DEEPSEEK_API_KEY (or aliases in .env)")

    api_key, endpoint, resolved_model = _resolve_key_endpoint_model(resolved_provider, model)
    if not api_key or not endpoint:
        raise RuntimeError("Provider key/endpoint missing after env resolution")

    system_prompt = (
        "你是一位医疗AI战略分析师。请围绕用户问题输出结构化、可执行、证据导向的深度分析报告。"
        "必须包含：摘要、现状分析、未来三年趋势、细分方向突破路径、风险与监管、落地建议、结论。"
    )

    llm_resp = _call_chat_completions(
        endpoint=endpoint,
        api_key=api_key,
        model=resolved_model,
        system_prompt=system_prompt,
        user_prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    report_text = _extract_content(llm_resp)
    if not report_text:
        raise RuntimeError("LLM returned empty report")

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "llm_generated_full_report.md"
    report_path.write_text(report_text + ("\n" if not report_text.endswith("\n") else ""), encoding="utf-8")

    kb_docs = _collect_kb_texts(kb_paths)
    metrics = compute_metrics(report_text, prompt, kb_docs)

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "provider": resolved_provider,
            "model": resolved_model,
            "endpoint": endpoint,
            "prompt": prompt,
            "report_path": str(report_path),
            "kb_paths": [str(p) for p in kb_paths],
            "response_usage": llm_resp.get("usage", {}),
        },
        "metrics": metrics,
    }

    json_path = output_dir / "llm_report_auto_metrics.json"
    md_path = output_dir / "llm_report_auto_metrics.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown_summary(md_path, payload)

    return {
        "report_path": str(report_path),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "payload": payload,
    }


def _safe_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_") or "model"


def run_benchmark(
    prompt: str,
    output_dir: Path,
    targets: Sequence[str],
    kb_paths: Sequence[Path],
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    benchmark_dir = output_dir / "benchmark_runs"
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    for index, raw_target in enumerate(targets, start=1):
        target = raw_target.strip()
        if not target:
            continue
        if ":" in target:
            provider, model = target.split(":", 1)
            provider = provider.strip().lower()
            model = model.strip()
        else:
            provider = "openai"
            model = target

        run_dir = benchmark_dir / f"{index:02d}_{_safe_name(provider)}_{_safe_name(model)}"
        try:
            result = run_once(
                prompt=prompt,
                output_dir=run_dir,
                provider=provider,
                model=model,
                kb_paths=kb_paths,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            metrics = (result.get("payload") or {}).get("metrics") or {}
            score = (
                0.10 * float(metrics.get("novelty", 0.0))
                + 0.10 * float(metrics.get("relevance", 0.0))
                + 0.20 * float(metrics.get("grounding", 0.0))
                + 0.05 * float(metrics.get("insight_length", 0.0))
                + 0.15 * (1.0 - float(metrics.get("insight_hallucination_risk", 1.0)))
                + 0.10 * float(metrics.get("report_structure_quality", 0.0))
                + 0.10 * float(metrics.get("report_coherence", 0.0))
                + 0.05 * float(metrics.get("report_actionability", 0.0))
                + 0.075 * float(metrics.get("insight_anchor_density", 0.0))
                + 0.075 * float(metrics.get("insight_factual_anchor_score", 0.0))
            )
            rows.append(
                {
                    "target": target,
                    "provider": provider,
                    "model": model,
                    "success": True,
                    "score": round(score, 6),
                    "run_dir": str(run_dir),
                    "report_path": result.get("report_path", ""),
                    "metrics_json": result.get("json_path", ""),
                    "metrics_markdown": result.get("markdown_path", ""),
                    "metrics": metrics,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "target": target,
                    "provider": provider,
                    "model": model,
                    "success": False,
                    "score": 0.0,
                    "run_dir": str(run_dir),
                    "error": str(exc),
                }
            )

    successes = [row for row in rows if row.get("success")]
    best = max(successes, key=lambda item: float(item.get("score", 0.0))) if successes else None

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "prompt": prompt,
        "targets": list(targets),
        "rows": rows,
        "success_count": len(successes),
        "total_count": len(rows),
        "best_target": (best or {}).get("target", ""),
        "best_score": (best or {}).get("score", 0.0),
    }
    json_path = output_dir / "llm_report_benchmark_summary.json"
    md_path = output_dir / "llm_report_benchmark_summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# LLM 报告生成多模型基准",
        "",
        f"- 时间: {summary['generated_at']}",
        f"- 成功数: `{summary['success_count']}/{summary['total_count']}`",
        f"- 最优目标: `{summary['best_target'] or 'N/A'}`",
        f"- 最优综合分: `{float(summary.get('best_score', 0.0)):.6f}`",
        "",
        "| target | success | score | report_coherence | grounding | factual_anchor |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        metrics = row.get("metrics") or {}
        md_lines.append(
            f"| {row.get('target','')} | {row.get('success', False)} | {float(row.get('score', 0.0)):.6f} | "
            f"{float(metrics.get('report_coherence', 0.0)):.6f} | {float(metrics.get('grounding', 0.0)):.6f} | "
            f"{float(metrics.get('insight_factual_anchor_score', 0.0)):.6f} |"
        )
    md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return {
        "summary": summary,
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate standalone LLM report and compute automated quality metrics")
    parser.add_argument("--prompt", required=True, help="Research prompt for standalone LLM report")
    parser.add_argument("--provider", default="openai", choices=["auto", "openai", "deepseek", "gemini", "qwen"], help="LLM provider")
    parser.add_argument("--model", default="", help="Override model")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=2200)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--kb-path", action="append", default=[], help="KB file/dir for novelty/grounding/factual checks (repeatable)")
    parser.add_argument("--benchmark-targets", default="", help="Comma-separated targets, e.g. deepseek:deepseek-chat,openai:gpt-4o,gemini:gemini-2.0-flash,qwen:qwen-max")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT_DIR / f"experiment/report/llm_standalone_metrics/{_now_tag()}"),
        help="Output directory",
    )
    args = parser.parse_args()

    kb_paths = [Path(p).expanduser().resolve() for p in args.kb_path]
    if not kb_paths:
        default_kb = ROOT_DIR / "experiment/report/step3_runtime_dual_experiment/20260318_full_step3_runtime_dual_v2/comparison"
        kb_paths = [default_kb]

    output_dir = Path(args.output_dir).expanduser().resolve()
    if args.benchmark_targets.strip():
        targets = [item.strip() for item in args.benchmark_targets.split(",") if item.strip()]
        bench = run_benchmark(
            prompt=args.prompt,
            output_dir=output_dir,
            targets=targets,
            kb_paths=kb_paths,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        )
        print(f"[OK] benchmark json: {bench['json_path']}")
        print(f"[OK] benchmark markdown: {bench['markdown_path']}")
        print(f"[INFO] best target: {bench['summary'].get('best_target')}")
    else:
        result = run_once(
            prompt=args.prompt,
            output_dir=output_dir,
            provider=args.provider,
            model=args.model,
            kb_paths=kb_paths,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        )

        print(f"[OK] generated report: {result['report_path']}")
        print(f"[OK] metrics json: {result['json_path']}")
        print(f"[OK] metrics markdown: {result['markdown_path']}")


if __name__ == "__main__":
    main()
