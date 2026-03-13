import streamlit as st
import requests
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from search import search_news
import webbrowser
from dotenv import load_dotenv
import os
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None
try:
    import yake
except Exception:
    yake = None

st.set_page_config(page_title="知识标注系统", page_icon="🧠", layout="wide")

load_dotenv()  # 加载.env文件

def get_hypothesis_annotations(username, token, current_urls=None):
    """
    从Hypothesis API获取用户的注释。
    如果提供current_urls，只返回这些URL的注释。
    返回 (annotations, error_message)
    """
    url = f"https://hypothes.is/api/search?user={username}&limit=200"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "grabNews/1.0",
        "Accept": "application/json",
    }

    response = None
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            break
        except requests.exceptions.SSLError as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
        except requests.exceptions.RequestException as error:
            last_error = error
            time.sleep(1.0 * (attempt + 1))

    if response is None:
        if isinstance(last_error, requests.exceptions.SSLError):
            return [], (
                "连接 Hypothesis 失败（SSL握手异常）。"
                "请检查网络/代理/VPN，稍后重试；"
                "如果在公司网络，建议切换手机热点测试。"
            )
        return [], f"请求Hypothesis失败: {last_error}"

    if response.status_code == 200:
        data = response.json()
        annotations = []
        current_url_set = set(current_urls) if current_urls else None
        for row in data.get('rows', []):
            tags = row.get('tags', [])
            uri = row.get('uri', '')
            if current_url_set and uri not in current_url_set:
                continue  # 静默跳过，不打印
            if '!' in tags:
                mark_type = '!'
            elif '?' in tags:
                mark_type = '?'
            else:
                continue  # 静默跳过，不打印
            
            # 提取高亮文本
            highlight_text = ""
            targets = row.get('target', [])
            if targets:
                selectors = targets[0].get('selector', [])
                for selector in selectors:
                    if selector.get('type') == 'TextQuoteSelector':
                        highlight_text = selector.get('exact', '')
                        break
            if not highlight_text.strip():
                continue  # 静默跳过，不打印
            
            annotations.append({
                'type': mark_type,
                'text': highlight_text,
                'url': uri,
                'timestamp': row.get('created', '')
            })
        return annotations, None
    else:
        return [], f"获取Hypothesis注释失败: {response.status_code}"

# 假设标注数据存储在内存中（实际可存文件）
if 'annotations' not in st.session_state:
    st.session_state.annotations = []
if 'seen_annotation_keys' not in st.session_state:
    st.session_state.seen_annotation_keys = set()
if 'latest_new_annotations' not in st.session_state:
    st.session_state.latest_new_annotations = []
if 'flash_messages' not in st.session_state:
    st.session_state.flash_messages = []
if 'sync_enabled' not in st.session_state:
    st.session_state.sync_enabled = True
if 'sync_interval' not in st.session_state:
    st.session_state.sync_interval = 6


def build_focus_tags(title, snippet, keyword):
    """基于 NLP 关键词提取生成重点标签（非硬编码规则）。"""
    raw_text = f"{title}。{snippet}"
    if not raw_text.strip():
        return []

    is_zh = bool(re.search(r"[\u4e00-\u9fff]", raw_text))
    lang = "zh" if is_zh else "en"

    # 使用 YAKE 进行无监督关键词提取
    if yake is not None:
        extractor = yake.KeywordExtractor(
            lan=lang,
            n=2,
            dedupLim=0.9,
            top=8,
            features=None,
        )
        key_phrases = extractor.extract_keywords(raw_text)
        ordered = [phrase.strip() for phrase, _ in key_phrases if phrase and phrase.strip()]
    else:
        # 兜底：没有 yake 时做最小分词回退
        ordered = re.findall(r"[A-Za-z][A-Za-z\-]{2,}|[\u4e00-\u9fff]{2,}", raw_text)

    cleaned = []
    for phrase in ordered:
        p = phrase.strip(" -_.,:;()[]{}\"'`“”‘’")
        if len(p) < 2:
            continue
        if p.lower() in {"https", "http", "www", "com"}:
            continue
        if p not in cleaned:
            cleaned.append(p)

    # 给用户关键词做轻微加权：如果包含搜索词，优先展示
    if keyword:
        kws = [k.strip() for k in keyword.split() if k.strip()]
        boosted = []
        others = []
        for tag in cleaned:
            if any(k.lower() in tag.lower() for k in kws):
                boosted.append(tag)
            else:
                others.append(tag)
        cleaned = boosted + others

    return cleaned[:4]

def append_new_annotations(annotations):
    """只处理新增标注：更新session、终端打印、追加写入txt。"""
    new_anns = []
    with open("annotations.txt", "a", encoding="utf-8") as f:
        for ann in annotations:
            key = f"{ann['type']}|{ann['text']}|{ann.get('url','')}"
            if key in st.session_state.seen_annotation_keys:
                continue
            st.session_state.seen_annotation_keys.add(key)
            st.session_state.annotations.append(ann)
            new_anns.append(ann)
            st.session_state.flash_messages.append({
                "message": f"新增标记 {ann['type']} | {ann['text'][:80]}",
                "created_at": time.time()
            })
            print(f"新增标记 & {ann['type']} | {ann['text']}", flush=True)
            f.write(f"{ann['type']} | {ann['text']} | {ann.get('timestamp','')}\n")
    return new_anns


def run_search_with_animation(keyword, num_results=10):
    """搜索时展示平滑的阶段式进度条，避免闪烁。"""
    stages = [
        "准备检索…",
        "连接搜索引擎…",
        "抓取候选结果…",
        "按相关度与时间排序…",
        "整理展示内容…",
    ]

    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    started_at = time.time()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(search_news, keyword, num_results)
        progress = 2

        while not future.done():
            stage_index = min(len(stages) - 1, max(0, progress // 22))
            status_placeholder.info(f"🔎 {stages[stage_index]}")
            progress_placeholder.progress(progress, text=f"搜索中 {progress}%")
            progress = min(92, progress + 3)
            time.sleep(0.12)

        urls = future.result()

    # 确保动画至少显示一小段时间，避免“闪一下”
    while time.time() - started_at < 1.1:
        progress = min(96, progress + 2)
        progress_placeholder.progress(progress, text=f"搜索中 {progress}%")
        time.sleep(0.08)

    status_placeholder.success("✅ 搜索完成")
    progress_placeholder.progress(100, text="搜索完成 100%")
    time.sleep(0.22)
    status_placeholder.empty()
    progress_placeholder.empty()
    return urls

def main():
    st.markdown(
        """
        <style>
            html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stMain"] {
                height: 100vh;
                overflow: hidden !important;
            }
            [data-testid="stMainBlockContainer"] {
                max-height: calc(100vh - 3.2rem);
                overflow: hidden !important;
                padding-top: 1.45rem;
                padding-bottom: 0.2rem;
            }
            .main-title {font-size: 1.35rem; font-weight: 750; margin-top: 0.2rem; margin-bottom: 0.06rem; line-height: 1.3; transition: transform .18s ease, color .18s ease, text-shadow .18s ease; display: inline-block; cursor: default;}
            .main-title:hover {transform: translateY(-1px) scale(1.01); color: #0f172a; text-shadow: 0 3px 10px rgba(15,23,42,0.12);}
            .sub-title {color: #6b7280; margin-bottom: 0.20rem; font-size: 0.82rem; line-height: 1.25;}
            .small-tip {color: #6b7280; font-size: 0.82rem;}
            div[data-testid="stMarkdownContainer"] p,
            div[data-testid="stMarkdownContainer"] li,
            label,
            .stTextInput label,
            .stSelectbox label,
            .stTextArea label,
            .stButton button {
                font-size: 0.9rem !important;
            }
            h3, [data-testid="stSubheader"] {
                font-size: 1.05rem !important;
                line-height: 1.2 !important;
            }
            .flash-item {
                background: #ecfdf5;
                border: 1px solid #86efac;
                color: #065f46;
                border-radius: 10px;
                padding: 0.42rem 0.6rem;
                margin-bottom: 0.28rem;
                font-size: 0.86rem;
            }
            .meta-row {display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin: 0.2rem 0 0.35rem 0;}
            .date-pill {font-size: 0.78rem; color: #374151; background: #f3f4f6; border-radius: 999px; padding: 0.14rem 0.5rem;}
            .tag-pill {font-size: 0.74rem; color: #075985; background: #e0f2fe; border-radius: 999px; padding: 0.14rem 0.45rem; border: 1px solid #bae6fd; transition: transform .15s ease, box-shadow .15s ease, background-color .15s ease; display: inline-block; cursor: pointer;}
            .tag-pill:hover {transform: translateY(-1px); box-shadow: 0 4px 10px rgba(3,105,161,0.18); background: #dbeafe;}
            .result-title {font-size: 0.98rem; font-weight: 700; color: #0f172a; transition: color .18s ease, transform .18s ease; display: inline-block; cursor: pointer;}
            .result-title:hover {color: #1d4ed8; transform: translateX(2px);}

            .stButton > button,
            div[data-testid="stFormSubmitButton"] > button {
                transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease, background-color .16s ease;
            }
            .stButton > button:hover,
            div[data-testid="stFormSubmitButton"] > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 8px 16px rgba(15, 23, 42, 0.12);
                border-color: #93c5fd;
                background-color: #f8fbff;
            }
            .stButton > button:active,
            div[data-testid="stFormSubmitButton"] > button:active {
                transform: translateY(0px) scale(0.99);
            }
            .kpi-strip {display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 0.2rem 0 0.45rem 0;}
            .kpi-pill {background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 999px; padding: 0.18rem 0.62rem; font-size: 0.78rem; color: #334155;}
            @media (max-height: 900px) {
                .main-title {font-size: 1.2rem;}
                .sub-title {font-size: 0.76rem;}
                .kpi-pill {font-size: 0.72rem; padding: 0.12rem 0.5rem;}
                [data-testid="stMainBlockContainer"] {
                    max-height: calc(100vh - 2.8rem);
                    padding-top: 1.1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='main-title'>知识标注系统</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>搜索新闻 · 打开网页标记 · 自动同步标注</div>", unsafe_allow_html=True)

    # 仅保留最近8秒的动态消息
    now_ts = time.time()
    st.session_state.flash_messages = [
        m for m in st.session_state.flash_messages
        if now_ts - m.get("created_at", 0) <= 8
    ]
    for msg in st.session_state.flash_messages:
        st.markdown(f"<div class='flash-item'>{msg['message']}</div>", unsafe_allow_html=True)

    st.markdown(
        (
            "<div class='kpi-strip'>"
            f"<span class='kpi-pill'>累计标注：{len(st.session_state.annotations)}</span>"
            f"<span class='kpi-pill'>本轮新增：{len(st.session_state.get('latest_new_annotations', []))}</span>"
            f"<span class='kpi-pill'>当前关键词：{st.session_state.get('current_keyword', '-')}</span>"
            f"<span class='kpi-pill'>搜索结果数：{len(st.session_state.get('urls', []))}</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    has_api_key = bool(os.getenv('SERPAPI_API_KEY'))
    if not has_api_key:
        st.warning("未设置 SERPAPI_API_KEY，当前无法执行检索。请先配置后再搜索。")

    # 顶部搜索栏（用 form 提升点击稳定性）
    with st.form("search_form", clear_on_submit=False):
        top_left, top_right = st.columns([5, 1])
        with top_left:
            keyword = st.text_input("搜索关键词", st.session_state.get('current_keyword', 'GraphRAG research'), key="keyword_input")
        with top_right:
            do_search = st.form_submit_button("🔎 搜索", use_container_width=True)

    if do_search:
        try:
            urls = run_search_with_animation(keyword, 10)
            st.session_state['urls'] = urls
            st.session_state['current_keyword'] = keyword
            if not urls:
                st.warning("本次未检索到结果，请换关键词或稍后再试。")
        except Exception as error:
            st.error(f"搜索失败：{error}")

    # 自适应面板高度：根据顶部提示数量自动收敛，降低整页滚动概率
    flash_count = len(st.session_state.flash_messages)
    warning_offset = 40 if not has_api_key else 0
    panel_height = max(380, 540 - flash_count * 18 - warning_offset)

    left_col, right_col = st.columns([1.7, 1], gap="small")

    with left_col:
        st.subheader("搜索结果")
        result_panel = st.container(height=panel_height, border=True)
        with result_panel:
            urls = st.session_state.get('urls', [])
            if not urls:
                st.info("先在上方输入关键词并点击搜索。")
            else:
                for i, url_data in enumerate(urls):
                    with st.container(border=True):
                        item_left, item_right = st.columns([4, 1])
                        with item_left:
                            st.markdown(f"<div class='result-title'>{url_data['title']}</div>", unsafe_allow_html=True)
                            st.write(f"来源：{url_data['url']}")
                            publish_time = url_data.get('date', '')
                            tags = build_focus_tags(
                                url_data.get('title', ''),
                                url_data.get('snippet', ''),
                                st.session_state.get('current_keyword', '')
                            )
                            tags_html = "".join([f"<span class='tag-pill'>{t}</span>" for t in tags])
                            st.markdown(
                                f"<div class='meta-row'><span class='date-pill'>发表时间：{publish_time if publish_time else '未知'}</span>{tags_html}</div>",
                                unsafe_allow_html=True,
                            )
                            st.write(f"摘要：{url_data['snippet'][:240]}...")
                        with item_right:
                            if st.button(f"打开网页 {i+1}", key=f"open_{i}", use_container_width=True):
                                webbrowser.open(url_data['url'])
                                st.session_state['current_open_url'] = url_data['url']
                                st.success("已打开")

    with right_col:
        st.subheader("标记与同步")
        right_panel = st.container(height=panel_height, border=True)
        with right_panel:
            st.caption("在浏览器中使用 Hypothesis 高亮并打标签（! / ?），系统会自动同步。")

            current_open_url = st.session_state.get('current_open_url', '')
            st.write(f"当前页面：{current_open_url if current_open_url else '未选择'}")

            hypothesis_username = st.text_input(
                "Hypothesis 用户名",
                value=os.getenv('HYPOTHESIS_USERNAME', ''),
                key="hypothesis_username"
            )
            hypothesis_token = st.text_input(
                "Hypothesis API Token",
                value=os.getenv('HYPOTHESIS_TOKEN', ''),
                type="password",
                key="hypothesis_token"
            )

            sync_col1, sync_col2 = st.columns([1.2, 1])
            with sync_col1:
                st.session_state.sync_enabled = st.checkbox("实时同步", value=st.session_state.sync_enabled)
            with sync_col2:
                st.session_state.sync_interval = st.selectbox(
                    "轮询秒数",
                    [4, 6, 8, 10],
                    index=[4, 6, 8, 10].index(st.session_state.sync_interval) if st.session_state.sync_interval in [4, 6, 8, 10] else 1,
                )

            # 自动轮询仅在同步阶段开启，默认较慢轮询减少闪烁
            if (
                st_autorefresh is not None
                and st.session_state.sync_enabled
                and current_open_url
                and hypothesis_username
                and hypothesis_token
            ):
                st_autorefresh(interval=st.session_state.sync_interval * 1000, key="hypothesis_auto_poll")
            elif st_autorefresh is None:
                st.info("未安装 streamlit-autorefresh，自动同步可能较慢。")

            # 自动同步当前页面标注
            if current_open_url and hypothesis_username and hypothesis_token and st.session_state.sync_enabled:
                annotations, error = get_hypothesis_annotations(
                    hypothesis_username,
                    hypothesis_token,
                    [current_open_url]
                )
                if error:
                    st.error(error)
                else:
                    new_anns = append_new_annotations(annotations)
                    st.session_state.latest_new_annotations = new_anns

            tab_sync, tab_new, tab_all = st.tabs(["同步控制", "新增流", "累计标注"])

            with tab_sync:
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("手动获取", use_container_width=True):
                        if hypothesis_username and hypothesis_token:
                            annotations, error = get_hypothesis_annotations(
                                hypothesis_username,
                                hypothesis_token,
                                [current_open_url] if current_open_url else []
                            )
                            if error:
                                st.error(error)
                            else:
                                new_anns = append_new_annotations(annotations)
                                st.session_state.latest_new_annotations = new_anns
                                st.success(f"新增 {len(new_anns)} 条")
                        else:
                            st.error("请填写 Hypothesis 用户名和 Token")
                with btn_col2:
                    if st.button("导出 JSON", use_container_width=True):
                        data = {
                            'keyword': st.session_state.get('current_keyword', ''),
                            'annotations': st.session_state.annotations
                        }
                        with open("annotations.json", "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                        st.success("已导出 annotations.json")

                with st.expander("手动添加标记", expanded=False):
                    marked_text = st.text_area("粘贴标记内容", height=120, key="marked_text")
                    mark_type = st.selectbox("标记类型", ["?", "!"], key="mark_type")
                    if st.button("添加标记", use_container_width=True):
                        if marked_text.strip():
                            ann = {
                                'type': mark_type,
                                'text': marked_text,
                                'url': current_open_url,
                                'timestamp': str(datetime.now())
                            }
                            appended = append_new_annotations([ann])
                            st.session_state.latest_new_annotations = appended
                            st.success("标记已添加")
                        else:
                            st.error("请粘贴标记内容")

                if st.button("导出 TXT", use_container_width=True):
                    with open("annotations.txt", "w", encoding="utf-8") as f:
                        f.write(f"关键词: {st.session_state.get('current_keyword', '')}\n\n")
                        for ann in st.session_state.annotations:
                            f.write(f"{ann['type']} | {ann['text']} | {ann.get('timestamp','')}\n")
                    st.success("已导出 annotations.txt")

            with tab_new:
                latest = st.session_state.get('latest_new_annotations', [])
                if latest:
                    for ann in latest:
                        st.markdown(f"- **{ann['type']}** | {ann['text']}")
                else:
                    st.caption("暂无新增。")

            with tab_all:
                st.json(st.session_state.annotations)

if __name__ == "__main__":
    main()