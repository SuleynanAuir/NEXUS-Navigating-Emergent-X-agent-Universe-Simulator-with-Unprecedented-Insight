from serpapi import GoogleSearch
import requests
import os
from datetime import datetime, timedelta
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, unquote, quote_plus
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
from dotenv import load_dotenv
import yake


load_dotenv(override=True)


LAST_SEARCH_DEBUG = {
    "provider": "",
    "recency": "",
    "errors": [],
    "fallback_provider": "",
    "primary_failure_reason": "",
}


def _reset_search_debug(provider: str, recency: str) -> None:
    LAST_SEARCH_DEBUG["provider"] = provider
    LAST_SEARCH_DEBUG["recency"] = recency
    LAST_SEARCH_DEBUG["errors"] = []
    LAST_SEARCH_DEBUG["fallback_provider"] = ""
    LAST_SEARCH_DEBUG["primary_failure_reason"] = ""


def _record_search_error(provider: str, message: str) -> None:
    LAST_SEARCH_DEBUG.setdefault("errors", []).append(f"{provider}: {message}")
    _set_primary_failure_reason(provider, message)


def _humanize_search_error(provider: str, message: str) -> str:
    text = str(message or "")
    lowered = text.lower()
    if provider == "bigmodel_web_search":
        if "余额不足" in text or "无可用资源包" in text:
            return "BigModel 搜索当前不可用：账号余额不足或资源包已用尽。"
        if "429" in lowered:
            return "BigModel 搜索当前被限流，暂时无法继续请求。"
        if "401" in lowered or "403" in lowered:
            return "BigModel 搜索鉴权失败，请检查 API Key 是否有效。"
    if provider == "serpapi" and ("429" in lowered or "quota" in lowered):
        return "SerpAPI 配额不足或请求过多。"
    if provider == "brave_api" and "missing brave_search_api_key" in lowered:
        return "Brave Search 未配置 API Key。"
    if provider == "baidu_serpapi" and "missing serpapi_api_key" in lowered:
        return "Baidu SerpAPI 依赖的 SERPAPI_API_KEY 未配置。"
    if provider == "google_news_rss":
        return "Google News RSS 请求失败。"
    return f"{provider} 不可用：{text}"


def _set_primary_failure_reason(provider: str, message: str) -> None:
    if not LAST_SEARCH_DEBUG.get("primary_failure_reason"):
        LAST_SEARCH_DEBUG["primary_failure_reason"] = _humanize_search_error(provider, message)


def get_last_search_debug():
    return dict(LAST_SEARCH_DEBUG)


def _resolve_provider(provider=None):
    value = (provider or os.getenv("SEARCH_PROVIDER", "serpapi")).strip().lower()
    return value if value in {"serpapi", "baidu_serpapi", "brave_api", "bigmodel_web_search"} else "serpapi"


def _resolve_recency(recency=None):
    value = (recency or os.getenv("SEARCH_RECENCY", "oneWeek")).strip()
    allowed = {"oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"}
    return value if value in allowed else "oneWeek"


def _google_tbs_from_recency(recency: str) -> str:
    mapping = {
        "oneDay": "qdr:d",
        "oneWeek": "qdr:w",
        "oneMonth": "qdr:m",
        "oneYear": "qdr:y",
        "noLimit": "",
    }
    return mapping.get(recency, "qdr:w")


def _brave_freshness_from_recency(recency: str) -> str:
    mapping = {
        "oneDay": "pd",
        "oneWeek": "pw",
        "oneMonth": "pm",
        "oneYear": "py",
        "noLimit": "",
    }
    return mapping.get(recency, "pw")


def _parse_date_for_sort(date_text):
    """将日期文本转为可排序的时间戳，无法解析时返回最小值。"""
    if not date_text:
        return datetime.min

    text = str(date_text).strip().lower()
    now = datetime.now()

    match = re.search(r"(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\s+ago", text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if "minute" in unit:
            return now - timedelta(minutes=value)
        if "hour" in unit:
            return now - timedelta(hours=value)
        if "day" in unit:
            return now - timedelta(days=value)
        if "week" in unit:
            return now - timedelta(weeks=value)
        if "month" in unit:
            return now - timedelta(days=value * 30)
        if "year" in unit:
            return now - timedelta(days=value * 365)

    for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_text, fmt)
        except Exception:
            continue

    return datetime.min


def _serpapi_request(params):
    last_error = None
    for attempt in range(3):
        try:
            return GoogleSearch(params).get_dict()
        except Exception as error:
            last_error = error
            time.sleep(1.0 * (attempt + 1))
    print(f"SerpAPI 请求失败: {last_error}")
    _record_search_error("serpapi", str(last_error))
    return {}


def _normalize_results(result_items):
    normalized = []
    for result in result_items:
        normalized.append(
            {
                "title": result.get("title", ""),
                "url": result.get("link", "") or result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "date": result.get("date", ""),
            }
        )
    return normalized


def _normalize_brave_results(result_items):
    normalized = []
    for result in result_items:
        normalized.append(
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("description", "") or result.get("snippet", ""),
                "date": result.get("age", "") or result.get("page_age", ""),
            }
        )
    return normalized


def _normalize_bigmodel_results(result_items):
    normalized = []
    for result in result_items:
        normalized.append(
            {
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("content", ""),
                "date": result.get("publish_date", ""),
            }
        )
    return normalized

def _search_with_google_serpapi(keyword, num_results, api_key, recency):
    news_params = {
        "engine": "google",
        "q": keyword,
        "tbm": "nws",
        "num": num_results,
        "api_key": api_key,
    }
    tbs_value = _google_tbs_from_recency(recency)
    if tbs_value:
        news_params["tbs"] = tbs_value
    news_results = _serpapi_request(news_params)
    combined = _normalize_results(news_results.get("news_results", []))

    if len(combined) < num_results:
        web_params = {
            "engine": "google",
            "q": keyword,
            "num": num_results,
            "api_key": api_key,
        }
        if tbs_value:
            web_params["tbs"] = tbs_value
        web_results = _serpapi_request(web_params)
        combined.extend(_normalize_results(web_results.get("organic_results", [])))
    return combined


def _search_with_baidu_serpapi(keyword, num_results, api_key, recency):
    params = {
        "engine": "baidu",
        "q": keyword,
        "rn": num_results,
        "api_key": api_key,
    }
    baidu_results = _serpapi_request(params)
    combined = _normalize_results(baidu_results.get("organic_results", []))

    # 结果不足时，用 Google Web 做兜底，保证稳定性
    if len(combined) < num_results:
        fallback_params = {
            "engine": "google",
            "q": keyword,
            "num": num_results,
            "api_key": api_key,
        }
        tbs_value = _google_tbs_from_recency(recency)
        if tbs_value:
            fallback_params["tbs"] = tbs_value
        web_results = _serpapi_request(fallback_params)
        combined.extend(_normalize_results(web_results.get("organic_results", [])))
    return combined


def _brave_request(keyword, num_results, brave_api_key, recency):
    last_error = None
    endpoint = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": brave_api_key,
    }
    params = {
        "q": keyword,
        "count": num_results,
        "search_lang": "zh-hans",
        "country": "CN",
    }
    freshness = _brave_freshness_from_recency(recency)
    if freshness:
        params["freshness"] = freshness
    for attempt in range(3):
        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=12)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error
            time.sleep(1.0 * (attempt + 1))
    print(f"Brave Search 请求失败: {last_error}")
    _record_search_error("brave_api", str(last_error))
    return {}


def _search_with_brave_api(keyword, num_results, brave_api_key, recency):
    result = _brave_request(keyword, num_results, brave_api_key, recency)
    combined = _normalize_brave_results((result.get("web") or {}).get("results", []))
    return combined


def _bigmodel_web_search_request(keyword, num_results, bigmodel_api_key, recency):
    last_error = None
    endpoint = "https://open.bigmodel.cn/api/paas/v4/web_search"
    headers = {
        "Authorization": f"Bearer {bigmodel_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "search_query": keyword[:70],
        "search_engine": os.getenv("BIGMODEL_SEARCH_ENGINE", "search_pro"),
        "search_intent": False,
        "count": max(1, min(50, int(num_results))),
        "search_recency_filter": recency,
        "content_size": os.getenv("BIGMODEL_CONTENT_SIZE", "medium"),
        "request_id": str(uuid.uuid4()),
        "user_id": os.getenv("BIGMODEL_USER_ID", "grabnews_user"),
    }

    domain_filter = os.getenv("BIGMODEL_SEARCH_DOMAIN_FILTER", "").strip()
    if domain_filter:
        payload["search_domain_filter"] = domain_filter

    for attempt in range(3):
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            error_text = str(error)
            response = getattr(error, "response", None)
            if response is not None:
                body = (response.text or "").strip()
                if body:
                    error_text = f"{error_text}; body={body[:280]}"
            last_error = error_text
            if "429" in str(error):
                break
            time.sleep(1.0 * (attempt + 1))
    print(f"BigModel web-search 请求失败: {last_error}")
    _record_search_error("bigmodel_web_search", str(last_error))
    return {}


def _search_with_bigmodel_web_search(keyword, num_results, bigmodel_api_key, recency):
    result = _bigmodel_web_search_request(keyword, num_results, bigmodel_api_key, recency)
    combined = _normalize_bigmodel_results(result.get("search_result", []))
    return combined


def _extract_duckduckgo_target_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target) if target else raw_url
    return raw_url


def _duckduckgo_html_request(keyword, num_results):
    endpoint = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        response = requests.post(endpoint, data={"q": keyword}, headers=headers, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as error:
        _record_search_error("duckduckgo_html", str(error))
        print(f"DuckDuckGo HTML 检索失败: {error}")
        return ""


def _search_with_duckduckgo_html(keyword, num_results):
    html = _duckduckgo_html_request(keyword, num_results)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select("div.result"):
        title_node = item.select_one("a.result__a")
        snippet_node = item.select_one("a.result__snippet, div.result__snippet")
        if not title_node:
            continue
        raw_url = str(title_node.get("href", "")).strip()
        clean_url = _extract_duckduckgo_target_url(raw_url)
        title = title_node.get_text(" ", strip=True)
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        if not clean_url or not title:
            continue
        results.append(
            {
                "title": title,
                "url": clean_url,
                "snippet": snippet,
                "date": "",
            }
        )
        if len(results) >= num_results * 2:
            break
    return results


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _build_search_jump_url(query: str) -> str:
    text = " ".join((query or "").split()).strip()
    if not text:
        return ""
    return f"https://www.google.com/search?q={quote_plus(text[:120])}"


def _extract_topic_keywords(item: dict, fallback_keyword: str) -> list[str]:
    title = str(item.get("title", "") or "").strip()
    # 只基于标题做关键词抽取，去掉编号与发布时间噪声
    cleaned_title = re.sub(r"^\s*\d+[\.、]\s*", "", title)
    cleaned_title = re.sub(r"[（(]\s*发布时间[:：].*?[）)]", "", cleaned_title)
    cleaned_title = " ".join(cleaned_title.split())

    cleaned_blob = cleaned_title
    if not cleaned_blob:
        return [" ".join(fallback_keyword.split())] if fallback_keyword else []

    stopwords = {
        "发布时间", "内容", "正式", "上线", "超级", "个体", "分钟", "自动", "可以", "相关", "继续",
        "report", "news", "article", "content", "update"
    }

    query_tokens = set(
        token.lower()
        for token in re.split(r"[^\w\u4e00-\u9fff-]+", str(fallback_keyword or ""))
        if len(token) >= 2
    )

    def _normalize_term(text: str) -> str:
        return " ".join(str(text).split()).strip("，。,.!?！？:：;；()（）[]【】\"'")

    # ===== 多角度关键词提取 =====
    all_keywords: dict[str, float] = {}

    # 【角度1】语义重要性（YAKE）
    semantic_candidates: list[tuple[str, float]] = []
    for lang in ["zh", "en"]:
        try:
            extractor = yake.KeywordExtractor(
                lan=lang,
                n=3,
                dedupLim=0.9,
                top=15,
                features=None,
            )
            semantic_candidates.extend(extractor.extract_keywords(cleaned_blob))
        except Exception:
            continue

    ranked = sorted(semantic_candidates, key=lambda x: x[1])
    for phrase, base_score in ranked:
        normalized_phrase = _normalize_term(phrase)
        if not normalized_phrase or len(normalized_phrase) < 3 or len(normalized_phrase) > 25:
            continue

        candidate_tokens = set(
            token.lower()
            for token in re.split(r"[^\w\u4e00-\u9fff-]+", normalized_phrase)
            if len(token) >= 2
        )
        overlap = (len(candidate_tokens & query_tokens) / max(1, len(query_tokens))) if query_tokens else 0.0

        length_penalty = abs(len(normalized_phrase) - 14) * 0.015
        relevance_bonus = 0.18 * overlap
        score = float(base_score) + length_penalty - relevance_bonus
        
        key = normalized_phrase.lower()
        if key not in stopwords:
            all_keywords[normalized_phrase] = all_keywords.get(normalized_phrase, score)

    # 【角度2】实体词（单个重要词汇，如技术名、人名、产品名）
    # 提取大写开头的词、英文词、中文重要词
    entity_pattern = r"[A-Z][a-zA-Z0-9\-]*|[a-z]+[A-Z][a-zA-Z0-9\-]*|[\u4e00-\u9fff]{2,6}(?:[\u4e00-\u9fff]{1,3})*"
    for match in re.finditer(entity_pattern, cleaned_title):
        entity = _normalize_term(match.group())
        if entity and 3 <= len(entity) <= 30 and entity.lower() not in stopwords:
            key = entity.lower()
            if key not in all_keywords:
                all_keywords[entity] = 0.5  # 实体词给中等分数

    # 【角度3】概念组合（抽取短语片段，但选择不同的切分方式）
    # 按标点符号、逻辑词、关键语言符号分片
    phrase_fragments = re.split(r"[，。，、；|/]|(?:和|或|与|以及)", cleaned_title)
    for fragment in phrase_fragments:
        frag = _normalize_term(fragment)
        if not frag or len(frag) < 3 or len(frag) > 20:
            continue
        key = frag.lower()
        if key not in stopwords and key not in all_keywords:
            all_keywords[frag] = 0.6

    # 【角度4】应用场景与技术词（从组合中提取2-3词的片段）
    words = re.split(r"[\s\-_]", cleaned_title)
    filtered_words = [w for w in words if len(w) >= 2 and w.lower() not in stopwords]
    
    # 2词组合（覆盖"应用+场景"、"技术+领域"等）
    for i in range(len(filtered_words) - 1):
        combo = f"{filtered_words[i]} {filtered_words[i+1]}"
        combo_norm = _normalize_term(combo)
        if 4 <= len(combo_norm) <= 30 and combo_norm.lower() not in stopwords:
            key = combo_norm.lower()
            if key not in all_keywords:
                all_keywords[combo_norm] = 0.55

    # 【角度5】按位置权重（标题前半部分的词往往更重要）
    title_first_half = cleaned_title[:len(cleaned_title) // 2]
    for word in re.findall(r"[\u4e00-\u9fff]{2,5}|[A-Za-z][A-Za-z0-9\-]*", title_first_half):
        word_norm = _normalize_term(word)
        if word_norm and len(word_norm) >= 3 and word_norm.lower() not in stopwords:
            if word_norm not in all_keywords:
                all_keywords[word_norm] = 0.4  # 前半部分词给更低分数（更重要）
            else:
                all_keywords[word_norm] = min(all_keywords[word_norm], 0.4)

    # 【角度6】长尾关键词（较长但独特的词组）
    long_phrase_pattern = r"[\u4e00-\u9fff]{4,8}[A-Za-z0-9\-]*[\u4e00-\u9fff]{0,4}|[A-Z][a-zA-Z0-9\-]*[\u4e00-\u9fff]{2,6}"
    for match in re.finditer(long_phrase_pattern, cleaned_title):
        phrase = _normalize_term(match.group())
        if phrase and 4 <= len(phrase) <= 35 and phrase.lower() not in stopwords:
            if phrase not in all_keywords:
                all_keywords[phrase] = 0.65

    # 排序并去重 + 多样性筛选
    sorted_keywords = sorted(all_keywords.items(), key=lambda x: x[1])
    
    output: list[str] = []
    seen = set()
    seen_substrings: set[str] = set()  # 跟踪已选关键词的 token，避免高重合
    
    for keyword, _score in sorted_keywords:
        if not keyword:
            continue
        key = keyword.lower()
        if key in seen or key in stopwords:
            continue
        
        # 多样性检查：避免与已选关键词的 token 重合
        keyword_tokens = set(
            t.lower() for t in re.split(r"[^\w一-鿿-]+", key)
            if len(t) >= 2
        )
        
        # 检查是否与任何已选关键词共享核心 token
        should_skip = False
        for seen_sub in seen_substrings:
            seen_tokens = set(
                t.lower() for t in re.split(r"[^\w一-鿿-]+", seen_sub)
                if len(t) >= 2
            )
            # 严格模式：只要有任何重合的核心词（长度 >= 3）就跳过
            core_keyword_tokens = {t for t in keyword_tokens if len(t) >= 3}
            core_seen_tokens = {t for t in seen_tokens if len(t) >= 3}
            if core_keyword_tokens & core_seen_tokens:  # 有重合核心词就跳过
                should_skip = True
                break
        
        if should_skip:
            continue
        
        seen.add(key)
        seen_substrings.add(key)
        output.append(keyword)
        if len(output) >= 8:
            break

    # 始终包含原始搜索词（如果不在列表中）
    fallback = " ".join(fallback_keyword.split()).strip()
    if fallback and fallback.lower() not in seen:
        output.append(fallback)

    return output[:8]


def _attach_topic_keywords_for_all(items: list[dict], keyword: str, max_keywords: int = 3) -> list[dict]:
    if not items:
        return items
    output = []
    for item in items:
        fixed = dict(item)
        keywords = _extract_topic_keywords(fixed, keyword)
        fixed["topic_keywords"] = keywords[:max(1, max_keywords)]
        if not fixed.get("inferred_topic") and fixed["topic_keywords"]:
            fixed["inferred_topic"] = fixed["topic_keywords"][0]
        output.append(fixed)
    return output


def _attach_related_links_for_missing_urls(items: list[dict], keyword: str, recency: str, num_results: int) -> list[dict]:
    if not items:
        return items

    per_query_limit = max(3, min(8, num_results))

    def _pick_primary_topic(candidates: list[str]) -> str:
        if not candidates:
            return ""
        query_tokens = set(
            token.lower()
            for token in re.split(r"[^\w\u4e00-\u9fff-]+", str(keyword or ""))
            if len(token) >= 2
        )

        def _topic_score(text: str) -> float:
            tokens = set(
                token.lower()
                for token in re.split(r"[^\w\u4e00-\u9fff-]+", text)
                if len(token) >= 2
            )
            relevance = (len(tokens & query_tokens) / max(1, len(query_tokens))) if query_tokens else 0.0
            entity_boost = 0.18 if bool(re.search(r"[A-Za-z0-9]+-[A-Za-z0-9]+", text)) else 0.0
            length_penalty = abs(len(text) - 12) * 0.006
            return relevance + entity_boost - length_penalty

        scored = sorted(
            ((str(i).strip(), _topic_score(str(i).strip())) for i in candidates if str(i).strip()),
            key=lambda x: x[1], reverse=True,
        )
        return scored[0][0] if scored else candidates[0]

    def _process_missing(item: dict) -> dict:
        fixed = dict(item)
        current_url = str(fixed.get("url", "") or "").strip()
        if current_url:
            return fixed

        topic_keywords = [str(t).strip() for t in (fixed.get("topic_keywords") or []) if str(t).strip()]
        if not topic_keywords:
            topic_keywords = _extract_topic_keywords(fixed, keyword)
        inferred_topic = _pick_primary_topic(topic_keywords)
        search_queries = topic_keywords[:3]

        # 三关键词并发 RSS 搜索
        query_results_map: dict = {}
        with ThreadPoolExecutor(max_workers=max(1, len(search_queries))) as pool:
            future_to_query = {
                pool.submit(_search_with_google_news_rss, q, per_query_limit, recency): q
                for q in search_queries
            }
            for future in as_completed(future_to_query):
                q = future_to_query[future]
                try:
                    query_results_map[q] = future.result()
                except Exception:
                    query_results_map[q] = []

        related_links: list = []
        seen_urls: set = set()

        # 第一轮：每个关键词至少取 1 条
        for q in search_queries:
            for entry in query_results_map.get(q, []):
                link = str(entry.get("url", "") or "").strip()
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)
                related_links.append({
                    "title": str(entry.get("title", "") or "").strip(),
                    "url": link,
                    "snippet": str(entry.get("snippet", "") or "").strip(),
                    "date": str(entry.get("date", "") or "").strip(),
                    "query": q,
                })
                break
            if len(related_links) >= 3:
                break

        # 第二轮：若不足 3 条再补足
        if len(related_links) < 3:
            for q in search_queries:
                for entry in query_results_map.get(q, []):
                    link = str(entry.get("url", "") or "").strip()
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)
                    related_links.append({
                        "title": str(entry.get("title", "") or "").strip(),
                        "url": link,
                        "snippet": str(entry.get("snippet", "") or "").strip(),
                        "date": str(entry.get("date", "") or "").strip(),
                        "query": q,
                    })
                    if len(related_links) >= 3:
                        break
                if len(related_links) >= 3:
                    break

        if not related_links and inferred_topic:
            related_links.append({
                "title": f"Google 搜索：{inferred_topic}",
                "url": _build_search_jump_url(inferred_topic),
                "snippet": "", "date": "", "query": inferred_topic,
            })

        # 若不足 3 个，用主题及关键词的 Google 搜索链接补足到 3 个
        if len(related_links) < 3:
            fallback_queries = [inferred_topic] + topic_keywords if inferred_topic else topic_keywords
            for fallback_q in fallback_queries:
                if len(related_links) >= 3:
                    break
                if not any(link.get("query") == fallback_q for link in related_links):
                    related_links.append({
                        "title": f"Google 搜索：{fallback_q}",
                        "url": _build_search_jump_url(fallback_q),
                        "snippet": "", "date": "", "query": fallback_q,
                    })

        fixed["topic_keywords"] = topic_keywords[:3]
        fixed["inferred_topic"] = inferred_topic
        fixed["related_links"] = related_links[:3]
        return fixed

    missing_items = [item for item in items if not str(item.get("url", "") or "").strip()]
    if not missing_items:
        return items

    # 多条无直链结果并发处理
    processed_missing: dict = {}
    with ThreadPoolExecutor(max_workers=min(4, len(missing_items))) as pool:
        future_to_idx = {pool.submit(_process_missing, item): i for i, item in enumerate(missing_items)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                processed_missing[idx] = future.result()
            except Exception:
                processed_missing[idx] = missing_items[idx]

    # 按原始顺序合并
    output = []
    miss_ptr = 0
    for item in items:
        if str(item.get("url", "") or "").strip():
            output.append(item)
        else:
            output.append(processed_missing.get(miss_ptr, item))
            miss_ptr += 1
    return output

def _extract_related_queries(item: dict, fallback_keyword: str) -> list[str]:
    title = str(item.get("title", "") or "").strip()
    snippet = str(item.get("snippet", "") or "").strip()
    text_blob = f"{title} {snippet}".strip()

    queries: list[str] = []

    for matched in re.findall(r"[\"“”']([^\"“”']{2,80})[\"“”']", text_blob):
        cleaned = " ".join(matched.split()).strip()
        if cleaned:
            queries.append(cleaned)

    for matched in re.findall(r"\b[A-Z][A-Z0-9-]{2,}\b", text_blob):
        cleaned = matched.strip()
        if cleaned and not cleaned.isdigit():
            queries.append(cleaned)

    compact_title = re.sub(r"[（(].*?[）)]", " ", title)
    compact_title = re.sub(r"\d{4}-\d{2}-\d{2}[^\s]*", " ", compact_title)
    compact_title = " ".join(compact_title.split())
    if compact_title:
        queries.append(compact_title[:80])

    if fallback_keyword:
        queries.append(" ".join(fallback_keyword.split()))

    deduped = []
    seen = set()
    for query in queries:
        key = query.lower()
        if query and key not in seen:
            seen.add(key)
            deduped.append(query)
    return deduped[:6]


def _enrich_missing_urls(items: list[dict], keyword: str, recency: str, num_results: int) -> list[dict]:
    if not items:
        return items

    enriched = []
    search_limit = max(3, min(8, num_results))
    for item in items:
        current_url = str(item.get("url", "") or "").strip()
        if current_url:
            enriched.append(item)
            continue

        fixed_item = dict(item)
        related_queries = _extract_related_queries(item, keyword)
        direct_url = ""
        used_query = ""

        for query in related_queries:
            rss_results = _search_with_google_news_rss(query, search_limit, recency)
            candidate = next((entry for entry in rss_results if str(entry.get("url", "")).strip()), None)
            if candidate:
                direct_url = str(candidate.get("url", "")).strip()
                used_query = query
                if not fixed_item.get("date") and candidate.get("date"):
                    fixed_item["date"] = candidate.get("date", "")
                if not fixed_item.get("snippet") and candidate.get("snippet"):
                    fixed_item["snippet"] = candidate.get("snippet", "")
                break

        if not direct_url:
            fallback_query = related_queries[0] if related_queries else keyword
            direct_url = _build_search_jump_url(fallback_query)
            used_query = fallback_query

        fixed_item["url"] = direct_url
        fixed_item["enriched_query"] = used_query
        fixed_item["enriched_from_missing_link"] = True
        enriched.append(fixed_item)

    return enriched


def _rss_query_variants(keyword: str) -> list[str]:
    compact = " ".join((keyword or "").split())
    if not compact:
        return []
    head_phrase = " ".join(compact.split()[:8])
    variants = [compact]
    if head_phrase and head_phrase != compact:
        variants.append(f'"{head_phrase}"')
    if "research" not in compact.lower():
        variants.append(f"{compact} research")
    if "study" not in compact.lower():
        variants.append(f"{compact} study")
    deduped = []
    for item in variants:
        if item not in deduped:
            deduped.append(item)
    return deduped[:4]


def _search_with_google_news_rss(keyword, num_results, recency):
    when_map = {
        "oneDay": " when:1d",
        "oneWeek": " when:7d",
        "oneMonth": " when:30d",
        "oneYear": " when:365d",
        "noLimit": "",
    }
    locales = [
        ("zh-CN", "CN", "CN:zh-Hans"),
        ("en-US", "US", "US:en"),
        ("en-GB", "GB", "GB:en"),
    ]
    queries = _rss_query_variants(keyword)
    results = []
    seen = set()

    def _fetch_locale(scoped_query: str, hl: str, gl: str, ceid: str) -> list:
        params = {"q": scoped_query, "hl": hl, "gl": gl, "ceid": ceid}
        try:
            response = requests.get("https://news.google.com/rss/search", params=params, timeout=4)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception as error:
            _record_search_error("google_news_rss", f"{hl}/{gl}: {error}")
            return []
        items = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = _strip_html_tags(item.findtext("description") or "")
            pub_date = (item.findtext("pubDate") or "").strip()
            if title and link:
                items.append({"title": title, "url": link, "snippet": description, "date": pub_date})
        return items

    for query in queries:
        if len(results) >= num_results * 6:
            break
        scoped_query = f"{query}{when_map.get(recency, '')}".strip()
        with ThreadPoolExecutor(max_workers=len(locales)) as pool:
            futures = [pool.submit(_fetch_locale, scoped_query, hl, gl, ceid) for hl, gl, ceid in locales]
            for future in as_completed(futures):
                for entry in future.result():
                    key = entry["url"] or entry["title"]
                    if key not in seen:
                        seen.add(key)
                        results.append(entry)
                        if len(results) >= num_results * 6:
                            break
    return results


def _run_single_provider(keyword, num_results, provider, recency):
    if provider == "brave_api":
        brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
        if not brave_api_key:
            _record_search_error("brave_api", "missing BRAVE_SEARCH_API_KEY")
            return []
        return _search_with_brave_api(keyword, num_results, brave_api_key, recency)

    if provider == "bigmodel_web_search":
        bigmodel_api_key = os.getenv("BIGMODEL_API_KEY", "").strip()
        if not bigmodel_api_key:
            _record_search_error("bigmodel_web_search", "missing BIGMODEL_API_KEY")
            return []
        return _search_with_bigmodel_web_search(keyword, num_results, bigmodel_api_key, recency)

    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        _record_search_error(provider, "missing SERPAPI_API_KEY")
        return []

    if provider == "baidu_serpapi":
        return _search_with_baidu_serpapi(keyword, num_results, api_key, recency)
    return _search_with_google_serpapi(keyword, num_results, api_key, recency)


def _fallback_provider_order(selected_provider):
    order = [selected_provider]
    candidates = ["bigmodel_web_search", "serpapi", "brave_api", "baidu_serpapi"]
    for provider in candidates:
        if provider != selected_provider:
            order.append(provider)
    return order


def search_news(keyword, num_results=10, provider=None, recency=None):
    """
    仅使用 SerpAPI 搜索关键词（不使用 DuckDuckGo）。
    优先新闻检索，结果不足时补充通用网页检索。
    """
    selected_provider = _resolve_provider(provider)
    selected_recency = _resolve_recency(recency)
    _reset_search_debug(selected_provider, selected_recency)

    combined = []
    used_provider = selected_provider
    for attempt_provider in _fallback_provider_order(selected_provider):
        candidate_results = _run_single_provider(keyword, num_results, attempt_provider, selected_recency)
        if candidate_results:
            combined = candidate_results
            used_provider = attempt_provider
            if attempt_provider != selected_provider:
                LAST_SEARCH_DEBUG["fallback_provider"] = attempt_provider
                print(f"搜索源 {selected_provider} 无结果，已自动降级到 {attempt_provider}。")
            break

    if not combined and selected_recency != "noLimit":
        for attempt_provider in _fallback_provider_order(used_provider):
            candidate_results = _run_single_provider(keyword, num_results, attempt_provider, "noLimit")
            if candidate_results:
                combined = candidate_results
                if attempt_provider != selected_provider:
                    LAST_SEARCH_DEBUG["fallback_provider"] = attempt_provider
                print(f"当前时效 {selected_recency} 无结果，已自动放宽到 noLimit。")
                break

    if not combined:
        fallback_results = _search_with_google_news_rss(keyword, num_results, selected_recency)
        if fallback_results:
            combined = fallback_results
            LAST_SEARCH_DEBUG["fallback_provider"] = "google_news_rss"
            print("主搜索源不可用，已自动降级到 Google News RSS 检索。")

    if not combined:
        fallback_results = _search_with_duckduckgo_html(keyword, num_results)
        if fallback_results:
            combined = fallback_results
            LAST_SEARCH_DEBUG["fallback_provider"] = "duckduckgo_html"
            print("主搜索源不可用，已自动降级到 DuckDuckGo HTML 检索。")

    if not combined:
        return []

    combined = _attach_topic_keywords_for_all(combined, keyword, max_keywords=3)
    combined = _attach_related_links_for_missing_urls(combined, keyword, selected_recency, num_results)

    filtered = []
    all_items = []
    keyword_tokens = [token.lower() for token in keyword.split() if token.strip()]
    for item in combined:
        all_items.append(item)
        title = item["title"].lower()
        snippet = item["snippet"].lower()
        if any(token in title or token in snippet for token in keyword_tokens):
            filtered.append(item)

    ranked = filtered if filtered else all_items
    deduped = []
    seen = set()
    for item in ranked:
        key = item.get("url", "") or f"{item.get('title','')}|{item.get('snippet','')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda x: _parse_date_for_sort(x.get("date", "")), reverse=True)
    return deduped[:num_results]

if __name__ == "__main__":
    keyword = "GraphRAG research"
    urls = search_news(keyword, 10, provider=os.getenv("SEARCH_PROVIDER", "serpapi"))
    print(urls)