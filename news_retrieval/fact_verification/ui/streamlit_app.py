import json
import os
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
import streamlit as st
from dotenv import load_dotenv

from search import search_news, get_last_search_debug
from fact_verification.agents.webpage_report_agent import WebpageReportAgent
from fact_verification.pipeline.orchestrator import FactVerificationOrchestrator
from fact_verification.scoring.confidence import get_confidence_level_info, verdict_from_score


load_dotenv(override=True)


def _ensure_state() -> None:
    defaults = {
        "search_results": [],
        "search_attempted": False,
        "last_search_info": "",
        "selected_urls": [],
        "selected_search_items": [],
        "hl_marks": [],
        "generated_reports": [],
        "last_hl_export_path": "",
        "keyword": "GraphRAG research",
        "current_open_url": "",
        "page_name": "搜索与浏览",
        "search_provider": os.getenv("SEARCH_PROVIDER", "serpapi"),
        "search_recency": os.getenv("SEARCH_RECENCY", "oneWeek"),
        "theme_mode": "light",
        "relevance_threshold": 0.3,
        "step3_mode": "平衡模式",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value



def _fetch_hypothesis_annotations(url: str) -> list:
    """从 Hypothesis API 拉取指定 URL 下当前用户的全部高亮标注，返回 mark 列表。"""
    username = os.getenv("HYPOTHESIS_USERNAME", "").strip()
    token = os.getenv("HYPOTHESIS_TOKEN", "").strip()
    if not username or not token:
        return []
    try:
        resp = requests.get(
            "https://api.hypothes.is/api/search",
            params={"uri": url, "user": f"acct:{username}@hypothes.is", "limit": 200},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json().get("rows", [])
    except Exception:
        return []

    marks = []
    for ann in rows:
        quote = ""
        for target in ann.get("target", []):
            for sel in target.get("selector", []):
                if sel.get("type") == "TextQuoteSelector":
                    quote = sel.get("exact", "").strip()
                    break
            if quote:
                break
        if not quote:
            continue
        note = ann.get("text", "").strip()
        tags = ann.get("tags", [])
        mark_type = "?" if "?" in tags else "!"
        marks.append({
            "type": mark_type,
            "text": quote,
            "note": note,
            "tags": tags,
            "url": url,
            "hypothesis_id": ann.get("id", ""),
            "timestamp": ann.get("created", datetime.utcnow().isoformat() + "Z"),
            "source": "hypothesis",
        })
    return marks


def _resolve_result_url(item: Dict[str, Any]) -> str:
    url = str(item.get("url", "")).strip()
    if url:
        return url
    related_links = item.get("related_links", []) or []
    if related_links:
        return str(related_links[0].get("url", "")).strip()
    return ""


def _result_item_id(item: Dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(item.get("url", "")).strip(),
            str(item.get("title", "")).strip(),
            str(item.get("snippet", "")).strip(),
            str(item.get("date", "")).strip(),
        ]
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _build_content_report_from_item(item: Dict[str, Any], focus_marks: List[str]) -> Dict[str, Any]:
    title = str(item.get("title", "")).strip()
    snippet = str(item.get("snippet", "")).strip()
    date_text = str(item.get("date", "")).strip()
    blob = f"{title} {snippet}".lower()

    checks = []
    for mark in focus_marks[:12]:
        mark_text = str(mark).strip()
        if not mark_text:
            continue
        tokens = [token.lower() for token in mark_text.split() if len(token) >= 2]
        hit = sum(1 for token in tokens if token in blob)
        if hit >= max(2, len(tokens) // 2):
            status = "supported"
        elif hit >= 1:
            status = "partially_supported"
        else:
            status = "unclear"
        checks.append(
            {
                "claim": mark_text,
                "status": status,
                "evidence_from_page": snippet or title,
            }
        )

    key_points = [point for point in [snippet, title, f"发布时间：{date_text}" if date_text else ""] if point]
    return {
        "url": "",
        "title": title or "（无直链内容）",
        "highlighted_claims": focus_marks,
        "page_summary": snippet,
        "key_points": key_points[:6],
        "risk_flags": ["no_direct_url_content_mode"],
        "keywords": [],
        "reliability_assessment": {
            "score": 0.46,
            "rationale": "No direct URL available; report generated from result title/snippet content.",
        },
        "structured_claim_checks": checks,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generator": "content_only",
        "_source_text_excerpt": "\n".join([part for part in [title, snippet, f"发布时间：{date_text}" if date_text else ""] if part]),
    }


def _dedupe_texts(items: List[str], limit: int = 20) -> List[str]:
    output: List[str] = []
    seen = set()
    for item in items:
        text = " ".join(str(item).split()).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _resolve_focus_marks_payload(marks: List[Dict[str, Any]], url: str) -> Dict[str, List[str]]:
    normalized_marks = [mark for mark in (marks or []) if str(mark.get("text", "")).strip()]
    scoped_marks = [mark for mark in normalized_marks if url and str(mark.get("url", "")).strip() == url]
    active_marks = scoped_marks or normalized_marks

    priority_focus_marks = _dedupe_texts(
        [str(mark.get("text", "")).strip() for mark in active_marks if str(mark.get("type", "")).strip() == "!"],
        limit=12,
    )
    secondary_focus_marks = _dedupe_texts(
        [str(mark.get("text", "")).strip() for mark in active_marks if str(mark.get("type", "")).strip() != "!"],
        limit=12,
    )

    if not priority_focus_marks and normalized_marks:
        priority_focus_marks = _dedupe_texts(
            [str(mark.get("text", "")).strip() for mark in normalized_marks if str(mark.get("type", "")).strip() == "!"],
            limit=12,
        )
    if not secondary_focus_marks and normalized_marks:
        secondary_focus_marks = _dedupe_texts(
            [str(mark.get("text", "")).strip() for mark in normalized_marks if str(mark.get("type", "")).strip() != "!"],
            limit=12,
        )

    focus_marks = _dedupe_texts(priority_focus_marks + secondary_focus_marks, limit=20)
    if not focus_marks:
        focus_marks = ["请重点核查页面中与主题相关的事实信息"]

    return {
        "priority_focus_marks": priority_focus_marks,
        "secondary_focus_marks": secondary_focus_marks,
        "focus_marks": focus_marks,
    }

def _render_keyword_tags(keywords: List[str]) -> None:
    cleaned_keywords = [str(item).strip() for item in keywords if str(item).strip()]
    if not cleaned_keywords:
        st.caption("关键词：未提取")
        return

    tags_html = " ".join(
        f"<span style='display:inline-block;background:#eef4ff;color:#3867d6;border:1px solid #d7e5ff;"
        f"border-radius:999px;padding:2px 10px;margin:2px 6px 2px 0;font-size:0.78rem;font-weight:500;'>#{keyword}</span>"
        for keyword in cleaned_keywords
    )
    st.markdown(tags_html, unsafe_allow_html=True)


def _save_hl_content_json(keyword: str, selected_urls: List[str], marks: List[Dict[str, Any]]) -> str:
    folder = Path("/Users/suleynan_suir/Desktop/grabNews/hl_content")
    folder.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_path = folder / f"hl_content_{ts}.json"

    payload = {
        "keyword": keyword,
        "selected_urls": selected_urls,
        "hl_content": marks,
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(file_path)


def _save_summary_report(
    selected_reports: List[Dict[str, Any]],
    keyword: str,
) -> Dict[str, str]:
    """
    将选中报告保存到项目根目录下的 summary_report/ 文件夹，生成两个文件：
      1. summary_report_<ts>.json  —— 完整报告 JSON
      2. summary_only_<ts>.md      —— 仅包含 page_summary + web_content 的简洁文件

    返回 {"full_path": ..., "summary_path": ...}
    """
    BASE_DIR = Path("/Users/suleynan_suir/Desktop/grabNews")
    folder = BASE_DIR / "summary_report"
    folder.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # ── 1. 完整报告 JSON ──────────────────────────────────────────────────────
    full_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "keyword": keyword,
        "report_count": len(selected_reports),
        "reports": selected_reports,
    }
    full_path = folder / f"summary_report_{ts}.json"
    full_path.write_text(json.dumps(full_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 2. page_summary + web_content 文件（Markdown 格式）───────────────────
    md_lines: List[str] = [
        f"# 深度摘要报告",
        f"",
        f"> 关键词：{keyword}  |  生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"",
        f"---",
        f"",
    ]
    for idx, report in enumerate(selected_reports, start=1):
        title = str(report.get("title", "(无标题)")).strip()
        url = str(report.get("url", "")).strip()
        page_summary = str(report.get("page_summary", "")).strip()
        web_content = str(report.get("web_content", "")).strip()
        generator = str(report.get("generator", "unknown")).strip()

        # 深度分析字段
        deep = report.get("deep_analysis") or {}
        core_claims = deep.get("core_claims") or []
        evidence_chain = deep.get("evidence_chain") or []
        background_context = str(deep.get("background_context", "")).strip()
        implications = deep.get("implications") or []
        limitations = deep.get("limitations") or []
        data_points = deep.get("data_points") or []
        methodology = str(deep.get("methodology", "")).strip()

        md_lines.append(f"## 报告 {idx}：{title}")
        md_lines.append(f"")
        if url:
            md_lines.append(f"**来源：** [{url}]({url})")
        md_lines.append(f"**分析模式：** `{generator}`")
        md_lines.append(f"")

        if page_summary:
            md_lines.append(f"### 📝 深度摘要 (page_summary)")
            md_lines.append(f"")
            md_lines.append(page_summary)
            md_lines.append(f"")

        if core_claims:
            md_lines.append(f"### 🎯 核心主张")
            for c in core_claims:
                md_lines.append(f"- {c}")
            md_lines.append(f"")

        if evidence_chain:
            md_lines.append(f"### 🔗 证据链条")
            for e in evidence_chain:
                md_lines.append(f"- {e}")
            md_lines.append(f"")

        if background_context:
            md_lines.append(f"### 🌐 背景与研究脉络")
            md_lines.append(background_context)
            md_lines.append(f"")

        if implications:
            md_lines.append(f"### 💡 延伸意义与影响")
            for imp in implications:
                md_lines.append(f"- {imp}")
            md_lines.append(f"")

        if limitations:
            md_lines.append(f"### ⚠️ 局限性与注意事项")
            for lim in limitations:
                md_lines.append(f"- {lim}")
            md_lines.append(f"")

        if data_points:
            md_lines.append(f"### 📊 关键数据点")
            for dp in data_points:
                md_lines.append(f"- {dp}")
            md_lines.append(f"")

        if methodology:
            md_lines.append(f"### 🔬 研究方法 / 信息来源")
            md_lines.append(methodology)
            md_lines.append(f"")

        if web_content:
            md_lines.append(f"### 🌐 网页原文 (web_content)")
            md_lines.append(f"")
            md_lines.append("```")
            md_lines.append(web_content[:8000])  # 最多保留 8000 字符
            if len(web_content) > 8000:
                md_lines.append(f"... (原文共 {len(web_content)} 字符，已截断)")
            md_lines.append("```")
            md_lines.append(f"")

        md_lines.append(f"---")
        md_lines.append(f"")

    summary_path = folder / f"summary_only_{ts}.md"
    summary_path.write_text("\n".join(md_lines), encoding="utf-8")

    return {"full_path": str(full_path), "summary_path": str(summary_path)}


def _collect_focus_marks(report_json: Dict[str, Any]) -> List[str]:
    focus_marks = []
    focus_marks.extend(report_json.get("focused_hl_content", []) or [])
    focus_marks.extend(report_json.get("priority_focus_marks", []) or [])
    focus_marks.extend(report_json.get("secondary_focus_marks", []) or [])
    focus_marks.extend(report_json.get("highlighted_claims", []) or [])

    deduped: List[str] = []
    seen = set()
    for item in focus_marks:
        text = " ".join(str(item).split()).strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        deduped.append(text)
        if len(deduped) >= 20:
            break
    return deduped


def _focus_relevance_score(text: str, focus_marks: List[str]) -> float:
    candidate = " ".join(str(text or "").split()).strip()
    if not candidate:
        return 0.0
    if not focus_marks:
        return 0.6

    candidate_lower = candidate.lower()
    candidate_tokens = set(_tokenize_text(candidate_lower))

    token_overlaps: List[float] = []
    phrase_hits = 0
    for mark in focus_marks:
        mark_text = " ".join(str(mark).split()).strip()
        if not mark_text:
            continue
        mark_lower = mark_text.lower()
        mark_tokens = set(_tokenize_text(mark_lower))
        if mark_lower in candidate_lower:
            phrase_hits += 1
        if mark_tokens:
            token_overlaps.append(len(mark_tokens & candidate_tokens) / max(1, len(mark_tokens)))

    token_score = max(token_overlaps) if token_overlaps else 0.0
    phrase_score = phrase_hits / max(1, len(focus_marks))
    return round(min(1.0, 0.62 * token_score + 0.38 * phrase_score), 3)


def _select_relevant_texts(candidates: List[str], focus_marks: List[str], top_k: int, min_score: float = 0.16) -> List[str]:
    scored: List[Tuple[float, str]] = []
    for item in candidates:
        text = " ".join(str(item).split()).strip()
        if not text:
            continue
        score = _focus_relevance_score(text, focus_marks)
        scored.append((score, text))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [text for score, text in scored if score >= min_score][:top_k]
    if selected:
        return selected
    return [text for _score, text in scored[:top_k]]


def _report_text_for_fast_verify(report_json: Dict[str, Any]) -> str:
    title = str(report_json.get("title", "")).strip()
    summary = str(report_json.get("page_summary", "")).strip()
    key_points = report_json.get("key_points", []) or []
    claim_checks = report_json.get("structured_claim_checks", []) or []
    multi_agent = report_json.get("multi_agent_analysis", {}) or {}
    integrated = multi_agent.get("integrated_findings", {}) or {}
    agent_claim_reports = multi_agent.get("agent_claim_reports", []) or []
    focus_marks = _collect_focus_marks(report_json)
    try:
        strictness = float(report_json.get("_relevance_threshold", 0.3) or 0.3)
    except Exception:
        strictness = 0.3
    strictness = max(0.2, min(0.4, strictness))

    keypoint_min = max(0.08, strictness - 0.1)
    consensus_min = max(0.12, strictness - 0.04)
    risk_min = max(0.12, strictness - 0.04)
    check_min = strictness
    agent_min = min(0.5, strictness + 0.05)

    lines = [title, summary]
    lines.extend(_select_relevant_texts([str(point).strip() for point in key_points[:10]], focus_marks, top_k=6, min_score=keypoint_min))
    lines.extend(
        _select_relevant_texts(
            [str(item).strip() for item in (integrated.get("key_consensus_points", []) or [])[:8]],
            focus_marks,
            top_k=5,
            min_score=consensus_min,
        )
    )
    lines.extend(
        _select_relevant_texts(
            [str(item).strip() for item in (integrated.get("major_risks", []) or [])[:8]],
            focus_marks,
            top_k=4,
            min_score=risk_min,
        )
    )
    narrative_summary = str(integrated.get("narrative_summary", "")).strip()
    if narrative_summary:
        lines.append(narrative_summary)

    check_lines: List[str] = []
    for check in claim_checks[:16]:
        claim = str(check.get("claim", "")).strip()
        status = str(check.get("status", "")).strip()
        evidence = str(check.get("evidence_from_page", "")).strip()
        if claim:
            check_lines.append(f"Claim: {claim}; Status: {status}; Evidence: {evidence}")
    lines.extend(_select_relevant_texts(check_lines, focus_marks, top_k=8, min_score=check_min))

    agent_lines: List[str] = []
    for agent_item in agent_claim_reports[:10]:
        claim = str(agent_item.get("claim", "")).strip()
        verdict = str(agent_item.get("verdict", "")).strip()
        confidence_score = agent_item.get("confidence_score", 0.0)
        evidence = ""
        supporting = agent_item.get("supporting_evidence", []) or []
        if supporting:
            evidence = str(supporting[0].get("quote", "")).strip()
        elif agent_item.get("refuting_evidence"):
            evidence = str((agent_item.get("refuting_evidence") or [])[0].get("quote", "")).strip()
        if claim:
            agent_lines.append(f"AgentClaim: {claim}; Verdict: {verdict}; Confidence: {confidence_score}; Evidence: {evidence}")
    lines.extend(_select_relevant_texts(agent_lines, focus_marks, top_k=6, min_score=agent_min))

    deduped = []
    seen = set()
    for item in lines:
        cleaned = " ".join(str(item).split()).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return "\n".join(deduped)


def _aggregate_fast_reports(reports) -> Dict[str, Any]:
    if not reports:
        return {
            "confidence_score": 0.0,
            "verdict": "insufficient",
            "confidence_level": get_confidence_level_info(0.0),
            "keywords": [],
        }

    best_report = max(reports, key=lambda item: item.confidence_score)
    avg_confidence = round(sum(item.confidence_score for item in reports) / len(reports), 2)

    keywords = set()
    for report in reports:
        for evidence in report.supporting_evidence[:3]:
            quote = (evidence.quote or "").strip()
            for token in quote.split():
                if 3 <= len(token) <= 18:
                    keywords.add(token)

    return {
        "confidence_score": avg_confidence,
        "verdict": best_report.verdict,
        "confidence_level": best_report.confidence_level,
        "keywords": sorted(keywords)[:12],
    }


def _quick_fast_result_local(report_json: Dict[str, Any], focus_marks: List[str]) -> Dict[str, Any]:
    checks = report_json.get("structured_claim_checks", []) or []
    reliability = report_json.get("reliability_assessment", {}) or {}
    key_points = report_json.get("key_points", []) or []
    base = 48.0
    support_ratio = _weighted_support_ratio(checks)
    coverage = _focus_coverage_score(report_json, focus_marks)
    relevance = _report_relevance_alignment(report_json, focus_marks)
    try:
        reliability_score = float(reliability.get("score", 0.55) or 0.55)
    except Exception:
        reliability_score = 0.55
    score = (
        base
        + 26.0 * support_ratio
        + 14.0 * relevance
        + 8.0 * coverage
        + 9.0 * max(0.0, min(1.0, reliability_score))
    )
    score = max(20.0, min(96.0, round(score, 2)))
    keywords = set()
    for text in key_points[:8]:
        for token in str(text).split():
            cleaned = str(token).strip("，。；：,.!?:;()[]{}\"'“”")
            if 3 <= len(cleaned) <= 18:
                keywords.add(cleaned)
    return {
        "confidence_score": score,
        "verdict": verdict_from_score(score),
        "confidence_level": get_confidence_level_info(score),
        "keywords": sorted(keywords)[:12],
    }


def _fast_result_from_multi_agent(report_json: Dict[str, Any]) -> Dict[str, Any] | None:
    multi_agent = report_json.get("multi_agent_analysis", {}) or {}
    agent_claim_reports = multi_agent.get("agent_claim_reports", []) or []
    integrated = multi_agent.get("integrated_findings", {}) or {}
    if not agent_claim_reports:
        return None

    try:
        focus_marks = _collect_focus_marks(report_json)
        weighted_sum = 0.0
        total_weight = 0.0
        relevance_scores: List[float] = []
        for item in agent_claim_reports:
            claim = str(item.get("claim", "") or "").strip()
            evidence_text = ""
            supporting = item.get("supporting_evidence") or []
            if supporting:
                evidence_text = str(supporting[0].get("quote", "") or "").strip()
            relevance = _focus_relevance_score(f"{claim} {evidence_text}", focus_marks)
            relevance_scores.append(relevance)
            weight = 0.35 + 0.65 * relevance
            weighted_sum += float(item.get("confidence_score", 0.0) or 0.0) * weight
            total_weight += weight

        avg_confidence = round(weighted_sum / max(1e-6, total_weight), 2)
        relevance_alignment = sum(relevance_scores) / max(1, len(relevance_scores)) if relevance_scores else 0.0
        if relevance_alignment >= 0.72:
            avg_confidence = min(96.0, round(avg_confidence + 6.5, 2))
        elif relevance_alignment >= 0.58:
            avg_confidence = min(94.0, round(avg_confidence + 3.0, 2))
    except Exception:
        avg_confidence = 0.0

    verdict = str(integrated.get("overall_verdict", "")).strip() or verdict_from_score(avg_confidence)
    confidence_level = integrated.get("overall_confidence_level") or get_confidence_level_info(avg_confidence)

    keywords = set()
    for item in agent_claim_reports[:6]:
        evidence_candidates = (item.get("supporting_evidence") or [])[:2]
        if not evidence_candidates:
            evidence_candidates = (item.get("refuting_evidence") or [])[:2]
        for evidence in evidence_candidates:
            quote = str(evidence.get("quote", "") or "").strip()
            for token in quote.split():
                if 3 <= len(token) <= 18:
                    keywords.add(token)

    return {
        "confidence_score": avg_confidence,
        "verdict": verdict,
        "confidence_level": confidence_level,
        "keywords": sorted(keywords)[:12],
    }


def _build_and_verify_single_item(
    picked_item: Dict[str, Any],
    marks: List[Dict[str, Any]],
    relevance_threshold: float = 0.3,
    step3_mode: str = "平衡模式",
) -> Dict[str, Any]:
    local_agent = WebpageReportAgent()
    mode = str(step3_mode or "平衡模式").strip()
    if mode == "极速模式":
        use_llm = False
        llm_strategy = "off"
        enable_multi_agent_analysis = False
        skip_external_verify = True
    elif mode == "深度模式":
        use_llm = True
        llm_strategy = "deep"
        enable_multi_agent_analysis = True
        skip_external_verify = False
    else:
        use_llm = True
        llm_strategy = "assist"
        enable_multi_agent_analysis = False
        skip_external_verify = True
    url = _resolve_result_url(picked_item)
    focus_payload = _resolve_focus_marks_payload(marks, url)
    priority_focus_marks = focus_payload["priority_focus_marks"]
    secondary_focus_marks = focus_payload["secondary_focus_marks"]
    focus_marks = focus_payload["focus_marks"]

    if url:
        try:
            item_snippet = str(picked_item.get("snippet", "") or "").strip()
            report_json = local_agent.build_report(
                url,
                focus_marks,
                priority_focus_marks=priority_focus_marks,
                secondary_focus_marks=secondary_focus_marks,
                enable_multi_agent_analysis=enable_multi_agent_analysis,
                snippet=item_snippet,
                use_llm=use_llm,
                llm_strategy=llm_strategy,
            )
        except Exception as error:
            report_json = {
                "url": url,
                "title": "",
                "highlighted_claims": focus_marks,
                "page_summary": "",
                "key_points": [],
                "risk_flags": [f"report_generation_failed: {error}"],
                "keywords": [],
                "reliability_assessment": {"score": 0.2, "rationale": "generation_failed"},
                "structured_claim_checks": [],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "generator": "error",
                "_source_text_excerpt": "",
            }
    else:
        report_json = _build_content_report_from_item(picked_item, focus_marks)
        report_json["priority_focus_marks"] = priority_focus_marks
        report_json["secondary_focus_marks"] = secondary_focus_marks
        if enable_multi_agent_analysis:
            report_json["multi_agent_analysis"] = local_agent.build_multi_agent_analysis(
                report_json,
                priority_focus_marks,
                secondary_focus_marks,
            )
            report_json["structured_claim_checks"] = local_agent.merge_multi_agent_claim_checks(
                report_json.get("structured_claim_checks", []),
                report_json["multi_agent_analysis"].get("agent_claim_reports", []),
            )

    fast_result = _fast_result_from_multi_agent(report_json)
    if fast_result is None:
        if skip_external_verify:
            fast_result = _quick_fast_result_local(report_json, focus_marks)
        else:
            verify_input = _report_text_for_fast_verify(report_json)
            local_orchestrator = FactVerificationOrchestrator()
            fast_reports = local_orchestrator.verify_text(verify_input, source_type="web_report", mode="fast")
            fast_result = _aggregate_fast_reports(fast_reports)

    report_json["fast_verification"] = {
        "confidence_score": fast_result["confidence_score"],
        "confidence_level": fast_result["confidence_level"],
        "verdict": fast_result["verdict"],
        "keywords": fast_result["keywords"],
    }
    report_json["_relevance_threshold"] = max(0.2, min(0.4, float(relevance_threshold)))
    report_json["quant_metrics"] = _calc_report_metrics(report_json, focus_marks)
    report_json["focused_hl_content"] = focus_marks
    report_json["priority_focus_marks"] = report_json.get("priority_focus_marks", priority_focus_marks)
    report_json["secondary_focus_marks"] = report_json.get("secondary_focus_marks", secondary_focus_marks)
    return report_json


def _normalize_check_status(status: str) -> str:
    normalized = str(status or "").strip().lower()
    mapping = {
        "support": "supported",
        "supported": "supported",
        "partially_supported": "partially_supported",
        "partial": "partially_supported",
        "related": "partially_supported",
        "consistent": "partially_supported",
        "unclear": "unclear",
        "unknown": "unclear",
        "mixed": "unclear",
        "contradicted": "contradicted",
        "refuted": "contradicted",
        "refute": "contradicted",
        "支持": "supported",
        "部分支持": "partially_supported",
        "相关": "partially_supported",
        "不明确": "unclear",
        "矛盾": "contradicted",
        "反驳": "contradicted",
    }
    return mapping.get(normalized, "unclear")


def _tokenize_text(text: str) -> List[str]:
    lowered = str(text or "").lower()
    return [token for token in re.split(r"[^\w\u4e00-\u9fff]+", lowered) if len(token) >= 2]


def _weighted_support_ratio(checks: List[Dict[str, Any]]) -> float:
    if not checks:
        return 0.0

    status_weights = {
        "supported": 1.0,
        "partially_supported": 0.72,
        "unclear": 0.4,
        "contradicted": 0.0,
    }
    weighted = sum(status_weights.get(_normalize_check_status(item.get("status", "")), 0.4) for item in checks)
    return round(weighted / len(checks), 3)


def _focus_coverage_score(report_json: Dict[str, Any], focus_marks: List[str]) -> float:
    normalized_marks = [str(mark).strip() for mark in focus_marks if str(mark).strip()]
    if not normalized_marks:
        return 0.6

    text_blob = " ".join(
        [
            str(report_json.get("title", "")),
            str(report_json.get("page_summary", "")),
            " ".join(str(item) for item in (report_json.get("key_points", []) or [])),
            " ".join(str(item.get("claim", "")) for item in (report_json.get("structured_claim_checks", []) or [])),
            " ".join(str(item.get("evidence_from_page", "")) for item in (report_json.get("structured_claim_checks", []) or [])),
        ]
    ).lower()
    blob_tokens = set(_tokenize_text(text_blob))

    scores: List[float] = []
    for mark in normalized_marks:
        mark_lower = mark.lower()
        if mark_lower in text_blob:
            scores.append(1.0)
            continue

        mark_tokens = set(_tokenize_text(mark_lower))
        if mark_tokens:
            overlap = len(mark_tokens & blob_tokens) / max(1, len(mark_tokens))
            scores.append(min(1.0, overlap))
        else:
            scores.append(0.0)

    return round(sum(scores) / max(1, len(scores)), 3)


def _report_relevance_alignment(report_json: Dict[str, Any], focus_marks: List[str]) -> float:
    if not focus_marks:
        return 0.65

    candidates: List[str] = []
    candidates.append(str(report_json.get("title", "")))
    candidates.append(str(report_json.get("page_summary", "")))
    candidates.extend(str(item) for item in (report_json.get("key_points", []) or [])[:8])
    for check in (report_json.get("structured_claim_checks", []) or [])[:12]:
        claim = str(check.get("claim", "") or "").strip()
        evidence = str(check.get("evidence_from_page", "") or "").strip()
        candidates.append(f"{claim} {evidence}".strip())

    scored = [_focus_relevance_score(text, focus_marks) for text in candidates if str(text).strip()]
    if not scored:
        return 0.0
    scored.sort(reverse=True)
    top = scored[: min(8, len(scored))]
    top_avg = round(sum(top) / len(top), 3)
    coverage = _focus_coverage_score(report_json, focus_marks)
    return round(max(top_avg, coverage), 3)


def _derive_report_confidence(report_json: Dict[str, Any], focus_marks: List[str]) -> Dict[str, Any]:
    fast_result = report_json.get("fast_verification", {}) or {}
    checks = report_json.get("structured_claim_checks", []) or []
    risk_flags = report_json.get("risk_flags", []) or []
    key_points = report_json.get("key_points", []) or []
    reliability = report_json.get("reliability_assessment", {}) or {}

    fast_score = float(fast_result.get("confidence_score", 0.0) or 0.0)
    fast_signal = max(0.0, min(1.0, fast_score / 100.0)) if fast_score > 0 else None
    support_ratio = _weighted_support_ratio(checks)
    focus_coverage = _focus_coverage_score(report_json, focus_marks)
    relevance_alignment = _report_relevance_alignment(report_json, focus_marks)

    reliability_score = reliability.get("score", None)
    try:
        reliability_score = float(reliability_score)
    except Exception:
        reliability_score = None

    if reliability_score is None:
        generator = str(report_json.get("generator", "")).lower()
        if generator == "llm":
            reliability_score = 0.72
        elif generator == "fallback":
            reliability_score = 0.58
        elif generator == "error":
            reliability_score = 0.28
        else:
            reliability_score = 0.4

    check_coverage = min(
        1.0,
        len(checks) / max(1, max(len(report_json.get("highlighted_claims", []) or []), 3)),
    )
    evidence_coverage = sum(1 for item in checks if str(item.get("evidence_from_page", "")).strip()) / max(1, len(checks)) if checks else 0.0
    richness = min(
        1.0,
        0.45 * min(1.0, len(key_points) / 5.0)
        + 0.25 * min(1.0, len(str(report_json.get("page_summary", "")).strip()) / 240.0)
        + 0.30 * evidence_coverage,
    )

    contradicted_count = sum(1 for item in checks if _normalize_check_status(item.get("status", "")) == "contradicted")
    supported_count = sum(1 for item in checks if _normalize_check_status(item.get("status", "")) in {"supported", "partially_supported"})
    risk_penalty = min(0.18, 0.035 * len(risk_flags) + 0.04 * contradicted_count)

    if fast_signal is None:
        combined = (
            0.36 * support_ratio
            + 0.20 * reliability_score
            + 0.16 * focus_coverage
            + 0.16 * relevance_alignment
            + 0.08 * check_coverage
            + 0.04 * richness
        )
    else:
        combined = (
            0.40 * fast_signal
            + 0.20 * support_ratio
            + 0.12 * reliability_score
            + 0.12 * focus_coverage
            + 0.10 * relevance_alignment
            + 0.04 * check_coverage
            + 0.02 * richness
        )

    if supported_count >= 2 and support_ratio >= 0.7:
        combined += 0.08
    if focus_coverage >= 0.7:
        combined += 0.04
    if relevance_alignment >= 0.72:
        combined += 0.08
    elif relevance_alignment >= 0.6:
        combined += 0.04
    if contradicted_count > supported_count and contradicted_count > 0:
        combined -= 0.12

    combined = max(0.18, min(0.96, combined - risk_penalty))
    final_score = round(combined * 100, 2)

    return {
        "confidence_score": final_score,
        "confidence_level": get_confidence_level_info(final_score),
        "verdict": verdict_from_score(final_score),
        "support_ratio": support_ratio,
        "focus_coverage": focus_coverage,
        "relevance_alignment": relevance_alignment,
        "keyword_count": len((fast_result.get("keywords", []) or report_json.get("keywords", []) or [])),
        "risk_flag_count": len(risk_flags),
        "key_point_count": len(key_points),
    }


def _calc_report_metrics(report_json: Dict[str, Any], focus_marks: List[str]) -> Dict[str, Any]:
    return _derive_report_confidence(report_json, focus_marks)


def _render_multi_agent_analysis(analysis: Dict[str, Any], block_key: str) -> None:
    if not analysis:
        return

    integrated = analysis.get("integrated_findings", {}) or {}
    priority_marks = analysis.get("priority_focus_marks", []) or []
    secondary_marks = analysis.get("secondary_focus_marks", []) or []
    claim_reports = analysis.get("agent_claim_reports", []) or []
    confidence_level = integrated.get("overall_confidence_level", {}) or {}

    with st.expander("多 Agents 深度整合分析", expanded=False):
        top1, top2, top3 = st.columns(3)
        top1.metric("整合置信度", integrated.get("overall_confidence", 0.0))
        top2.metric("整合结论", integrated.get("overall_verdict", "insufficient"))
        top3.metric("重点 ! 标记数", len(priority_marks))

        if priority_marks:
            st.markdown("**重点关注的 ! 标记**")
            for item in priority_marks:
                st.markdown(f"- {item}")
        if secondary_marks:
            st.markdown("**补充参考标记**")
            for item in secondary_marks[:6]:
                st.markdown(f"- {item}")

        if integrated.get("narrative_summary"):
            st.markdown("**整合摘要**")
            st.write(integrated.get("narrative_summary", ""))

        left, right = st.columns(2)
        with left:
            if integrated.get("key_consensus_points"):
                st.markdown("**共识结论**")
                for item in integrated.get("key_consensus_points", [])[:6]:
                    st.markdown(f"- {item}")
            if integrated.get("logic_watchpoints"):
                st.markdown("**逻辑关注点**")
                for item in integrated.get("logic_watchpoints", [])[:6]:
                    st.markdown(f"- {item}")
        with right:
            if integrated.get("major_risks"):
                st.markdown("**主要风险**")
                for item in integrated.get("major_risks", [])[:6]:
                    st.markdown(f"- {item}")
            if integrated.get("premise_gaps"):
                st.markdown("**前提缺口**")
                for item in integrated.get("premise_gaps", [])[:6]:
                    st.markdown(f"- {item}")

        if integrated.get("evidence_highlights"):
            st.markdown("**证据摘录**")
            for item in integrated.get("evidence_highlights", [])[:4]:
                st.markdown(f"> {item}")

        if claim_reports:
            st.markdown("**逐条子结论**")
            for idx, item in enumerate(claim_reports[:8], start=1):
                verdict = str(item.get("verdict", "")).strip()
                score = item.get("confidence_score", 0.0)
                claim = str(item.get("claim", "")).strip()
                with st.container(border=True):
                    st.markdown(f"**{idx}. {claim or '（未命名主张）'}**")
                    info1, info2, info3 = st.columns(3)
                    info1.metric("结论", verdict)
                    info2.metric("置信度", score)
                    info3.metric("等级", f"{confidence_level.get('emoji', '❓')} {confidence_level.get('name', '未知')}")
                    logic_conditions = item.get("logic_conditions", []) or []
                    hidden_premises = item.get("hidden_premises", []) or []
                    if logic_conditions:
                        st.caption("逻辑 Agent")
                        for entry in logic_conditions[:4]:
                            st.markdown(f"- {entry}")
                    if hidden_premises:
                        st.caption("前提 Agent")
                        for entry in hidden_premises[:4]:
                            st.markdown(f"- {entry}")
                    supporting = item.get("supporting_evidence", []) or []
                    if supporting:
                        st.caption("证据 Agent")
                        for entry in supporting[:2]:
                            quote = str(entry.get("quote", "")).strip()
                            source = str(entry.get("url", "")).strip()
                            st.markdown(f"- {quote}")
                            if source:
                                st.caption(source)


def _render_live_mark_panel(current_url: str, selected_urls: List[str], panel_key_suffix: str = "main") -> None:
    """浏览与标记联动面板：自动同步 Hypothesis 标注，支持手动补充。"""
    st.markdown("**浏览与标记联动面板（实时）**")
    if current_url:
        display_url = (current_url[:60] + "...") if len(current_url) > 60 else current_url
        st.markdown(f"当前浏览网页：[{display_url}]({current_url})")
    else:
        st.caption('当前浏览网页：未设置，请在左侧点击"设为当前浏览页"')

    # ── 自动静默同步 Hypothesis（每次面板渲染时触发，无需手动点击）──
    hyp_user = os.getenv("HYPOTHESIS_USERNAME", "")
    hyp_token = os.getenv("HYPOTHESIS_TOKEN", "")
    if hyp_user and hyp_token and current_url:
        fetched = _fetch_hypothesis_annotations(current_url)
        if fetched:
            existing_ids = {m.get("hypothesis_id", "") for m in st.session_state.hl_marks if m.get("hypothesis_id")}
            existing_keys = {(m.get("url", ""), m.get("text", "")) for m in st.session_state.hl_marks}
            added = 0
            for m in fetched:
                hid = m.get("hypothesis_id", "")
                key = (m.get("url", ""), m.get("text", ""))
                if (hid and hid in existing_ids) or (key in existing_keys):
                    continue
                st.session_state.hl_marks.append(m)
                added += 1
            if added:
                st.rerun()

    all_marks: List[Dict[str, Any]] = st.session_state.hl_marks
    related_marks = [m for m in all_marks if current_url and m.get("url") == current_url]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("当前页标记数", len(related_marks))
    col_b.metric("累计标记总数", len(all_marks))
    col_c.metric("已选中网页数", len({url for url in selected_urls if url}))

    if current_url:
        with st.expander("✏️ 手动添加标记（补充）", expanded=False):
            inp_col1, inp_col2 = st.columns([1, 3])
            with inp_col1:
                new_type = st.selectbox(
                    "类型", options=["!", "?"],
                    key=f"inline_mark_type_{panel_key_suffix}",
                    label_visibility="collapsed",
                )
            with inp_col2:
                new_text = st.text_input(
                    "内容",
                    placeholder="手动输入或粘贴补充标记内容…",
                    key=f"inline_mark_text_{panel_key_suffix}",
                    label_visibility="collapsed",
                )
            if st.button("➕ 添加", key=f"inline_btn_add_mark_{panel_key_suffix}", use_container_width=True):
                if new_text.strip():
                    st.session_state.hl_marks.append({
                        "type": new_type,
                        "text": new_text.strip(),
                        "url": current_url,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "source": "manual",
                    })
                    st.rerun()
                else:
                    st.warning("请先输入内容。")

    st.divider()

    if related_marks:
        st.markdown("**当前页已标记内容：**")
        for i, mark in enumerate(related_marks, 1):
            tag = mark.get("type", "")
            text = mark.get("text", "")
            note = mark.get("note", "")
            source = mark.get("source", "manual")
            border_color = "#e74c3c" if tag == "!" else "#2980b9"
            bg_color = "#fff5f5" if tag == "!" else "#f0f7ff"
            emoji = "🔴" if tag == "!" else "🔵"
            src_badge = (
                "<span style='font-size:0.75em;background:#e8f4fd;color:#1a6a9a;"
                "padding:1px 6px;border-radius:3px;margin-left:5px;'>Hypothesis</span>"
                if source == "hypothesis"
                else "<span style='font-size:0.75em;background:#f0f0f0;color:#555;"
                "padding:1px 6px;border-radius:3px;margin-left:5px;'>手动</span>"
            )
            note_html = f"<div style='color:#666;font-size:0.85em;margin-top:3px;'>💬 {note}</div>" if note else ""
            del_col, content_col = st.columns([1, 9])
            with content_col:
                st.markdown(
                    f"""<div style='border-left:3px solid {border_color};"""
                    f"""padding:6px 10px;margin:3px 0;border-radius:4px;background:{bg_color};font-size:0.92em;'>"""
                    f"""<span style='font-weight:600;color:{border_color};'>{emoji} [{tag}] #{i}</span>{src_badge}<br>"""
                    f"""<span style='color:#222;'>{text}</span>{note_html}</div>""",
                    unsafe_allow_html=True,
                )
            with del_col:
                if st.button("🗑", key=f"del_mark_{panel_key_suffix}_{i}", help="删除此条标记"):
                    target_idx = next(
                        (j for j, m in enumerate(all_marks)
                         if m.get("url") == current_url
                         and m.get("text") == text
                         and m.get("timestamp") == mark.get("timestamp")),
                        None,
                    )
                    if target_idx is not None:
                        st.session_state.hl_marks.pop(target_idx)
                    st.rerun()
    elif current_url:
        st.caption('🔍 当前页暂无标记——点击上方"同步 Hypothesis 标记"自动拉取。')
    else:
        st.caption('请先在左侧点击"设为当前浏览页"。')

    if all_marks and len(all_marks) > len(related_marks):
        with st.expander(f"查看全部 {len(all_marks)} 条标记", expanded=False):
            for mark in all_marks:
                tag = mark.get("type", "")
                url_s = mark.get("url", "")
                url_s = "..." + url_s[-45:] if len(url_s) > 45 else url_s
                color = "#e74c3c" if tag == "!" else "#2980b9"
                src_lbl = " [Hyp]" if mark.get("source") == "hypothesis" else ""
                st.markdown(
                    f"<span style='color:{color};font-weight:600;'>[{tag}]{src_lbl}</span> "
                    f"{mark.get('text', '')} "
                    f"<span style='color:#999;font-size:0.8em;'>— {url_s}</span>",
                    unsafe_allow_html=True,
                )

def main() -> None:
    st.set_page_config(page_title="搜索-标记-检验工作台", page_icon="✅", layout="wide")
    _ensure_state()

    pages = ["搜索与浏览", "标记与导出", "生成评估", "最终导出"]

    mode_col_l, mode_col_r = st.columns([6, 1])
    with mode_col_r:
        current_mode = st.session_state.get("theme_mode", "light")
        toggle_label = "🌙 深色背景" if current_mode == "light" else "☀️ 浅色背景"
        if st.button(toggle_label, key="btn_toggle_theme_mode", use_container_width=True):
            st.session_state.theme_mode = "dark" if current_mode == "light" else "light"
            st.rerun()

    is_dark = st.session_state.get("theme_mode", "light") == "dark"

    # ── 颜色变量 ────────────────────────────────────────────────────────
    if is_dark:
        # 夜晚模式：深蓝紫调，柔和不刺眼
        app_bg              = "#16152a"
        app_bg2             = "#1e1c35"
        text_color          = "#e8e4f0"
        subtext_color       = "#a89fc0"
        heading_color       = "#d4cfe8"
        card_bg             = "#221f3a"
        card_border         = "#3a3560"
        card_shadow         = "0 4px 18px rgba(0,0,0,0.40)"
        input_bg            = "#1e1c35"
        input_text          = "#e8e4f0"
        input_border        = "#4a4570"
        btn_bg              = "linear-gradient(135deg, #7c6fcd 0%, #a78bfa 100%)"
        btn_text            = "#ffffff"
        btn_hover_shadow    = "rgba(124,111,205,0.50)"
        btn_disabled_bg     = "#2a2845"
        btn_disabled_text   = "#6b6890"
        btn_disabled_border = "#3a3560"
        sidebar_bg          = "#13122200"
        sidebar_border      = "#2e2b50"
        sidebar_text        = "#c8c2dc"
        metric_label        = "#a89fc0"
        metric_value        = "#e8e4f0"
        progress_track      = "#dbeafe"
        progress_fill       = "#7dd3fc"
        toggle_btn_bg       = "linear-gradient(135deg, #a78bfa 0%, #c4b5fd 100%)"
    else:
        # 白天模式：米白+薰衣草，温柔清新
        app_bg              = "#faf8ff"
        app_bg2             = "#f3f0ff"
        text_color          = "#3d3558"
        subtext_color       = "#8b7fa8"
        heading_color       = "#2d2548"
        card_bg             = "#ffffff"
        card_border         = "#e8e0f5"
        card_shadow         = "0 2px 12px rgba(100,80,160,0.07)"
        input_bg            = "#ffffff"
        input_text          = "#3d3558"
        input_border        = "#d4c8f0"
        btn_bg              = "linear-gradient(135deg, #9b72ef 0%, #c084fc 100%)"
        btn_text            = "#ffffff"
        btn_hover_shadow    = "rgba(155,114,239,0.40)"
        btn_disabled_bg     = "#f3f0f8"
        btn_disabled_text   = "#b0a8c8"
        btn_disabled_border = "#ddd6f0"
        sidebar_bg          = "#f5f0ff"
        sidebar_border      = "#e0d8f8"
        sidebar_text        = "#4a3f6b"
        metric_label        = "#9b8db8"
        metric_value        = "#3d3558"
        progress_track      = "#dbeafe"
        progress_fill       = "#7dd3fc"
        toggle_btn_bg       = "linear-gradient(135deg, #9b72ef 0%, #c084fc 100%)"

    st.markdown(
        f"""
        <style>
        /* ── 导入字体 ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* ── 全局背景与字体 ── */
        .stApp {{
            background: linear-gradient(160deg, {app_bg} 0%, {app_bg2} 100%) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
        }}

        /* ── 基础文字颜色 ── */
        .stApp p, .stApp li, .stApp span, .stApp div,
        .stApp label, .stApp td, .stApp th {{
            color: {text_color} !important;
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
            color: {heading_color} !important;
            font-weight: 700 !important;
            letter-spacing: -0.3px;
        }}
        .stApp small, .stCaption,
        [data-testid="stCaptionContainer"] p {{
            color: {subtext_color} !important;
            font-size: 0.80rem !important;
        }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: {sidebar_bg} !important;
            border-right: 1px solid {sidebar_border} !important;
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div {{
            color: {sidebar_text} !important;
        }}

        /* ── 主按钮 ── */
        .stButton > button {{
            background: {btn_bg} !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            letter-spacing: 0.3px;
            padding: 0.42rem 1.1rem !important;
            transition: opacity .18s ease, transform .16s ease, box-shadow .16s ease;
            position: relative;
            overflow: hidden;
        }}
        .stButton > button::after {{
            content: "";
            position: absolute;
            top: -120%;
            left: -30%;
            width: 40%;
            height: 320%;
            background: linear-gradient(110deg, rgba(255,255,255,0.0), rgba(255,255,255,0.26), rgba(255,255,255,0.0));
            transform: rotate(18deg);
            transition: left .45s ease;
            pointer-events: none;
        }}
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {{
            color: #ffffff !important;
        }}
        .stButton > button:hover {{
            opacity: 0.88;
            transform: translateY(-2px);
            box-shadow: 0 8px 22px {btn_hover_shadow} !important;
        }}
        .stButton > button:hover::after {{
            left: 120%;
        }}
        .stButton > button:active {{
            transform: translateY(0px) !important;
            box-shadow: none !important;
            opacity: 1;
        }}
        .stButton > button:disabled,
        .stButton > button[disabled] {{
            background: {btn_disabled_bg} !important;
            color: {btn_disabled_text} !important;
            border: 1px solid {btn_disabled_border} !important;
            box-shadow: none !important;
            transform: none !important;
            opacity: 0.7;
            cursor: not-allowed;
        }}
        .stButton > button:disabled p,
        .stButton > button[disabled] p {{
            color: {btn_disabled_text} !important;
        }}

        /* ── Metric 卡片 ── */
        [data-testid="stMetric"] {{
            background: {card_bg} !important;
            border: 1px solid {card_border} !important;
            border-radius: 14px !important;
            padding: 12px 16px !important;
            box-shadow: {card_shadow} !important;
            transition: transform .22s ease, box-shadow .22s ease;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 28px {btn_hover_shadow} !important;
        }}

        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {{
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
            border-radius: 12px !important;
        }}
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 26px {btn_hover_shadow} !important;
            border-color: #b9a8ef !important;
        }}
        [data-testid="stMetricLabel"] p {{
            color: {metric_label} !important;
            font-size: 0.76rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        [data-testid="stMetricValue"] {{
            color: {metric_value} !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
        }}

        /* ── 进度条：统一浅蓝色 ── */
        [data-testid="stProgress"] {{
            background: transparent !important;
        }}
        [data-testid="stProgress"] p,
        [data-testid="stProgress"] label,
        [data-testid="stProgress"] span {{
            color: {text_color} !important;
            font-size: 0.9rem !important;
            line-height: 1.35 !important;
            margin-bottom: 0.28rem !important;
        }}
        [data-testid="stProgress"] [role="progressbar"],
        .stProgress [role="progressbar"] {{
            background: {progress_track} !important;
            border-radius: 999px !important;
            height: 8px !important;
            overflow: hidden !important;
            box-shadow: none !important;
        }}
        [data-testid="stProgress"] [role="progressbar"] > div,
        .stProgress [role="progressbar"] > div {{
            background: linear-gradient(90deg, {progress_fill}, #93c5fd, {progress_fill}) !important;
            background-size: 220% 100% !important;
            border-radius: 999px !important;
            height: 8px !important;
            box-shadow: none !important;
            animation: progressShimmer 1.8s linear infinite;
        }}
        @keyframes progressShimmer {{
            0% {{ background-position: 180% 0; }}
            100% {{ background-position: -20% 0; }}
        }}

        /* ── 输入框 / 下拉框 / 文本区 ── */
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] > div {{
            background: {input_bg} !important;
            border-color: {input_border} !important;
            border-radius: 8px !important;
        }}
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] input {{
            color: {input_text} !important;
            background: {input_bg} !important;
        }}
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within {{
            border-color: #a78bfa !important;
            box-shadow: 0 0 0 2px rgba(167,139,250,0.18) !important;
        }}

        /* ── 下拉菜单选项 ── */
        [data-baseweb="menu"] li,
        [data-baseweb="menu"] [role="option"] {{
            color: {input_text} !important;
            background: {input_bg} !important;
        }}
        [data-baseweb="menu"] [role="option"]:hover {{
            background: {card_border} !important;
        }}

        /* ── Radio / Checkbox 标签 ── */
        [data-testid="stRadio"] label,
        [data-testid="stRadio"] p,
        [data-testid="stCheckbox"] label,
        [data-testid="stCheckbox"] p {{
            color: {text_color} !important;
        }}
        [data-testid="stRadio"] [role="radiogroup"] {{
            gap: 8px;
        }}
        [data-testid="stRadio"] [role="radio"] {{
            border: 1px solid {card_border} !important;
            border-radius: 999px !important;
            padding: 6px 12px !important;
            background: rgba(255,255,255,0.35);
            transition: all .2s ease;
        }}
        [data-testid="stRadio"] [role="radio"]:hover {{
            border-color: #b69cf8 !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(140,114,239,0.16);
        }}
        [data-testid="stRadio"] [role="radio"][aria-checked="true"] {{
            background: linear-gradient(135deg, rgba(155,114,239,0.16), rgba(125,211,252,0.18)) !important;
            border-color: #a78bfa !important;
        }}

        /* ── number_input 上下箭头区域 ── */
        [data-testid="stNumberInput"] button {{
            background: {card_border} !important;
            color: {text_color} !important;
            border-radius: 6px !important;
        }}

        /* ── 分割线 ── */
        hr {{
            border: none !important;
            border-top: 1px solid {card_border} !important;
            margin: 0.6rem 0 !important;
        }}

        /* ── 主题切换按钮特殊配色 ── */
        #btn_toggle_theme_mode > button {{
            background: {toggle_btn_bg} !important;
            font-size: 0.82rem !important;
            padding: 0.35rem 0.8rem !important;
        }}

        /* ── Step3 动效增强 ── */
        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 0 0 rgba(155,114,239,0.30); transform: translateY(0); }}
            70% {{ box-shadow: 0 0 0 12px rgba(155,114,239,0.00); transform: translateY(-1px); }}
            100% {{ box-shadow: 0 0 0 0 rgba(155,114,239,0.00); transform: translateY(0); }}
        }}
        #btn_finish_and_generate > button {{
            animation: pulseGlow 2.2s ease-in-out infinite;
            border: 1px solid {card_border} !important;
        }}
        #btn_finish_and_generate > button:hover {{
            transform: translateY(-1px);
        }}
        .step3-tip-card {{
            background: linear-gradient(135deg, rgba(155,114,239,0.12), rgba(125,211,252,0.12));
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 10px 12px;
            margin: 6px 0 12px 0;
            transition: transform .2s ease, box-shadow .2s ease;
        }}
        .step3-tip-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 24px rgba(125, 110, 200, 0.16);
        }}

        [data-testid="stExpander"] details {{
            border-radius: 12px !important;
            border: 1px solid {card_border} !important;
            background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0.16));
            transition: border-color .2s ease, box-shadow .2s ease;
        }}
        [data-testid="stExpander"] details:hover {{
            border-color: #b69cf8 !important;
            box-shadow: 0 8px 20px rgba(120, 90, 200, 0.15);
        }}

        .ui-hero-card {{
            background: radial-gradient(120% 140% at 0% 0%, rgba(155,114,239,0.20), rgba(125,211,252,0.10) 55%, transparent 100%), {card_bg};
            border: 1px solid {card_border};
            border-radius: 16px;
            padding: 12px 14px;
            margin: 8px 0 14px 0;
            box-shadow: {card_shadow};
            animation: floatFade 3.2s ease-in-out infinite;
        }}
        @keyframes floatFade {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-2px); }}
            100% {{ transform: translateY(0px); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🛸 NEXUS ✨")
    st.caption("1️⃣ 实时热点新闻采集 → 2️⃣ 人类关注信号标注 → 3️⃣ 多智能体协同验证（事实一致性 / 时效性 / 逻辑完整性）→ 4️⃣ 自动化分析报告生成 → 5️⃣ 高质量数据集导出用于下游模型表现")
    st.caption("用户可自定义时效 ⏰ → 用户自由标注新闻关注点 ✍️~ → 多智能体协同验证信息来源 🤖 → 多智能体分析整合报告 📊 → 高质量数据集导出用于下游模型表现 🔝")
    st.markdown(
        """
        <div class="ui-hero-card">
            <div style="font-weight:700;font-size:1.02rem;">✨ 智能核查工作台升级版</div>
            <div style="font-size:0.9rem;opacity:0.92;margin-top:4px;">
                动态按钮 + 交互反馈已开启：可在 Step3 直接切换 <b>极速 / 平衡 / 深度</b> 模式，
                获得更流畅的生成体验与更聚焦的摘要结果。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    serp_ready = bool(os.getenv("SERPAPI_API_KEY"))
    brave_ready = bool(os.getenv("BRAVE_SEARCH_API_KEY"))
    bigmodel_ready = bool(os.getenv("BIGMODEL_API_KEY"))
    deepseek_ready = bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEP_SEEK_API_KEY"))
    top1, top2, top3, top4 = st.columns(4)
    top1.metric("SerpApi", "已配置" if serp_ready else "未配置")
    top2.metric("Brave Search", "已配置" if brave_ready else "未配置")
    top3.metric("BigModel Search", "已配置" if bigmodel_ready else "未配置")
    top4.metric("DeepSeek", "已启用" if deepseek_ready else "未启用")

    def _on_page_radio_change():
        st.session_state.page_name = st.session_state.workflow_page_radio

    st.sidebar.radio(
        "流程分页",
        options=pages,
        index=pages.index(st.session_state.page_name) if st.session_state.page_name in pages else 0,
        key="workflow_page_radio",
        on_change=_on_page_radio_change,
    )

    current_idx = pages.index(st.session_state.page_name)
    st.progress((current_idx + 1) / len(pages), text=f"{current_idx + 1}/{len(pages)}")

    nav_l, nav_r = st.columns(2)
    with nav_l:
        if current_idx > 0 and st.button("⬅ 上一页", key="btn_prev_page"):
            st.session_state.page_name = pages[current_idx - 1]
            st.rerun()
    with nav_r:
        if current_idx < len(pages) - 1 and st.button("下一页 ➡", key="btn_next_page"):
            st.session_state.page_name = pages[current_idx + 1]
            st.rerun()

    if st.session_state.page_name == "搜索与浏览":
        st.subheader("Step 1：自定义捕捉新闻热点")
        c1, c2, c3, c4 = st.columns([2.7, 1, 1.6, 1.2])
        with c1:
            keyword = st.text_input("搜索关键词", value=st.session_state.get("keyword", "GraphRAG research"), key="search_keyword_input")
        with c2:
            num_results = st.number_input("结果数", min_value=3, max_value=20, value=8, step=1, key="search_num")
        with c3:
            provider_display = st.selectbox(
                "搜索源",
                options=["serpapi", "baidu_serpapi", "brave_api", "bigmodel_web_search"],
                index=["serpapi", "baidu_serpapi", "brave_api", "bigmodel_web_search"].index(
                    st.session_state.get("search_provider", "serpapi")
                    if st.session_state.get("search_provider", "serpapi") in {"serpapi", "baidu_serpapi", "brave_api", "bigmodel_web_search"}
                    else "serpapi"
                ),
                key="search_provider_select",
                help="`serpapi`=Google 新闻/网页；`baidu_serpapi`=百度网页；`brave_api`=Brave Search API；`bigmodel_web_search`=智谱网络搜索",
            )
            st.session_state.search_provider = provider_display
            os.environ["SEARCH_PROVIDER"] = provider_display
        with c4:
            recency_map = {
                "一天": "oneDay",
                "一周": "oneWeek",
                "一月": "oneMonth",
                "一年": "oneYear",
                "不限": "noLimit",
            }
            inv_recency_map = {value: key for key, value in recency_map.items()}
            recency_default = st.session_state.get("search_recency", "oneWeek")
            recency_display = st.selectbox(
                "时效",
                options=list(recency_map.keys()),
                index=list(recency_map.keys()).index(inv_recency_map.get(recency_default, "一周")),
                key="search_recency_select",
                help="优先返回近期内容；建议日常核查选“一周”或“一天”。",
            )
            st.session_state.search_recency = recency_map[recency_display]
            os.environ["SEARCH_RECENCY"] = st.session_state.search_recency

        if st.button("执行搜索", type="primary", key="btn_search"):
            provider = st.session_state.search_provider
            st.session_state.search_attempted = True
            if provider in {"serpapi", "baidu_serpapi"} and not serp_ready:
                st.error("缺少 `SERPAPI_API_KEY`，无法执行该搜索源。")
                st.session_state.last_search_info = "搜索未执行：缺少 SERPAPI_API_KEY"
            elif provider == "brave_api" and not brave_ready:
                st.error("缺少 `BRAVE_SEARCH_API_KEY`，无法执行 Brave 搜索。")
                st.session_state.last_search_info = "搜索未执行：缺少 BRAVE_SEARCH_API_KEY"
            elif provider == "bigmodel_web_search" and not bigmodel_ready:
                st.error("缺少 `BIGMODEL_API_KEY`，无法执行 BigModel web-search。")
                st.session_state.last_search_info = "搜索未执行：缺少 BIGMODEL_API_KEY"
            elif not keyword.strip():
                st.warning("请输入搜索关键词。")
                st.session_state.last_search_info = "搜索未执行：关键词为空"
            else:
                query = keyword.strip()
                n = int(num_results)
                search_results = []
                _compat_warning = False
                _recency_relaxed = False
                search_debug: dict = {}
                fallback_provider = ""
                primary_failure_reason = ""

                with st.status("🔍 搜索中，请稍候…", expanded=True) as _search_status:
                    st.write(f"▶ 正在向 **{st.session_state.search_provider}** 发起请求…")

                    variants = [
                        {"provider": st.session_state.search_provider, "recency": st.session_state.search_recency},
                        {"provider": st.session_state.search_provider},
                        {"recency": st.session_state.search_recency},
                        {},
                    ]
                    last_type_error = None
                    for kwargs in variants:
                        try:
                            search_results = search_news(query, n, **kwargs)
                            if kwargs != variants[0]:
                                _compat_warning = True
                            break
                        except TypeError as error:
                            last_type_error = error
                    else:
                        raise last_type_error

                    # 时效过严时自动放宽到 noLimit 再尝试一次
                    if not search_results and st.session_state.search_recency != "noLimit":
                        st.write("⏳ 当前时效无结果，放宽到「不限时间」重试…")
                        for kwargs in [
                            {"provider": st.session_state.search_provider, "recency": "noLimit"},
                            {"provider": st.session_state.search_provider},
                            {},
                        ]:
                            try:
                                search_results = search_news(query, n, **kwargs)
                                if search_results:
                                    _recency_relaxed = True
                                break
                            except TypeError:
                                continue

                    search_debug = get_last_search_debug()
                    fallback_provider = str(search_debug.get("fallback_provider", "")).strip()
                    primary_failure_reason = str(search_debug.get("primary_failure_reason", "")).strip()

                    if search_results:
                        st.write(f"✅ 已获取 **{len(search_results)}** 条结果，正在提取关键词与补全相关链接…")
                        _search_status.update(
                            label=f"✅ 搜索完成，共获取 {len(search_results)} 条结果",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        st.write("⚠️ 未获取到任何结果")
                        _search_status.update(
                            label="⚠️ 搜索结束，未找到相关结果",
                            state="error",
                            expanded=False,
                        )

                # status 框外显示附加提示
                if _compat_warning:
                    st.info("当前搜索模块不完全支持所选参数，已自动兼容运行。")
                if _recency_relaxed:
                    st.warning("当前时效条件下无结果，已自动放宽到“不限时间”并返回结果。")
                if primary_failure_reason:
                    st.warning(primary_failure_reason)
                if fallback_provider:
                    st.info(f"主搜索源暂不可用，已自动切换到 `{fallback_provider}` 返回结果。")

                st.session_state.search_results = search_results
                if not search_results:
                    st.info("未检索到结果：可尝试切换搜索源、放宽时效到“不限”，或更换关键词。")
                    st.session_state.last_search_info = (
                        f"已搜索但无结果：provider={st.session_state.search_provider}, "
                        f"recency={st.session_state.search_recency}, keyword={query}"
                    )
                else:
                    st.session_state.last_search_info = (
                        f"搜索成功：provider={st.session_state.search_provider}, "
                        f"recency={st.session_state.search_recency}, 返回 {len(search_results)} 条"
                    )
                st.session_state.keyword = keyword.strip()
                st.session_state.generated_reports = []

        results = st.session_state.search_results
        # 从 checkbox 状态重建 selected_search_items 与 selected_urls
        selected_item_ids = {
            _result_item_id(item)
            for item in st.session_state.get("selected_search_items", [])
            if isinstance(item, dict)
        }
        checkbox_item_pairs: List[tuple[str, Dict[str, Any]]] = []
        left_col, right_col = st.columns([1.8, 1.2], gap="small")

        with left_col:
            st.markdown("**搜索结果**")
            if results:
                for idx, item in enumerate(results):
                    raw_url = str(item.get("url", "")).strip()
                    effective_url = _resolve_result_url(item)
                    inferred_topic = str(item.get("inferred_topic", "")).strip()
                    related_links = item.get("related_links", []) or []
                    topic_keywords = [str(token).strip() for token in (item.get("topic_keywords", []) or []) if str(token).strip()][:3]
                    item_id = _result_item_id(item)
                    display_title = str(item.get("title", "")).strip() or "（无标题结果）"
                    display_date = str(item.get("date", "")).strip() or "未知时间"
                    display_snippet = str(item.get("snippet", "")).strip() or "（该结果未返回摘要内容）"
                    with st.container(border=True):
                        suffix = item_id[:10]
                        checkbox_key = f"pick_url_{suffix}"
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = item_id in selected_item_ids

                        st.checkbox(
                            "用于后续报告",
                            key=checkbox_key,
                        )
                        checkbox_item_pairs.append((checkbox_key, dict(item)))
                        st.markdown(f"**{idx + 1}. {display_title}**")
                        if raw_url:
                            st.caption(f"{display_date} · {raw_url}")
                        else:
                            st.caption(f"{display_date} · （原结果无直链，内容可直接纳入后续报告）")
                        _render_keyword_tags(topic_keywords)
                        st.write(display_snippet)

                        if not raw_url and related_links:
                            st.markdown("**相关链接（基于关键词继续搜索）**")
                            for link_idx, link_item in enumerate(related_links[:3], start=1):
                                link_url = str(link_item.get("url", "")).strip()
                                link_title = str(link_item.get("title", "")).strip() or f"相关链接 {link_idx}"
                                if link_url:
                                    st.link_button(
                                        f"{link_idx}. {link_title[:56]}",
                                        link_url,
                                    )

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("设为当前浏览页", key=f"btn_set_open_{idx}"):
                                if effective_url:
                                    st.session_state.current_open_url = effective_url
                                else:
                                    st.warning("该结果没有可用链接，无法设为当前浏览页。")
                                st.rerun()
                        with b2:
                            if effective_url:
                                st.link_button("打开网页", effective_url)
                            else:
                                st.button("打开网页（无链接）", key=f"btn_open_disabled_{idx}", disabled=True)
            else:
                if st.session_state.get("search_attempted", False):
                    st.warning("已执行搜索，但当前条件下没有结果。")
                    info_text = st.session_state.get("last_search_info", "")
                    if info_text:
                        st.caption(info_text)
                else:
                    st.info("请先搜索。")

        selected_items: List[Dict[str, Any]] = []
        seen_item_ids = set()
        for checkbox_key, picked_item in checkbox_item_pairs:
            if not st.session_state.get(checkbox_key, False):
                continue
            current_id = _result_item_id(picked_item)
            if current_id in seen_item_ids:
                continue
            seen_item_ids.add(current_id)
            selected_items.append(picked_item)

        selected_urls = []
        seen_urls = set()
        for picked_item in selected_items:
            picked_url = _resolve_result_url(picked_item)
            if picked_url and picked_url not in seen_urls:
                seen_urls.add(picked_url)
                selected_urls.append(picked_url)

        st.session_state.selected_search_items = selected_items
        st.session_state.selected_urls = selected_urls

        with right_col:
            selected_content_count = sum(1 for item in st.session_state.selected_search_items if not _resolve_result_url(item))
            if selected_content_count > 0:
                st.caption(f"已选中无直链内容：{selected_content_count} 条")
            _render_live_mark_panel(st.session_state.current_open_url, st.session_state.selected_urls, panel_key_suffix="browse")

    if st.session_state.page_name == "标记与导出":
        st.subheader("Step 2：用户标注关注点")
        selected_items = st.session_state.get("selected_search_items", [])
        selected_urls = st.session_state.selected_urls
        if not selected_items:
            st.info('请先到"搜索与浏览"页勾选内容。')
        else:
            left_m, right_m = st.columns([1, 1.6], gap="large")

            with left_m:
                st.markdown("**选择当前浏览页**")
                if selected_urls:
                    default_url = (
                        st.session_state.current_open_url
                        if st.session_state.current_open_url in selected_urls
                        else selected_urls[0]
                    )
                    mark_url = st.selectbox(
                        "网页",
                        options=selected_urls,
                        index=selected_urls.index(default_url),
                        key="mark_url",
                        label_visibility="collapsed",
                    )
                    st.session_state.current_open_url = mark_url
                    st.link_button("🌐 在浏览器中打开此页", mark_url, use_container_width=True)
                else:
                    mark_url = ""
                    st.caption("当前勾选内容均无直链，可直接在 Step 3 生成内容报告。")

                st.markdown("---")
                c_clr, c_exp = st.columns(2)
                with c_clr:
                    if st.button("🗑 清空所有标记", use_container_width=True, key="btn_clear_marks"):
                        st.session_state.hl_marks = []
                        st.rerun()
                with c_exp:
                    if st.button("💾 导出 JSON", use_container_width=True, key="btn_export_hl_json", type="secondary"):
                        export_path = _save_hl_content_json(
                            keyword=st.session_state.get("keyword", ""),
                            selected_urls=selected_urls,
                            marks=st.session_state.hl_marks,
                        )
                        st.session_state.last_hl_export_path = export_path
                        st.success(f"已导出到：{export_path}")

                if st.session_state.last_hl_export_path:
                    st.caption(f"最近导出：`{st.session_state.last_hl_export_path}`")

            with right_m:
                _render_live_mark_panel(mark_url, selected_urls, panel_key_suffix="mark_page")

    if st.session_state.page_name == "生成评估":
        st.subheader("Step 3：多智能体协作产出及验证 ⚡")
        if st.session_state.last_hl_export_path:
            st.caption(f"当前 hl_content 文件：`{st.session_state.last_hl_export_path}`")

        step3_mode = st.radio(
            "🚀 Step3 模式",
            options=["极速模式", "平衡模式", "深度模式"],
            index=["极速模式", "平衡模式", "深度模式"].index(st.session_state.get("step3_mode", "平衡模式"))
            if st.session_state.get("step3_mode", "平衡模式") in {"极速模式", "平衡模式", "深度模式"}
            else 1,
            horizontal=True,
            help="极速：最快（禁用LLM与多Agent）；平衡：默认推荐（辅助LLM低token策略）；深度：最全面（深度LLM + 多Agent + 外部校验）。",
        )
        st.session_state.step3_mode = step3_mode

        relevance_threshold = st.select_slider(
            "🎯 最低相关阈值（越高越严格）",
            options=[0.2, 0.3, 0.4],
            value=float(st.session_state.get("relevance_threshold", 0.3)),
            key="step3_relevance_threshold_slider",
            format_func=lambda x: f"{x:.1f} · {'宽松' if x <= 0.2 else ('平衡' if x <= 0.3 else '严格')}",
            help="控制进入 Step3 分析的最低相关分数阈值。0.4 更严格，0.2 更宽松。",
        )
        st.session_state.relevance_threshold = float(relevance_threshold)

        strict_label = "🟢 平衡" if relevance_threshold == 0.3 else ("🟠 严格" if relevance_threshold >= 0.4 else "🔵 宽松")
        st.markdown(
            f"""
            <div class="step3-tip-card">
                <div><b>✨ 智能相关性模式</b> · 当前阈值：<b>{relevance_threshold:.1f}</b>（{strict_label}）</div>
                <div style="font-size:0.92rem;opacity:0.92;margin-top:4px;">系统会优先保留与你标记内容高度相关的证据与结论，提升分析命中率与置信度。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("完成浏览", type="primary", key="btn_finish_and_generate"):
            selected_items = st.session_state.get("selected_search_items", [])
            if not selected_items:
                st.warning("没有勾选内容，无法生成报告。")
            else:
                marks = st.session_state.hl_marks

                progress = st.progress(0.0, text="🧠 生成与评估中，请稍候...")
                total_items = len(selected_items)
                outputs_by_idx: Dict[int, Dict[str, Any]] = {}
                try:
                    max_workers_env = int(str(os.getenv("STEP3_MAX_WORKERS", "3") or "3").strip())
                except Exception:
                    max_workers_env = 3
                max_workers = min(max(1, max_workers_env), max(1, total_items))
                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    future_to_idx = {
                        pool.submit(
                            _build_and_verify_single_item,
                            picked_item,
                            marks,
                            float(relevance_threshold),
                            str(step3_mode),
                        ): idx
                        for idx, picked_item in enumerate(selected_items, start=1)
                    }
                    completed = 0
                    for future in as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            outputs_by_idx[idx] = future.result()
                        except Exception as error:
                            picked_item = selected_items[idx - 1]
                            fallback_url = _resolve_result_url(picked_item)
                            outputs_by_idx[idx] = {
                                "url": fallback_url,
                                "title": str(picked_item.get("title", "") or "").strip(),
                                "highlighted_claims": [],
                                "page_summary": "",
                                "key_points": [],
                                "risk_flags": [f"parallel_generation_failed: {error}"],
                                "keywords": [],
                                "reliability_assessment": {"score": 0.2, "rationale": "parallel_generation_failed"},
                                "structured_claim_checks": [],
                                "generated_at": datetime.utcnow().isoformat() + "Z",
                                "generator": "error",
                                "_source_text_excerpt": "",
                                "fast_verification": {
                                    "confidence_score": 0.0,
                                    "confidence_level": get_confidence_level_info(0.0),
                                    "verdict": "insufficient",
                                    "keywords": [],
                                },
                                "quant_metrics": {
                                    "confidence_score": 0.0,
                                    "confidence_level": get_confidence_level_info(0.0),
                                    "overall_verdict": "insufficient",
                                    "support_ratio": 0.0,
                                    "focus_coverage": 0.0,
                                    "risk_density": 1.0,
                                },
                                "focused_hl_content": [],
                                "priority_focus_marks": [],
                                "secondary_focus_marks": [],
                            }
                        completed += 1
                        progress.progress(completed / max(1, total_items), text=f"⚙️ 已处理 {completed}/{total_items}")

                outputs = [outputs_by_idx[i] for i in range(1, total_items + 1) if i in outputs_by_idx]

                st.session_state.generated_reports = outputs
                st.success(f"✅ 已生成并评估 {len(outputs)} 篇被勾选内容报告。")
                try:
                    st.toast(f"🎉 Step 3 完成：{len(outputs)} 篇报告已生成", icon="✨")
                except Exception:
                    pass

        reports = st.session_state.generated_reports
        if reports:
            for idx, report in enumerate(reports):
                focus_marks = report.get("focused_hl_content") or report.get("highlighted_claims") or []
                metrics = _calc_report_metrics(report, focus_marks)
                report["quant_metrics"] = metrics
                level = metrics.get("confidence_level", {})
                with st.container(border=True):
                    st.markdown(f"**报告 {idx + 1}：{report.get('title', '(无标题)')}**")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("置信度", metrics.get("confidence_score", 0.0))
                    c2.metric("等级", f"{level.get('emoji', '❓')} {level.get('name', '未知')}")
                    c3.metric("支持率", metrics.get("support_ratio", 0.0))
                    c4.metric("标记覆盖率", metrics.get("focus_coverage", 0.0))
                    _render_multi_agent_analysis(report.get("multi_agent_analysis", {}) or {}, f"step3_{idx}")

    if st.session_state.page_name == "最终导出":
        st.subheader("Step 4：用户筛选报告并导出增强数据集 📊")
        reports = st.session_state.generated_reports
        selected_reports = []
        if reports:
            for idx, report in enumerate(reports):
                focus_marks = report.get("focused_hl_content") or report.get("highlighted_claims") or []
                metrics = _calc_report_metrics(report, focus_marks)
                report["quant_metrics"] = metrics
                level = metrics.get("confidence_level", {})
                with st.container(border=True):
                    keep = st.checkbox("选择该报告用于最终导出", key=f"pick_report_{idx}")
                    st.markdown(f"**报告 {idx + 1}：{report.get('title', '(无标题)')}**")
                    st.caption(report.get("url", ""))

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("置信度", metrics.get("confidence_score", 0.0))
                    m2.metric("等级", f"{level.get('emoji', '❓')} {level.get('name', '未知')}")
                    m3.metric("支持率", metrics.get("support_ratio", 0.0))
                    m4.metric("标记覆盖率", metrics.get("focus_coverage", 0.0))
                    # ── 深度摘要展示 ───────────────────────────────────────
                    page_summary = str(report.get("page_summary", "")).strip()
                    generator = str(report.get("generator", "")).strip()
                    deep = report.get("deep_analysis") or {}
                    web_content = str(report.get("web_content", "")).strip()

                    if page_summary:
                        gen_badge = {
                            "llm_deep": "🧠 LLM 深度分析",
                            "llm_inferred": "🔮 LLM 推断分析（无原文）",
                            "llm": "🤖 LLM 标准分析",
                            "fallback": "📄 结构化提取",
                            "content_only": "📋 摘要内容",
                        }.get(generator, f"⚙️ {generator}")
                        badge_color = "#fff3e0" if generator == "llm_inferred" else "#e8f4ff"
                        badge_text_color = "#b45309" if generator == "llm_inferred" else "#3867d6"
                        st.markdown(
                            f"**📝 深度摘要** <span style=\"background:{badge_color};color:{badge_text_color};"
                            f"border-radius:6px;padding:2px 8px;font-size:0.78rem;margin-left:8px;\">{gen_badge}</span>",
                            unsafe_allow_html=True,
                        )
                        if generator == "llm_inferred":
                            st.warning("⚠️ 网页原文无法抓取，以下为 DeepSeek 基于标题与标记内容的推断分析，仅供参考。")
                        st.info(page_summary)

                    if deep:
                        with st.expander("🔬 深度分析详情（核心主张 / 证据链 / 背景 / 影响）", expanded=False):
                            if deep.get("core_claims"):
                                st.markdown("**🎯 核心主张**")
                                for c in deep["core_claims"]:
                                    st.markdown(f"- {c}")
                            if deep.get("evidence_chain"):
                                st.markdown("**🔗 证据链条**")
                                for e in deep["evidence_chain"]:
                                    st.markdown(f"- {e}")
                            if deep.get("background_context"):
                                st.markdown("**🌐 背景与研究脉络**")
                                st.write(deep["background_context"])
                            if deep.get("implications"):
                                st.markdown("**💡 延伸意义与影响**")
                                for imp in deep["implications"]:
                                    st.markdown(f"- {imp}")
                            if deep.get("limitations"):
                                st.markdown("**⚠️ 局限性与注意事项**")
                                for lim in deep["limitations"]:
                                    st.markdown(f"- {lim}")
                            if deep.get("data_points"):
                                st.markdown("**📊 关键数据点**")
                                for dp in deep["data_points"]:
                                    st.markdown(f"- {dp}")
                            if deep.get("methodology"):
                                st.markdown("**🔬 研究方法 / 信息来源**")
                                st.write(deep["methodology"])

                    if web_content:
                        with st.expander("🌐 网页原文 (web_content)", expanded=False):
                            st.code(
                                web_content[:6000] + ("\n\n\u2026（已截断，完整内容见导出文件）" if len(web_content) > 6000 else ""),
                                language=None,
                            )

                    _render_multi_agent_analysis(report.get("multi_agent_analysis", {}) or {}, f"step4_{idx}")
                    if keep:
                        selected_reports.append(report)
        else:
            st.info("暂无报告。请先到\u201c生成评估\u201d页点击完成浏览。")

        merged_payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "keyword": st.session_state.get("keyword", ""),
            "hl_content_file": st.session_state.get("last_hl_export_path", ""),
            "selected_url_count": len(st.session_state.get("selected_urls", [])),
            "report_count": len(reports) if reports else 0,
            "selected_report_count": len(selected_reports),
            "selected_reports": selected_reports,
        }

        st.markdown("---")
        st.markdown("### 📥 导出报告")

        btn_col1, btn_col2 = st.columns(2)

        # ── 浏览器下载按钮（保持原有功能）──────────────────────────────────
        with btn_col1:
            st.download_button(
                "⬇️ 浏览器下载 JSON",
                data=json.dumps(merged_payload, ensure_ascii=False, indent=2),
                file_name="final_selected_reports.json",
                mime="application/json",
                disabled=len(selected_reports) == 0,
                key="btn_download_final_json",
                use_container_width=True,
            )

        # ── 保存到本地 summary_report/ 目录 ─────────────────────────────────
        with btn_col2:
            if st.button(
                "💾 保存到本地 summary_report/",
                disabled=len(selected_reports) == 0,
                key="btn_save_summary_report",
                type="primary",
                use_container_width=True,
            ):
                try:
                    saved = _save_summary_report(
                        selected_reports,
                        keyword=st.session_state.get("keyword", ""),
                    )
                    st.success("✅ 报告已保存到本地！")
                    st.markdown(
                        f"""
                        <div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #86efac;
                        border-radius:12px;padding:14px 18px;margin-top:8px;">
                            <div style="font-weight:600;color:#166534;margin-bottom:6px;">📁 保存位置</div>
                            <div style="font-size:0.88rem;color:#15803d;margin-bottom:4px;">
                                📄 完整报告 JSON：<code>{saved["full_path"]}</code>
                            </div>
                            <div style="font-size:0.88rem;color:#15803d;">
                                📝 深度摘要 Markdown：<code>{saved["summary_path"]}</code>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    try:
                        st.toast("🎉 已保存到 summary_report/ 文件夹", icon="💾")
                    except Exception:
                        pass
                except Exception as save_error:
                    st.error(f"保存失败：{save_error}")

        if len(selected_reports) == 0 and reports:
            st.caption("请先勾选至少一篇报告，再点击下载或保存。")


if __name__ == "__main__":
    main()
