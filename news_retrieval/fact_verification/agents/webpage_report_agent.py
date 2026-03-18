import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from .llm_client import LLMClient
from ..scoring.confidence import get_confidence_level_info, verdict_from_score


class WebpageReportAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()
        self._page_orchestrator = None
        report_llm_flag = str(os.getenv("WEB_REPORT_ENABLE_LLM", "0") or "0").strip().lower()
        self.enable_llm_report_generation = report_llm_flag in {"1", "true", "yes", "on"}
        llm_summary_flag = str(os.getenv("MULTI_AGENT_ENABLE_LLM_SUMMARY", "0") or "0").strip().lower()
        self.enable_llm_integrated_findings = llm_summary_flag in {"1", "true", "yes", "on"}
        try:
            claim_limit = int(str(os.getenv("MULTI_AGENT_CLAIM_LIMIT", "3") or "3").strip())
        except Exception:
            claim_limit = 3
        self.analysis_claim_limit = max(1, min(5, claim_limit))
        self.llm_strategy_default = self._normalize_llm_strategy(os.getenv("WEB_REPORT_LLM_STRATEGY", "assist"))
        try:
            assist_tokens = int(str(os.getenv("WEB_REPORT_AUX_MAX_TOKENS", "700") or "700").strip())
        except Exception:
            assist_tokens = 700
        self.aux_max_tokens = max(220, min(2200, assist_tokens))
        try:
            deep_tokens = int(str(os.getenv("WEB_REPORT_DEEP_MAX_TOKENS", "1400") or "1400").strip())
        except Exception:
            deep_tokens = 1400
        self.deep_max_tokens = max(600, min(4200, deep_tokens))

    @staticmethod
    def _normalize_llm_strategy(strategy: Optional[str]) -> str:
        normalized = str(strategy or "").strip().lower()
        if normalized in {"off", "none", "disable", "disabled", "0"}:
            return "off"
        if normalized in {"deep", "full", "comprehensive"}:
            return "deep"
        return "assist"

    @property
    def page_orchestrator(self):
        if self._page_orchestrator is None:
            from ..pipeline.orchestrator import FactVerificationOrchestrator

            self._page_orchestrator = FactVerificationOrchestrator()
        return self._page_orchestrator

    # 轮换 UA，降低反爬命中率
    _USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    ]

    def fetch_page_text(self, url: str, timeout: int = 25) -> Tuple[str, str]:
        import random
        ua = random.choice(self._USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
        }
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            html = response.text
        except Exception:
            # 二次尝试：换 UA + 更长超时
            try:
                headers["User-Agent"] = self._USER_AGENTS[-1]
                response = requests.get(url, headers=headers, timeout=timeout + 10, allow_redirects=True)
                response.raise_for_status()
                html = response.text
            except Exception:
                return "", ""

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "footer", "nav", "aside",
                         "header", "form", "button", "iframe", "canvas"]):
            tag.decompose()

        title = (soup.title.string or "").strip() if soup.title else ""

        # 依次尝试语义化容器，逐步放宽
        raw_text = ""
        for selector in ["article", "main", '[role="main"]', ".content", "#content", ".post", ".article"]:
            candidate = soup.select_one(selector)
            if candidate:
                raw_text = candidate.get_text("\n", strip=True)
                if len(raw_text) >= 200:
                    break
        if len(raw_text) < 200:
            raw_text = soup.get_text("\n", strip=True)

        # 短行阈值降至 15，保留更多内容
        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) >= 15]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return title, text[:14000]

    def _llm_title_only_analysis(
        self,
        url: str,
        title: str,
        marked_claims: List[str],
        snippet: str = "",
    ) -> Optional[Dict[str, Any]]:
        """当网页正文无法抓取时，基于标题、URL、摘要片段和标记内容让 DeepSeek 进行专业推断分析。"""
        if not self.llm.enabled:
            return None

        claims_json = json.dumps(marked_claims[:10], ensure_ascii=False)
        snippet_part = f"\n搜索摘要片段：{snippet[:600]}" if snippet.strip() else ""

        prompt_system = (
            "你是一位资深信息分析专家与事实核查记者。"
            "当前无法直接访问网页正文（可能被反爬或需要登录），但你可以基于以下已有信息进行专业推断分析。"
            "你的任务是：结合标题语义、URL 域名特征、搜索摘要片段和重点标记内容，"
            "运用你的知识库与推理能力，给出尽可能专业、有深度的分析报告。\n"
            "必须只输出一个合法 JSON 对象，不要 Markdown 代码块，不要任何解释。\n"
            "JSON 字段固定为：\n"
            "  page_summary: 综合推断摘要（200-400字），需明确指出分析基于标题与已知信息推断，"
            "包含：①该内容可能的核心论点 ②相关背景知识 ③对标记内容的推断性回应 ④可信度说明\n"
            "  key_points: 6-10条推断要点，每条标注'[推断]'前缀\n"
            "  deep_analysis: 对象，包含：\n"
            "    core_claims: 基于标题推断的核心主张（2-4条）\n"
            "    evidence_chain: 可能的证据链或论证逻辑（推断）\n"
            "    background_context: 相关领域背景（基于你的知识库）\n"
            "    implications: 该议题的潜在意义与影响\n"
            "    limitations: 因无法访问原文导致的分析局限（必填）\n"
            "    data_points: 基于领域知识推断的可能数据点\n"
            "    methodology: '基于标题语义+领域知识推断，未经原文验证'\n"
            "  keywords: 10-15个关键词\n"
            "  reliability_assessment: {score: 0.3-0.55（因无原文降低可信度）, rationale: 说明为何是推断分析}\n"
            "  structured_claim_checks: 针对标记内容的推断核查，每项含 claim、status、evidence_from_page（标注'[推断]'）"
        )

        prompt_user = (
            f"网页 URL：{url}\n"
            f"网页标题：{title or '（无标题）'}\n"
            f"{snippet_part}\n\n"
            f"重点标记内容（请在分析中优先覆盖）：\n{claims_json}\n\n"
            "注意：网页正文抓取失败，请基于以上信息进行专业推断分析，并在摘要中明确说明这是推断性分析。"
        )

        result = self.llm.json_call(prompt_system, prompt_user)
        if not result or not isinstance(result, dict):
            return None

        page_summary = str(result.get("page_summary", "")).strip()
        if not page_summary:
            return None

        key_points = self._dedupe_list(result.get("key_points") or [], limit=10)
        keywords = self._dedupe_list(result.get("keywords") or [], limit=15)
        reliability = result.get("reliability_assessment") or {}
        if not isinstance(reliability, dict):
            reliability = {}
        try:
            rel_score = max(0.2, min(0.55, float(reliability.get("score", 0.4) or 0.4)))
        except Exception:
            rel_score = 0.4
        rel_rationale = str(reliability.get("rationale", "基于标题推断，未访问原文。")).strip()

        structured_checks = self._dedupe_claim_checks(result.get("structured_claim_checks") or [], limit=10)

        deep_analysis = result.get("deep_analysis") or {}
        if not isinstance(deep_analysis, dict):
            deep_analysis = {}

        def _safe_str_list(val: Any, fallback: Optional[List[str]] = None) -> List[str]:
            """将任意值强制转为字符串列表，避免中文字符被逐字拆分。"""
            if isinstance(val, list):
                return [str(item).strip() for item in val if str(item).strip()]
            if isinstance(val, str) and val.strip():
                return [val.strip()]
            return fallback or []

        default_limitation = ["原文无法访问，以下分析为推断性质，需后续原文验证"]
        deep_analysis_clean = {
            "core_claims":        self._dedupe_list(_safe_str_list(deep_analysis.get("core_claims")), limit=4),
            "evidence_chain":     self._dedupe_list(_safe_str_list(deep_analysis.get("evidence_chain")), limit=4),
            "background_context": str(deep_analysis.get("background_context", "")).strip(),
            "implications":       self._dedupe_list(_safe_str_list(deep_analysis.get("implications")), limit=4),
            "limitations":        self._dedupe_list(_safe_str_list(deep_analysis.get("limitations"), fallback=default_limitation), limit=4),
            "data_points":        self._dedupe_list(_safe_str_list(deep_analysis.get("data_points")), limit=8),
            "methodology":        str(deep_analysis.get("methodology", "基于标题语义+领域知识推断，未经原文验证")).strip(),
        }

        return {
            "page_summary": page_summary,
            "key_points": key_points,
            "deep_analysis": deep_analysis_clean,
            "keywords": keywords,
            "reliability_assessment": {"score": rel_score, "rationale": rel_rationale},
            "structured_claim_checks": structured_checks,
            "generator": "llm_inferred",
        }

    def _llm_deep_summary(
        self,
        url: str,
        title: str,
        text: str,
        marked_claims: List[str],
    ) -> Optional[Dict[str, Any]]:
        """使用 LLM 对网页原文进行深度分析，生成多维度丰富摘要。
        返回包含 page_summary、key_points、deep_analysis 等字段的字典，失败时返回 None。
        """
        if not self.llm.enabled:
            return None

        # 提取与标记内容最相关的上下文，兼顾速度与相关性
        text_excerpt = self._select_focus_context(text, marked_claims, max_chars=7600)
        claims_json = json.dumps(marked_claims[:10], ensure_ascii=False)

        prompt_system = (
            "你是顶级事实核查分析师。目标是：围绕用户标记主题，输出高相关、可追溯、信息密度高的网页深度摘要。"
            "你必须优先处理与标记主题一致的内容；与主题弱相关段落只可少量提及。"
            "必须只输出一个合法 JSON 对象，不要 Markdown，不要解释文字。\n"
            "严格字段：\n"
            "  page_summary: 260-420字，结构化覆盖：核心结论/关键证据/研究背景/争议与局限/对标记内容的直接回应。\n"
            "  key_points: 8-10条，高信息密度，优先给出数据、实验、来源线索、边界条件。\n"
            "  deep_analysis: {core_claims,evidence_chain,background_context,implications,limitations,data_points,methodology}\n"
            "  keywords: 12-18个主题关键词（与标记主题强相关）。\n"
            "  reliability_assessment: {score:0-1,rationale:string}，需说明证据充分度与不确定性来源。\n"
            "  structured_claim_checks: 对每条标记内容输出 claim/status/evidence_from_page。status仅 allowed: supported|partially_supported|unclear|contradicted。\n"
            "要求：不要空泛观点；尽量引用原文中的事实片段。"
        )

        prompt_user = (
            f"网页 URL：{url}\n"
            f"网页标题：{title}\n\n"
            f"重点标记内容（请在分析中优先覆盖）：\n{claims_json}\n\n"
            f"网页原文（完整内容）：\n{text_excerpt}"
        )

        result = self.llm.json_call(prompt_system, prompt_user, max_tokens=self.deep_max_tokens)
        if not result or not isinstance(result, dict):
            return None

        # 规范化返回字段
        page_summary = str(result.get("page_summary", "")).strip()
        if not page_summary:
            return None

        key_points = self._dedupe_list(result.get("key_points") or [], limit=12)
        keywords = self._dedupe_list(result.get("keywords") or [], limit=20)
        reliability = result.get("reliability_assessment") or {}
        if not isinstance(reliability, dict):
            reliability = {}
        try:
            rel_score = max(0.0, min(1.0, float(reliability.get("score", 0.72) or 0.72)))
        except Exception:
            rel_score = 0.72
        rel_rationale = str(reliability.get("rationale", "LLM deep analysis completed.")).strip()

        structured_checks = self._dedupe_claim_checks(result.get("structured_claim_checks") or [], limit=15)

        deep_analysis = result.get("deep_analysis") or {}
        if not isinstance(deep_analysis, dict):
            deep_analysis = {}
        deep_analysis_clean = {
            "core_claims": self._dedupe_list(deep_analysis.get("core_claims") or [], limit=5),
            "evidence_chain": self._dedupe_list(deep_analysis.get("evidence_chain") or [], limit=6),
            "background_context": str(deep_analysis.get("background_context", "")).strip(),
            "implications": self._dedupe_list(deep_analysis.get("implications") or [], limit=4),
            "limitations": self._dedupe_list(deep_analysis.get("limitations") or [], limit=4),
            "data_points": self._dedupe_list(deep_analysis.get("data_points") or [], limit=10),
            "methodology": str(deep_analysis.get("methodology", "")).strip(),
        }

        return {
            "page_summary": page_summary,
            "key_points": key_points,
            "deep_analysis": deep_analysis_clean,
            "keywords": keywords,
            "reliability_assessment": {"score": rel_score, "rationale": rel_rationale},
            "structured_claim_checks": structured_checks,
            "generator": "llm_deep",
        }

    def _llm_assist_summary(
        self,
        url: str,
        title: str,
        text: str,
        marked_claims: List[str],
    ) -> Optional[Dict[str, Any]]:
        if not self.llm.enabled:
            return None

        compact_context = self._select_focus_context(text, marked_claims, max_chars=2200)
        if not compact_context:
            return None

        prompt_system = (
            "你是网页事实核查辅助助手。"
            "目标是在低成本条件下输出高相关、可复核的结构化摘要。"
            "必须只输出一个合法 JSON 对象，不要 Markdown，不要解释。"
            "字段固定：page_summary,key_points,keywords,reliability_assessment,structured_claim_checks。"
            "其中 page_summary 控制在 120-220 字；key_points 4-6 条；keywords 6-10 个；"
            "structured_claim_checks 对每条标记输出 claim/status/evidence_from_page，"
            "status 仅 allowed: supported|partially_supported|unclear|contradicted。"
        )
        prompt_user = (
            f"网页 URL：{url}\n"
            f"网页标题：{title}\n"
            f"重点标记：{json.dumps(marked_claims[:8], ensure_ascii=False)}\n\n"
            f"网页核心上下文（已压缩）：\n{compact_context}"
        )

        aux_model = self.llm.aux_model or None
        result = self.llm.json_call(
            prompt_system,
            prompt_user,
            temperature=0.1,
            model_override=aux_model,
            max_tokens=self.aux_max_tokens,
        )
        if not result or not isinstance(result, dict):
            return None

        page_summary = str(result.get("page_summary", "")).strip()
        if not page_summary:
            return None

        key_points = self._dedupe_list(result.get("key_points") or [], limit=8)
        keywords = self._dedupe_list(result.get("keywords") or [], limit=12)
        reliability = result.get("reliability_assessment") or {}
        if not isinstance(reliability, dict):
            reliability = {}
        try:
            rel_score = max(0.0, min(1.0, float(reliability.get("score", 0.66) or 0.66)))
        except Exception:
            rel_score = 0.66
        rel_rationale = str(reliability.get("rationale", "LLM assist summary generated.")).strip()
        structured_checks = self._dedupe_claim_checks(result.get("structured_claim_checks") or [], limit=12)

        return {
            "page_summary": page_summary,
            "key_points": key_points,
            "deep_analysis": {},
            "keywords": keywords,
            "reliability_assessment": {"score": rel_score, "rationale": rel_rationale},
            "structured_claim_checks": structured_checks,
            "generator": "llm_assist",
        }

    @staticmethod
    def _select_focus_context(text: str, marked_claims: List[str], max_chars: int = 7600) -> str:
        full = str(text or "").strip()
        if not full:
            return ""
        paragraphs = [p.strip() for p in re.split(r"\n{2,}|\n", full) if len(p.strip()) >= 25]
        if not paragraphs:
            return full[:max_chars]

        focus_tokens = set()
        for claim in marked_claims[:10]:
            for token in re.split(r"[^\w\u4e00-\u9fff]+", str(claim).lower()):
                if len(token) >= 2:
                    focus_tokens.add(token)

        if not focus_tokens:
            return full[:max_chars]

        scored: List[Tuple[int, str]] = []
        for para in paragraphs:
            para_l = para.lower()
            score = sum(1 for t in focus_tokens if t in para_l)
            if score > 0:
                scored.append((score, para))
        scored.sort(key=lambda x: x[0], reverse=True)

        selected: List[str] = []
        length = 0
        for _score, para in scored[:20]:
            if length + len(para) + 2 > max_chars:
                continue
            selected.append(para)
            length += len(para) + 2

        if not selected:
            return full[:max_chars]
        return "\n".join(selected)

    def _fallback_report(
        self,
        url: str,
        title: str,
        text: str,
        marked_claims: List[str],
    ) -> Dict[str, Any]:
        paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 50]
        preview = paragraphs[:6]

        claim_checks = []
        lower_text = text.lower()
        for claim in marked_claims[:15]:
            claim_tokens = [token.lower() for token in claim.split() if len(token) > 2]
            hit = sum(1 for token in claim_tokens if token in lower_text)
            if hit >= max(2, len(claim_tokens) // 2):
                status = "supported"
            elif hit >= max(1, len(claim_tokens) // 3):
                status = "partially_supported"
            else:
                status = "unclear"
            claim_checks.append(
                {
                    "claim": claim,
                    "status": status,
                    "evidence_from_page": preview[0] if preview else "",
                }
            )

        return {
            "url": url,
            "title": title,
            "highlighted_claims": marked_claims,
            "page_summary": "\n".join(preview[:3]),
            "key_points": preview[:5],
            "risk_flags": ["LLM unavailable: fallback summary used"],
            "keywords": [],
            "reliability_assessment": {
                "score": 0.58,
                "rationale": "Fallback mode based on structural page extraction without LLM semantic validation.",
            },
            "structured_claim_checks": claim_checks,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": "fallback",
            "_source_text_excerpt": text[:4000],
            "web_content": text,
        }

    @staticmethod
    def _split_sentences(text: str, limit: int = 6) -> List[str]:
        chunks = re.split(r"(?<=[。！？!?\.])\s+|\n+", str(text or ""))
        sentences = []
        for chunk in chunks:
            sentence = " ".join(str(chunk).split()).strip()
            if len(sentence) < 12:
                continue
            sentences.append(sentence)
            if len(sentences) >= limit:
                break
        return sentences

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip()).lower()

    def _dedupe_list(self, items: List[Any], limit: int = 10) -> List[Any]:
        seen = set()
        output: List[Any] = []
        for item in items:
            text = self._normalize_text(str(item))
            if not text or text in seen:
                continue
            seen.add(text)
            output.append(str(item).strip())
            if len(output) >= limit:
                break
        return output

    def _dedupe_claim_checks(self, checks: List[Dict[str, Any]], limit: int = 12) -> List[Dict[str, Any]]:
        seen = set()
        output: List[Dict[str, Any]] = []
        for item in checks:
            claim = str(item.get("claim", "")).strip()
            status = str(item.get("status", "")).strip()
            evidence = str(item.get("evidence_from_page", "")).strip()
            key = (
                self._normalize_text(claim),
                self._normalize_text(status),
                self._normalize_text(evidence),
            )
            if not key[0] or key in seen:
                continue
            seen.add(key)
            output.append(
                {
                    "claim": claim,
                    "status": status,
                    "evidence_from_page": evidence,
                }
            )
            if len(output) >= limit:
                break
        return output

    @staticmethod
    def _verdict_to_status(verdict: str) -> str:
        mapping = {
            "fully_supported": "supported",
            "strongly_supported": "supported",
            "moderately_supported": "partially_supported",
            "uncertain": "unclear",
            "insufficient": "unclear",
            "strongly_refuted": "contradicted",
        }
        return mapping.get(str(verdict or "").strip().lower(), "unclear")

    def _prepare_analysis_claims(
        self,
        report_json: Dict[str, Any],
        priority_focus_marks: List[str],
        secondary_focus_marks: List[str],
        limit: int = 3,
    ) -> List[str]:
        candidates: List[str] = []
        candidates.extend(priority_focus_marks[:3])
        candidates.extend(secondary_focus_marks[:2])
        if not priority_focus_marks:
            candidates.extend((report_json.get("highlighted_claims", []) or [])[:3])
        title = str(report_json.get("title", "")).strip()
        if title:
            candidates.append(title)
        candidates.extend((report_json.get("key_points", []) or [])[:2])
        candidates.extend(self._split_sentences(report_json.get("page_summary", ""), limit=2))
        candidates.extend(self._split_sentences(report_json.get("_source_text_excerpt", ""), limit=2))

        prepared: List[str] = []
        seen = set()
        for item in candidates:
            claim = " ".join(str(item).split()).strip(" -•\t")
            normalized = self._normalize_text(claim)
            if len(claim) < 8 or not normalized or normalized in seen:
                continue
            seen.add(normalized)
            prepared.append(claim)
            if len(prepared) >= limit:
                break

        if not prepared:
            fallback_title = title or "请核查页面核心事实与论证"
            prepared.append(fallback_title)
        return prepared

    @staticmethod
    def _serialize_evidence(evidence: Any) -> Dict[str, Any]:
        return {
            "quote": getattr(evidence, "quote", ""),
            "url": getattr(evidence, "url", ""),
            "source": getattr(evidence, "source", ""),
            "stance": getattr(evidence, "stance", ""),
            "credibility": getattr(evidence, "credibility", 0.0),
            "relevance": getattr(evidence, "relevance", 0.0),
            "rationale": getattr(evidence, "rationale", ""),
            "context_alignment": getattr(evidence, "context_alignment", 0.0),
            "semantic_depth": getattr(evidence, "semantic_depth", 0.0),
            "evidence_strength": getattr(evidence, "evidence_strength", 0.0),
        }

    def _serialize_verification_report(self, report: Any) -> Dict[str, Any]:
        score = getattr(report, "score_breakdown", None)
        return {
            "claim": getattr(report, "claim", ""),
            "confidence_score": getattr(report, "confidence_score", 0.0),
            "confidence_level": getattr(report, "confidence_level", {}) or {},
            "verdict": getattr(report, "verdict", "uncertain"),
            "score_breakdown": {
                "factuality": getattr(score, "factuality", 0.0),
                "source_credibility": getattr(score, "source_credibility", 0.0),
                "evidence_consistency": getattr(score, "evidence_consistency", 0.0),
                "logical_rigor": getattr(score, "logical_rigor", 0.0),
                "premise_coverage": getattr(score, "premise_coverage", 0.0),
            },
            "logic_conditions": list(getattr(report, "logic_conditions", []) or []),
            "hidden_premises": list(getattr(report, "hidden_premises", []) or []),
            "supporting_evidence": [
                self._serialize_evidence(item) for item in (getattr(report, "supporting_evidence", []) or [])[:4]
            ],
            "refuting_evidence": [
                self._serialize_evidence(item) for item in (getattr(report, "refuting_evidence", []) or [])[:4]
            ],
            "reasoning_chain": list(getattr(report, "reasoning_chain", []) or []),
            "trace": dict(getattr(report, "trace", {}) or {}),
        }

    def merge_multi_agent_claim_checks(
        self,
        base_checks: List[Dict[str, Any]],
        agent_claim_reports: List[Dict[str, Any]],
        limit: int = 18,
    ) -> List[Dict[str, Any]]:
        merged = list(base_checks or [])
        for item in agent_claim_reports:
            claim = str(item.get("claim", "")).strip()
            if not claim:
                continue
            evidence_sources = item.get("supporting_evidence") or item.get("refuting_evidence") or []
            evidence_text = ""
            if evidence_sources:
                evidence_text = str(evidence_sources[0].get("quote", "")).strip()
            merged.append(
                {
                    "claim": claim,
                    "status": self._verdict_to_status(item.get("verdict", "")),
                    "evidence_from_page": evidence_text,
                }
            )
        return self._dedupe_claim_checks(merged, limit=limit)

    def _fallback_integrated_findings(
        self,
        report_json: Dict[str, Any],
        agent_claim_reports: List[Dict[str, Any]],
        priority_focus_marks: List[str],
        secondary_focus_marks: List[str],
    ) -> Dict[str, Any]:
        scores = [float(item.get("confidence_score", 0.0) or 0.0) for item in agent_claim_reports]
        average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        overall_verdict = verdict_from_score(average_score) if scores else "insufficient"

        key_consensus_points: List[str] = []
        major_risks: List[str] = []
        logic_watchpoints: List[str] = []
        premise_gaps: List[str] = []
        evidence_highlights: List[str] = []

        for item in agent_claim_reports:
            claim = str(item.get("claim", "")).strip()
            verdict = str(item.get("verdict", "")).strip()
            confidence_score = float(item.get("confidence_score", 0.0) or 0.0)
            if verdict in {"fully_supported", "strongly_supported", "moderately_supported"} and claim:
                key_consensus_points.append(f"{claim}（{confidence_score:.1f}）")
            if verdict in {"strongly_refuted", "uncertain", "insufficient"} and claim:
                major_risks.append(f"{claim}（{verdict}）")
            logic_watchpoints.extend(item.get("logic_conditions", []) or [])
            premise_gaps.extend(item.get("hidden_premises", []) or [])
            supporting = item.get("supporting_evidence", []) or []
            if supporting:
                quote = str(supporting[0].get("quote", "")).strip()
                if quote:
                    evidence_highlights.append(quote)

        key_consensus_points = self._dedupe_list(key_consensus_points, limit=6)
        major_risks = self._dedupe_list((report_json.get("risk_flags", []) or []) + major_risks, limit=8)
        logic_watchpoints = self._dedupe_list(logic_watchpoints, limit=8)
        premise_gaps = self._dedupe_list(premise_gaps, limit=8)
        evidence_highlights = self._dedupe_list(evidence_highlights, limit=6)

        focus_summary = []
        if priority_focus_marks:
            focus_summary.append(f"重点核查 ! 标记 {len(priority_focus_marks)} 条")
        if secondary_focus_marks:
            focus_summary.append(f"补充参考其余标记 {len(secondary_focus_marks)} 条")
        if not focus_summary:
            focus_summary.append("围绕页面核心结论与证据链展开核查")

        narrative_summary = "；".join(
            self._dedupe_list(
                focus_summary
                + key_consensus_points[:3]
                + major_risks[:3],
                limit=6,
            )
        )

        return {
            "overall_confidence": average_score,
            "overall_confidence_level": get_confidence_level_info(average_score),
            "overall_verdict": overall_verdict,
            "key_consensus_points": key_consensus_points,
            "major_risks": major_risks,
            "logic_watchpoints": logic_watchpoints,
            "premise_gaps": premise_gaps,
            "evidence_highlights": evidence_highlights,
            "narrative_summary": narrative_summary,
        }

    def _llm_integrated_findings(
        self,
        report_json: Dict[str, Any],
        agent_claim_reports: List[Dict[str, Any]],
        priority_focus_marks: List[str],
        secondary_focus_marks: List[str],
    ) -> Optional[Dict[str, Any]]:
        if not self.llm.enabled:
            return None

        compact_reports = []
        for item in agent_claim_reports[:6]:
            compact_reports.append(
                {
                    "claim": item.get("claim", ""),
                    "confidence_score": item.get("confidence_score", 0.0),
                    "verdict": item.get("verdict", ""),
                    "logic_conditions": item.get("logic_conditions", [])[:3],
                    "hidden_premises": item.get("hidden_premises", [])[:3],
                    "supporting_evidence": [entry.get("quote", "") for entry in (item.get("supporting_evidence") or [])[:2]],
                    "refuting_evidence": [entry.get("quote", "") for entry in (item.get("refuting_evidence") or [])[:2]],
                }
            )

        prompt_system = (
            "你是多代理网页核查总控助手。"
            "必须只输出一个合法 JSON 对象，不要 Markdown，不要解释。"
            "JSON 字段固定为：overall_confidence,overall_verdict,key_consensus_points,major_risks,"
            "logic_watchpoints,premise_gaps,evidence_highlights,narrative_summary。"
            "其中 overall_confidence 为 0-100 数值；overall_verdict 参考 fully_supported|strongly_supported|"
            "moderately_supported|uncertain|insufficient|strongly_refuted。"
            "必须优先围绕 ! 标记内容综合多个 agent 结果。"
        )
        prompt_user = (
            f"标题：{report_json.get('title', '')}\n"
            f"页面摘要：{report_json.get('page_summary', '')}\n"
            f"重点 ! 标记：{json.dumps(priority_focus_marks, ensure_ascii=False)}\n"
            f"其他标记：{json.dumps(secondary_focus_marks, ensure_ascii=False)}\n"
            f"多代理子报告：{json.dumps(compact_reports, ensure_ascii=False)}"
        )
        result = self.llm.json_call(prompt_system, prompt_user)
        if not result:
            return None

        try:
            overall_confidence = round(float(result.get("overall_confidence", 0.0) or 0.0), 2)
        except Exception:
            overall_confidence = 0.0
        result["overall_confidence"] = max(0.0, min(100.0, overall_confidence))
        result["overall_verdict"] = result.get("overall_verdict") or verdict_from_score(result["overall_confidence"])
        result["overall_confidence_level"] = get_confidence_level_info(result["overall_confidence"])
        result["key_consensus_points"] = self._dedupe_list(result.get("key_consensus_points") or [], limit=6)
        result["major_risks"] = self._dedupe_list(result.get("major_risks") or [], limit=8)
        result["logic_watchpoints"] = self._dedupe_list(result.get("logic_watchpoints") or [], limit=8)
        result["premise_gaps"] = self._dedupe_list(result.get("premise_gaps") or [], limit=8)
        result["evidence_highlights"] = self._dedupe_list(result.get("evidence_highlights") or [], limit=6)
        result["narrative_summary"] = str(result.get("narrative_summary", "")).strip()
        return result

    def build_multi_agent_analysis(
        self,
        report_json: Dict[str, Any],
        priority_focus_marks: List[str],
        secondary_focus_marks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        secondary_focus_marks = secondary_focus_marks or []
        analysis_claims = self._prepare_analysis_claims(
            report_json,
            priority_focus_marks,
            secondary_focus_marks,
            limit=self.analysis_claim_limit,
        )
        verify_input = "\n".join(analysis_claims)

        try:
            verification_reports = self.page_orchestrator.verify_text(
                verify_input,
                source_type="webpage_analysis",
                mode="fast",
            )
        except Exception as error:
            verification_reports = []
            return {
                "analysis_mode": "hybrid_multi_agent",
                "priority_focus_marks": priority_focus_marks,
                "secondary_focus_marks": secondary_focus_marks,
                "analysis_claims": analysis_claims,
                "agent_claim_reports": [],
                "integrated_findings": {
                    "overall_confidence": 0.0,
                    "overall_confidence_level": get_confidence_level_info(0.0),
                    "overall_verdict": "insufficient",
                    "key_consensus_points": [],
                    "major_risks": [f"multi_agent_analysis_failed: {error}"],
                    "logic_watchpoints": [],
                    "premise_gaps": [],
                    "evidence_highlights": [],
                    "narrative_summary": "多代理分析失败，当前仅保留基础网页报告。",
                },
            }

        agent_claim_reports = [self._serialize_verification_report(item) for item in verification_reports]
        integrated_findings = self._fallback_integrated_findings(
            report_json,
            agent_claim_reports,
            priority_focus_marks,
            secondary_focus_marks,
        )
        if self.enable_llm_integrated_findings:
            integrated_findings = self._llm_integrated_findings(
                report_json,
                agent_claim_reports,
                priority_focus_marks,
                secondary_focus_marks,
            ) or integrated_findings

        return {
            "analysis_mode": "hybrid_multi_agent",
            "priority_focus_marks": priority_focus_marks,
            "secondary_focus_marks": secondary_focus_marks,
            "analysis_claims": analysis_claims,
            "agent_claim_reports": agent_claim_reports,
            "integrated_findings": integrated_findings,
        }

    def build_report(
        self,
        url: str,
        marked_claims: List[str],
        priority_focus_marks: Optional[List[str]] = None,
        secondary_focus_marks: Optional[List[str]] = None,
        enable_multi_agent_analysis: bool = True,
        snippet: str = "",
        use_llm: Optional[bool] = None,
        llm_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        llm_enabled_for_report = self.enable_llm_report_generation if use_llm is None else bool(use_llm)
        strategy = self._normalize_llm_strategy(llm_strategy or self.llm_strategy_default)
        if not llm_enabled_for_report:
            strategy = "off"
        title, text = self.fetch_page_text(url)
        if not text.strip():
            # 正文抓取失败 → 优先用 LLM 基于标题+snippet 做推断分析
            if self.llm.enabled and llm_enabled_for_report and strategy != "off":
                inferred = self._llm_title_only_analysis(url, title, marked_claims, snippet=snippet)
            else:
                inferred = None

            if inferred:
                result: Dict[str, Any] = {
                    "url": url,
                    "title": title or url,
                    "highlighted_claims": self._dedupe_list(marked_claims, limit=15),
                    "page_summary": inferred["page_summary"],
                    "key_points": inferred["key_points"],
                    "deep_analysis": inferred["deep_analysis"],
                    "risk_flags": ["⚠️ 网页正文抓取失败，以下为基于标题+标记内容的 AI 推断分析"],
                    "keywords": inferred["keywords"],
                    "reliability_assessment": inferred["reliability_assessment"],
                    "structured_claim_checks": inferred["structured_claim_checks"],
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "generator": "llm_inferred",
                    "_source_text_excerpt": "",
                    "web_content": "",
                }
            else:
                result = {
                    "url": url,
                    "title": title,
                    "highlighted_claims": marked_claims,
                    "page_summary": "",
                    "key_points": [],
                    "risk_flags": ["No extractable text from page", "LLM inference also unavailable"],
                    "keywords": [],
                    "reliability_assessment": {
                        "score": 0.2,
                        "rationale": "Page text could not be extracted and LLM is unavailable.",
                    },
                    "structured_claim_checks": [],
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "generator": "empty",
                    "_source_text_excerpt": "",
                    "web_content": "",
                }
            result["priority_focus_marks"] = self._dedupe_list(priority_focus_marks or [], limit=15)
            result["secondary_focus_marks"] = self._dedupe_list(secondary_focus_marks or [], limit=15)
            if enable_multi_agent_analysis:
                result["multi_agent_analysis"] = self.build_multi_agent_analysis(
                    result,
                    result["priority_focus_marks"],
                    result["secondary_focus_marks"],
                )
                result["structured_claim_checks"] = self.merge_multi_agent_claim_checks(
                    result.get("structured_claim_checks", []),
                    result["multi_agent_analysis"].get("agent_claim_reports", []),
                )
            return result

        if not self.llm.enabled or strategy == "off":
            result = self._fallback_report(url, title, text, marked_claims)
            result["priority_focus_marks"] = self._dedupe_list(priority_focus_marks or [], limit=15)
            result["secondary_focus_marks"] = self._dedupe_list(secondary_focus_marks or [], limit=15)
            if enable_multi_agent_analysis:
                result["multi_agent_analysis"] = self.build_multi_agent_analysis(
                    result,
                    result["priority_focus_marks"],
                    result["secondary_focus_marks"],
                )
                result["structured_claim_checks"] = self.merge_multi_agent_claim_checks(
                    result.get("structured_claim_checks", []),
                    result["multi_agent_analysis"].get("agent_claim_reports", []),
                )
            return result

        # ── LLM 分层策略：assist 优先，deep 按需 ────────────────────────────────
        deep_result = None
        if strategy == "assist":
            deep_result = self._llm_assist_summary(url, title, text, marked_claims)
        if deep_result is None and strategy == "deep":
            deep_result = self._llm_deep_summary(url, title, text, marked_claims)
        if deep_result:
            result: Dict[str, Any] = {
                "url": url,
                "title": title,
                "highlighted_claims": self._dedupe_list(marked_claims, limit=15),
                "page_summary": deep_result["page_summary"],
                "key_points": deep_result["key_points"],
                "deep_analysis": deep_result["deep_analysis"],
                "risk_flags": [],
                "keywords": deep_result["keywords"],
                "reliability_assessment": deep_result["reliability_assessment"],
                "structured_claim_checks": deep_result["structured_claim_checks"],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "generator": str(deep_result.get("generator") or "llm"),
                "_source_text_excerpt": text[:4000],
                "web_content": text,
            }
        else:
            # 降级：轻量 LLM 提示（原有逻辑）
            prompt_system = (
                "你是网页事实核查整理助手。"
                "必须只输出一个合法 JSON 对象，不要 Markdown，不要解释性文本。"
                "JSON 字段固定为："
                "url,title,highlighted_claims,page_summary,key_points,risk_flags,keywords,"
                "reliability_assessment,structured_claim_checks,generated_at,generator。"
                "其中 reliability_assessment={score:0-1,rationale:string};"
                "structured_claim_checks 是数组，每项包含 claim,status,evidence_from_page。"
                "status 只允许 supported|partially_supported|unclear|contradicted。"
                "必须优先围绕 highlighted_claims 组织分析，输出内容要简洁、可复核。"
            )
            prompt_user = (
                f"网页URL：{url}\n"
                f"网页标题：{title}\n"
                f"重点标记内容（必须突出分析）：{json.dumps(marked_claims, ensure_ascii=False)}\n"
                f"网页正文（截断）：\n{text}"
            )
            result = self.llm.json_call(
                prompt_system,
                prompt_user,
                temperature=0.15,
                model_override=self.llm.aux_model or None,
                max_tokens=self.aux_max_tokens,
            )
            if not result:
                return self._fallback_report(url, title, text, marked_claims)

            result["url"] = result.get("url") or url
            result["title"] = result.get("title") or title
            result["highlighted_claims"] = self._dedupe_list(result.get("highlighted_claims") or marked_claims, limit=15)
            result["key_points"] = self._dedupe_list(result.get("key_points") or [], limit=10)
            result["risk_flags"] = self._dedupe_list(result.get("risk_flags") or [], limit=8)
            result["structured_claim_checks"] = self._dedupe_claim_checks(result.get("structured_claim_checks") or [], limit=12)
            result["generated_at"] = result.get("generated_at") or (datetime.utcnow().isoformat() + "Z")
            result["generator"] = "llm"
            result["_source_text_excerpt"] = text[:4000]
            result["web_content"] = text

        result["priority_focus_marks"] = self._dedupe_list(priority_focus_marks or [], limit=15)
        result["secondary_focus_marks"] = self._dedupe_list(secondary_focus_marks or [], limit=15)
        if enable_multi_agent_analysis:
            result["multi_agent_analysis"] = self.build_multi_agent_analysis(
                result,
                result["priority_focus_marks"],
                result["secondary_focus_marks"],
            )
            result["structured_claim_checks"] = self.merge_multi_agent_claim_checks(
                result.get("structured_claim_checks", []),
                result["multi_agent_analysis"].get("agent_claim_reports", []),
            )
        return result