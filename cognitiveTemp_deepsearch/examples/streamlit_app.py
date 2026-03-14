"""
Streamlit Web界面
为Deep Search Agent提供友好的Web界面
"""

import os
import sys
import streamlit as st
from datetime import datetime
import re
import html
from urllib.parse import urlparse

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import DeepSearchAgent, Config
from src.visualization import MetricsVisualizer, MetricsCalculator


def init_session_state():
    """初始化session state"""
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = None
    if 'api_configured' not in st.session_state:
        st.session_state.api_configured = False
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'progress_animation' not in st.session_state:
        st.session_state.progress_animation = 0
    if 'motion_intensity' not in st.session_state:
        st.session_state.motion_intensity = "Medium"
    if 'language' not in st.session_state:
        st.session_state.language = "EN"  # 默认英文


def get_motion_settings(level: str) -> dict:
    presets = {
        "High": {
            "app_duration": "10s",
            "hero_duration": "6s",
            "report_duration": "10s",
            "app_mid": "26% 18%, 70% 28%, 48% 90%, 100% 55%",
            "app_q1": "20% 12%, 76% 14%, 30% 86%, 40% 60%",
            "app_q3": "12% 24%, 88% 30%, 70% 78%, 64% 44%",
            "report_mid": "28% 20%, 68% 26%, 48% 92%, 100% 56%",
            "report_q1": "22% 14%, 74% 14%, 30% 86%, 38% 62%",
            "report_q3": "14% 26%, 86% 32%, 70% 78%, 66% 42%",
        },
        "Medium": {
            "app_duration": "14s",
            "hero_duration": "9s",
            "report_duration": "14s",
            "app_mid": "24% 14%, 70% 26%, 48% 90%, 100% 55%",
            "app_q1": "18% 10%, 76% 14%, 30% 85%, 40% 60%",
            "app_q3": "10% 20%, 88% 28%, 68% 78%, 60% 45%",
            "report_mid": "26% 18%, 68% 24%, 46% 92%, 100% 55%",
            "report_q1": "20% 12%, 76% 14%, 30% 86%, 38% 62%",
            "report_q3": "12% 22%, 86% 30%, 68% 78%, 64% 44%",
        },
        "Low": {
            "app_duration": "24s",
            "hero_duration": "14s",
            "report_duration": "26s",
            "app_mid": "12% 8%, 86% 16%, 44% 90%, 100% 52%",
            "app_q1": "8% 6%, 92% 8%, 44% 92%, 20% 52%",
            "app_q3": "6% 10%, 90% 14%, 56% 86%, 66% 48%",
            "report_mid": "12% 8%, 86% 16%, 44% 90%, 100% 52%",
            "report_q1": "8% 6%, 92% 8%, 44% 92%, 20% 52%",
            "report_q3": "6% 10%, 90% 14%, 56% 86%, 66% 48%",
        },
    }
    return presets.get(level, presets["Medium"])


def extract_keywords(query: str, paragraphs) -> list[str]:
    keywords = set()
    if query:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}|[\u4e00-\u9fff]{2,}", query):
            keywords.add(token.strip())

    for paragraph in paragraphs:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{4,}|[\u4e00-\u9fff]{2,}", paragraph.title):
            keywords.add(token.strip())

    return sorted(keywords, key=len, reverse=True)[:20]


def get_text(key: str) -> str:
    """根据当前语言获取文本"""
    texts = {
        "EN": {
            # Page config
            "page_title": "Deep Search Agent",
            "page_icon": "🔍",
            
            # Steps
            "step1_title": "Choose your LLM provider",
            "step2_title": "Configure API keys",
            "step3_title": "Run deep research",
            
            # LLM Provider
            "llm_provider_description": "Select the Large Language Model (LLM) provider you want to use.",
            "deepseek_option": "🚀 DeepSeek (Recommended)",
            "deepseek_desc": "Cost-effective, high performance",
            "openai_option": "🤖 OpenAI",
            "openai_desc": "Industry standard, powerful",
            
            # API Configuration
            "api_config_description": "Please enter your API keys. Your keys are only stored in the current session and will not be saved.",
            "api_key_label": "API Key",
            "tavily_key_label": "Tavily API Key",
            "model_select_label": "Select model",
            "start_button": "✨ Start using",
            "api_error": "Please enter all required API keys",
            
            # Sidebar
            "sidebar_advanced": "⚙️ Advanced settings",
            "sidebar_animation": "Animation intensity",
            "sidebar_animation_help": "Low: reading mode, High: presentation mode",
            "sidebar_current_mode": "Current mode",
            "sidebar_current_session": "Current session",
            "sidebar_llm_provider": "LLM Provider",
            "sidebar_model": "Model",
            "sidebar_search_engine": "Search Engine",
            "sidebar_edit_api": "🔄 Edit API configuration",
            
            # Search Parameters
            "search_params_title": "📊 Search parameters",
            "reflection_rounds": "Reflection rounds",
            "reflection_help": "How many reflection iterations the model runs",
            "results_per_search": "Results per search",
            "results_help": "How many web results are returned per query",
            "max_content_length": "Max content length",
            "content_help": "Maximum length of processed content",
            
            # Search Enhancement
            "search_enhancement_title": "🔍 Search enhancement",
            "search_strategy": "Search strategy",
            "strategy_help": "fast: Quick results | balanced: Default | deep: Comprehensive search",
            "enable_query_expansion": "Enable query expansion",
            "expansion_help": "Automatically expand queries to capture more relevant results",
            "expansion_queries": "Expansion queries",
            "expansion_count_help": "Number of query variations to search",
            "enable_semantic": "Enable semantic search",
            "semantic_help": "Use semantic understanding for better relevance",
            "enable_multilang": "Enable multi-language",
            "multilang_help": "Search in multiple languages",
            
            # Content Filtering
            "content_filter_title": "🎯 Content filtering",
            "min_quality": "Min content quality",
            "quality_help": "Filter out low-quality content",
            "dedup_threshold": "Deduplication threshold",
            "dedup_help": "Remove similar results (higher = more aggressive)",
            "filter_by_date": "Filter by date",
            "date_help": "Only return recent results",
            "days_back": "Days back",
            "days_help": "Search results from the last N days",
            
            # Priority & Verification
            "priority_title": "⭐ Priority & verification",
            "search_priority": "Search priority",
            "priority_help": "relevance: Most relevant first | recency: Latest first | authority: Most trusted first",
            "enable_fact_check": "Enable fact-checking",
            "fact_help": "Verify claims against reliable sources",
            "enable_source_verify": "Enable source verification",
            "source_help": "Verify source credibility",
            "enable_iterative": "Enable iterative refinement",
            "iterative_help": "Iteratively improve search results based on feedback",
            "refinement_depth": "Refinement depth",
            "depth_help": "How many refinement iterations to perform",
            
            # Main Interface
            "research_query_title": "📝 Research query",
            "query_placeholder": "Example: AI development trends in 2026",
            "query_label": "Enter your research question",
            "example_prompts": "💡 Optional: Example prompts",
            "select_example": "Select a sample prompt",
            "status_title": "📊 Status",
            "total_sections": "Total sections",
            "completed": "Completed",
            "no_research": "No research started yet",
            "start_research": "🚀 Start research",
            "query_error": "❌ Please enter a research question",
            
            # Progress
            "progress_title": "📈 Research progress",
            "generating_structure": "🏗️ Generating research structure...",
            "searching": "🔍 Searching",
            "reflecting": "💭 Reflecting",
            "generating_report": "📄 Generating final report...",
            "research_complete": "✅ Research complete!",
            "research_failed": "❌ Research failed",
            
            # Results
            "final_report": "📊 Final report",
            "download_report": "⬇️ Download HTML report",
            "view_state": "🔍 View research state (debug)",
            
            # Report sections
            "report_title": "Deep Search Academic Report",
            "structured_overview": "Structured Overview",
            "references": "📚 References",
            "open_source": "Open source →",
            
            # Examples
            "example1": "AI development trends in 2026",
            "example2": "Applications of deep learning in healthcare",
            "example3": "Latest progress of blockchain technology",
            "example4": "Sustainable energy technology landscape",
            "example5": "Current state of quantum computing",
            
            # Results display
            "research_success": "✅ Research finished successfully!",
            "results_title": "📊 Results",
            "tab_narrative": "📄 Narrative",
            "tab_details": "📋 Details",
            "tab_html": "🌐 Styled HTML",
            "tab_download": "⬇️ Download",
            "structured_overview": "Structured overview",
            "segmented_narrative": "Segmented narrative",
            "full_output": "Full output",
            "section_details": "Section details",
            "search_count": "Search count",
            "reflection_rounds": "Reflection rounds",
            "planned_scope": "Planned scope",
            "final_section_text": "Final section text",
            "search_history": "🔍 Search history",
            "search": "Search",
            "title": "Title",
            "url": "URL",
            "content": "Content",
            "section": "Section",
            "searches": "Searches",
            "reflections": "Reflections",
            "relevance_score": "Relevance score",
            "content_preview": "Content preview",
            "download_html_report": "⬇️ Download HTML report",
            "view_debug": "🔍 View research state (debug)",
        },
        "ZH": {
            # Page config
            "page_title": "深度搜索代理",
            "page_icon": "🔍",
            
            # Steps
            "step1_title": "选择您的 LLM 提供商",
            "step2_title": "配置 API 密钥",
            "step3_title": "运行深度研究",
            
            # LLM Provider
            "llm_provider_description": "选择您想要使用的大语言模型（LLM）提供商。",
            "deepseek_option": "🚀 DeepSeek（推荐）",
            "deepseek_desc": "性价比高，性能优异",
            "openai_option": "🤖 OpenAI",
            "openai_desc": "行业标准，功能强大",
            
            # API Configuration
            "api_config_description": "请输入您的 API 密钥。您的密钥仅存储在当前会话中，不会被保存。",
            "api_key_label": "API 密钥",
            "tavily_key_label": "Tavily API 密钥",
            "model_select_label": "选择模型",
            "start_button": "✨ 开始使用",
            "api_error": "请输入所有必需的 API 密钥",
            
            # Sidebar
            "sidebar_advanced": "⚙️ 高级设置",
            "sidebar_animation": "动画强度",
            "sidebar_animation_help": "低：阅读模式，高：演示模式",
            "sidebar_current_mode": "当前模式",
            "sidebar_current_session": "当前会话",
            "sidebar_llm_provider": "LLM 提供商",
            "sidebar_model": "模型",
            "sidebar_search_engine": "搜索引擎",
            "sidebar_edit_api": "🔄 编辑 API 配置",
            
            # Search Parameters
            "search_params_title": "📊 搜索参数",
            "reflection_rounds": "反思轮次",
            "reflection_help": "模型运行多少次反思迭代",
            "results_per_search": "每次搜索结果数",
            "results_help": "每个查询返回多少网络结果",
            "max_content_length": "最大内容长度",
            "content_help": "处理内容的最大长度",
            
            # Search Enhancement
            "search_enhancement_title": "🔍 搜索增强",
            "search_strategy": "搜索策略",
            "strategy_help": "fast：快速结果 | balanced：默认 | deep：全面搜索",
            "enable_query_expansion": "启用查询扩展",
            "expansion_help": "自动扩展查询以获取更相关的结果",
            "expansion_queries": "扩展查询数",
            "expansion_count_help": "要搜索的查询变体数量",
            "enable_semantic": "启用语义搜索",
            "semantic_help": "使用语义理解获得更好的相关性",
            "enable_multilang": "启用多语言",
            "multilang_help": "在多种语言中搜索",
            
            # Content Filtering
            "content_filter_title": "🎯 内容过滤",
            "min_quality": "最小内容质量",
            "quality_help": "过滤低质量内容",
            "dedup_threshold": "去重阈值",
            "dedup_help": "删除相似结果（越高越激进）",
            "filter_by_date": "按日期过滤",
            "date_help": "仅返回最近的结果",
            "days_back": "回溯天数",
            "days_help": "搜索最近 N 天的结果",
            
            # Priority & Verification
            "priority_title": "⭐ 优先级与验证",
            "search_priority": "搜索优先级",
            "priority_help": "relevance：最相关优先 | recency：最新优先 | authority：最可信优先",
            "enable_fact_check": "启用事实检验",
            "fact_help": "根据可靠来源验证声明",
            "enable_source_verify": "启用来源验证",
            "source_help": "验证来源可信度",
            "enable_iterative": "启用迭代优化",
            "iterative_help": "根据反馈迭代改进搜索结果",
            "refinement_depth": "优化深度",
            "depth_help": "执行多少次优化迭代",
            
            # Main Interface
            "research_query_title": "📝 研究查询",
            "query_placeholder": "示例：2026年AI发展趋势",
            "query_label": "输入您的研究问题",
            "example_prompts": "💡 示例提示",
            "select_example": "选择示例提示",
            "status_title": "📊 状态",
            "total_sections": "总章节数",
            "completed": "已完成",
            "no_research": "尚未开始研究",
            "start_research": "🚀 开始研究",
            "query_error": "❌ 请输入研究问题",
            
            # Progress
            "progress_title": "📈 研究进度",
            "generating_structure": "🏗️ 生成研究结构中...",
            "searching": "🔍 搜索中",
            "reflecting": "💭 反思中",
            "generating_report": "📄 生成最终报告中...",
            "research_complete": "✅ 研究完成！",
            "research_failed": "❌ 研究失败",
            
            # Results
            "final_report": "📊 最终报告",
            "download_report": "⬇️ 下载 HTML 报告",
            "view_state": "🔍 查看研究状态（调试）",
            
            # Report sections
            "report_title": "深度搜索学术报告",
            "structured_overview": "结构化概览",
            "references": "📚 参考资料",
            "open_source": "打开来源 →",
            
            # Examples
            "example1": "2026年AI发展趋势",
            "example2": "深度学习在医疗保健中的应用",
            "example3": "区块链技术最新进展",
            "example4": "可持续能源技术现状",
            "example5": "量子计算当前状态",
            
            # Results display
            "research_success": "✅ 研究成功完成！",
            "results_title": "📊 结果",
            "tab_narrative": "📄 叙述",
            "tab_details": "📋 详情",
            "tab_html": "🌐 样式化 HTML",
            "tab_download": "⬇️ 下载",
            "structured_overview": "结构化概览",
            "segmented_narrative": "分段叙述",
            "full_output": "完整输出",
            "section_details": "章节详情",
            "search_count": "搜索次数",
            "reflection_rounds": "反思轮次",
            "planned_scope": "计划范围",
            "final_section_text": "最终章节文本",
            "search_history": "🔍 搜索历史",
            "search": "搜索",
            "title": "标题",
            "url": "URL",
            "content": "内容",
            "section": "章节",
            "searches": "搜索",
            "reflections": "反思",
            "relevance_score": "相关度分数",
            "content_preview": "内容预览",
            "download_html_report": "⬇️ 下载 HTML 报告",
            "view_debug": "🔍 查看研究状态（调试）",
        }
    }
    
    lang = st.session_state.get('language', 'EN')
    return texts.get(lang, texts['EN']).get(key, key)


def highlight_keywords(text: str, keywords: list[str]) -> str:
    if not text:
        return ""
    safe_text = html.escape(text)
    for keyword in keywords:
        pattern = re.compile(re.escape(html.escape(keyword)), re.IGNORECASE)
        safe_text = pattern.sub(
            lambda m: f'<span class="kw-highlight"><strong>{m.group(0)}</strong></span>',
            safe_text,
        )
    return safe_text


def paragraphize(text: str, keywords: list[str]) -> str:
    chunks = [c.strip() for c in re.split(r"\n{2,}", text or "") if c.strip()]
    if not chunks:
        return "<p>No content available.</p>"
    return "\n".join(f"<p>{highlight_keywords(chunk, keywords)}</p>" for chunk in chunks)


def render_metrics_explanation_panel(agent: DeepSearchAgent):
    """在指标Tab中展示阈值与可解释说明。"""
    metrics = getattr(getattr(agent, "metrics_collector", None), "metrics", None)
    quality = getattr(metrics, "search_quality", None)
    if not quality:
        return

    threshold = float(
        getattr(
            quality,
            "relevance_threshold",
            MetricsCalculator.DEFAULT_RELEVANCE_THRESHOLD,
        )
    )
    p1 = float(quality.precision_at_1 or 0.0)
    p3 = float(quality.precision_at_3 or 0.0)
    p5 = float(quality.precision_at_5 or 0.0)
    p10 = float(quality.precision_at_10 or 0.0)
    bpref = float(quality.bpref or 0.0)
    mrr = float(quality.mrr or 0.0)

    first_rank = int(round(1 / mrr)) if mrr > 0 else None
    hit_top5 = int(round(p5 * 5))
    hit_top10 = int(round(p10 * 10))

    lang = st.session_state.get("language", "ZH")
    if lang == "EN":
        st.info(
            f"Metrics threshold synchronized to relevance ≥ {threshold:.2f}. "
            "P@K, MRR, MAP, and BPref all use the same threshold."
        )

        if p5 == 0 and p10 > 0:
            st.warning(
                "Interpretation: P@5 = 0 but P@10 > 0 is expected. "
                "It means relevant hits start after rank 5 (typically ranks 6-10)."
            )

        with st.expander("📘 Metric interpretation (threshold-aware)", expanded=False):
            st.markdown(
                f"""
                - **Threshold**: Relevant if relevance score $\geq {threshold:.2f}$.
                - **P@1 / P@3 / P@5 / P@10**: Relevant ratio in Top-$k$ results.
                - **Current Top-k hits**: Top-5 = **{hit_top5}/5**, Top-10 = **{hit_top10}/10**.
                - **MRR**: Reciprocal rank of the first relevant result. Estimated first relevant rank: **{first_rank if first_rank else 'N/A'}**.
                - **BPref**: Robust preference score under incomplete judgments, current value: **{bpref:.4f}**.
                """
            )
    else:
        st.info(
            f"指标阈值已同步为相关性 ≥ {threshold:.2f}；"
            "P@K、MRR、MAP、BPref 使用同一阈值。"
        )

        if p5 == 0 and p10 > 0:
            st.warning(
                "解释：P@5=0 但 P@10>0 是正常现象，表示相关结果在第5名之后才出现（通常在第6-10名）。"
            )

        with st.expander("📘 指标解释（含阈值）", expanded=False):
            st.markdown(
                f"""
                - **阈值定义**：相关性分数 $\geq {threshold:.2f}$ 记为“相关”。
                - **P@1 / P@3 / P@5 / P@10**：Top-$k$ 中相关结果占比。
                - **当前命中情况**：Top-5 命中 **{hit_top5}/5**，Top-10 命中 **{hit_top10}/10**。
                - **MRR**：首个相关结果倒数排名；当前估算首个相关排名约为 **{first_rank if first_rank else 'N/A'}**。
                - **BPref**：在不完全标注下更稳健的排序偏好指标，当前值 **{bpref:.4f}**。
                """
            )


def main():
    """主函数"""
    st.set_page_config(
        page_title="Deep Search Agent",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_session_state()
    motion = get_motion_settings(st.session_state.motion_intensity)
    
    # 自定义CSS美化界面和动态效果
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,600;1,700&family=Noto+Sans+SC:wght@300;400;500;700;900&family=Crimson+Pro:ital,wght@0,400;0,600;1,400;1,600&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        * {{
            font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            letter-spacing: -0.01em;
        }}

        body, .stApp {{
            background:
                radial-gradient(circle at 8% 12%, rgba(76, 110, 245, 0.18) 0%, transparent 28%),
                radial-gradient(circle at 88% 18%, rgba(16, 185, 129, 0.16) 0%, transparent 26%),
                radial-gradient(circle at 52% 86%, rgba(249, 115, 22, 0.12) 0%, transparent 24%),
                linear-gradient(145deg, #f4f7fb 0%, #eef2f8 45%, #e8eef6 100%);
            background-size: 240% 240%, 220% 220%, 210% 210%, 300% 300%;
            animation: appGradientFlow {motion['app_duration']} ease-in-out infinite !important;
        }}

        @keyframes appGradientFlow {{
            0% {{
                background-position: 0% 0%, 100% 0%, 50% 100%, 0% 50%;
            }}
            25% {{
                background-position: {motion['app_q1']};
            }}
            50% {{
                background-position: {motion['app_mid']};
            }}
            75% {{
                background-position: {motion['app_q3']};
            }}
            100% {{
                background-position: 0% 0%, 100% 0%, 50% 100%, 0% 50%;
            }}
        }}
        
        /* 语言切换按钮 */
        .language-switcher {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50px;
            padding: 8px 16px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            display: flex;
            gap: 8px;
            align-items: center;
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
        }}
        
        .language-switcher:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }}
        
        .lang-btn {{
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 25px;
            padding: 6px 14px;
            color: white;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            letter-spacing: 0.02em;
        }}
        
        .lang-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        
        .lang-btn.active {{
            background: white;
            color: #667eea;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }}
        
        /* 主标题样式 */
        .main-header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            background-size: 220% 220%;
            padding: 3rem 2rem;
            border-radius: 15px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            animation: slideDown 0.6s ease-out, heroGradientFlow {motion['hero_duration']} ease-in-out infinite;
        }}

        @keyframes heroGradientFlow {{{{
            0% {{{{ background-position: 0% 50%; }}}}
            50% {{{{ background-position: 100% 50%; }}}}
            100% {{{{ background-position: 0% 50%; }}}}
        }}}}
        
        .main-header h1 {{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-size: 2.8rem;
            font-weight: 800;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            letter-spacing: -0.02em;
            line-height: 1.2;
        }}
        
        .main-header p {{
            font-family: 'Crimson Pro', 'Noto Sans SC', serif;
            font-size: 1.2rem;
            margin-top: 0.8rem;
            opacity: 0.95;
            font-weight: 400;
            font-style: italic;
            letter-spacing: 0.01em;
        }}
        
        /* 动画 */
        @keyframes slideDown {{{{
            from {{{{
                opacity: 0;
                transform: translateY(-20px);
            }}}}
            to {{{{
                opacity: 1;
                transform: translateY(0);
            }}}}
        }}}}
        
        @keyframes fadeIn {{{{
            from {{{{ opacity: 0; }}}}
            to {{{{ opacity: 1; }}}}
        }}}}
        
        @keyframes pulse {{{{
            0%, 100% {{{{ opacity: 1; }}}}
            50% {{{{ opacity: 0.7; }}}}
        }}}}
        
        @keyframes slideInLeft {{{{
            from {{{{
                opacity: 0;
                transform: translateX(-30px);
            }}}}
            to {{{{
                opacity: 1;
                transform: translateX(0);
            }}}}
        }}}}
        
        /* LLM选择器卡片 */
        .llm-card {{{{
            padding: 2rem;
            border-radius: 12px;
            border: 2px solid #e0e0e0;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            animation: fadeIn 0.5s ease-in;
        }}}}
        
        .llm-card h3 {{{{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-weight: 700;
            font-size: 1.4rem;
            margin-bottom: 0.5rem;
        }}}}
        
        .llm-card p {{{{
            font-family: 'Crimson Pro', 'Noto Sans SC', serif;
            font-style: italic;
            font-size: 0.95rem;
            color: #666;
        }}}}
        
        .llm-card:hover {{{{
            border-color: #667eea;
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.2);
            transform: translateY(-5px);
        }}}}
        
        .llm-card.selected {{{{
            border-color: #667eea;
            background: linear-gradient(135deg, #667eea15, #764ba215);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.25);
            transform: scale(1.02);
        }}}}
        
        /* API配置区 */
        .api-config-section {{{{
            background: linear-gradient(135deg, #f5f7ff 0%, #f0f4ff 100%);
            padding: 2rem;
            border-radius: 12px;
            margin: 1.5rem 0;
            border-left: 4px solid #667eea;
            animation: slideInLeft 0.5s ease-out;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
        }}}}
        
        .api-config-section h3 {{{{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-weight: 700;
            font-style: italic;
            color: #667eea;
            margin-bottom: 1rem;
        }}}}
        
        /* 成功消息 */
        .success-message {{{{
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border: 2px solid #28a745;
            color: #155724;
            padding: 1.2rem;
            border-radius: 10px;
            margin: 1rem 0;
            animation: slideInLeft 0.5s ease-out;
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.15);
            font-weight: 500;
        }}}}
        
        .success-message strong {{{{
            font-weight: 700;
            font-style: italic;
        }}}}
        
        /* 按钮样式 */
        .stButton > button {{{{
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            padding: 0.8rem 1.5rem;
            border: none;
            font-size: 1rem;
        }}}}
        
        .stButton > button:hover {{{{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
        }}}}
        
        /* 输入框样式 */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {{{{
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            font-size: 1rem;
            transition: all 0.3s ease;
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 400;
            line-height: 1.6;
        }}}}
        
        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder {{{{
            font-family: 'Crimson Pro', 'Noto Sans SC', serif;
            font-style: italic;
            color: #999;
            font-weight: 400;
        }}}}
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{{{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}}}
        
        /* 进度条美化 */
        .stProgress > div > div > div {{{{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }}}}
        
        /* Metric卡片 */
        .metric-card {{{{
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            border: 2px solid #e0e0e0;
            text-align: center;
            animation: fadeIn 0.5s ease-in;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}}}
        
        /* 标签页美化 */
        .stTabs > div > div > button {{{{
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            transition: all 0.3s ease;
        }}}}
        
        /* 侧边栏 */
        .sidebar-content {{{{
            background: linear-gradient(180deg, #f5f7ff 0%, #f0f4ff 100%);
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
        }}}}
        
        /* 侧边栏标题美化 */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {{{{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 1rem;
        }}}}
        
        [data-testid="stSidebar"] h4 {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 600;
            font-style: italic;
            color: #555;
            margin-top: 1.5rem;
            margin-bottom: 0.8rem;
        }}}}
        
        /* 侧边栏文本 */
        [data-testid="stSidebar"] p {{{{
            font-size: 0.95rem;
            line-height: 1.6;
        }}}}
        
        [data-testid="stSidebar"] label {{{{
            font-weight: 500;
            font-size: 0.9rem;
        }}}}
        
        /* 分隔线 */
        .separator {{{{
            height: 2px;
            background: linear-gradient(90deg, transparent, #667eea, transparent);
            margin: 1.5rem 0;
        }}}}

        .kw-highlight {{{{
            background: linear-gradient(120deg, #ffd89b 0%, #19547b 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            padding: 0.05rem 0.3rem;
            border-radius: 4px;
            position: relative;
        }}}}
        
        .kw-highlight::before {{{{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 216, 155, 0.2);
            border-radius: 4px;
            z-index: -1;
        }}}}
        
        /* 标题样式增强 */
        h1, h2, h3 {{{{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}}}
        
        h4, h5, h6 {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 600;
            letter-spacing: -0.01em;
        }}}}
        
        /* 段落文字优化 */
        p {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-size: 1rem;
            line-height: 1.7;
            letter-spacing: -0.005em;
        }}}}
        
        /* 强调文字斜体 */
        em, .italic-text {{{{
            font-family: 'Crimson Pro', 'Noto Sans SC', serif;
            font-style: italic;
            font-weight: 400;
        }}}}
        
        /* 代码和技术文字 */
        code, pre, .monospace {{{{
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 0.9em;
            letter-spacing: 0;
        }}}}
        
        /* 标签和徽章 */
        .stTabs [data-baseweb="tab"] {{{{
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.02em;
        }}}}
        
        /* 侧边栏标题 */
        .sidebar .sidebar-content h1,
        .sidebar .sidebar-content h2,
        .sidebar .sidebar-content h3 {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 700;
            letter-spacing: -0.01em;
        }}}}
        
        /* 按钮文字 */
        button {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 600;
            letter-spacing: 0.01em;
        }}}}
        
        /* 链接样式 */
        a {{{{
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s ease;
        }}}}
        
        a:hover {{{{
            font-weight: 600;
        }}}}
        
        /* 引用文字样式 */
        blockquote {{{{
            font-family: 'Crimson Pro', 'Noto Sans SC', serif;
            font-style: italic;
            font-size: 1.1rem;
            border-left: 4px solid #667eea;
            padding-left: 1.5rem;
            margin: 1.5rem 0;
            color: #555;
            font-weight: 400;
        }}}}
        
        /* 数字和统计信息 */
        .stat-number {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 800;
            font-size: 2rem;
            color: #667eea;
            letter-spacing: -0.03em;
        }}}}
        
        /* 小标签 */
        .tag, .badge {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}}}
        
        /* 进度和状态文字 */
        .progress-text {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 500;
            font-style: italic;
            color: #667eea;
        }}}}
        
        /* 表格标题 */
        table th {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}}}
        
        /* 列表项 */
        li {{{{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            line-height: 1.8;
        }}}}
        
        /* 突出显示的重要文字 */
        .highlight-text {{{{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-weight: 700;
            font-style: italic;
            background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}}}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(
        f"""
        <style>
        body, .stApp {{
            animation-duration: {motion['app_duration']} !important;
        }}

        .main-header {{
            animation-duration: 0.6s, {motion['hero_duration']} !important;
        }}

        @keyframes appGradientFlow {{
            0% {{
                background-position: 0% 0%, 100% 0%, 50% 100%, 0% 50%;
            }}
            25% {{
                background-position: {motion['app_q1']};
            }}
            50% {{
                background-position: {motion['app_mid']};
            }}
            75% {{
                background-position: {motion['app_q3']};
            }}
            100% {{
                background-position: 0% 0%, 100% 0%, 50% 100%, 0% 50%;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # 语言切换按钮 (使用容器实现点击切换)
    lang_container = st.container()
    with lang_container:
        # 在页面右上角显示语言切换按钮
        cols = st.columns([5, 1])
        with cols[1]:
            current_lang = st.session_state.language
            if st.button("🌐 EN" if current_lang == "ZH" else "🌐 中文", key="lang_switch"):
                st.session_state.language = "EN" if current_lang == "ZH" else "ZH"
                st.rerun()
    
    # 标题区域
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div class="main-header">
                <h1>🔍 {get_text('page_title')}</h1>
                <p>Framework-free Deep Search Assistant</p>
            </div>
        """, unsafe_allow_html=True)
    
    # 检查是否已选择 LLM 提供商
    if st.session_state.llm_provider is None:
        show_llm_selector()
    else:
        show_api_configuration()
        show_main_interface()


def show_llm_selector():
    """显示LLM提供商选择界面"""
    st.markdown(f"## {get_text('step1_title')}")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("")
    
    with col2:
        st.markdown(f"""
        #### {get_text('llm_provider_description')}
        """)
    
    with col3:
        st.markdown("")
    
    # 选择按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button(get_text('openai_option'), use_container_width=True, key="select_openai"):
            st.session_state.llm_provider = "openai"
            st.rerun()
    
    with col2:
        st.markdown("")
    
    with col3:
        if st.button(get_text('deepseek_option'), use_container_width=True, key="select_deepseek"):
            st.session_state.llm_provider = "deepseek"
            st.rerun()
    
    st.markdown("---")
    if st.session_state.language == "EN":
        st.info("""
        📌 **Quick help:**
        - **OpenAI**: supports `gpt-4o-mini` and `gpt-4o`.
        - **DeepSeek**: cost-efficient and strong reasoning model.
        """)
    else:
        st.info("""
        📌 **快速帮助:**
        - **OpenAI**: 支持 `gpt-4o-mini` 和 `gpt-4o`。
        - **DeepSeek**: 性价比高且推理能力强的模型。
        """)


def show_api_configuration():
    """显示API配置界面"""
    if not st.session_state.api_configured:
        st.markdown(f"## {get_text('step2_title')}")
        st.markdown("---")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 显示已选择的提供商
            provider_display = get_text('openai_option') if st.session_state.llm_provider == "openai" else get_text('deepseek_option')
            if st.session_state.language == "EN":
                st.markdown(f"### Current provider: {provider_display}")
            else:
                st.markdown(f"### 当前提供商: {provider_display}")
            
            if st.button("🔄 " + ("Re-select provider" if st.session_state.language == "EN" else "重新选择提供商")):
                st.session_state.llm_provider = None
                st.session_state.api_configured = False
                st.rerun()
        
        # API配置区域
        # Tavily API Key（通用）
        tavily_key = st.text_input(
            f"🔑 {get_text('tavily_key_label')}",
            type="password",
            placeholder="Enter Tavily API key for web search" if st.session_state.language == "EN" else "输入 Tavily API 密钥进行网络搜索",
            key="tavily_key_input"
        )
        
        # 根据选择的提供商显示相应的API配置
        if st.session_state.llm_provider == "openai":
            default_openai_key = getattr(default_config, 'OPENAI_API_KEY', '')
            
            openai_key_input = st.text_input(
                f"🔑 {get_text('api_key_label')} (OpenAI)",
                type="password",
                placeholder="Enter OpenAI API key (留空使用默认)" if st.session_state.language == "EN" else "输入 OpenAI API 密钥(留空使用config.py中的默认密钥)",
                key="openai_key_input",
                help="留空将使用 config.py 中的默认密钥" if st.session_state.language == "ZH" else "Leave empty to use default key from config.py"
            )
            model_options = ["gpt-4o-mini", "gpt-4o"]
            model_name = st.selectbox(
                f"🤖 {get_text('model_select_label')}",
                model_options,
                key="openai_model_select"
            )
            llm_key = openai_key_input.strip() if openai_key_input.strip() else default_openai_key
        else:  # deepseek
            # 从config.py获取默认密钥
            import config as default_config
            default_deepseek_key = getattr(default_config, 'DEEPSEEK_API_KEY', '')
            
            deepseek_key = st.text_input(
                f"🔑 {get_text('api_key_label')} (DeepSeek)",
                type="password",
                placeholder="Enter DeepSeek API key (留空使用默认)" if st.session_state.language == "EN" else "输入 DeepSeek API 密钥（留空使用config.py中的默认密钥）",
                key="deepseek_key_input",
                help="留空将使用 config.py 中的默认密钥" if st.session_state.language == "ZH" else "Leave empty to use default key from config.py"
            )
            model_options = ["deepseek-chat"]
            model_name = st.selectbox(
                f"🤖 {get_text('model_select_label')}",
                model_options,
                key="deepseek_model_select"
            )
            # 如果用户未输入密钥，使用默认密钥
            llm_key = deepseek_key.strip() if deepseek_key.strip() else default_deepseek_key
        
        # 验证和保存配置
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            button_text = "✅ " + ("Validate and continue" if st.session_state.language == "EN" else "验证并继续")
            if st.button(button_text, use_container_width=True, type="primary"):
                # 检查 Tavily 密钥
                if not tavily_key:
                    error_msg = "❌ Tavily API Key is required (not found in config.py)" if st.session_state.language == "EN" else "❌ 需要 Tavily API 密钥(config.py 中未找到默认密钥)"
                    st.error(error_msg)
                    return
                
                # 检查 LLM 密钥
                if not llm_key:
                    provider_name = "OpenAI" if st.session_state.llm_provider == "openai" else "DeepSeek"
                    error_msg = f"❌ {provider_name} API Key is required (not found in config.py)" if st.session_state.language == "EN" else f"❌ 需要 {provider_name} API 密钥(config.py 中未找到默认密钥)"
                    st.error(error_msg)
                    return
                
                # 保存到session state
                st.session_state.tavily_key = tavily_key
                st.session_state.llm_key = llm_key
                st.session_state.model_name = model_name
                st.session_state.api_configured = True
                
                success_msg = "✅ API configuration saved." if st.session_state.language == "EN" else "✅ API 配置已保存。"
                st.markdown(f'<div class="success-message">{success_msg}</div>', unsafe_allow_html=True)
                st.rerun()


def show_main_interface():
    """显示主界面"""
    if not st.session_state.api_configured:
        return
    
    st.markdown(f"## {get_text('step3_title')}")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.header(get_text('sidebar_advanced'))
        st.divider()

        selected_motion = st.select_slider(
            get_text('sidebar_animation'),
            options=["Low", "Medium", "High"],
            value=st.session_state.motion_intensity,
            help=get_text('sidebar_animation_help'),
        )
        if selected_motion != st.session_state.motion_intensity:
            st.session_state.motion_intensity = selected_motion
            st.rerun()

        st.caption(
            f"{get_text('sidebar_current_mode')}: **{st.session_state.motion_intensity}**"
        )
        st.divider()
        
        # 用户信息
        provider_display = '🤖 OpenAI' if st.session_state.llm_provider == 'openai' else '🚀 DeepSeek'
        st.markdown(f"""
        ### {get_text('sidebar_current_session')}
        - **{get_text('sidebar_llm_provider')}**: {provider_display}
        - **{get_text('sidebar_model')}**: {st.session_state.model_name}
        - **{get_text('sidebar_search_engine')}**: Tavily
        """)
        st.divider()
        
        if st.button(get_text('sidebar_edit_api')):
            st.session_state.llm_provider = None
            st.session_state.api_configured = False
            st.rerun()
        
        st.divider()
        
        # 高级配置
        st.subheader(get_text('search_params_title'))
        max_reflections = st.slider(get_text('reflection_rounds'), 1, 5, 2, help=get_text('reflection_help'))
        max_search_results = st.slider(get_text('results_per_search'), 1, 10, 5, help=get_text('results_help'))
        max_content_length = st.number_input(get_text('max_content_length'), 1000, 50000, 20000, help=get_text('content_help'))
        
        # 搜索增强配置
        st.divider()
        st.subheader(get_text('search_enhancement_title'))
        
        search_strategy = st.selectbox(
            get_text('search_strategy'),
            options=["fast", "balanced", "deep"],
            help=get_text('strategy_help')
        )
        
        enable_search_expansion = st.checkbox(
            get_text('enable_query_expansion'),
            value=True,
            help=get_text('expansion_help')
        )
        
        if enable_search_expansion:
            search_expansion_count = st.slider(
                get_text('expansion_queries'),
                1, 5, 3,
                help=get_text('expansion_count_help')
            )
        else:
            search_expansion_count = 0
        
        enable_semantic_search = st.checkbox(
            get_text('enable_semantic'),
            value=True,
            help=get_text('semantic_help')
        )
        
        enable_multi_language = st.checkbox(
            get_text('enable_multilang'),
            value=True,
            help=get_text('multilang_help')
        )
        
        # 内容过滤
        st.divider()
        st.subheader(get_text('content_filter_title'))
        
        min_quality_score = st.slider(
            get_text('min_quality'),
            0.0, 1.0, 0.3,
            step=0.1,
            help=get_text('quality_help')
        )
        
        dedup_threshold = st.slider(
            get_text('dedup_threshold'),
            0.0, 1.0, 0.7,
            step=0.05,
            help=get_text('dedup_help')
        )
        
        filter_by_date = st.checkbox(
            get_text('filter_by_date'),
            value=True,
            help=get_text('date_help')
        )
        
        if filter_by_date:
            days_back = st.slider(
                get_text('days_back'),
                1, 365, 90,
                help=get_text('days_help')
            )
        else:
            days_back = 365
        
        # 优先级和验证
        st.divider()
        st.subheader(get_text('priority_title'))
        
        search_priority = st.selectbox(
            get_text('search_priority'),
            options=["relevance", "recency", "authority"],
            help=get_text('priority_help')
        )
        
        enable_fact_checking = st.checkbox(
            get_text('enable_fact_check'),
            value=True,
            help=get_text('fact_help')
        )
        
        enable_source_verification = st.checkbox(
            get_text('enable_source_verify'),
            value=True,
            help=get_text('source_help')
        )
        
        enable_iterative_refinement = st.checkbox(
            get_text('enable_iterative'),
            value=True,
            help=get_text('iterative_help')
        )
        
        if enable_iterative_refinement:
            refinement_depth = st.slider(
                get_text('refinement_depth'),
                1, 3, 2,
                help=get_text('depth_help')
            )
        else:
            refinement_depth = 1
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(get_text('research_query_title'))
        query = st.text_area(
            get_text('query_label'),
            placeholder=get_text('query_placeholder'),
            height=100
        )
        
        # 预设查询示例
        st.subheader(get_text('example_prompts'))
        example_queries = [
            get_text('example1'),
            get_text('example2'),
            get_text('example3'),
            get_text('example4'),
            get_text('example5')
        ]
        
        custom_label = "Custom" if st.session_state.language == "EN" else "自定义"
        selected_example = st.selectbox(get_text('select_example'), [custom_label] + example_queries)
        if selected_example != custom_label:
            query = selected_example
    
    with col2:
        st.header(get_text('status_title'))
        if 'agent' in st.session_state and hasattr(st.session_state.agent, 'state'):
            progress = st.session_state.agent.get_progress_summary()
            st.metric(get_text('total_sections'), progress['total_paragraphs'])
            st.metric(get_text('completed'), progress['completed_paragraphs'])
            st.progress(progress['progress_percentage'] / 100)
        else:
            st.info(get_text('no_research'))
    
    # 执行按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        start_research = st.button(get_text('start_research'), type="primary", use_container_width=True)
    
    # 验证配置
    if start_research:
        if not query.strip():
            st.error(get_text('query_error'))
            return
        
        # 保存查询内容到session state用于后续生成报告
        st.session_state.last_query = query
        
        # 创建配置
        if st.session_state.llm_provider == "deepseek":
            config = Config(
                deepseek_api_key=st.session_state.llm_key,
                tavily_api_key=st.session_state.tavily_key,
                default_llm_provider="deepseek",
                deepseek_model=st.session_state.model_name,
                max_reflections=max_reflections,
                max_search_results=max_search_results,
                max_content_length=max_content_length,
                search_strategy=search_strategy,
                enable_search_expansion=enable_search_expansion,
                search_query_expansion_count=search_expansion_count,
                enable_semantic_search=enable_semantic_search,
                enable_multi_language_search=enable_multi_language,
                min_content_quality_score=min_quality_score,
                dedup_similarity_threshold=dedup_threshold,
                filter_by_date=filter_by_date,
                days_back=days_back,
                search_priority_mode=search_priority,
                enable_fact_checking=enable_fact_checking,
                enable_source_verification=enable_source_verification,
                enable_iterative_refinement=enable_iterative_refinement,
                refinement_depth=refinement_depth,
                output_dir="streamlit_reports"
            )
        else:  # openai
            config = Config(
                openai_api_key=st.session_state.llm_key,
                tavily_api_key=st.session_state.tavily_key,
                default_llm_provider="openai",
                openai_model=st.session_state.model_name,
                max_reflections=max_reflections,
                max_search_results=max_search_results,
                max_content_length=max_content_length,
                search_strategy=search_strategy,
                enable_search_expansion=enable_search_expansion,
                search_query_expansion_count=search_expansion_count,
                enable_semantic_search=enable_semantic_search,
                enable_multi_language_search=enable_multi_language,
                min_content_quality_score=min_quality_score,
                dedup_similarity_threshold=dedup_threshold,
                filter_by_date=filter_by_date,
                days_back=days_back,
                search_priority_mode=search_priority,
                enable_fact_checking=enable_fact_checking,
                enable_source_verification=enable_source_verification,
                enable_iterative_refinement=enable_iterative_refinement,
                refinement_depth=refinement_depth,
                output_dir="streamlit_reports"
            )
        
        # 执行研究
        execute_research(query, config)


def generate_html_report(agent: DeepSearchAgent, final_report: str, query: str):
    """Generate English HTML report with sections, table, keyword highlighting, quality metrics, and rich colors."""

    all_searches = []
    for paragraph in agent.state.paragraphs:
        all_searches.extend(paragraph.research.search_history)

    keywords = extract_keywords(query, agent.state.paragraphs)
    motion = get_motion_settings(st.session_state.get("motion_intensity", "Medium"))
    para_count = len(agent.state.paragraphs)
    search_count = len(all_searches)
    reflection_count = sum(p.research.reflection_iteration for p in agent.state.paragraphs)
    
    # 收集所有质量指标
    all_quality_metrics = []
    for search in all_searches:
        if search.quality_metrics:
            all_quality_metrics.append(search.quality_metrics)
    
    # 计算平均质量指标
    avg_metrics = None
    if all_quality_metrics:
        avg_metrics = {
            'ndcg': sum(m.get('ndcg', 0) for m in all_quality_metrics) / len(all_quality_metrics),
            'mrr': sum(m.get('mrr', 0) for m in all_quality_metrics) / len(all_quality_metrics),
            'precision_at_k': {},
            'relevance_score': sum(m.get('relevance_score', 0) for m in all_quality_metrics) / len(all_quality_metrics),
            'total_searches': len(all_quality_metrics)
        }
        # 计算平均 Precision@K
        for k in [1, 3, 5, 10]:
            k_values = [m.get('precision_at_k', {}).get(k, 0) for m in all_quality_metrics if m.get('precision_at_k')]
            if k_values:
                avg_metrics['precision_at_k'][k] = sum(k_values) / len(k_values)

    table_rows = []
    section_blocks = []
    for index, paragraph in enumerate(agent.state.paragraphs, start=1):
        summary_text = paragraph.research.latest_summary or paragraph.content
        table_rows.append(
            f"<tr><td>{index}</td><td>{highlight_keywords(paragraph.title, keywords)}</td><td>{paragraph.research.get_search_count()}</td><td>{paragraph.research.reflection_iteration}</td></tr>"
        )
        section_blocks.append(
            f'''<article class="report-section-block">
                <h3>Section {index}: {highlight_keywords(paragraph.title, keywords)}</h3>
                <div class="section-content">{paragraphize(summary_text, keywords)}</div>
            </article>'''
        )

    table_html = f'''<section class="summary-table-wrap">
        <h2>Structured Overview</h2>
        <table class="summary-table">
            <thead><tr><th>#</th><th>Section</th><th>Searches</th><th>Reflections</th></tr></thead>
            <tbody>{''.join(table_rows) if table_rows else '<tr><td colspan="4">No sections available</td></tr>'}</tbody>
        </table>
    </section>'''
    
    # 添加质量指标展示 - 扩展显示所有指标
    quality_metrics_html = ""
    if avg_metrics:
        # 计算所有Precision@K值
        p_at_1 = avg_metrics['precision_at_k'].get(1, 0)
        p_at_3 = avg_metrics['precision_at_k'].get(3, 0)
        p_at_5 = avg_metrics['precision_at_k'].get(5, 0)
        p_at_10 = avg_metrics['precision_at_k'].get(10, 0)
        
        quality_metrics_html = f'''<section class="quality-metrics-section">
        <h2>📊 Search Quality Metrics</h2>
        <p class="metrics-intro">Academic-standard evaluation of search result quality based on {avg_metrics['total_searches']} search operations</p>
        
        <!-- 主要指标卡片 -->
        <div class="metrics-grid primary-metrics">
            <div class="metric-card primary">
                <div class="metric-icon">🎯</div>
                <div class="metric-label">NDCG Score</div>
                <div class="metric-value">{avg_metrics['ndcg']:.4f}</div>
                <div class="metric-desc">Normalized Discounted Cumulative Gain</div>
                <div class="metric-quality {"excellent" if avg_metrics['ndcg'] > 0.8 else "good" if avg_metrics['ndcg'] > 0.6 else "fair"}">
                    {"🌟 Excellent Ranking" if avg_metrics['ndcg'] > 0.8 else "✅ Good Ranking" if avg_metrics['ndcg'] > 0.6 else "⚠️ Fair Ranking"}
                </div>
                <div class="metric-detail">Measures how well results are ranked by relevance</div>
            </div>
            
            <div class="metric-card secondary">
                <div class="metric-icon">📍</div>
                <div class="metric-label">MRR Score</div>
                <div class="metric-value">{avg_metrics['mrr']:.4f}</div>
                <div class="metric-desc">Mean Reciprocal Rank</div>
                <div class="metric-quality {"excellent" if avg_metrics['mrr'] > 0.8 else "good" if avg_metrics['mrr'] > 0.5 else "fair"}">
                    {"🎯 Top Result Relevant" if avg_metrics['mrr'] > 0.8 else "📌 Good Position" if avg_metrics['mrr'] > 0.5 else "⚠️ Needs Improvement"}
                </div>
                <div class="metric-detail">First relevant result position: #{int(1/avg_metrics['mrr']) if avg_metrics['mrr'] > 0 else 'N/A'}</div>
            </div>
            
            <div class="metric-card accent">
                <div class="metric-icon">⭐</div>
                <div class="metric-label">Avg Relevance</div>
                <div class="metric-value">{avg_metrics['relevance_score']:.4f}</div>
                <div class="metric-desc">Average Content Quality Score</div>
                <div class="metric-quality {"excellent" if avg_metrics['relevance_score'] > 0.7 else "good" if avg_metrics['relevance_score'] > 0.5 else "fair"}">
                    {"🌟 High Quality" if avg_metrics['relevance_score'] > 0.7 else "✅ Good Quality" if avg_metrics['relevance_score'] > 0.5 else "⚠️ Moderate Quality"}
                </div>
                <div class="metric-detail">Overall content relevance across all results</div>
            </div>
            
            <div class="metric-card info">
                <div class="metric-icon">🔢</div>
                <div class="metric-label">DCG Score</div>
                <div class="metric-value">{avg_metrics.get('dcg', 0):.4f}</div>
                <div class="metric-desc">Discounted Cumulative Gain</div>
                <div class="metric-quality good">
                    📊 Position-Weighted Score
                </div>
                <div class="metric-detail">Cumulative relevance with position discount</div>
            </div>
        </div>
        
        <!-- Precision@K 详细指标 -->
        <div class="precision-section">
            <h3>🎓 Precision@K Analysis</h3>
            <p class="section-desc">Accuracy of top K results - higher values indicate better filtering</p>
            <div class="precision-grid">
                <div class="precision-card">
                    <div class="precision-k">P@1</div>
                    <div class="precision-value">{p_at_1:.3f}</div>
                    <div class="precision-bar">
                        <div class="precision-fill" style="width: {p_at_1*100}%"></div>
                    </div>
                    <div class="precision-desc">{int(p_at_1*100)}% - First result accuracy</div>
                </div>
                
                <div class="precision-card">
                    <div class="precision-k">P@3</div>
                    <div class="precision-value">{p_at_3:.3f}</div>
                    <div class="precision-bar">
                        <div class="precision-fill" style="width: {p_at_3*100}%"></div>
                    </div>
                    <div class="precision-desc">{int(p_at_3*3)} of 3 results relevant</div>
                </div>
                
                <div class="precision-card">
                    <div class="precision-k">P@5</div>
                    <div class="precision-value">{p_at_5:.3f}</div>
                    <div class="precision-bar">
                        <div class="precision-fill" style="width: {p_at_5*100}%"></div>
                    </div>
                    <div class="precision-desc">{int(p_at_5*5)} of 5 results relevant</div>
                </div>
                
                <div class="precision-card">
                    <div class="precision-k">P@10</div>
                    <div class="precision-value">{p_at_10:.3f}</div>
                    <div class="precision-bar">
                        <div class="precision-fill" style="width: {p_at_10*100}%"></div>
                    </div>
                    <div class="precision-desc">{int(p_at_10*10)} of 10 results relevant</div>
                </div>
            </div>
        </div>
        
        <!-- 质量评估总结 -->
        <div class="metrics-summary">
            <h3>📈 Quality Assessment Summary</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-icon">🎯</div>
                    <div class="summary-content">
                        <strong>Ranking Quality (NDCG: {avg_metrics['ndcg']:.3f})</strong>
                        <p>{"✨ Optimal - Most relevant results appear at the top" if avg_metrics['ndcg'] > 0.8 else "✅ Good - Results are well-ranked with minor optimization potential" if avg_metrics['ndcg'] > 0.6 else "⚠️ Fair - Result ordering could be significantly improved"}</p>
                    </div>
                </div>
                
                <div class="summary-item">
                    <div class="summary-icon">📍</div>
                    <div class="summary-content">
                        <strong>First Result Quality (MRR: {avg_metrics['mrr']:.3f})</strong>
                        <p>{"🌟 Excellent - First result is highly relevant" if avg_metrics['mrr'] > 0.8 else "✅ Good - Relevant results in top 2-3 positions" if avg_metrics['mrr'] > 0.5 else "⚠️ Moderate - Relevant results appear further down"}</p>
                    </div>
                </div>
                
                <div class="summary-item">
                    <div class="summary-icon">🎓</div>
                    <div class="summary-content">
                        <strong>Top Results Accuracy (P@3: {p_at_3:.3f})</strong>
                        <p>{f"✨ Excellent - {int(p_at_3*100)}% of top 3 results are relevant" if p_at_3 > 0.7 else f"✅ Good - {int(p_at_3*100)}% relevance in top results" if p_at_3 > 0.5 else f"⚠️ Fair - Only {int(p_at_3*100)}% of top results are relevant"}</p>
                    </div>
                </div>
                
                <div class="summary-item">
                    <div class="summary-icon">⭐</div>
                    <div class="summary-content">
                        <strong>Overall Content Quality ({avg_metrics['relevance_score']:.3f})</strong>
                        <p>{"🌟 High quality sources with strong relevance" if avg_metrics['relevance_score'] > 0.7 else "✅ Good quality with acceptable relevance" if avg_metrics['relevance_score'] > 0.5 else "⚠️ Moderate quality - consider stricter filtering"}</p>
                    </div>
                </div>
            </div>
        </div>
    </section>'''

    references_html = ""
    if all_searches:
        # 收集所有唯一的参考文献
        unique_refs = []
        seen_urls = set()
        for search in all_searches:
            if search.url and search.url not in seen_urls:
                seen_urls.add(search.url)
                unique_refs.append(search)
        
        references_html = f'''<div class="references-section">
        <div class="references-header">
            <h2>📚 Information Sources & References</h2>
            <div class="references-count">Total: {len(unique_refs)} unique sources</div>
        </div>
        <p class="references-intro">All sources used in this research report, verified and quality-checked through academic search metrics.</p>
        <div class="reference-grid">
'''
        
        for idx, search in enumerate(unique_refs, 1):
            parsed = urlparse(search.url)
            domain = parsed.netloc.replace('www.', '') or "source"
            screenshot_url = f"https://image.thum.io/get/width/700/{search.url}"
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
            
            # 转义内容
            title_safe = html.escape(search.title[:100])
            content_preview = html.escape(search.content[:200]) + "..." if len(search.content) > 200 else html.escape(search.content)
            url_safe = html.escape(search.url)
            
            references_html += f'''<div class="reference-card">
                <div class="ref-number">[{idx}]</div>
                <div class="ref-content-wrapper">
                    <div class="ref-header">
                        <div class="ref-image-wrap">
                            <img class="ref-image" src="{screenshot_url}" alt="source preview" onerror="this.style.display='none'; this.parentElement.classList.add('no-image');"/>
                            <div class="ref-fallback"><img src="{favicon_url}" alt="favicon"/><span>{html.escape(domain)}</span></div>
                        </div>
                        <div class="ref-meta">
                            <div class="ref-domain-badge">🌐 {html.escape(domain)}</div>
                        </div>
                    </div>
                    <h4 class="ref-title">{highlight_keywords(search.title[:100], keywords)}</h4>
                    <p class="ref-content">{highlight_keywords(content_preview, keywords)}</p>
                    <div class="ref-footer">
                        <a href="{search.url}" target="_blank" rel="noopener noreferrer" class="ref-link">
                            <span class="link-icon">🔗</span>
                            <span class="link-text">Visit Source</span>
                            <span class="link-arrow">→</span>
                        </a>
                        <div class="ref-url-display">{url_safe}</div>
                    </div>
                </div>
            </div>
'''

        references_html += '''</div>
        <div class="references-footer">
            <p>💡 <strong>Note:</strong> All sources have been automatically evaluated for relevance and quality using academic search metrics (NDCG, MRR, Precision@K).</p>
        </div>
    </div>
'''

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deep Search Academic Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@600;700;800&family=Noto+Sans+SC:wght@400;500;700&display=swap');

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html {{
            scroll-behavior: smooth;
        }}
        
        body {{
            font-family: 'Inter', 'Noto Sans SC', 'Segoe UI', sans-serif;
            line-height: 1.8;
            color: #2c3e50;
            background:
                radial-gradient(circle at 8% 12%, rgba(79, 70, 229, 0.18) 0%, transparent 26%),
                radial-gradient(circle at 88% 16%, rgba(15, 118, 110, 0.16) 0%, transparent 24%),
                radial-gradient(circle at 52% 86%, rgba(217, 119, 6, 0.12) 0%, transparent 22%),
                linear-gradient(145deg, #f4f7fb 0%, #edf2f9 45%, #e8eef7 100%);
            padding: 20px;
            min-height: 100vh;
            background-size: 240% 240%, 220% 220%, 210% 210%, 300% 300%;
            animation: reportGradientFlow {motion['report_duration']} ease-in-out infinite;
        }}

        @keyframes reportGradientFlow {{
            0% {{
                background-position: 0% 0%, 100% 0%, 50% 100%, 0% 50%;
            }}
            25% {{
                background-position: {motion['report_q1']};
            }}
            50% {{
                background-position: {motion['report_mid']};
            }}
            75% {{
                background-position: {motion['report_q3']};
            }}
            100% {{
                background-position: 0% 0%, 100% 0%, 50% 100%, 0% 50%;
            }}
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
            overflow: hidden;
            border: 1px solid rgba(108, 92, 231, 0.1);
        }}
        
        :root {{
            --primary: #1f2937;
            --accent: #4f46e5;
            --secondary: #0f766e;
            --warning: #d97706;
            --light: #f8fafc;
            --border: #d1d9e6;
            --kw-bg: #d1d5db;
            --kw-text: #111827;
        }}
        
        .header {{
            background: linear-gradient(135deg, #34495e 0%, #2c3e50 50%, #1a5276 100%);
            color: white;
            padding: 5rem 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120"><path d="M0,64L48,80C96,96 192,128 288,128C384,128 480,96 576,85.3C672,75 768,85 864,90.7C960,96 1056,96 1104,96L1152,96L1152,120L1104,120C1056,120 960,120 864,120C768,120 672,120 576,120C480,120 384,120 288,120C192,120 96,120 48,120L0,120Z" fill="%23ffffff" fill-opacity="0.1"/></svg>');
            animation: float 6s ease-in-out infinite;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-20px); }}
        }}
        
        .header h1 {{
            font-family: 'Playfair Display', 'Noto Sans SC', serif;
            font-size: 2.8rem;
            margin-bottom: 0.5rem;
            position: relative;
            z-index: 1;
            font-weight: 800;
            text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.2);
        }}
        
        .header .subtitle {{
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            font-size: 1.15rem;
            opacity: 0.95;
            position: relative;
            z-index: 1;
            font-weight: 500;
            letter-spacing: 0.5px;
        }}
        
        .header .metadata {{
            font-size: 0.95rem;
            opacity: 0.9;
            margin-top: 1.5rem;
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }}
        
        .metadata-item {{
            text-align: center;
        }}
        
        .metadata-label {{
            font-size: 0.85rem;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metadata-value {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 0.3rem;
        }}
        
        .content {{
            padding: 3.5rem 2.5rem;
        }}
        
        .query-box {{
            background: linear-gradient(135deg, rgba(108, 92, 231, 0.05) 0%, rgba(0, 184, 148, 0.05) 100%);
            border-left: 5px solid var(--accent);
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 3rem;
            backdrop-filter: blur(10px);
        }}
        
        .query-box h3 {{
            color: var(--primary);
            margin-bottom: 0.8rem;
            font-size: 1.2rem;
        }}
        
        .query-box p {{
            font-size: 1.05rem;
            color: #34495e;
            line-height: 1.6;
        }}
        
        h2 {{
            color: var(--primary);
            margin-top: 2.5rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.8rem;
            border-bottom: 3px solid var(--accent);
            position: relative;
            font-size: 1.8rem;
            font-weight: 700;
        }}
        
        h3 {{
            color: #34495e;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }}
        
        h4 {{
            color: #555;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        
        p {{
            margin-bottom: 1.2rem;
            line-height: 1.8;
            color: #444;
        }}
        
        .report-section {{
            margin-bottom: 2.5rem;
            padding: 2rem;
            background: var(--light);
            border-radius: 12px;
            border-left: 5px solid var(--secondary);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }}
        
        .report-section h2 {{
            margin-top: 0;
            border-bottom: none;
            padding-bottom: 0;
            color: var(--primary);
        }}
        
        /* 统计信息卡片 */
        .statistics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
            margin: 2.5rem 0;
        }}
        
        .stat-card {{
            background: white;
            border: 2px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--secondary));
        }}
        
        .stat-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 8px 25px rgba(108, 92, 231, 0.15);
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            color: #7f8c8d;
            font-size: 1rem;
            margin-top: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }}
        
        /* 参考来源网格 */
        .references-section {{
            background: linear-gradient(135deg, #f5f9fc 0%, #f8f7fc 100%);
            padding: 3rem 2.5rem;
            border-radius: 12px;
            margin-top: 3rem;
            border: 2px solid rgba(108, 92, 231, 0.2);
        }}
        
        .references-section h2 {{
            color: var(--primary);
            margin-top: 0;
            border-color: var(--accent);
        }}
        
        .reference-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.8rem;
            margin-top: 2rem;
        }}
        
        .reference-card {{
            background: white;
            border: 2px solid var(--border);
            border-radius: 12px;
            padding: 1.8rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        
        .reference-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent), var(--secondary));
        }}
        
        .reference-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 12px 30px rgba(108, 92, 231, 0.2);
            transform: translateY(-8px);
        }}
        
        .ref-number {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
        }}
        
        .ref-image-wrap {{
            width: 120px;
            height: 80px;
            background: linear-gradient(135deg, #eef2ff 0%, #ecfeff 100%);
            border-radius: 8px;
            position: relative;
            overflow: hidden;
            border: 1px solid var(--border);
            flex-shrink: 0;
        }}
        
        .ref-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .ref-fallback {{
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            color: #475569;
            background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .ref-fallback img {{
            width: 20px;
            height: 20px;
        }}

        .no-image .ref-fallback {{
            display: flex;
        }}

        .ref-image-wrap:not(.no-image) .ref-fallback {{
            display: none;
        }}
        
        .ref-meta {{
            flex: 1;
        }}
        
        .ref-domain-badge {{
            display: inline-block;
            background: linear-gradient(135deg, rgba(108, 92, 231, 0.1), rgba(0, 184, 148, 0.1));
            color: var(--primary);
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        
        .ref-title {{
            color: var(--primary);
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0.8rem 0;
            line-height: 1.4;
        }}
        
        .ref-content {{
            font-size: 0.95rem;
            color: #666;
            margin-bottom: 1rem;
            line-height: 1.6;
        }}
        
        .ref-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 1rem;
            border-top: 1px solid rgba(0, 0, 0, 0.05);
            gap: 1rem;
            flex-wrap: wrap;
        }}
        
        .ref-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            color: white;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            text-decoration: none;
            font-weight: 600;
            padding: 0.6rem 1.2rem;
            border-radius: 25px;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }}
        
        .ref-link:hover {{
            transform: translateX(5px);
            box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3);
        }}
        
        .link-icon {{
            font-size: 1.1rem;
        }}
        
        .link-text {{
            font-weight: 600;
        }}
        
        .link-arrow {{
            font-size: 1.2rem;
            transition: transform 0.3s ease;
        }}
        
        .ref-link:hover .link-arrow {{
            transform: translateX(5px);
        }}
        
        .ref-url-display {{
            font-size: 0.8rem;
            color: #95a5a6;
            word-break: break-all;
            font-family: 'Courier New', monospace;
            flex: 1;
        }}
        
        .references-footer {{
            margin-top: 2rem;
            padding: 1.5rem;
            background: white;
            border-radius: 10px;
            border-left: 4px solid var(--accent);
        }}
        
        .references-footer p {{
            margin: 0;
            color: #7f8c8d;
            font-size: 0.95rem;
        }}
        
        .references-footer strong {{
            color: var(--primary);
        }}

        .kw-highlight {{
            background: var(--kw-bg);
            color: var(--kw-text);
            padding: 0.06rem 0.28rem;
            border-radius: 4px;
            display: inline;
        }}
        
        .summary-table-wrap {{
            margin: 2rem 0;
        }}

        .summary-table-wrap h2 {{
            margin-top: 0;
        }}

        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 6px 24px rgba(79, 70, 229, 0.12);
            background: white;
        }}

        .report-sections {{
            display: grid;
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .report-section-block {{
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.2rem 1.3rem;
        }}

        .report-section-block h3 {{
            margin-top: 0;
            color: var(--primary);
        }}

        .section-content p {{
            margin-bottom: 0.8rem;
        }}
        
        .footer {{
            background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
            padding: 2.5rem;
            border-top: 3px solid var(--accent);
            text-align: center;
            color: #ecf0f1;
            font-size: 0.95rem;
        }}
        
        .footer p {{
            margin-bottom: 0.6rem;
            color: #bdc3c7;
        }}
        
        .footer strong {{
            color: white;
        }}
        
        /* 质量指标样式 */
        .quality-metrics-section {{
            margin: 3rem 0;
            padding: 2.5rem;
            background: linear-gradient(135deg, rgba(108, 92, 231, 0.03) 0%, rgba(0, 184, 148, 0.03) 100%);
            border-radius: 15px;
            border: 2px solid rgba(108, 92, 231, 0.1);
        }}
        
        .quality-metrics-section h2 {{
            margin-top: 0;
            color: var(--primary);
            text-align: center;
            font-size: 2rem;
            margin-bottom: 2rem;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 1.8rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            border: 2px solid transparent;
            position: relative;
            overflow: hidden;
        }}
        
        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--secondary));
        }}
        
        .metric-card.primary::before {{
            background: linear-gradient(90deg, #6c5ce7, #a29bfe);
        }}
        
        .metric-card.secondary::before {{
            background: linear-gradient(90deg, #00b894, #00cec9);
        }}
        
        .metric-card.accent::before {{
            background: linear-gradient(90deg, #fd79a8, #fdcb6e);
        }}
        
        .metric-card.info::before {{
            background: linear-gradient(90deg, #0984e3, #74b9ff);
        }}
        
        .metric-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(108, 92, 231, 0.15);
            border-color: rgba(108, 92, 231, 0.3);
        }}
        
        .metric-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.8rem;
        }}
        
        .metric-label {{
            font-size: 0.85rem;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .metric-value {{
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--primary);
            margin: 0.5rem 0;
            font-family: 'Inter', sans-serif;
        }}
        
        .metric-desc {{
            font-size: 0.9rem;
            color: #95a5a6;
            margin-top: 0.5rem;
            font-style: italic;
        }}
        
        .metric-quality {{
            margin-top: 1rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-block;
        }}
        
        .metric-quality.excellent {{
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
        }}
        
        .metric-quality.good {{
            background: linear-gradient(135deg, #d1ecf1, #bee5eb);
            color: #0c5460;
        }}
        
        .metric-quality.fair {{
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404;
        }}
        
        .metric-detail {{
            margin-top: 0.8rem;
            padding-top: 0.8rem;
            border-top: 1px solid rgba(0, 0, 0, 0.05);
            font-size: 0.85rem;
            color: #7f8c8d;
            font-style: italic;
        }}
        
        /* Precision@K 区域样式 */
        .precision-section {{
            margin: 2.5rem 0;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }}
        
        .precision-section h3 {{
            color: var(--primary);
            margin-bottom: 0.5rem;
            font-size: 1.5rem;
        }}
        
        .section-desc {{
            color: #7f8c8d;
            margin-bottom: 1.5rem;
            font-style: italic;
        }}
        
        .precision-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }}
        
        .precision-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            border: 2px solid rgba(108, 92, 231, 0.1);
            transition: all 0.3s ease;
        }}
        
        .precision-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(108, 92, 231, 0.12);
            border-color: rgba(108, 92, 231, 0.3);
        }}
        
        .precision-k {{
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .precision-value {{
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--primary);
            margin: 0.5rem 0;
        }}
        
        .precision-bar {{
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 1rem 0;
        }}
        
        .precision-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--secondary));
            border-radius: 10px;
            transition: width 0.5s ease;
        }}
        
        .precision-desc {{
            font-size: 0.85rem;
            color: #7f8c8d;
            font-style: italic;
        }}
        
        /* 评估总结样式 */
        .metrics-summary {{
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            margin-top: 2rem;
        }}
        
        .metrics-summary h3 {{
            color: var(--primary);
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
        }}
        
        .summary-item {{
            display: flex;
            gap: 1rem;
            padding: 1.2rem;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 10px;
            border-left: 4px solid var(--accent);
            transition: all 0.3s ease;
        }}
        
        .summary-item:hover {{
            transform: translateX(5px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        }}
        
        .summary-icon {{
            font-size: 2rem;
            flex-shrink: 0;
        }}
        
        .summary-content {{
            flex: 1;
        }}
        
        .summary-content strong {{
            color: var(--primary);
            display: block;
            margin-bottom: 0.5rem;
        }}
        
        .summary-content p {{
            margin: 0;
            color: #555;
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        
        .metrics-intro {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 2rem;
            font-style: italic;
        }}
        
        .primary-metrics {{
            margin-bottom: 2rem;
        }}
        
        /* References 增强样式 */
        .references-section {{
            margin: 3rem 0;
            padding: 2.5rem;
            background: linear-gradient(135deg, rgba(0, 184, 148, 0.03) 0%, rgba(108, 92, 231, 0.03) 100%);
            border-radius: 15px;
            border: 2px solid rgba(0, 184, 148, 0.1);
        }}
        
        .references-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .references-header h2 {{
            color: var(--primary);
            font-size: 2rem;
            margin: 0;
        }}
        
        .references-count {{
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            color: white;
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        
        .references-intro {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 2rem;
            font-style: italic;
        }}
        
        .reference-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.8rem;
        }}
        
        .reference-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            border: 2px solid transparent;
            display: flex;
            gap: 0;
        }}
        
        .reference-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0, 184, 148, 0.15);
            border-color: rgba(0, 184, 148, 0.3);
        }}
        
        .ref-number {{
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            color: white;
            font-weight: 800;
            font-size: 1.2rem;
            padding: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 60px;
            writing-mode: vertical-rl;
            text-align: center;
        }}
        
        .ref-content-wrapper {{
            flex: 1;
            padding: 1.5rem;
        }}
        
        .ref-header {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            align-items: flex-start;
        }}
        
        /* 表格样式 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: white;
        }}
        
        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        
        th {{
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9rem;
            letter-spacing: 0.5px;
        }}
        
        tr:hover {{
            background: var(--light);
        }}
        
        /* 代码块样式 */
        code {{
            background: #f4f4f4;
            color: var(--accent);
            padding: 0.3em 0.6em;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border-left: 4px solid var(--accent);
        }}
        
        /* 打印样式 */
        @media print {{
            body {{
                background: white;
            }}
            
            .container {{
                box-shadow: none;
                border: none;
            }}
            
            .reference-card {{
                page-break-inside: avoid;
            }}
        }}
        
        /* 响应式 */
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}
            
            .content {{
                padding: 2rem 1.5rem;
            }}
            
            .reference-grid {{
                grid-template-columns: 1fr;
            }}
            
            .statistics {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🔬 Deep Search Academic Report</h1>
            <div class="subtitle">AI-powered deep web research and structured analysis</div>
            <div class="metadata">
                <div class="metadata-item">
                    <div class="metadata-label">Research Topic</div>
                    <div class="metadata-value">{highlight_keywords(query, keywords)}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Generated On</div>
                    <div class="metadata-value">{datetime.now().strftime('%Y-%m-%d')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Model</div>
                    <div class="metadata-value">{st.session_state.llm_provider.upper()} - {st.session_state.model_name}</div>
                </div>
            </div>
        </div>
        
        <!-- 内容 -->
        <div class="content">
            <!-- 查询信息 -->
            <div class="query-box">
                <h3>📋 Research Brief</h3>
                <p><strong>Question:</strong> {highlight_keywords(query, keywords)}</p>
                <p><strong>Method:</strong> Iterative web search, reflection loops, and synthesis.</p>
            </div>

            {table_html}
            
            {quality_metrics_html}

            <h2>Segmented Findings</h2>
            <div class="report-sections">{''.join(section_blocks)}</div>

            <h2>Full Narrative</h2>
            <div class="report-section">{paragraphize(final_report, keywords)}</div>

            <h2>📊 Research Metrics</h2>
            <div class="statistics">
                <div class="stat-card">
                    <div class="stat-number">{para_count}</div>
                    <div class="stat-label">Sections</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{search_count}</div>
                    <div class="stat-label">Sources</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{reflection_count}</div>
                    <div class="stat-label">Reflections</div>
                </div>
            </div>
            
            <!-- 参考来源 -->
            {references_html}
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>📄 <strong>Deep Search Agent</strong> — Academic Report</p>
            <p>🔬 AI-assisted evidence collection and synthesis</p>
            <p>💾 Offline-friendly HTML output, print-ready and shareable</p>
            <p style="margin-top: 1.5rem; font-size: 0.85rem; color: #95a5a6;">© {datetime.now().year} Deep Search Agent. All rights reserved.</p>
        </div>
    </div>
</body>
</html>'''
    
    return html_content


def execute_research(query: str, config: Config):
    """执行研究"""
    try:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 初始化Agent
        init_msg = "🔄 Initializing agent..." if st.session_state.language == "EN" else "🔄 初始化代理中..."
        status_text.text(init_msg)
        agent = DeepSearchAgent(config)
        st.session_state.agent = agent
        
        progress_bar.progress(10)
        
        # 生成报告结构
        outline_msg = "📋 Building report outline..." if st.session_state.language == "EN" else "📋 构建报告大纲中..."
        status_text.text(outline_msg)
        agent._generate_report_structure(query)
        progress_bar.progress(20)
        
        # 处理段落
        total_paragraphs = len(agent.state.paragraphs)
        for i in range(total_paragraphs):
            section_msg = f"🔍 Processing section {i+1}/{total_paragraphs}: {agent.state.paragraphs[i].title}" if st.session_state.language == "EN" else f"🔍 处理章节 {i+1}/{total_paragraphs}: {agent.state.paragraphs[i].title}"
            status_text.text(section_msg)
            
            # 初始搜索和总结
            agent._initial_search_and_summary(i)
            progress_value = 20 + (i + 0.5) / total_paragraphs * 60
            progress_bar.progress(int(progress_value))
            
            # 反思循环
            agent._reflection_loop(i)
            agent.state.paragraphs[i].research.mark_completed()
            
            progress_value = 20 + (i + 1) / total_paragraphs * 60
            progress_bar.progress(int(progress_value))
        
        # 生成最终报告
        final_msg = "📄 Generating final report..." if st.session_state.language == "EN" else "📄 生成最终报告中..."
        status_text.text(final_msg)
        final_report = agent._generate_final_report()
        progress_bar.progress(90)
        
        # 保存报告
        save_msg = "💾 Saving report files..." if st.session_state.language == "EN" else "💾 保存报告文件中..."
        status_text.text(save_msg)
        agent._save_report(final_report)
        progress_bar.progress(100)
        
        complete_msg = "✅ Research completed!" if st.session_state.language == "EN" else "✅ 研究完成！"
        status_text.text(complete_msg)
        
        # 显示结果
        display_results(agent, final_report)
        
    except Exception as e:
        error_msg = f"❌ Error during research: {str(e)}" if st.session_state.language == "EN" else f"❌ 研究过程中出错: {str(e)}"
        st.error(error_msg)


def display_results(agent: DeepSearchAgent, final_report: str):
    """显示研究结果"""
    # 获取查询内容
    query = getattr(st.session_state, 'last_query', 'Research Report')
    
    st.success(get_text('research_success'))
    st.divider()
    st.header(get_text('results_title'))
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([get_text('tab_narrative'), get_text('tab_details'), get_text('tab_html'), get_text('tab_download'), "📊 Research Metrics"])
    
    with tab1:
        table_data = []
        for i, paragraph in enumerate(agent.state.paragraphs, start=1):
            table_data.append(
                {
                    "#": i,
                    get_text('section'): paragraph.title,
                    get_text('searches'): paragraph.research.get_search_count(),
                    get_text('reflections'): paragraph.research.reflection_iteration,
                }
            )
        st.subheader(get_text('structured_overview'))
        st.table(table_data)
        st.subheader(get_text('segmented_narrative'))
        for i, paragraph in enumerate(agent.state.paragraphs, start=1):
            section_label = f"{get_text('section')} {i}: {paragraph.title}"
            with st.expander(section_label, expanded=(i == 1)):
                st.markdown(paragraph.research.latest_summary or paragraph.content)
        st.subheader(get_text('full_output'))
        st.markdown(final_report)
    
    with tab2:
        # 段落详情
        st.subheader(get_text('section_details'))
        for i, paragraph in enumerate(agent.state.paragraphs):
            section_label = f"📌 {get_text('section')} {i+1}: {paragraph.title}"
            with st.expander(section_label):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**{get_text('search_count')}:**", paragraph.research.get_search_count())
                    st.write(f"**{get_text('reflection_rounds')}:**", paragraph.research.reflection_iteration)
                with col2:
                    scope_text = paragraph.content[:100] + "..." if len(paragraph.content) > 100 else paragraph.content
                    st.write(f"**{get_text('planned_scope')}:**", scope_text)
                
                st.divider()
                st.write(f"**{get_text('final_section_text')}:**")
                final_text = paragraph.research.latest_summary[:500] + "..." if len(paragraph.research.latest_summary) > 500 else paragraph.research.latest_summary
                st.markdown(final_text)
        
        # 搜索历史
        st.subheader(get_text('search_history'))
        all_searches = []
        for paragraph in agent.state.paragraphs:
            all_searches.extend(paragraph.research.search_history)
        
        if all_searches:
            search_count = 0
            for search in all_searches:
                search_count += 1
                search_label = f"{get_text('search')} {search_count}: {search.query}"
                with st.expander(search_label):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.write(f"**{get_text('title')}:**", search.title)
                        st.write(f"**{get_text('url')}:**", search.url)
                    with col2:
                        if search.score:
                            st.write(f"**{get_text('relevance_score')}:**", f"{search.score:.2f}")
                    
                    st.divider()
                    st.write(f"**{get_text('content_preview')}:**")
                    st.markdown(search.content[:300] + "..." if len(search.content) > 300 else search.content)
    
    with tab3:
        # 生成并显示HTML报告
        html_title = "🌐 Styled HTML report" if st.session_state.language == "EN" else "🌐 样式化 HTML 报告"
        html_info = "💡 Preview the final HTML report here, then download it from the Download tab." if st.session_state.language == "EN" else "💡 在此预览最终 HTML 报告，然后从下载选项卡下载。"
        st.subheader(html_title)
        st.info(html_info)
        
        html_report = generate_html_report(agent, final_report, query)
        st.components.v1.html(html_report, height=1200, scrolling=True)
    
    with tab4:
        # 下载选项
        download_title = "📥 Download options" if st.session_state.language == "EN" else "📥 下载选项"
        st.subheader(download_title)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Markdown下载
            md_label = "⬇️ Markdown report" if st.session_state.language == "EN" else "⬇️ Markdown 报告"
            st.download_button(
                label=md_label,
                data=final_report,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col2:
            # HTML下载
            html_label = "⬇️ HTML report" if st.session_state.language == "EN" else "⬇️ HTML 报告"
            html_report = generate_html_report(agent, final_report, query)
            st.download_button(
                label=html_label,
                data=html_report,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col3:
            # JSON状态下载
            json_label = "⬇️ State JSON" if st.session_state.language == "EN" else "⬇️ 状态 JSON"
            state_json = agent.state.to_json()
            st.download_button(
                label=json_label,
                data=state_json,
                file_name=f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
    
    with tab5:
        # 研究指标仪表板
        st.subheader("📊 Research Metrics Dashboard")
        st.markdown("---")
        
        # 检查metrics是否可用
        if agent.metrics_collector and agent.metrics_collector.metrics:
            render_metrics_explanation_panel(agent)

            # 生成HTML仪表板
            visualizer = MetricsVisualizer()
            language = st.session_state.language if hasattr(st.session_state, 'language') else "ZH"
            metrics_html = visualizer.generate_html_dashboard(agent.metrics_collector.metrics, language=language)
            
            # 显示HTML仪表板
            st.components.v1.html(metrics_html, height=1600, scrolling=True)
            
            # 提供下载按钮
            st.markdown("---")
            metrics_label = "⬇️ Download Metrics Report" if st.session_state.language == "EN" else "⬇️ 下载指标报告"
            st.download_button(
                label=metrics_label,
                data=metrics_html,
                file_name=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.warning("⚠️ Metrics data not available. Please ensure the research has been completed.")


if __name__ == "__main__":
    main()
