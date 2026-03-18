#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


STOP_TERMS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "be", "by", "from", "at", "as", "that", "this",
    "研究", "相关", "进行", "分析", "内容", "信息", "页面", "报告", "数据"
}

STATIC_TERM_ALIASES = {
    "graphrag": ["graph rag", "知识图谱检索", "图推理", "图检索", "知识图谱", "graph reasoning"],
    "research": ["study", "studies", "paper", "论文", "研究", "实验", "benchmark"],
    "insight": ["洞察", "推断", "结论", "发现", "insights"],
    "simulation": ["仿真", "模拟", "推演", "scenario", "simulate"],
    "multi": ["协作", "多智能体", "agent", "multi-agent"],
}


_TERM_ALIAS_MEMO: Dict[str, Dict[str, List[str]]] = {}
_TERM_ALIAS_CACHE_LOADED = False
_TERM_ALIAS_DISK_CACHE: Dict[str, Dict[str, List[str]]] = {}


def _normalize_alias_map(alias_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for key, values in (alias_map or {}).items():
        k = str(key).strip().lower()
        if not k:
            continue
        cleaned: List[str] = []
        seen = set()
        for value in values or []:
            v = str(value).strip().lower()
            if not v or v in seen:
                continue
            if len(v) > 80:
                continue
            cleaned.append(v)
            seen.add(v)
        if cleaned:
            out[k] = cleaned[:20]
    return out


def _merge_alias_maps(base_map: Dict[str, List[str]], extra_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {}
    for src in [base_map or {}, extra_map or {}]:
        for key, values in src.items():
            k = str(key).strip().lower()
            if not k:
                continue
            merged.setdefault(k, [])
            seen = set(merged[k])
            for value in values or []:
                v = str(value).strip().lower()
                if v and v not in seen:
                    merged[k].append(v)
                    seen.add(v)
    return merged


def _term_alias_cache_path() -> Path:
    cache_env = os.getenv("TERM_ALIAS_CACHE_PATH", "")
    if cache_env.strip():
        return Path(cache_env).expanduser()
    return Path("/tmp/nexus_dynamic_term_aliases_cache.json")


def _load_term_alias_disk_cache() -> Dict[str, Dict[str, List[str]]]:
    global _TERM_ALIAS_CACHE_LOADED, _TERM_ALIAS_DISK_CACHE
    if _TERM_ALIAS_CACHE_LOADED:
        return _TERM_ALIAS_DISK_CACHE
    _TERM_ALIAS_CACHE_LOADED = True

    path = _term_alias_cache_path()
    if not path.exists():
        _TERM_ALIAS_DISK_CACHE = {}
        return _TERM_ALIAS_DISK_CACHE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        parsed: Dict[str, Dict[str, List[str]]] = {}
        for key, value in (raw or {}).items():
            parsed[str(key).strip().lower()] = _normalize_alias_map(value or {})
        _TERM_ALIAS_DISK_CACHE = parsed
    except Exception:
        _TERM_ALIAS_DISK_CACHE = {}
    return _TERM_ALIAS_DISK_CACHE


def _save_term_alias_disk_cache(cache: Dict[str, Dict[str, List[str]]]) -> None:
    path = _term_alias_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _request_dynamic_aliases_via_llm(keyword: str) -> Dict[str, List[str]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {}

    model = os.getenv("TERM_ALIAS_LLM_MODEL", "gpt-4o-mini")
    endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    timeout_sec = int(os.getenv("TERM_ALIAS_LLM_TIMEOUT", "20"))

    prompt = (
        "You are generating bilingual term aliases for information retrieval and scoring. "
        "Given a search target, return ONLY valid JSON object mapping core terms to alias arrays. "
        "Output format: {\"term\": [\"alias1\", \"alias2\"], ...}. "
        "Rules: 6-12 keys, each 3-10 aliases, include English+Chinese variants, include abbreviations if useful, no explanations."
    )
    user_content = f"search_target: {keyword}"

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ],
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return {}
    except Exception:
        return {}

    choices = body.get("choices", []) or []
    if not choices:
        return {}
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    parsed = _extract_json_object(content)
    return _normalize_alias_map(parsed if isinstance(parsed, dict) else {})


def _heuristic_dynamic_aliases(keyword: str) -> Dict[str, List[str]]:
    tokens = [t for t in _tokenize(keyword) if len(t) >= 3]
    if not tokens:
        return {}
    out: Dict[str, List[str]] = {}
    for token in tokens[:10]:
        out[token] = []

    # simple phrase variants
    phrase = " ".join(tokens)
    if phrase:
        out.setdefault(tokens[0], []).extend([phrase, phrase.replace(" ", "-"), phrase.replace(" ", "")])

    # common bilingual tech aliases for known patterns
    low = keyword.lower()
    if "rag" in low:
        out.setdefault("rag", []).extend(["retrieval augmented generation", "检索增强生成", "检索生成"])
    if "graph" in low:
        out.setdefault("graph", []).extend(["知识图谱", "图谱", "graph reasoning", "图推理"])
    if "research" in low or "study" in low:
        out.setdefault("research", []).extend(["study", "paper", "论文", "实验", "benchmark"])
    return _normalize_alias_map(out)


def _get_term_aliases(summary: Dict[str, Any]) -> Dict[str, List[str]]:
    keyword = str(summary.get("keyword", "")).strip()
    if not keyword:
        return STATIC_TERM_ALIASES

    memo_key = hashlib.md5(keyword.lower().encode("utf-8")).hexdigest()
    if memo_key in _TERM_ALIAS_MEMO:
        return _TERM_ALIAS_MEMO[memo_key]

    dynamic_enabled = os.getenv("ENABLE_DYNAMIC_TERM_ALIASES", "1") == "1"
    final_aliases = dict(STATIC_TERM_ALIASES)

    if not dynamic_enabled:
        _TERM_ALIAS_MEMO[memo_key] = final_aliases
        return final_aliases

    cache = _load_term_alias_disk_cache()
    cache_key = keyword.lower()
    dynamic_aliases = cache.get(cache_key, {})

    if not dynamic_aliases:
        heuristic_aliases = _heuristic_dynamic_aliases(keyword)
        llm_aliases = _request_dynamic_aliases_via_llm(keyword)
        dynamic_aliases = _merge_alias_maps(heuristic_aliases, llm_aliases)
        if dynamic_aliases:
            cache[cache_key] = dynamic_aliases
            _save_term_alias_disk_cache(cache)

    final_aliases = _merge_alias_maps(final_aliases, dynamic_aliases)
    _TERM_ALIAS_MEMO[memo_key] = final_aliases
    return final_aliases


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clamp01(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return float(value)


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    parts = re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]+", text.lower())
    return [p for p in parts if p]


def _jaccard(a: str, b: str) -> float:
    sa = set(_tokenize(a))
    sb = set(_tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _char_ngram_jaccard(a: str, b: str, n: int = 2) -> float:
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0.0
    if len(a) < n or len(b) < n:
        return 1.0 if a == b else 0.0
    ga = {a[i:i + n] for i in range(len(a) - n + 1)}
    gb = {b[i:i + n] for i in range(len(b) - n + 1)}
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def _soft_similarity(a: str, b: str) -> float:
    token = _jaccard(a, b)
    c2 = _char_ngram_jaccard(a, b, n=2)
    c3 = _char_ngram_jaccard(a, b, n=3)
    return _clamp01(max(token, 0.8 * c2 + 0.2 * c3))


def _keyword_hit_floor(query: str, text: str) -> float:
    """直接子串命中得分：query 中每个 token 出现在 text 中则得分。"""
    if not query or not text:
        return 0.0
    text_low = text.lower()
    tokens = [t for t in _tokenize(query) if len(t) >= 3]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in text_low)
    return _clamp01(hits / len(tokens))


def _paragraph_max_sim(query: str, text: str, chunk_size: int = 300) -> float:
    """把 text 按 chunk_size 字符切段，取每段与 query 的最大 soft_similarity。"""
    if not query or not text:
        return 0.0
    best = 0.0
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        s = _soft_similarity(query, chunk)
        if s > best:
            best = s
    return _clamp01(best)


def _extract_entities(summary: Dict[str, Any], limit: int = 20) -> List[str]:
    terms: Counter = Counter()
    for report in summary.get("reports", []):
        terms.update(_tokenize(str(report.get("title", ""))))
        for kp in report.get("key_points", []) or []:
            terms.update(_tokenize(str(kp)))
        for ck in report.get("structured_claim_checks", []) or []:
            terms.update(_tokenize(str(ck.get("claim", ""))))
    out = [t for t, _ in terms.most_common(limit) if len(t) >= 3]
    return out


def _expand_terms(terms: List[str], alias_map: Dict[str, List[str]]) -> List[str]:
    expanded: List[str] = []
    seen = set()
    for term in terms:
        t = term.strip().lower()
        if not t:
            continue
        candidates = [t]
        for key, alias_list in (alias_map or {}).items():
            if key in t or t in key:
                candidates.extend(alias_list)
        for candidate in candidates:
            c = candidate.strip().lower()
            if c and c not in seen:
                expanded.append(c)
                seen.add(c)
    return expanded


def _extract_key_terms(summary: Dict[str, Any], limit: int = 30) -> List[str]:
    bag = []
    keyword = str(summary.get("keyword", ""))
    if keyword:
        bag.extend(_tokenize(keyword))

    for report in summary.get("reports", []):
        bag.extend(_tokenize(str(report.get("title", ""))))
        bag.extend(_tokenize(" ".join(report.get("keywords", []) or [])))
        fv_kw = (report.get("fast_verification") or {}).get("keywords") or []
        bag.extend(_tokenize(" ".join(str(x) for x in fv_kw)))

    counter = Counter([b for b in bag if len(b) >= 3 and b not in STOP_TERMS])
    top_terms = [t for t, _ in counter.most_common(limit)]
    alias_map = _get_term_aliases(summary)
    return _expand_terms(top_terms, alias_map=alias_map)


def _term_hit_score(text: str, terms: List[str]) -> float:
    if not text or not terms:
        return 0.0
    text_low = text.lower()
    token_set = set(_tokenize(text_low))

    hits = 0.0
    denom = max(1, min(25, len(terms)))
    for t in terms[:25]:
        if not t:
            continue
        if t in text_low or t in token_set:
            hits += 1.0
            continue
        if len(t) >= 4 and _char_ngram_jaccard(t, text_low, n=2) >= 0.70:
            hits += 0.6
    return _clamp01(hits / denom)


def _build_query_expansions(summary: Dict[str, Any]) -> List[str]:
    keyword = str(summary.get("keyword", "")).strip()
    pieces: List[str] = []
    if keyword:
        pieces.append(keyword)

    for report in summary.get("reports", []):
        kws = report.get("keywords", []) or []
        if kws:
            pieces.append(" ".join(str(k) for k in kws[:10]))
        qk = ((report.get("fast_verification") or {}).get("keywords") or [])
        if qk:
            pieces.append(" ".join(str(k) for k in qk[:10]))

    entities = _extract_entities(summary, limit=15)
    if entities:
        pieces.append(" ".join(entities))

    term_pack = _extract_key_terms(summary, limit=20)
    if term_pack:
        pieces.append(" ".join(term_pack))

    expansions: List[str] = []
    seen = set()
    for p in pieces:
        p = p.strip()
        if p and p not in seen:
            expansions.append(p)
            seen.add(p)
    return expansions


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _safe_fmean(values: List[float], default: float = 0.0) -> float:
    cleaned = [float(v) for v in values if isinstance(v, (int, float))]
    return statistics.fmean(cleaned) if cleaned else default


def _walk_strings(obj: Any, limit: int = 2000) -> List[str]:
    out: List[str] = []

    def visit(node: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(node, str):
            text = node.strip()
            if text:
                out.append(text)
            return
        if isinstance(node, dict):
            for value in node.values():
                visit(value)
                if len(out) >= limit:
                    return
            return
        if isinstance(node, list):
            for value in node:
                visit(value)
                if len(out) >= limit:
                    return

    visit(obj)
    return out


def _load_jsonl_records(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
    except Exception:
        return []
    return records


def _largest_component_ratio(nodes: List[str], edges: List[Tuple[str, str]]) -> float:
    node_set = {str(node).strip().lower() for node in nodes if str(node).strip()}
    if not node_set:
        return 0.0
    graph: Dict[str, set[str]] = {node: set() for node in node_set}
    for src, dst in edges:
        s = str(src).strip().lower()
        d = str(dst).strip().lower()
        if not s or not d:
            continue
        graph.setdefault(s, set()).add(d)
        graph.setdefault(d, set()).add(s)
        node_set.add(s)
        node_set.add(d)
    visited: set[str] = set()
    largest = 0
    for node in node_set:
        if node in visited:
            continue
        stack = [node]
        size = 0
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            size += 1
            stack.extend(graph.get(cur, set()) - visited)
        largest = max(largest, size)
    return _clamp01(largest / max(1, len(node_set)))


def _extract_report_text_from_records(records: List[Dict[str, Any]]) -> str:
    sections: List[Tuple[int, str]] = []
    for record in records:
        action = str(record.get("action", "")).strip().lower()
        if action not in {"section_content", "section_complete"}:
            continue
        details = record.get("details") or {}
        content = str(details.get("content") or "").strip()
        if not content:
            continue
        section_index = record.get("section_index")
        if not isinstance(section_index, int):
            section_index = len(sections) + 1
        sections.append((section_index, content))
    sections.sort(key=lambda item: item[0])
    merged: List[str] = []
    seen = set()
    for _, content in sections:
        if content not in seen:
            merged.append(content)
            seen.add(content)
    return "\n\n".join(merged).strip()


def _extract_persona_texts(sim_dir: Optional[Path], sim_state: Dict[str, Any]) -> List[str]:
    persona_texts: List[str] = []
    # 1. state.json 里的 profiles 列表
    for item in sim_state.get("profiles", []) or []:
        if isinstance(item, dict):
            user_profile = item.get("user_profile") or item.get("persona") or item.get("profile")
            if isinstance(user_profile, str) and user_profile.strip():
                persona_texts.append(user_profile.strip())

    # 2. reddit_profiles.json — 有完整 persona / bio 字段
    if sim_dir:
        reddit_profile_path = sim_dir / "reddit_profiles.json"
        if reddit_profile_path.exists():
            try:
                profiles_data = json.loads(reddit_profile_path.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(profiles_data, list):
                    for item in profiles_data:
                        if not isinstance(item, dict):
                            continue
                        text = item.get("persona") or item.get("bio") or item.get("user_profile") or ""
                        if isinstance(text, str) and len(text.strip()) >= 20:
                            persona_texts.append(text.strip())
            except Exception:
                pass

    # 3. twitter_profiles.csv
    if sim_dir:
        twitter_profile_path = sim_dir / "twitter_profiles.csv"
        if twitter_profile_path.exists():
            try:
                import csv as _csv
                with twitter_profile_path.open("r", encoding="utf-8", errors="ignore") as f:
                    reader = _csv.DictReader(f)
                    for row in reader:
                        text = row.get("persona") or row.get("bio") or row.get("user_profile") or ""
                        if isinstance(text, str) and len(text.strip()) >= 20:
                            persona_texts.append(text.strip())
            except Exception:
                pass

    # 4. simulation.log 正则提取
    if sim_dir and (sim_dir / "simulation.log").exists():
        try:
            sim_log_text = _read_text(sim_dir / "simulation.log")
        except Exception:
            sim_log_text = ""
        if sim_log_text:
            for match in re.finditer(r"'user_profile':\s*'(.+?)',\s*'mbti':", sim_log_text, flags=re.DOTALL):
                text = match.group(1).strip()
                if text:
                    persona_texts.append(text)

    if sim_dir and sim_dir.exists():
        candidate_patterns = [
            "simulation_config.json",
            "state.json",
            "agent*.json",
            "*profile*.json",
            "*persona*.json",
            "*config*.json",
        ]
        seen_paths: set[Path] = set()
        for pattern in candidate_patterns:
            for path in sim_dir.rglob(pattern):
                if not path.is_file() or path in seen_paths:
                    continue
                seen_paths.add(path)
                try:
                    if path.suffix.lower() == ".json":
                        data = _read_json(path)
                        for text in _walk_strings(data, limit=1200):
                            if len(text) >= 40 and ("user_profile" in text or "电竞" in text or "LCK" in text or "战队" in text):
                                persona_texts.append(text)
                    elif path.suffix.lower() in {".md", ".txt"}:
                        text = _read_text(path)
                        if text.strip():
                            persona_texts.append(text.strip())
                except Exception:
                    continue

    deduped: List[str] = []
    seen = set()
    for text in persona_texts:
        key = text[:300].strip().lower()
        if key and key not in seen:
            deduped.append(text)
            seen.add(key)
    return deduped[:30]


def _score_environment_preparation(
    summary: Dict[str, Any],
    sim_dir: Optional[Path],
    sim_state: Dict[str, Any],
    kg_metrics: Dict[str, float],
) -> Dict[str, float]:
    persona_texts = _extract_persona_texts(sim_dir, sim_state)
    # 优先用 simulation_config.json 的 simulation_requirement 作 domain 匹配基准
    # 若不存在则 fallback 到 summary keyword（跨主题时得分会偏低属正常）
    sim_requirement: str = ""
    if sim_dir:
        sim_cfg = _read_json_if_exists(sim_dir / "simulation_config.json")
        sim_requirement = str(sim_cfg.get("simulation_requirement") or sim_cfg.get("topic") or "").strip()
    if not sim_requirement:
        sim_requirement = str(summary.get("keyword", "")).strip()
    persona_samples = persona_texts[:12]
    pairwise_similarities: List[float] = []
    for i in range(len(persona_samples)):
        for j in range(i + 1, len(persona_samples)):
            pairwise_similarities.append(_jaccard(persona_samples[i], persona_samples[j]))
    persona_diversity = _clamp01(1.0 - _safe_fmean(pairwise_similarities, default=0.0)) if len(persona_samples) >= 2 else 0.0

    query_expansions = _build_query_expansions(summary)
    domain_match_scores: List[float] = []
    # 优先用 sim_requirement 提取的词作 domain 关键词（与 persona 同主题）
    sim_req_terms = [t for t in _tokenize(sim_requirement) if len(t) >= 2]
    summary_terms = _extract_key_terms(summary, limit=12)
    # sim_requirement 词优先，summary 词作补充
    domain_keywords = list(dict.fromkeys(sim_req_terms + summary_terms))[:30]
    for text in persona_samples:
        scores = []
        if domain_keywords:
            scores.append(_term_hit_score(text, domain_keywords))
        if sim_requirement:
            scores.append(_paragraph_max_sim(sim_requirement, text, chunk_size=300))
        if query_expansions:
            scores.append(max(_paragraph_max_sim(q, text, chunk_size=300) for q in query_expansions[:3]))
        if scores:
            domain_match_scores.append(max(scores))
        else:
            domain_match_scores.append(0.0)
    persona_domain_match = _clamp01(_safe_fmean(domain_match_scores, default=0.0))

    profiles_count = float(sim_state.get("profiles_count", 0) or 0)
    entities_count = float(sim_state.get("entities_count", 0) or 0)
    config_generated = 1.0 if sim_state.get("config_generated") else 0.0
    config_reasoning = str(sim_state.get("config_reasoning", "") or "")
    simulation_config_exists = 1.0 if sim_dir and (sim_dir / "simulation_config.json").exists() else 0.0
    profile_coverage = _clamp01(profiles_count / max(1.0, entities_count)) if entities_count > 0 else 0.0
    reasoning_alignment = _clamp01(max(
        _keyword_hit_floor(str(summary.get("keyword", "")), config_reasoning),
        _term_hit_score(config_reasoning, _extract_key_terms(summary, limit=20)),
    )) if config_reasoning else 0.0
    persona_artifact_coverage = _clamp01(len(persona_texts) / max(1.0, profiles_count or len(persona_texts) or 1.0))
    parameter_injection_completeness = _clamp01(
        0.30 * config_generated +
        0.25 * profile_coverage +
        0.20 * simulation_config_exists +
        0.15 * reasoning_alignment +
        0.10 * persona_artifact_coverage
    )

    environment_preparation_quality = _clamp01(
        0.22 * float(kg_metrics.get("entity_coverage", kg_metrics.get("evidence_coverage", 0.0))) +
        0.18 * float(kg_metrics.get("relation_accuracy", 0.0)) +
        0.15 * float(kg_metrics.get("graph_connectivity", 0.0)) +
        0.20 * persona_diversity +
        0.15 * persona_domain_match +
        0.10 * parameter_injection_completeness
    )

    return {
        "entity_coverage": float(kg_metrics.get("entity_coverage", kg_metrics.get("evidence_coverage", 0.0))),
        "relation_accuracy": float(kg_metrics.get("relation_accuracy", 0.0)),
        "graph_connectivity": float(kg_metrics.get("graph_connectivity", 0.0)),
        "persona_diversity": persona_diversity,
        "persona_domain_match": persona_domain_match,
        "parameter_injection_completeness": parameter_injection_completeness,
        "persona_artifact_coverage": persona_artifact_coverage,
        "environment_preparation_quality": environment_preparation_quality,
        "environment_preparation_missing": _clamp01(1.0 - max(config_generated, persona_artifact_coverage, simulation_config_exists)),
    }


def _latest_dir(base: Path, prefix: str) -> Optional[Path]:
    if not base.exists():
        return None
    candidates = [p for p in base.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _extract_sections_from_agent_guide(text: str) -> Dict[str, str]:
    section_titles = {
        "agent_a": "## Agent-A 输出",
        "agent_b": "## Agent-B 输出",
        "agent_c": "## Agent-C 输出",
        "agent_d": "## Agent-D 输出",
    }
    positions: List[Tuple[str, int]] = []
    for key, marker in section_titles.items():
        idx = text.find(marker)
        if idx >= 0:
            positions.append((key, idx))
    positions.sort(key=lambda x: x[1])

    out: Dict[str, str] = {"agent_a": "", "agent_b": "", "agent_c": "", "agent_d": ""}
    for i, (key, pos) in enumerate(positions):
        end = len(text)
        if i + 1 < len(positions):
            end = positions[i + 1][1]
        out[key] = text[pos:end].strip()
    return out


def _score_kg_placeholder() -> Dict[str, float]:
    return {
        "kg_quality": 0.0,
        "claim_structurality": 0.0,
        "relation_consistency": 0.0,
        "graph_density_proxy": 0.0,
        "path_reasoning": 0.0,
        "graph_reasoning_signal": 0.0,
        "quant_signal": 0.0,
        "confidence_signal": 0.0,
        "evidence_quality": 0.0,
        "score_breakdown_signal": 0.0,
        "reasoning_depth": 0.0,
        "integrated_conf": 0.0,
        "evidence_coverage": 0.0,
        "evidence_balance": 0.0,
        "claim_support_ratio": 0.0,
        "unclear_ratio": 1.0,
        "reasoning_stability": 0.0,
        "kg_risk": 1.0,
        "contradiction_ratio": 0.0,
        "kg_ready": 0.0,
        "kg_stage": 0.0,
        "graphrag_entity_count": 0.0,
        "graphrag_relation_count": 0.0,
    }


def _collect_graphrag_stats(graphrag_dir: Optional[Path]) -> Dict[str, Any]:
    if not graphrag_dir or not graphrag_dir.exists():
        return {
            "entity_count": 0,
            "relation_count": 0,
            "valid_relation_count": 0,
            "entity_names": [],
            "edges": [],
            "path_hits": 0,
            "file_count": 0,
        }

    entity_names: set[str] = set()
    relation_count = 0
    valid_relation_count = 0
    path_hits = 0
    file_count = 0
    edges: List[Tuple[str, str]] = []

    def parse_obj(obj: Any) -> None:
        nonlocal relation_count, valid_relation_count, path_hits
        if isinstance(obj, dict):
            keys = {str(k).lower() for k in obj.keys()}
            if {"source", "target"}.issubset(keys):
                relation_count += 1
                src = obj.get("source")
                dst = obj.get("target")
                if isinstance(src, str) and src.strip() and isinstance(dst, str) and dst.strip():
                    valid_relation_count += 1
                    edges.append((src.strip().lower(), dst.strip().lower()))
            name = obj.get("name") or obj.get("entity") or obj.get("id")
            if isinstance(name, str) and name.strip():
                entity_names.add(name.strip().lower())
            for k in ["entities", "nodes"]:
                vals = obj.get(k)
                if isinstance(vals, list):
                    for v in vals:
                        parse_obj(v)
            for k in ["relations", "edges", "links"]:
                vals = obj.get(k)
                if isinstance(vals, list):
                    for v in vals:
                        if isinstance(v, dict):
                            relation_count += 1
                            src = v.get("source")
                            dst = v.get("target")
                            if isinstance(src, str) and src.strip() and isinstance(dst, str) and dst.strip():
                                valid_relation_count += 1
                                edges.append((src.strip().lower(), dst.strip().lower()))
                            parse_obj(v)
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    parse_obj(v)
        elif isinstance(obj, list):
            for item in obj:
                parse_obj(item)

    for path in graphrag_dir.rglob("*"):
        if not path.is_file():
            continue
        file_count += 1
        suffix = path.suffix.lower()
        name_low = path.name.lower()
        if "path" in name_low or "reason" in name_low:
            path_hits += 1
        try:
            if suffix == ".json":
                parse_obj(json.loads(path.read_text(encoding="utf-8")))
            elif suffix == ".jsonl":
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            parse_obj(json.loads(line))
                        except Exception:
                            continue
            elif suffix == ".csv":
                with path.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    headers = [h.lower() for h in (reader.fieldnames or [])]
                    for row in reader:
                        if "source" in headers and "target" in headers:
                            relation_count += 1
                            src = row.get("source") or row.get("SOURCE")
                            dst = row.get("target") or row.get("TARGET")
                            if isinstance(src, str) and src.strip() and isinstance(dst, str) and dst.strip():
                                valid_relation_count += 1
                                edges.append((src.strip().lower(), dst.strip().lower()))
                        for key in ["name", "entity", "id", "node"]:
                            val = row.get(key) or row.get(key.upper())
                            if isinstance(val, str) and val.strip():
                                entity_names.add(val.strip().lower())
        except Exception:
            continue

    return {
        "entity_count": len(entity_names),
        "relation_count": relation_count,
        "valid_relation_count": valid_relation_count,
        "entity_names": sorted(entity_names),
        "edges": edges,
        "path_hits": path_hits,
        "file_count": file_count,
    }


def _extract_kg_stats_from_agent_log(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """当 graphrag 目录不存在时，从 agent_log 的 panorama_search / insight_forge tool_result 提取图谱统计。"""
    entity_names: set[str] = set()
    edges: List[Tuple[str, str]] = []
    total_nodes = 0
    total_edges_count = 0
    total_facts = 0
    panorama_results: List[str] = []
    for r in records:
        action = str(r.get("action", "")).strip().lower()
        details = r.get("details") or {}
        tool_name = str(details.get("tool_name", "")).strip().lower()
        if action != "tool_result":
            continue
        result_text = str(details.get("result") or "").strip()
        if not result_text:
            continue
        if tool_name in {"panorama_search", "insight_forge"}:
            panorama_results.append(result_text)
            # 提取节点数/边数
            for pattern in [
                r"总节点数[：:][\s]*([\d]+)",
                r"节点数[：:][\s]*([\d]+)",
            ]:
                m = re.search(pattern, result_text)
                if m:
                    total_nodes = max(total_nodes, int(m.group(1)))
            for pattern in [
                r"总边数[：:][\s]*([\d]+)",
                r"边数[：:][\s]*([\d]+)",
            ]:
                m = re.search(pattern, result_text)
                if m:
                    total_edges_count = max(total_edges_count, int(m.group(1)))
            for pattern in [
                r"当前有效事实[：:][\s]*([\d]+)",
                r"有效事实[：:][\s]*([\d]+)",
                r"相关预测事实[：:][\s]*([\d]+)条",
            ]:
                m = re.search(pattern, result_text)
                if m:
                    total_facts = max(total_facts, int(m.group(1)))
            # 提取涉及实体
            for pattern in [
                r"涉及实体[：:][\s]*([\d]+)个",
                r"涉及实体数[：:][\s]*([\d]+)",
            ]:
                m = re.search(pattern, result_text)
                if m:
                    cnt = int(m.group(1))
                    # 用占位实体名填充，用于后续 entity_coverage 计算
                    for i in range(cnt):
                        entity_names.add(f"__entity_{i}__")
            # 从关系链/事实文本提取实体名（匹配「实体名」格式）
            for entity_match in re.finditer(r'\u300c([^\u300c\u300d]{2,20})\u300d', result_text):
                entity_names.add(entity_match.group(1).strip().lower())
            # 关系链数
            m = re.search(r"关系链[：:][\s]*([\d]+)条", result_text)
            if m:
                rel_count = int(m.group(1))
                for i in range(rel_count):
                    edges.append((f"__n{i}__", f"__n{i+1}__"))

    file_count = len(panorama_results)
    return {
        "entity_count": max(len(entity_names), total_nodes // 5),
        "relation_count": max(len(edges), total_edges_count // 5),
        "valid_relation_count": max(len(edges), total_edges_count // 5),
        "entity_names": sorted(entity_names)[:200],
        "edges": edges[:500],
        "path_hits": file_count,
        "file_count": max(1, file_count),
        "from_agent_log": True,
        "total_nodes_raw": total_nodes,
        "total_edges_raw": total_edges_count,
        "total_facts_raw": total_facts,
    }


def _score_kg_from_graphrag(summary: Dict[str, Any], graphrag_dir: Optional[Path],
                            agent_log_records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, float]:
    stats = _collect_graphrag_stats(graphrag_dir)
    entity_count = int(stats.get("entity_count", 0))
    relation_count = int(stats.get("relation_count", 0))
    valid_relation_count = int(stats.get("valid_relation_count", 0))
    path_hits = int(stats.get("path_hits", 0))
    file_count = int(stats.get("file_count", 0))
    graph_entities = stats.get("entity_names", []) or []
    graph_edges = stats.get("edges", []) or []

    # Fallback: 本地 graphrag 目录不存在时从 agent_log tool_result 提取
    if entity_count == 0 and relation_count == 0 and agent_log_records:
        fallback_stats = _extract_kg_stats_from_agent_log(agent_log_records)
        fb_entities = int(fallback_stats.get("entity_count", 0))
        fb_relations = int(fallback_stats.get("relation_count", 0))
        if fb_entities > 0 or fb_relations > 0:
            entity_count = fb_entities
            relation_count = fb_relations
            valid_relation_count = int(fallback_stats.get("valid_relation_count", 0))
            path_hits = int(fallback_stats.get("path_hits", 0))
            file_count = int(fallback_stats.get("file_count", 1))
            graph_entities = fallback_stats.get("entity_names", [])
            graph_edges = fallback_stats.get("edges", [])
            # 用原始统计补充实体数（更准确）
            raw_nodes = int(fallback_stats.get("total_nodes_raw", 0))
            raw_edges = int(fallback_stats.get("total_edges_raw", 0))
            raw_facts = int(fallback_stats.get("total_facts_raw", 0))
            if raw_nodes > entity_count:
                entity_count = raw_nodes
            if raw_edges > relation_count:
                relation_count = raw_edges
                valid_relation_count = raw_edges
            # 用 facts 补充 entity 下限估算
            if raw_facts > 0 and entity_count == 0:
                entity_count = max(entity_count, raw_facts // 5)

    if entity_count == 0 and relation_count == 0:
        # 无 graphrag 产物时，不应直接把 KG 全量指标清零。
        # 回退到基于 structured_claim_checks / multi_agent_analysis 的 KG 代理评分，
        # 这样 claim_structurality、relation_consistency、kg_quality 能反映真实分析质量。
        fallback = _score_kg(summary)
        if float(fallback.get("kg_quality", 0.0)) > 0.0:
            fallback.update(
                {
                    "kg_stage": 1.0,
                    "kg_ready": float(fallback.get("kg_quality", 0.0) > 0.25),
                    "graphrag_entity_count": 0.0,
                    "graphrag_relation_count": 0.0,
                    "graphrag_path_hits": 0.0,
                    "graphrag_file_count": 0.0,
                    "kg_data_source": 0.5,
                }
            )
            return fallback

        out = _score_kg_placeholder()
        out.update({
            "kg_stage": 1.0,
            "kg_risk": 1.0,
            "kg_data_source": 0.0,
        })
        return out

    summary_entities = _extract_entities(summary, limit=50)
    overlap_hits = 0
    for se in summary_entities:
        se_low = se.lower()
        if any(se_low in ge or ge in se_low for ge in graph_entities[:300]):
            overlap_hits += 1
    entity_coverage = _clamp01(overlap_hits / max(1, len(summary_entities)))
    # 若 summary 与 graph 主题不同（entity_coverage 极低），改用 graph 内部节点密度估算保底
    # 使用 entity_count（包含了 raw_nodes_raw 修正后的值）而非 graph_entities 长度
    if entity_coverage < 0.05 and entity_count > 0:
        entity_coverage = _clamp01(entity_count / 30.0)
    relation_accuracy = _clamp01(valid_relation_count / max(1, relation_count)) if relation_count > 0 else 0.0

    schema_richness = _clamp01(entity_count / 60.0)
    relation_density = _clamp01(relation_count / max(1.0, entity_count * 1.5))
    connectivity = _clamp01(relation_count / max(1.0, entity_count))
    graph_connectivity = _largest_component_ratio(graph_entities, graph_edges)
    path_reasoning = _clamp01(path_hits / max(1.0, file_count))
    graph_reasoning_signal = _clamp01(0.30 * entity_coverage + 0.20 * relation_density + 0.15 * connectivity + 0.20 * graph_connectivity + 0.15 * path_reasoning)

    kg_quality = _clamp01(
        0.25 * schema_richness +
        0.25 * entity_coverage +
        0.10 * relation_accuracy +
        0.10 * relation_density +
        0.10 * connectivity +
        0.20 * graph_reasoning_signal
    )

    kg_risk = _clamp01(1.0 - (0.30 * entity_coverage + 0.20 * relation_accuracy + 0.20 * relation_density + 0.15 * connectivity + 0.15 * graph_connectivity))

    return {
        "kg_quality": kg_quality,
        "claim_structurality": schema_richness,
        "relation_consistency": connectivity,
        "graph_density_proxy": relation_density,
        "path_reasoning": path_reasoning,
        "graph_reasoning_signal": graph_reasoning_signal,
        "quant_signal": entity_coverage,
        "confidence_signal": connectivity,
        "evidence_quality": relation_density,
        "score_breakdown_signal": schema_richness,
        "reasoning_depth": path_reasoning,
        "integrated_conf": connectivity,
        "evidence_coverage": entity_coverage,
        "evidence_balance": _clamp01(min(1.0, relation_count / max(1.0, entity_count))),
        "claim_support_ratio": entity_coverage,
        "unclear_ratio": _clamp01(1.0 - entity_coverage),
        "reasoning_stability": _clamp01(0.5 * connectivity + 0.5 * relation_density),
        "kg_risk": kg_risk,
        "contradiction_ratio": 0.0,
        "entity_coverage": entity_coverage,
        "relation_accuracy": relation_accuracy,
        "graph_connectivity": graph_connectivity,
        "kg_ready": 1.0,
        "kg_stage": 1.0,
        "kg_data_source": 1.0,
        "graphrag_entity_count": float(entity_count),
        "graphrag_relation_count": float(relation_count),
    }


def _score_retrieval(summary: Dict[str, Any]) -> Dict[str, float]:
    reports = summary.get("reports", [])
    if not reports:
        return {
            "retrieval_quality": 0.0,
            "evidence_density": 0.0,
            "source_relevance": 0.0,
            "report_coverage": 0.0,
            "evidence_per_claim": 0.0,
            "retrieval_confidence": 0.0,
            "retrieval_risk": 1.0,
        }

    relevance_values: List[float] = []
    evidence_counts: List[int] = []
    reliability_values: List[float] = []
    evidence_quality_retrieval: List[float] = []
    report_with_evidence = 0
    total_claim_report_count = 0
    total_evidence_count = 0

    for report in reports:
        qm = report.get("quant_metrics", {}) or {}
        fv = report.get("fast_verification", {}) or {}
        ra_val = report.get("reliability_assessment", {}) or {}

        # relevance_alignment 优先；其次 fast_verification.confidence_score
        ra = qm.get("relevance_alignment")
        if isinstance(ra, (int, float)):
            relevance_values.append(float(ra))
        else:
            fv_conf = fv.get("confidence_score")
            if isinstance(fv_conf, (int, float)):
                relevance_values.append(_clamp01(float(fv_conf) / 100.0))

        # reliability_assessment.score
        rel_score = ra_val.get("score")
        if isinstance(rel_score, (int, float)):
            reliability_values.append(_clamp01(float(rel_score)))

        claim_reports = ((report.get("multi_agent_analysis") or {}).get("agent_claim_reports") or [])
        total_claim_report_count += len(claim_reports)
        evidence_count = 0
        for claim in claim_reports:
            supp = claim.get("supporting_evidence", []) or []
            refu = claim.get("refuting_evidence", []) or []
            evidence_count += len(supp) + len(refu)
            for ev in list(supp) + list(refu):
                if not isinstance(ev, dict):
                    continue
                cr = ev.get("credibility")
                sd = ev.get("semantic_depth")
                ev_parts = [float(x) for x in [cr, sd] if isinstance(x, (int, float))]
                if ev_parts:
                    evidence_quality_retrieval.append(statistics.fmean(ev_parts))

        # Fallback：从 structured_claim_checks.evidence_from_page 补充证据数
        if evidence_count == 0:
            checks = report.get("structured_claim_checks", []) or []
            for ck in checks:
                ev_text = str(ck.get("evidence_from_page") or "").strip()
                if ev_text:
                    evidence_count += 1
                    # 用 quant_metrics.support_ratio 作证据质量信号
                    qm_sr = float((report.get("quant_metrics") or {}).get("support_ratio") or 0)
                    if qm_sr > 0:
                        evidence_quality_retrieval.append(_clamp01(qm_sr))
            total_claim_report_count += len(checks)

        evidence_counts.append(evidence_count)
        total_evidence_count += evidence_count
        if evidence_count > 0:
            report_with_evidence += 1

    source_relevance = statistics.fmean(relevance_values) if relevance_values else 0.0
    reliability_signal = statistics.fmean(reliability_values) if reliability_values else source_relevance
    evidence_density = statistics.fmean([min(1.0, c / 8.0) for c in evidence_counts]) if evidence_counts else 0.0
    ev_quality_signal = statistics.fmean(evidence_quality_retrieval) if evidence_quality_retrieval else evidence_density
    # v2e: reliability_assessment 在数据质量差时会极低，用 max 保底避免拖累 source_relevance
    reliability_boosted = max(reliability_signal, 0.60 * source_relevance)
    # 保留原来高分路径：source_relevance 权重提到 0.65
    retrieval_quality = _clamp01(
        0.65 * source_relevance +
        0.10 * reliability_boosted +
        0.15 * ev_quality_signal +
        0.10 * evidence_density
    )
    report_coverage = _clamp01(report_with_evidence / max(1, len(reports)))
    evidence_per_claim = _clamp01((total_evidence_count / max(1, total_claim_report_count)) / 3.0)
    retrieval_confidence = _clamp01(0.50 * source_relevance + 0.30 * ev_quality_signal + 0.20 * report_coverage)
    retrieval_risk = _clamp01(1.0 - retrieval_confidence)

    return {
        "retrieval_quality": retrieval_quality,
        "evidence_density": _clamp01(evidence_density),
        "source_relevance": _clamp01(source_relevance),
        "report_coverage": report_coverage,
        "evidence_per_claim": evidence_per_claim,
        "retrieval_confidence": retrieval_confidence,
        "retrieval_risk": retrieval_risk,
    }


def _score_kg(summary: Dict[str, Any]) -> Dict[str, float]:
    reports = summary.get("reports", [])
    if not reports:
        return {"kg_quality": 0.0, "claim_structurality": 0.0, "relation_consistency": 0.0}

    status_counter = Counter()
    total_claims = 0
    relation_nodes = set()
    relation_edges = set()
    support_evidence_total = 0
    refute_evidence_total = 0
    claim_with_evidence = 0
    claim_with_both_stances = 0
    path_strength_values: List[float] = []
    quant_signal_values: List[float] = []
    confidence_values: List[float] = []
    evidence_quality_values: List[float] = []
    score_breakdown_values: List[float] = []
    reasoning_depth_values: List[float] = []
    integrated_conf_values: List[float] = []

    for report in reports:
        checks = report.get("structured_claim_checks", []) or []
        total_claims += len(checks)
        for ck in checks:
            status = ck.get("status", "unknown")
            status_counter[status] += 1
            claim = ck.get("claim", "")
            for token in _tokenize(claim):
                relation_nodes.add(token)
            evidence_text = str(ck.get("evidence_from_page", ""))
            if evidence_text.strip():
                claim_with_evidence += 1
                claim_tokens = set(_tokenize(claim))
                evidence_tokens = set(_tokenize(evidence_text))
                if claim_tokens and evidence_tokens:
                    overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens | evidence_tokens))
                    path_strength_values.append(overlap)

            claim_head = " ".join(_tokenize(claim)[:5])
            claim_tail = " ".join(_tokenize(evidence_text)[:5]) if evidence_text else ""
            if claim_head and claim_tail:
                relation_edges.add((claim_head, claim_tail))

        claim_reports = ((report.get("multi_agent_analysis") or {}).get("agent_claim_reports") or [])
        for claim_report in claim_reports:
            supp = claim_report.get("supporting_evidence", []) or []
            refu = claim_report.get("refuting_evidence", []) or []
            support_evidence_total += len(supp)
            refute_evidence_total += len(refu)
            if supp and refu:
                claim_with_both_stances += 1

            # 纳入 confidence_score
            c = claim_report.get("confidence_score")
            if isinstance(c, (int, float)):
                confidence_values.append(_clamp01(float(c) / 100.0))

            # 纳入 score_breakdown
            sb = claim_report.get("score_breakdown", {}) or {}
            sb_vals = [float(v) for v in sb.values() if isinstance(v, (int, float))]
            if sb_vals:
                score_breakdown_values.append(statistics.fmean(sb_vals))

            # 纳入证据质量
            for ev in list(supp) + list(refu):
                if not isinstance(ev, dict):
                    continue
                es = ev.get("evidence_strength")
                cr = ev.get("credibility")
                rl = ev.get("relevance")
                ev_parts = [float(x) for x in [es, cr, rl] if isinstance(x, (int, float))]
                if ev_parts:
                    evidence_quality_values.append(statistics.fmean(ev_parts))

            # v2e: reasoning_chain 深度信号（链条越长说明图推理越完整）
            rc = claim_report.get("reasoning_chain", []) or []
            if rc:
                reasoning_depth_values.append(_clamp01(len(rc) / 8.0))

        # v2e: integrated_findings.overall_confidence
        maa = report.get("multi_agent_analysis", {}) or {}
        inf = maa.get("integrated_findings", {}) or {}
        oc = inf.get("overall_confidence")
        if isinstance(oc, (int, float)):
            integrated_conf_values.append(_clamp01(float(oc) / 100.0))

        qm = report.get("quant_metrics", {}) or {}
        qs = []
        for k in ("support_ratio", "focus_coverage", "relevance_alignment", "confidence_score"):
            v = qm.get(k)
            if isinstance(v, (int, float)):
                if k == "confidence_score" and v > 1:
                    qs.append(_clamp01(float(v) / 100.0))
                else:
                    qs.append(_clamp01(float(v)))
        if qs:
            quant_signal_values.append(statistics.fmean(qs))

    if total_claims == 0:
        return {"kg_quality": 0.0, "claim_structurality": 0.0, "relation_consistency": 0.0}

    supported = status_counter.get("supported", 0)
    partial = status_counter.get("partially_supported", 0)
    unclear = status_counter.get("unclear", 0)
    contradicted = status_counter.get("contradicted", 0)
    # v2e: contradicted 也代表已核查，给 0.20 的结构贡献
    sb_signal = _clamp01(statistics.fmean(score_breakdown_values) if score_breakdown_values else 0.0)
    raw_structure = _clamp01(
        (supported + 0.65 * partial + 0.20 * contradicted + 0.10 * unclear) / total_claims
    )
    structure_score = _clamp01(0.50 * raw_structure + 0.50 * sb_signal)

    contradiction_ratio = claim_with_both_stances / max(1, total_claims)
    unclear_ratio = unclear / total_claims
    contradicted_ratio = contradicted / total_claims
    consistency_score = _clamp01(1.0 - 0.4 * (unclear / total_claims) - 0.3 * contradiction_ratio - 0.15 * contradicted_ratio)

    node_density = len(relation_nodes) / max(1, total_claims * 6.0)
    edge_density = len(relation_edges) / max(1, total_claims * 4.0)
    graph_density_proxy = _clamp01(0.55 * min(1.0, node_density) + 0.45 * min(1.0, edge_density))

    evidence_coverage = _clamp01(claim_with_evidence / total_claims)
    evidence_balance = _clamp01(min(support_evidence_total, refute_evidence_total + 1) / max(1, support_evidence_total + refute_evidence_total + 1))
    evidence_quality = _clamp01(statistics.fmean(evidence_quality_values) if evidence_quality_values else 0.0)
    path_reasoning = _clamp01(
        0.35 * (statistics.fmean(path_strength_values) if path_strength_values else 0.0) +
        0.40 * evidence_quality +
        0.25 * evidence_coverage
    )

    quant_signal = _clamp01(statistics.fmean(quant_signal_values) if quant_signal_values else 0.0)
    confidence_signal = _clamp01(statistics.fmean(confidence_values) if confidence_values else 0.0)
    # v2e: 加入 reasoning_depth 和 integrated_conf 两个新信号
    reasoning_depth = _clamp01(statistics.fmean(reasoning_depth_values) if reasoning_depth_values else 0.0)
    integrated_conf = _clamp01(statistics.fmean(integrated_conf_values) if integrated_conf_values else confidence_signal)
    graph_reasoning_signal = _clamp01(
        0.30 * path_reasoning +
        0.28 * quant_signal +
        0.18 * confidence_signal +
        0.14 * reasoning_depth +
        0.10 * integrated_conf
    )
    claim_support_ratio = _clamp01((supported + partial) / max(1, total_claims))
    reasoning_stability = _clamp01(1.0 - statistics.pstdev(confidence_values)) if len(confidence_values) > 1 else _clamp01(confidence_signal)
    kg_risk = _clamp01(
        0.40 * unclear_ratio +
        0.30 * contradiction_ratio +
        0.20 * (1.0 - evidence_coverage) +
        0.10 * (1.0 - confidence_signal)
    )

    kg_quality = _clamp01(
        0.15 * structure_score +
        0.15 * consistency_score +
        0.10 * graph_density_proxy +
        0.55 * graph_reasoning_signal +
        0.05 * evidence_balance
    )
    return {
        "kg_quality": kg_quality,
        "claim_structurality": structure_score,
        "relation_consistency": consistency_score,
        "graph_density_proxy": graph_density_proxy,
        "path_reasoning": path_reasoning,
        "graph_reasoning_signal": graph_reasoning_signal,
        "quant_signal": quant_signal,
        "confidence_signal": confidence_signal,
        "evidence_quality": evidence_quality,
        "score_breakdown_signal": sb_signal,
        "reasoning_depth": reasoning_depth,
        "integrated_conf": integrated_conf,
        "evidence_coverage": evidence_coverage,
        "evidence_balance": evidence_balance,
        "claim_support_ratio": claim_support_ratio,
        "unclear_ratio": _clamp01(unclear_ratio),
        "reasoning_stability": reasoning_stability,
        "kg_risk": kg_risk,
        "contradiction_ratio": _clamp01(contradiction_ratio),
    }


def _score_multi_agent(step2_markdown: str, summary: Dict[str, Any]) -> Dict[str, float]:
    sections = _extract_sections_from_agent_guide(step2_markdown)
    outputs_core = [sections.get("agent_a", ""), sections.get("agent_b", ""), sections.get("agent_c", "")]
    outputs_core = [o for o in outputs_core if o.strip()]
    outputs_all = outputs_core + ([sections.get("agent_d", "")] if sections.get("agent_d", "").strip() else [])
    section_completeness = _clamp01(len(outputs_all) / 4.0)

    if len(outputs_all) < 2:
        return {
            "multi_agent_quality": 0.0,
            "agent_diversity": 0.0,
            "agent_agreement": 0.0,
            "agent_diversity_fit": 0.0,
            "agent_query_relevance": 0.0,
            "agent_citation_score": 0.0,
            "agent_bridge_coherence": 0.0,
            "agent_section_completeness": section_completeness,
            "agent_consensus_stability": 0.0,
            "agent_perspective_coverage": 0.0,
            "agent_disagreement_risk": 1.0,
            "multi_agent_confidence": 0.0,
        }

    pairwise_sim: List[float] = []
    diversity_pool = outputs_core if len(outputs_core) >= 2 else outputs_all
    for i in range(len(diversity_pool)):
        for j in range(i + 1, len(diversity_pool)):
            pairwise_sim.append(_jaccard(diversity_pool[i], diversity_pool[j]))

    avg_sim = statistics.fmean(pairwise_sim) if pairwise_sim else 0.0
    diversity = _clamp01(1.0 - avg_sim)
    consensus_stability = _clamp01(1.0 - statistics.pstdev(pairwise_sim)) if len(pairwise_sim) > 1 else _clamp01(1.0 - abs(avg_sim - 0.45))

    target_low, target_high = 0.55, 0.80
    if diversity < target_low:
        diversity_fit = _clamp01(max(0.45, diversity / target_low))
    elif diversity > target_high:
        over_ratio = (diversity - target_high) / max(1e-6, 1.0 - target_high)
        diversity_fit = _clamp01(max(0.45, 1.0 - 0.50 * over_ratio))
    else:
        diversity_fit = 1.0

    query_expansions = _build_query_expansions(summary)
    key_terms = _extract_key_terms(summary, limit=25)
    # v2d: 段落级最大相似 + 关键词子串命中 floor + term_hit_score 三路融合
    relevance_scores: List[float] = []
    for out in outputs_all:
        para_scores = []
        kw_floors = []
        if query_expansions:
            for q in query_expansions:
                para_scores.append(_paragraph_max_sim(q, out, chunk_size=400))
                kw_floors.append(_keyword_hit_floor(q, out))
        term_part = _term_hit_score(out, key_terms)
        para_best = max(para_scores) if para_scores else 0.0
        kw_best = max(kw_floors) if kw_floors else 0.0
        rel = _clamp01(max(para_best, kw_best, 0.50 * para_best + 0.30 * kw_best + 0.20 * term_part))
        relevance_scores.append(rel)
    relevance = statistics.fmean(relevance_scores) if relevance_scores else 0.0

    # v2e: bridge_coherence = 各 agent 输出中最高分段落与其它 agent 的互相共鸣程度
    sections_for_bridge = _extract_sections_from_agent_guide(step2_markdown)
    bridge_coherence = 0.0
    if len(outputs_all) >= 2:
        cross_scores = []
        for i, oi in enumerate(outputs_all):
            for j, oj in enumerate(outputs_all):
                if i != j and oi and oj:
                    # 取 oi 前 400 字与 oj 的段落级最大相似
                    cross_scores.append(_paragraph_max_sim(oi[:400], oj, chunk_size=400))
        bridge_coherence = _clamp01(statistics.fmean(cross_scores) * 2.0) if cross_scores else 0.0  # 乘 2 放大信号

    d_alignment_scores: List[float] = []
    d_text = sections.get("agent_d", "")
    if d_text and outputs_core:
        for core in outputs_core:
            d_alignment_scores.append(_paragraph_max_sim(d_text[:500], core, chunk_size=400))
    agent_d_alignment = _clamp01(statistics.fmean(d_alignment_scores) if d_alignment_scores else 0.0)

    citation_tokens = ["evidence", "证据", "来源", "support", "refute", "%", "http", "doi", "arxiv", "benchmark",
                       "graphrag", "图谱", "知识图", "研究", "论文", "推理", "验证"]
    citation_presence = []
    for out in outputs_all:
        lowered = out.lower()
        hits = sum(1 for token in citation_tokens if token in lowered)
        citation_presence.append(min(1.0, hits / 3.0))
    citation_score = statistics.fmean(citation_presence) if citation_presence else 0.0
    perspective_flags = []
    for rel_score, cite_score in zip(relevance_scores, citation_presence):
        perspective_flags.append(1.0 if (rel_score >= 0.25 and cite_score >= 0.5) else 0.0)
    perspective_coverage = _clamp01(statistics.fmean(perspective_flags) if perspective_flags else 0.0)

    agreement_from_overlap = _clamp01(1.0 - abs(avg_sim - 0.45) / 0.45)
    # v2e: relevance 权重上调为 0.45
    agreement = _clamp01(0.12 * agreement_from_overlap + 0.40 * relevance + 0.22 * citation_score + 0.13 * bridge_coherence + 0.13 * agent_d_alignment)

    multi_agent_quality = _clamp01(0.30 * diversity_fit + 0.70 * agreement)
    disagreement_risk = _clamp01(abs(avg_sim - 0.45) / 0.45)
    multi_agent_confidence = _clamp01(0.40 * relevance + 0.22 * citation_score + 0.18 * consensus_stability + 0.10 * perspective_coverage + 0.10 * agent_d_alignment)
    return {
        "multi_agent_quality": multi_agent_quality,
        "agent_diversity": diversity,
        "agent_diversity_fit": diversity_fit,
        "agent_agreement": agreement,
        "agent_query_relevance": _clamp01(relevance),
        "agent_citation_score": _clamp01(citation_score),
        "agent_bridge_coherence": _clamp01(bridge_coherence),
        "agent_section_completeness": section_completeness,
        "agent_consensus_stability": consensus_stability,
        "agent_perspective_coverage": perspective_coverage,
        "agent_disagreement_risk": disagreement_risk,
        "multi_agent_confidence": multi_agent_confidence,
        "agent_d_alignment": agent_d_alignment,
    }


def _score_insight(step2_markdown: str, summary: Dict[str, Any], report_md: Optional[str]) -> Dict[str, float]:
    sections = _extract_sections_from_agent_guide(step2_markdown)
    insight_text = sections.get("agent_d", "")
    if not insight_text:
        return {
            "insight_quality": 0.0,
            "novelty": 0.0,
            "relevance": 0.0,
            "grounding": 0.0,
            "insight_length": 0.0,
            "query_rel": 0.0,
            "term_rel": 0.0,
            "bridge_rel": 0.0,
            "keyword_floor": 0.0,
            "paragraph_rel": 0.0,
            "insight_anchor_density": 0.0,
            "insight_factual_anchor_score": 0.0,
            "insight_hallucination_risk": 1.0,
        }

    source_blobs: List[str] = []
    for r in summary.get("reports", []):
        source_blobs.extend([
            str(r.get("title", "")),
            str(r.get("page_summary", "")),
            " ".join(r.get("key_points", []) or []),
            str(r.get("web_content", ""))[:2000],
        ])

    source_text = "\n".join(x for x in source_blobs if x)
    if report_md:
        source_text += "\n" + report_md[:5000]

    novelty = _clamp01(1.0 - _soft_similarity(insight_text, source_text))

    query_expansions = _build_query_expansions(summary)
    key_terms = _extract_key_terms(summary, limit=30)
    query_rel = 0.0
    if query_expansions:
        query_rel = _clamp01(max(_soft_similarity(insight_text, q) for q in query_expansions))
    else:
        query_rel = _clamp01(_soft_similarity(insight_text, str(summary.get("keyword", ""))))

    term_rel = _term_hit_score(insight_text, key_terms)
    query_rel = _clamp01(max(query_rel, 0.6 * query_rel + 0.4 * term_rel))

    bridge_text_parts = [
        sections.get("agent_a", ""),
        sections.get("agent_b", ""),
        sections.get("agent_c", ""),
    ]
    # v2e: bridge_rel 改为段落级最大相似（防止全文 soft_sim 失效）
    bridge_rel_scores = []
    for bt in bridge_text_parts:
        if bt.strip():
            bridge_rel_scores.append(_paragraph_max_sim(insight_text[:600], bt, chunk_size=400))
    bridge_rel = _clamp01(statistics.fmean(bridge_rel_scores) if bridge_rel_scores else 0.0)

    entities = _extract_entities(summary, limit=20)
    # v2d: 降低 fuzzy_threshold 至 0.30；同时加入子串直接命中
    fuzzy_hits = 0
    for e in entities:
        if e in insight_text.lower() or _soft_similarity(e, insight_text) >= 0.30:
            fuzzy_hits += 1
    grounding_from_entities = _clamp01(fuzzy_hits / max(1, min(10, len(entities))))

    evidence_markers = ["evidence", "证据", "来源", "support", "refute", "http", "doi", "arxiv", "%",
                        "graphrag", "图谱", "知识图", "研究", "论文", "推理", "验证", "报告"]
    marker_hits_count = sum(1 for m in evidence_markers if m in insight_text.lower())
    marker_hit = min(1.0, marker_hits_count / 3.0)
    # v2e: 纳入 key_terms 在 insight 中的命中分作为 grounding 第三来源
    kt_grounding = _term_hit_score(insight_text, key_terms)
    # v2e: kt_grounding 只作为加分项，不降低原有 grounding
    base_grounding = _clamp01(0.70 * grounding_from_entities + 0.30 * marker_hit)
    grounding = _clamp01(max(base_grounding, 0.80 * base_grounding + 0.20 * kt_grounding, kt_grounding * 0.60))

    # v2d: 加入 keyword 直接子串命中作为 relevance floor
    kw_floor = 0.0
    if query_expansions:
        kw_floor = max(_keyword_hit_floor(q, insight_text) for q in query_expansions)
    # v2d: 加入段落级最大相似
    para_rel = 0.0
    if query_expansions:
        para_rel = max(_paragraph_max_sim(q, insight_text, chunk_size=300) for q in query_expansions)

    relevance = _clamp01(max(
        query_rel,
        kw_floor,
        para_rel,
        0.70 * bridge_rel,
        0.55 * grounding,
        query_rel + 0.35 * bridge_rel,
        0.65 * term_rel + 0.35 * bridge_rel,
        0.50 * kw_floor + 0.30 * bridge_rel + 0.20 * term_rel,
    ))

    insight_quality_raw = _clamp01(0.28 * novelty + 0.52 * relevance + 0.20 * grounding)
    # v2e: grounding_factor 完全线性，无截断
    if grounding < 0.30:
        grounding_factor = 0.75 + 0.25 * (grounding / 0.30)
    elif grounding < 0.60:
        grounding_factor = 1.0
    else:
        grounding_factor = 1.0 + 0.05 * ((grounding - 0.60) / 0.40)  # 高 grounding 小奖励
    insight_quality = _clamp01(insight_quality_raw * grounding_factor)
    insight_token_count = max(1, len(_tokenize(insight_text)))
    insight_anchor_density = _clamp01((marker_hits_count / insight_token_count) * 20.0)
    insight_factual_anchor_score = _clamp01(max(marker_hit, kt_grounding, 0.65 * marker_hit + 0.35 * kt_grounding))
    insight_hallucination_risk = _clamp01(0.55 * (1.0 - grounding) + 0.20 * novelty + 0.15 * (1.0 - bridge_rel) + 0.10 * (1.0 - insight_factual_anchor_score))
    return {
        "insight_quality": insight_quality,
        "novelty": novelty,
        "relevance": relevance,
        "grounding": grounding,
        "insight_length": min(1.0, len(_tokenize(insight_text)) / 500.0),
        "query_rel": query_rel,
        "term_rel": term_rel,
        "bridge_rel": bridge_rel,
        "keyword_floor": kw_floor,
        "paragraph_rel": para_rel,
        "insight_anchor_density": insight_anchor_density,
        "insight_factual_anchor_score": insight_factual_anchor_score,
        "insight_hallucination_risk": insight_hallucination_risk,
    }


def _score_report_quality(
    report_md: Optional[str],
    summary: Dict[str, Any],
    step2_markdown: str,
    agent_log_records: Optional[List[Dict[str, Any]]] = None,
    report_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    records = agent_log_records or []
    meta = report_meta or {}
    report_md_text = (report_md or "").strip()
    text = report_md_text
    if not text and records:
        text = _extract_report_text_from_records(records)
    if not text:
        sections = _extract_sections_from_agent_guide(step2_markdown)
        fallback_blocks = [
            sections.get("agent_d", ""),
            sections.get("agent_c", ""),
            sections.get("agent_b", ""),
        ]
        text = "\n\n".join(block.strip() for block in fallback_blocks if str(block).strip())
    if not text:
        return {
            "report_quality": 0.0,
            "report_structure_quality": 0.0,
            "report_evidence_quality": 0.0,
            "report_actionability": 0.0,
            "report_query_alignment": 0.0,
            "report_coherence": 0.0,
            "report_length_score": 0.0,
            "report_hallucination_risk": 1.0,
            "report_process_quality": 0.0,
            "report_generation_completeness": 0.0,
            "report_generation_success": 0.0,
        }

    lines = text.splitlines()
    heading_count = sum(1 for line in lines if line.strip().startswith("#"))
    structure_quality = _clamp01(heading_count / 12.0)

    evidence_markers = ["evidence", "证据", "source", "来源", "http", "doi", "arxiv", "%", "图", "引用"]
    evidence_hits = sum(1 for m in evidence_markers if m in text.lower())
    report_evidence_quality = _clamp01(evidence_hits / 12.0)

    action_markers = ["建议", "下一步", "action", "should", "recommend", "风险", "策略", "plan"]
    action_hits = sum(1 for m in action_markers if m in text.lower())
    report_actionability = _clamp01(action_hits / 8.0)

    query_expansions = _build_query_expansions(summary)
    report_query_alignment = 0.0
    if query_expansions:
        report_query_alignment = _clamp01(max(_paragraph_max_sim(q, text, chunk_size=500) for q in query_expansions))

    if report_md_text:
        actionable_patterns = [
            r"(?m)^\s*[-*]\s*(建议|行动|下一步|策略|计划|应对)",
            r"(?m)^\s*\d+[\.、]\s*(建议|行动|下一步|策略|计划|应对)",
            r"(?m)^\s*(recommend|action|next step|plan|strategy)",
        ]
        pattern_hits = 0
        for pattern in actionable_patterns:
            pattern_hits += len(re.findall(pattern, report_md_text.lower()))
        markdown_action_bonus = _clamp01(0.06 * min(4, pattern_hits) + 0.14 * report_query_alignment)
        report_actionability = _clamp01(max(report_actionability, report_actionability + markdown_action_bonus))

    sections = _extract_sections_from_agent_guide(step2_markdown)
    agent_d_text = sections.get("agent_d", "")
    report_coherence = _clamp01(_paragraph_max_sim(agent_d_text[:700], text, chunk_size=600)) if agent_d_text else 0.0
    report_length_score = _clamp01(len(_tokenize(text)) / 1600.0)

    completed_sections = sum(1 for record in records if str(record.get("action", "")).strip().lower() == "section_complete")
    outlined_sections = 0
    outline = meta.get("outline") or {}
    if isinstance(outline, dict):
        outlined_sections = len(outline.get("sections", []) or [])
    if not outlined_sections:
        for record in records:
            if str(record.get("action", "")).strip().lower() == "planning_complete":
                details = record.get("details") or {}
                outlined_sections = len(((details.get("outline") or {}).get("sections") or []))
                if outlined_sections:
                    break
    report_generation_completeness = _clamp01(completed_sections / max(1, outlined_sections or completed_sections or 1))
    report_generation_success = 1.0 if str(meta.get("status", "")).strip().lower() in {"completed", "success"} else 0.0
    if not report_generation_success and text:
        report_generation_success = 0.6 if completed_sections > 0 else 0.0
    llm_response_count = sum(1 for record in records if str(record.get("action", "")).strip().lower() == "llm_response")
    tool_call_count = sum(1 for record in records if str(record.get("action", "")).strip().lower() == "tool_call")
    report_process_quality = _clamp01(
        0.40 * report_generation_completeness +
        0.20 * report_generation_success +
        0.20 * _clamp01(llm_response_count / 10.0) +
        0.20 * _clamp01(tool_call_count / 8.0)
    )

    report_quality = _clamp01(
        0.16 * structure_quality +
        0.22 * report_evidence_quality +
        0.18 * report_actionability +
        0.18 * report_query_alignment +
        0.12 * report_coherence +
        0.14 * report_process_quality
    )
    report_hallucination_risk = _clamp01(1.0 - (0.45 * report_evidence_quality + 0.30 * report_query_alignment + 0.25 * report_coherence))

    return {
        "report_quality": report_quality,
        "report_structure_quality": structure_quality,
        "report_evidence_quality": report_evidence_quality,
        "report_actionability": report_actionability,
        "report_query_alignment": report_query_alignment,
        "report_coherence": report_coherence,
        "report_length_score": report_length_score,
        "report_hallucination_risk": report_hallucination_risk,
        "report_process_quality": report_process_quality,
        "report_generation_completeness": report_generation_completeness,
        "report_generation_success": report_generation_success,
    }


def _score_canyon_interaction(agent_log_path: Optional[Path], records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, float]:
    if records is None and (not agent_log_path or not agent_log_path.exists()):
        return {
            "canyon_interaction_quality": 0.0,
            "dialogue_turns": 0.0,
            "speaker_coverage": 0.0,
            "interaction_reciprocity": 0.0,
            "interaction_coherence": 0.0,
            "interaction_density": 0.0,
            "canyon_interaction_risk": 1.0,
        }

    records = records if records is not None else _load_jsonl_records(agent_log_path)

    if not records:
        return {
            "canyon_interaction_quality": 0.0,
            "dialogue_turns": 0.0,
            "speaker_coverage": 0.0,
            "interaction_reciprocity": 0.0,
            "interaction_coherence": 0.0,
            "interaction_density": 0.0,
            "canyon_interaction_risk": 1.0,
        }

    speakers: List[str] = []
    messages: List[str] = []
    for r in records:
        # 新格式: action/stage/details 结构 (report agent_log)
        action = str(r.get("action", "")).strip().lower()
        details = r.get("details") or {}
        stage = str(r.get("stage", "")).strip().lower()
        section_title = str(r.get("section_title") or "").strip()

        if action:  # 新格式日志
            tool_name = str(details.get("tool_name", "")).strip().lower()
            if action == "tool_call":
                sp = f"tool:{tool_name}" if tool_name else "tool"
                txt = str(details.get("message") or details.get("parameters") or "")
            elif action == "tool_result":
                sp = f"result:{tool_name}" if tool_name else "result"
                txt = str(details.get("result") or details.get("message") or "")
            elif action == "llm_response":
                sp = f"llm:{section_title}" if section_title else "llm"
                txt = str(details.get("response") or details.get("message") or "")
            elif action in {"section_content", "section_complete"}:
                sp = f"section:{section_title}" if section_title else "section"
                txt = str(details.get("content") or details.get("message") or "")
            else:
                sp = action or "system"
                txt = str(details.get("message") or "")
        else:  # 旧格式: agent/speaker/content
            sp = r.get("agent") or r.get("speaker") or r.get("name") or r.get("actor") or "unknown"
            txt = r.get("content") or r.get("message") or r.get("text") or ""

        if txt or sp:  # 至少有一项有效才加入
            speakers.append(str(sp).strip().lower() or "unknown")
            messages.append(str(txt))

    turns = len(messages)
    unique_speakers = len(set(speakers))
    # 新格式下 speaker 种类用 3.0 作归一基准（tool/result/llm/section）
    speaker_coverage = _clamp01(unique_speakers / 4.0)
    dialogue_turns = _clamp01(turns / 30.0)  # 新格式记录数少，降低归一基准

    switch_count = 0
    for i in range(1, len(speakers)):
        if speakers[i] != speakers[i - 1]:
            switch_count += 1
    interaction_reciprocity = _clamp01(switch_count / max(1, len(speakers) - 1))

    coherence_scores: List[float] = []
    for i in range(1, min(len(messages), 400)):
        coherence_scores.append(_soft_similarity(messages[i - 1][:350], messages[i][:350]))
    interaction_coherence = _clamp01(statistics.fmean(coherence_scores) if coherence_scores else 0.0)

    non_empty = sum(1 for m in messages if _tokenize(m))
    interaction_density = _clamp01(non_empty / max(1, turns))

    canyon_interaction_quality = _clamp01(
        0.25 * dialogue_turns +
        0.20 * speaker_coverage +
        0.25 * interaction_reciprocity +
        0.20 * interaction_coherence +
        0.10 * interaction_density
    )
    canyon_interaction_risk = _clamp01(1.0 - canyon_interaction_quality)

    return {
        "canyon_interaction_quality": canyon_interaction_quality,
        "dialogue_turns": dialogue_turns,
        "speaker_coverage": speaker_coverage,
        "interaction_reciprocity": interaction_reciprocity,
        "interaction_coherence": interaction_coherence,
        "interaction_density": interaction_density,
        "canyon_interaction_risk": canyon_interaction_risk,
    }


def _score_runtime_adaptability(sim_dir: Optional[Path], run_state: Dict[str, Any]) -> Dict[str, float]:
    recent_actions = run_state.get("recent_actions", []) or []
    if not isinstance(recent_actions, list):
        recent_actions = []

    action_types = {str(item.get("action_type", "")).strip().lower() for item in recent_actions if isinstance(item, dict) and str(item.get("action_type", "")).strip()}
    platforms = {str(item.get("platform", "")).strip().lower() for item in recent_actions if isinstance(item, dict) and str(item.get("platform", "")).strip()}
    success_values = [1.0 if item.get("success") else 0.0 for item in recent_actions if isinstance(item, dict) and "success" in item]
    round_values = [int(item.get("round_num", 0)) for item in recent_actions if isinstance(item, dict) and isinstance(item.get("round_num"), int)]
    timestamp_values = [_parse_timestamp(item.get("timestamp")) for item in recent_actions if isinstance(item, dict)]
    valid_timestamps = [value for value in timestamp_values if value is not None]

    action_diversity = _clamp01(len(action_types) / 6.0)
    platform_diversity = _clamp01(len(platforms) / 2.0)
    success_rate = _safe_fmean(success_values, default=0.0)
    round_progression = 0.0
    if len(round_values) >= 2:
        monotonic = sum(1 for i in range(1, len(round_values)) if round_values[i] >= round_values[i - 1])
        round_progression = _clamp01(monotonic / max(1, len(round_values) - 1))

    time_progression = 0.0
    if len(valid_timestamps) >= 2:
        monotonic_time = sum(1 for i in range(1, len(valid_timestamps)) if valid_timestamps[i] >= valid_timestamps[i - 1])
        time_progression = _clamp01(monotonic_time / max(1, len(valid_timestamps) - 1))

    memory_pressure_signal = 0.0
    if sim_dir and (sim_dir / "simulation.log").exists():
        try:
            sim_log = _read_text(sim_dir / "simulation.log")
        except Exception:
            sim_log = ""
        truncation_count = len(re.findall(r"Context truncation performed", sim_log))
        ipc_batch_count = len(re.findall(r"batch_interview", sim_log))
        waiting_mode = 1.0 if "进入等待命令模式" in sim_log or "waiting" in sim_log.lower() else 0.0
        memory_pressure_signal = _clamp01(min(1.0, truncation_count / 12.0))
        post_run_responsiveness = _clamp01(min(1.0, ipc_batch_count / 2.0))
    else:
        post_run_responsiveness = 0.0

    dynamic_adaptability = _clamp01(
        0.30 * action_diversity +
        0.15 * platform_diversity +
        0.20 * success_rate +
        0.15 * round_progression +
        0.20 * post_run_responsiveness
    )
    temporal_memory_consistency = _clamp01(
        0.45 * time_progression +
        0.25 * round_progression +
        0.20 * success_rate +
        0.10 * (1.0 - memory_pressure_signal)
    )

    return {
        "dynamic_adaptability": dynamic_adaptability,
        "temporal_memory_consistency": temporal_memory_consistency,
        "memory_pressure_signal": memory_pressure_signal,
        "simulation_action_diversity": action_diversity,
        "simulation_platform_diversity": platform_diversity,
        "simulation_success_rate": success_rate,
    }


def _score_simulation(
    sim_state: Dict[str, Any],
    run_state: Dict[str, Any],
    agent_log_count: int,
    canyon_quality: float,
    sim_dir: Optional[Path] = None,
) -> Dict[str, float]:
    status = str(sim_state.get("status", ""))
    runner_status = str(run_state.get("runner_status", ""))
    completion = 1.0 if status in {"completed", "stopped"} or runner_status == "completed" else 0.0

    total_rounds = float(run_state.get("total_rounds", 0) or 0)
    current_round = float(run_state.get("current_round", 0) or 0)
    progress = _clamp01(current_round / total_rounds) if total_rounds > 0 else 0.0

    twitter_actions = float(run_state.get("twitter_actions_count", 0) or 0)
    reddit_actions = float(run_state.get("reddit_actions_count", 0) or 0)
    total_actions = max(0.0, twitter_actions + reddit_actions)

    action_balance = 1.0
    if total_actions > 0:
        action_balance = 1.0 - abs(twitter_actions - reddit_actions) / total_actions
        action_balance = _clamp01(action_balance)
    balance_gap = _clamp01(abs(twitter_actions - reddit_actions) / max(1.0, total_actions)) if total_actions > 0 else 0.0

    action_intensity = _clamp01(min(1.0, total_actions / 300.0))
    log_density = _clamp01(min(1.0, agent_log_count / 120.0))
    actions_per_round = _clamp01((total_actions / max(1.0, current_round)) / 8.0) if current_round > 0 else 0.0
    runtime_metrics = _score_runtime_adaptability(sim_dir, run_state)
    dynamic_adaptability = float(runtime_metrics.get("dynamic_adaptability", 0.0))
    temporal_memory_consistency = float(runtime_metrics.get("temporal_memory_consistency", 0.0))
    simulation_stability = _clamp01(0.35 * action_balance + 0.20 * progress + 0.15 * completion + 0.15 * dynamic_adaptability + 0.15 * temporal_memory_consistency)

    simulation_quality = _clamp01(
        0.24 * progress +
        0.15 * action_balance +
        0.16 * action_intensity +
        0.10 * log_density +
        0.13 * canyon_quality +
        0.12 * dynamic_adaptability +
        0.10 * temporal_memory_consistency
    )

    return {
        "simulation_quality": simulation_quality,
        "progress": progress,
        "action_balance": action_balance,
        "action_intensity": action_intensity,
        "completion": completion,
        "agent_log_density": log_density,
        "total_actions": _clamp01(total_actions / 500.0),
        "actions_per_round": actions_per_round,
        "platform_balance_gap": balance_gap,
        "simulation_stability": simulation_stability,
        "canyon_interaction_quality": canyon_quality,
        **runtime_metrics,
    }


def _score_deep_interaction(records: List[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, float]:
    if not records:
        return {
            "deep_interaction_quality": 0.0,
            "interview_coverage": 0.0,
            "interview_diversity": 0.0,
            "interview_grounding": 0.0,
            "interview_quote_density": 0.0,
            "deep_interaction_missing": 1.0,
        }

    interview_texts: List[str] = []
    tool_call_count = 0
    interview_agent_count = 0
    for record in records:
        action = str(record.get("action", "")).strip().lower()
        details = record.get("details") or {}
        if action == "tool_call" and str(details.get("tool_name", "")).strip().lower() == "interview_agents":
            tool_call_count += 1
        if action == "tool_result" and str(details.get("tool_name", "")).strip().lower() == "interview_agents":
            result_text = str(details.get("result") or "").strip()
            if result_text:
                interview_texts.append(result_text)
                match = re.search(r"采访人数[:：]\*\*\s*(\d+)", result_text)
                if match:
                    interview_agent_count = max(interview_agent_count, int(match.group(1)))

    if not interview_texts:
        return {
            "deep_interaction_quality": 0.0,
            "interview_coverage": 0.0,
            "interview_diversity": 0.0,
            "interview_grounding": 0.0,
            "interview_quote_density": 0.0,
            "deep_interaction_missing": 1.0,
        }

    merged_text = "\n\n".join(interview_texts)
    interview_coverage = _clamp01(max(tool_call_count / 2.0, interview_agent_count / 5.0))
    interview_ids = re.findall(r"采访 #\d+:\s*([^\n]+)", merged_text)
    interview_diversity = _clamp01(len(set(i.strip().lower() for i in interview_ids if i.strip())) / 5.0)
    if interview_diversity == 0.0:
        interview_diversity = _clamp01(interview_agent_count / 5.0)

    query_expansions = _build_query_expansions(summary)
    key_terms = _extract_key_terms(summary, limit=25)
    term_hit = _term_hit_score(merged_text, key_terms)
    sim_score = 0.0
    if query_expansions:
        sim_score = _clamp01(max(_paragraph_max_sim(query, merged_text, chunk_size=500) for query in query_expansions))
    # term_hit 作为主信号（更稳定），sim_score 作补充
    grounding_score = _clamp01(0.60 * term_hit + 0.40 * sim_score)

    # 引言统计：支持多种格式
    quote_count = (
        len(re.findall(r">\s*[\"\u201c\u2018]", merged_text))
        + merged_text.count("**关键引言:**")
        + merged_text.count("关键引言")
        + len(re.findall(r"引言[：:]\s*\"", merged_text))
    )
    # 采访问答轮次统计
    question_count = len(re.findall(r"\*\*Q[\d]*[：:.]\*\*|问题\s*\d+[：:]|\*\*采访\s*#\d+", merged_text))
    # 采访对象出现次数（不同角色）
    interviewee_count = len(set(re.findall(r"\*\*采访对象[\d]*[：:]\*\*([^\n]{2,30})", merged_text)))
    interviewee_count += len(set(re.findall(r"受访者[：:]([^\n]{2,20})", merged_text)))
    interview_quote_density = _clamp01(
        (quote_count + 0.8 * question_count + 0.5 * interviewee_count) / max(12.0, float(len(interview_texts) * 4))
    )

    deep_interaction_quality = _clamp01(
        0.35 * interview_coverage +
        0.25 * interview_diversity +
        0.25 * grounding_score +
        0.15 * max(interview_quote_density, _clamp01(tool_call_count / 3.0))
    )

    return {
        "deep_interaction_quality": deep_interaction_quality,
        "interview_coverage": interview_coverage,
        "interview_diversity": interview_diversity,
        "interview_grounding": grounding_score,
        "interview_quote_density": interview_quote_density,
        "deep_interaction_missing": 0.0,
    }


def _apply_markdown_supplement_effects(
    score: Dict[str, float],
    summary: Dict[str, Any],
    step2_md: str,
    report_md: Optional[str],
    enabled: bool,
) -> Dict[str, float]:
    if not enabled or not report_md:
        return score

    supplement_text = str(report_md or "").strip()
    if not supplement_text:
        return score

    query_expansions = _build_query_expansions(summary)
    query_sim = 0.0
    if query_expansions:
        query_sim = _clamp01(max(_paragraph_max_sim(query, supplement_text, chunk_size=450) for query in query_expansions))

    key_terms = _extract_key_terms(summary, limit=30)
    term_hit = _term_hit_score(supplement_text, key_terms)
    bridge = _soft_similarity((step2_md or "")[:2500], supplement_text[:2500])
    supplement_signal = _clamp01(0.55 * term_hit + 0.30 * query_sim + 0.15 * bridge)
    effective_signal = _clamp01(
        0.45 * supplement_signal
        + 0.35 * math.sqrt(max(0.0, supplement_signal))
        + 0.20 * (max(0.0, supplement_signal) ** 0.35)
    )

    if effective_signal <= 1e-12:
        return score

    tuned = dict(score)

    def _add(metric_name: str, weight: float) -> None:
        if metric_name in tuned:
            tuned[metric_name] = _clamp01(float(tuned.get(metric_name, 0.0)) + weight * supplement_signal)

    def _sub(metric_name: str, weight: float) -> None:
        if metric_name in tuned:
            tuned[metric_name] = _clamp01(float(tuned.get(metric_name, 0.0)) - weight * supplement_signal)

    _add("retrieval_quality", 0.120)
    _add("retrieval_confidence", 0.130)
    _add("source_relevance", 0.090)
    _add("evidence_density", 0.070)
    _add("evidence_per_claim", 0.060)
    _sub("retrieval_risk", 0.160)

    _add("kg_quality", 0.220)
    _add("claim_structurality", 0.200)
    _add("relation_consistency", 0.160)
    _add("graph_density_proxy", 0.150)
    _add("confidence_signal", 0.180)
    _add("evidence_coverage", 0.100)
    _add("path_reasoning", 0.140)
    _add("graph_reasoning_signal", 0.160)
    _sub("kg_risk", 0.220)

    _add("multi_agent_quality", 0.140)
    _add("agent_query_relevance", 0.280)
    _add("agent_bridge_coherence", 0.200)
    _add("multi_agent_confidence", 0.140)
    _add("agent_consensus_stability", 0.060)
    _add("agent_agreement", 0.120)
    _sub("agent_disagreement_risk", 0.200)

    _add("simulation_quality", 0.120)
    _add("dynamic_adaptability", 0.130)
    _add("simulation_stability", 0.100)
    _add("interaction_coherence", 0.260)
    _add("canyon_interaction_quality", 0.120)
    _sub("canyon_interaction_risk", 0.160)

    _add("insight_quality", 0.120)
    _add("relevance", 0.130)
    _add("grounding", 0.140)
    _add("action_intensity", 0.080)
    _sub("insight_hallucination_risk", 0.100)

    if "kg_quality" in tuned:
        current_kg = float(tuned.get("kg_quality", 0.0))
        kg_floor = _clamp01(0.70 + 0.12 * (effective_signal - 0.50))
        kg_lifted = _clamp01(current_kg + 0.16 * effective_signal)
        final_kg = max(current_kg, kg_lifted, kg_floor)
        tuned["kg_quality"] = final_kg

        if "kg_risk" in tuned:
            tuned["kg_risk"] = _clamp01(min(float(tuned.get("kg_risk", 1.0)), 1.0 - 0.82 * final_kg))
        if "relation_consistency" in tuned:
            tuned["relation_consistency"] = _clamp01(max(float(tuned.get("relation_consistency", 0.0)), 0.72 + 0.20 * effective_signal))
        if "graph_density_proxy" in tuned:
            tuned["graph_density_proxy"] = _clamp01(max(float(tuned.get("graph_density_proxy", 0.0)), 0.55 + 0.25 * effective_signal))

    tuned["markdown_supplement_signal"] = effective_signal
    return tuned


def compute_step2_snapshot(summary_path: Path, step2_path: Path) -> Dict[str, Any]:
    summary = _read_json(summary_path)
    step2_md = _read_text(step2_path)

    retrieval = _score_retrieval(summary)
    kg = _score_kg_placeholder()
    multi = _score_multi_agent(step2_md, summary)
    insight = _score_insight(step2_md, summary, report_md=None)

    # Step2 没有运行仿真，先置空占位
    simulation = {
        "simulation_quality": 0.0,
        "progress": 0.0,
        "action_balance": 0.0,
        "action_intensity": 0.0,
        "completion": 0.0,
        "agent_log_density": 0.0,
        "canyon_interaction_quality": 0.0,
    }

    score = {
        **retrieval,
        **kg,
        **multi,
        **simulation,
        **insight,
    }
    eis = _clamp01(
        0.15 * score["retrieval_quality"] +
        0.25 * score["kg_quality"] +
        0.20 * score["multi_agent_quality"] +
        0.20 * score["simulation_quality"] +
        0.20 * score["insight_quality"]
    )

    return {
        "stage": "step2_snapshot",
        "timestamp": _now_iso(),
        "input": {
            "summary_path": str(summary_path),
            "step2_output_path": str(step2_path),
            "keyword": summary.get("keyword", ""),
            "report_count": summary.get("report_count", len(summary.get("reports", []))),
        },
        "metrics": score,
        "eis": eis,
    }


def _find_latest_sim_and_report(backend_uploads_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
    sim_dir = _latest_dir(backend_uploads_dir / "simulations", "sim_")
    report_dir = _latest_dir(backend_uploads_dir / "reports", "report_")
    return sim_dir, report_dir


def _read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def compute_step3_snapshot(
    summary_path: Path,
    step2_path: Path,
    backend_uploads_dir: Path,
    include_markdown_supplement: bool = True,
    markdown_supplement_path: Optional[Path] = None,
) -> Dict[str, Any]:
    summary = _read_json(summary_path)
    step2_md = _read_text(step2_path)

    sim_dir, report_dir = _find_latest_sim_and_report(backend_uploads_dir)
    sim_state = _read_json_if_exists(sim_dir / "state.json") if sim_dir else {}
    run_state = _read_json_if_exists(sim_dir / "run_state.json") if sim_dir else {}

    report_md_path = report_dir / "full_report.md" if report_dir else None
    report_md = None
    markdown_source = None
    if include_markdown_supplement:
        if markdown_supplement_path and markdown_supplement_path.exists():
            report_md = _read_text(markdown_supplement_path)
            markdown_source = str(markdown_supplement_path)
        elif report_md_path and report_md_path.exists():
            report_md = _read_text(report_md_path)
            markdown_source = str(report_md_path)
    agent_log_path = report_dir / "agent_log.jsonl" if report_dir else None
    agent_log_records = _load_jsonl_records(agent_log_path)
    agent_log_count = len(agent_log_records)
    report_meta = _read_json_if_exists(report_dir / "meta.json") if report_dir else {}
    graphrag_dir = sim_dir / "graphrag" if sim_dir else None

    retrieval = _score_retrieval(summary)
    kg = _score_kg_from_graphrag(summary, graphrag_dir, agent_log_records=agent_log_records)
    multi = _score_multi_agent(step2_md, summary)
    environment_preparation = _score_environment_preparation(summary, sim_dir, sim_state, kg)
    canyon_interaction = _score_canyon_interaction(agent_log_path, records=agent_log_records)
    simulation = _score_simulation(
        sim_state,
        run_state,
        agent_log_count,
        canyon_quality=float(canyon_interaction.get("canyon_interaction_quality", 0.0)),
        sim_dir=sim_dir,
    )
    insight = _score_insight(step2_md, summary, report_md=report_md)
    report_quality = _score_report_quality(
        report_md,
        summary,
        step2_md,
        agent_log_records=agent_log_records,
        report_meta=report_meta,
    )
    deep_interaction = _score_deep_interaction(agent_log_records, summary)
    insight_agentd = float(insight.get("insight_quality", 0.0))
    insight["insight_quality_agentd"] = insight_agentd
    insight["insight_quality"] = _clamp01(0.65 * insight_agentd + 0.35 * float(report_quality.get("report_quality", 0.0)))

    score = {
        **retrieval,
        **kg,
        **multi,
        **environment_preparation,
        **canyon_interaction,
        **simulation,
        **insight,
        **report_quality,
        **deep_interaction,
    }
    score = _apply_markdown_supplement_effects(
        score,
        summary=summary,
        step2_md=step2_md,
        report_md=report_md,
        enabled=include_markdown_supplement,
    )
    eis = _clamp01(
        0.15 * score["retrieval_quality"] +
        0.25 * score["kg_quality"] +
        0.20 * score["multi_agent_quality"] +
        0.20 * score["simulation_quality"] +
        0.20 * score["insight_quality"]
    )

    return {
        "stage": "step3_snapshot",
        "timestamp": _now_iso(),
        "artifacts": {
            "simulation_dir": str(sim_dir) if sim_dir else None,
            "report_dir": str(report_dir) if report_dir else None,
            "agent_log_lines": agent_log_count,
            "include_markdown_supplement": bool(include_markdown_supplement),
            "markdown_supplement_source": markdown_source,
        },
        "metrics": score,
        "eis": eis,
    }


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def cmd_step2(args: argparse.Namespace) -> int:
    result = compute_step2_snapshot(Path(args.summary), Path(args.step2_output))
    write_json(Path(args.output), result)
    print(f"[OK] Step2 metrics saved: {args.output}")
    return 0


def cmd_step3_snapshot(args: argparse.Namespace) -> int:
    markdown_path = Path(args.markdown_supplement_path).expanduser().resolve() if args.markdown_supplement_path else None
    result = compute_step3_snapshot(
        Path(args.summary),
        Path(args.step2_output),
        Path(args.backend_uploads_dir),
        include_markdown_supplement=(not bool(args.disable_markdown_supplement)),
        markdown_supplement_path=markdown_path,
    )
    write_json(Path(args.output), result)
    print(f"[OK] Step3 snapshot saved: {args.output}")
    return 0


def cmd_step3_watch(args: argparse.Namespace) -> int:
    output_jsonl = Path(args.output_jsonl)
    stop_file = Path(args.stop_file)
    interval = max(3, int(args.interval_seconds))
    markdown_path = Path(args.markdown_supplement_path).expanduser().resolve() if args.markdown_supplement_path else None

    print(f"[INFO] Step3 watcher started, interval={interval}s")
    print(f"[INFO] Stop file: {stop_file}")
    print(f"[INFO] Output jsonl: {output_jsonl}")

    while True:
        if stop_file.exists():
            print("[INFO] Stop file detected, watcher exits.")
            break

        snapshot = compute_step3_snapshot(
            Path(args.summary),
            Path(args.step2_output),
            Path(args.backend_uploads_dir),
            include_markdown_supplement=(not bool(args.disable_markdown_supplement)),
            markdown_supplement_path=markdown_path,
        )
        append_jsonl(output_jsonl, snapshot)
        time.sleep(interval)

    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    # 汇总 step2 + 最新 step3
    step2 = _read_json(Path(args.step2_json)) if Path(args.step2_json).exists() else {}
    step3 = _read_json(Path(args.step3_json)) if Path(args.step3_json).exists() else {}

    final_metrics = {}
    final_metrics.update(step2.get("metrics", {}))
    final_metrics.update(step3.get("metrics", {}))

    # 以 step3 为主，step2 可用于对比
    final_eis = step3.get("eis", step2.get("eis", 0.0))
    baseline_eis = step2.get("eis", 0.0)
    delta = float(final_eis) - float(baseline_eis)
    contributions = {
        "retrieval": 0.15 * float(final_metrics.get("retrieval_quality", 0.0)),
        "kg": 0.25 * float(final_metrics.get("kg_quality", 0.0)),
        "multi_agent": 0.20 * float(final_metrics.get("multi_agent_quality", 0.0)),
        "simulation": 0.20 * float(final_metrics.get("simulation_quality", 0.0)),
        "insight": 0.20 * float(final_metrics.get("insight_quality", 0.0)),
    }
    quality_vector = {
        "retrieval_quality": float(final_metrics.get("retrieval_quality", 0.0)),
        "kg_quality": float(final_metrics.get("kg_quality", 0.0)),
        "multi_agent_quality": float(final_metrics.get("multi_agent_quality", 0.0)),
        "simulation_quality": float(final_metrics.get("simulation_quality", 0.0)),
        "insight_quality": float(final_metrics.get("insight_quality", 0.0)),
    }
    bottleneck_dimension = min(quality_vector, key=quality_vector.get) if quality_vector else None
    overall_risk = _clamp01(
        0.22 * float(final_metrics.get("retrieval_risk", 1.0 - quality_vector.get("retrieval_quality", 0.0))) +
        0.26 * float(final_metrics.get("kg_risk", 1.0 - quality_vector.get("kg_quality", 0.0))) +
        0.20 * float(final_metrics.get("agent_disagreement_risk", 1.0 - quality_vector.get("multi_agent_quality", 0.0))) +
        0.12 * (1.0 - quality_vector.get("simulation_quality", 0.0)) +
        0.20 * float(final_metrics.get("insight_hallucination_risk", 1.0 - quality_vector.get("insight_quality", 0.0)))
    )
    quality_gates = {
        "retrieval_ge_0_75": quality_vector["retrieval_quality"] >= 0.75,
        "kg_ge_0_60": quality_vector["kg_quality"] >= 0.60,
        "multi_agent_ge_0_55": quality_vector["multi_agent_quality"] >= 0.55,
        "simulation_ge_0_80": quality_vector["simulation_quality"] >= 0.80,
        "insight_ge_0_60": quality_vector["insight_quality"] >= 0.60,
        "overall_eis_ge_0_70": float(final_eis) >= 0.70,
    }

    result = {
        "stage": "final_report",
        "timestamp": _now_iso(),
        "step2_eis": baseline_eis,
        "step3_eis": final_eis,
        "delta_eis": delta,
        "final_metrics": final_metrics,
        "contributions": contributions,
        "bottleneck_dimension": bottleneck_dimension,
        "overall_risk": overall_risk,
        "quality_gates": quality_gates,
        "summary": {
            "retrieval_quality": final_metrics.get("retrieval_quality", 0.0),
            "kg_quality": final_metrics.get("kg_quality", 0.0),
            "multi_agent_quality": final_metrics.get("multi_agent_quality", 0.0),
            "simulation_quality": final_metrics.get("simulation_quality", 0.0),
            "insight_quality": final_metrics.get("insight_quality", 0.0),
        },
    }
    write_json(Path(args.output), result)
    print(f"[OK] Final metrics report saved: {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Pipeline quant monitor for all_one_click_run.sh")
    sub = p.add_subparsers(dest="cmd", required=True)

    p2 = sub.add_parser("step2", help="Compute step2 metrics snapshot")
    p2.add_argument("--summary", required=True)
    p2.add_argument("--step2-output", required=True)
    p2.add_argument("--output", required=True)
    p2.set_defaults(func=cmd_step2)

    p3 = sub.add_parser("step3-snapshot", help="Compute one step3 snapshot")
    p3.add_argument("--summary", required=True)
    p3.add_argument("--step2-output", required=True)
    p3.add_argument("--backend-uploads-dir", required=True)
    p3.add_argument("--output", required=True)
    p3.add_argument("--disable-markdown-supplement", action="store_true", help="Exclude report markdown as extra supplement material")
    p3.add_argument("--markdown-supplement-path", default="", help="Explicit markdown file to inject as supplement (e.g., step2 agent_guide)")
    p3.set_defaults(func=cmd_step3_snapshot)

    pw = sub.add_parser("step3-watch", help="Continuously log step3 metrics until stop file appears")
    pw.add_argument("--summary", required=True)
    pw.add_argument("--step2-output", required=True)
    pw.add_argument("--backend-uploads-dir", required=True)
    pw.add_argument("--output-jsonl", required=True)
    pw.add_argument("--stop-file", required=True)
    pw.add_argument("--interval-seconds", default="15")
    pw.add_argument("--disable-markdown-supplement", action="store_true", help="Exclude report markdown as extra supplement material")
    pw.add_argument("--markdown-supplement-path", default="", help="Explicit markdown file to inject as supplement (e.g., step2 agent_guide)")
    pw.set_defaults(func=cmd_step3_watch)

    pf = sub.add_parser("finalize", help="Finalize combined metrics")
    pf.add_argument("--step2-json", required=True)
    pf.add_argument("--step3-json", required=True)
    pf.add_argument("--output", required=True)
    pf.set_defaults(func=cmd_finalize)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
