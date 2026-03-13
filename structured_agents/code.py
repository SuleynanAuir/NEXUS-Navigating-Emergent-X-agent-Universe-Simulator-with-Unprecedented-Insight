"""
JSON → 结构化提取 → 多 Agent 协作深度分析 → 趋势预测 Agent 指导 TXT 生成器
=============================================================
架构：Multi-Agent Pipeline（面向趋势预测场景）

  Step 1  读取 JSON，结构化提取三个维度
           ① 用户关注点  (highlighted_claims / priority_focus_marks / secondary_focus_marks / keyword)
           ② 页面信息    (url / title / page_summary / key_points / reliability_assessment / risk_flags)
           ③ 关联事件    (structured_claim_checks / fast_verification / quant_metrics)

  Step 2  多 Agent 协作深度分析（使用 gpt-4o）
           Agent-A  用户焦点-趋势信号解析师  → 从用户关注点中挖掘趋势信号、演进脉络、关注热度
           Agent-B  内容-趋势证据评审师      → 从页面内容中提取技术演进证据、时间轴、关键节点
           Agent-C  事件-趋势关联推理师      → 从关联事件中推断技术扩散路径、行业采纳动态
           Agent-D  首席趋势战略整合师       → 整合三份报告，生成供趋势预测Agent使用的战略文档

  Step 3  整合输出"趋势预测Agent导引文档"
"""

import json
import os
import sys
import textwrap
import threading
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# ──────────────────────────────────────────────
# 进度条工具
# ──────────────────────────────────────────────

class _Spinner:
    """在后台线程持续刷新进度条，直到 stop() 被调用。"""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, label: str):
        self.label   = label
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._start  = time.time()

    def _run(self):
        idx = 0
        while not self._stop.is_set():
            elapsed = time.time() - self._start
            frame   = self.FRAMES[idx % len(self.FRAMES)]
            # 简单进度条：按秒数模拟，每 2 s 走 1 格，共 20 格
            filled  = min(int(elapsed / 2), 20)
            bar     = "█" * filled + "░" * (20 - filled)
            sys.stdout.write(f"\r  {frame} {self.label}  [{bar}] {elapsed:5.1f}s")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    def start(self):
        self._start = time.time()
        self._thread.start()
        return self

    def stop(self, success: bool = True):
        self._stop.set()
        self._thread.join()
        elapsed = time.time() - self._start
        icon    = "✅" if success else "❌"
        bar     = "█" * 20
        sys.stdout.write(f"\r  {icon} {self.label}  [{bar}] {elapsed:5.1f}s  完成\n")
        sys.stdout.flush()


def _run_with_spinner(label: str, fn, *args, **kwargs):
    """用进度条包裹任意函数调用，返回函数结果。"""
    sp = _Spinner(label).start()
    try:
        result = fn(*args, **kwargs)
        sp.stop(success=True)
        return result
    except Exception:
        sp.stop(success=False)
        raise

# ─────────────────────────────────────────────
# 客户端配置
# ─────────────────────────────────────────────
client = OpenAI(
    base_url="https://millionengine.com/v1",
    api_key="sk-ZvCHVW8kFibSLgtGW0N4clHHImBhF5uAbkqdygsoycQlB1ZI"
)

# 主分析模型：使用 gpt-4o 进行深度分析
LLM_MODEL = "gpt-4o"
# 快速辅助模型：用于内部链式调用的辅助步骤
LLM_MODEL_FAST = "gpt-4o"


# ═══════════════════════════════════════════════
# STEP 1：结构化提取
# ═══════════════════════════════════════════════

def extract_user_focus(report: dict, global_keyword: str) -> dict:
    """
    维度①：用户关注点
    来源字段：highlighted_claims / priority_focus_marks / secondary_focus_marks / global keyword
    """
    return {
        "global_keyword": global_keyword,
        "priority_claims": report.get("priority_focus_marks", []),
        "secondary_claims": report.get("secondary_focus_marks", []),
        "highlighted_claims": report.get("highlighted_claims", []),
        # 从 fast_verification 中提取关键词，作为用户搜索意图的补充
        "search_keywords": report.get("fast_verification", {}).get("keywords", []),
    }


def extract_page_info(report: dict) -> dict:
    """
    维度②：页面信息
    来源字段：url / title / page_summary / key_points / reliability_assessment / risk_flags / generator
    """
    return {
        "url": report.get("url", ""),
        "title": report.get("title", ""),
        "page_summary": report.get("page_summary", ""),
        "key_points": report.get("key_points", []),
        "reliability_score": report.get("reliability_assessment", {}).get("score", None),
        "reliability_rationale": report.get("reliability_assessment", {}).get("rationale", ""),
        "risk_flags": report.get("risk_flags", []),
        "generator": report.get("generator", ""),
        "generated_at": report.get("generated_at", ""),
    }


def extract_related_events(report: dict) -> dict:
    """
    维度③：有关联的相关事件信息
    来源字段：structured_claim_checks / fast_verification / quant_metrics
    """
    claim_checks = report.get("structured_claim_checks", [])

    # 按核验状态分类
    supported = [c for c in claim_checks if c.get("status") == "supported"]
    partially  = [c for c in claim_checks if c.get("status") == "partially_supported"]
    unclear    = [c for c in claim_checks if c.get("status") == "unclear"]

    fv = report.get("fast_verification", {})
    qm = report.get("quant_metrics", {})

    return {
        "claim_checks_supported":          supported,
        "claim_checks_partially_supported": partially,
        "claim_checks_unclear":            unclear,
        "fast_verification": {
            "confidence_score": fv.get("confidence_score"),
            "verdict":          fv.get("verdict"),
            "level_name":       fv.get("confidence_level", {}).get("name"),
            "level_desc":       fv.get("confidence_level", {}).get("description"),
        },
        "quant_metrics": {
            "confidence_score":    qm.get("confidence_score"),
            "verdict":             qm.get("verdict"),
            "support_ratio":       qm.get("support_ratio"),
            "focus_coverage":      qm.get("focus_coverage"),
            "relevance_alignment": qm.get("relevance_alignment"),
            "level_name":          qm.get("confidence_level", {}).get("name"),
        },
    }


def load_and_extract(json_path: str):
    """
    读取 JSON 文件，对每条 report 提取三个维度，
    返回列表，每个元素 = { "user_focus", "page_info", "related_events", "report_idx" }
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    global_keyword = data.get("keyword", "未知关键词")
    reports = data.get("reports", [])

    extracted = []
    for idx, report in enumerate(reports, start=1):
        extracted.append({
            "report_idx":     idx,
            "user_focus":     extract_user_focus(report, global_keyword),
            "page_info":      extract_page_info(report),
            "related_events": extract_related_events(report),
        })

    return extracted, data


# ═══════════════════════════════════════════════
# STEP 2：Multi-Agent 深度分析架构
# ═══════════════════════════════════════════════

def _call_agent(agent_name: str, system_prompt: str, user_content: str,
                model: str = None, max_tokens: int = 2500, temperature: float = 0.3) -> str:
    """
    统一 Agent 调用封装。
    支持多轮对话：messages 列表中可注入 assistant 的中间推理步骤（chain-of-thought）。
    """
    model = model or LLM_MODEL
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    result = response.choices[0].message.content.strip()
    return result


def _chain_of_thought_agent(agent_name: str, system_prompt: str,
                             first_pass_prompt: str, second_pass_prompt: str,
                             model: str = None, max_tokens: int = 2500) -> str:
    """
    两阶段链式 Agent：
      第一阶段 → 让 Agent 先做初步分析和自我提问
      第二阶段 → 基于第一阶段输出，进行深化和完善
    """
    model = model or LLM_MODEL

    # 第一阶段：初步分析
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": first_pass_prompt},
    ]
    r1 = client.chat.completions.create(
        model=model, messages=messages, temperature=0.3, max_tokens=max_tokens
    )
    first_output = r1.choices[0].message.content.strip()

    # 第二阶段：深化细化
    messages.append({"role": "assistant", "content": first_output})
    messages.append({"role": "user",      "content": second_pass_prompt})
    r2 = client.chat.completions.create(
        model=model, messages=messages, temperature=0.2, max_tokens=max_tokens
    )
    return r2.choices[0].message.content.strip()


# ──────────────────────────────────────────────
# Agent-A：用户焦点-趋势信号解析师
# ──────────────────────────────────────────────

def analyze_user_focus(all_user_focus: list) -> str:
    """
    Agent-A：用户焦点-趋势信号深度解析师
    核心任务：将用户关注点转化为可供趋势预测Agent使用的"跨域趋势信号图谱"
    分析视角：用户关注的"是什么" → 反映事件、政策、金融、学术、科技哪里在升温/降温
    """
    sections = []
    for item in all_user_focus:
        idx = item["_report_idx"]
        uf  = item["user_focus"]
        all_claims = list(dict.fromkeys(
            uf["priority_claims"] + uf["highlighted_claims"] + uf["secondary_claims"]
        ))
        block = (
            f"【报告{idx} · 原始关注数据】\n"
            f"▸ 搜索关键词：{uf['global_keyword']}\n"
            f"▸ 优先关注声明（{len(uf['priority_claims'])}条，代表用户最强烈的兴趣信号）：\n"
            + "\n".join(f"    P{i+1}: {c}" for i, c in enumerate(uf["priority_claims"])) + "\n"
            f"▸ 次要关注声明（{len(uf['secondary_claims'])}条，代表用户的边缘兴趣/疑虑）：\n"
            + "\n".join(f"    S{i+1}: {c}" for i, c in enumerate(uf["secondary_claims"])) + "\n"
            f"▸ 全部高亮声明（{len(uf['highlighted_claims'])}条）：\n"
            + "\n".join(f"    H{i+1}: {c}" for i, c in enumerate(uf["highlighted_claims"])) + "\n"
            f"▸ 系统提取关键词：{', '.join(uf['search_keywords']) or '无'}"
        )
        sections.append(block)

    raw_text = "\n\n" + ("─" * 50 + "\n").join(sections)

    system_prompt = textwrap.dedent("""
        你是 Agent-A：用户焦点-趋势信号深度解析师。
        你的专业背景融合了：趋势情报分析、用户行为研究、知识图谱技术、信息需求预测。

        【核心使命】
        你不是在"分析用户想要什么"，而是在"从用户的关注模式中，解码出跨域系统正在发生什么趋势变化"。
        用户的关注点是趋势的早期信号——用户关注什么、担忧什么、对比什么，折射出突发新闻、政策草案、金融信号、学术研究、科技前沿的联动方向。

        【跨域覆盖范围】
        你必须覆盖并识别以下五类信号：
        - 突发新闻：事件冲击、传播速度、二次舆情反应
        - 政策草案：监管方向、约束边界、落地节奏
        - 金融信号：价格波动、资金流向、估值重定价
        - 学术研究：共识形成、争议前沿、方法迁移
        - 科技前沿：能力突破、工程可行性、产业化进度

        【输出要求】
        - 每个论点必须直接引用原始声明原文作为证据，不能悬空推断
        - 对每个趋势信号，必须分析其"强度"（多少声明指向它）、"方向"（上升/下降/分化）、"时间位置"（当前处于扩散生命周期哪个阶段）
        - 明确区分"已发生的趋势事实"与"用户预判的未来趋势"
        - 对用户关注的每个问题，分析其背后折射的政策焦虑、金融预期、舆情压力、学术不确定性或技术机遇
        - 输出内容必须具体到事件名称、政策方向、金融指标、研究主题、技术/场景名称，不能出现"可能""也许""某些"等模糊表述
        - 每节至少500字，充分展开，不得简略
    """).strip()

    first_pass = textwrap.dedent(f"""
        以下是来自 {len(all_user_focus)} 份研究报告的用户关注点原始数据，搜索主题为：{all_user_focus[0]['user_focus']['global_keyword'] if all_user_focus else '未知'}

        请完成第一阶段扫描任务：
        1. 逐条阅读所有声明，标注每条声明的"趋势信号类型"：
           - [突发事件信号]：短期冲击事件及其传播链
           - [政策导向信号]：政策草案/监管口径变化
           - [金融定价信号]：价格、资金、估值变化
           - [学术演进信号]：论文共识、方法争议、研究热点迁移
           - [科技前沿信号]：能力突破、性能对比、工程边界变化
           - [应用扩张信号]：跨行业/跨场景渗透
           - [质疑/反转信号]：主流叙事被挑战或重估
        2. 统计各类信号的数量和分布
        3. 识别哪些事件/政策/金融/学术/科技议题被多份报告同时关注（跨报告共振信号）
        4. 列出你将在第二阶段重点展开的10个关键发现

        原始数据：
        {raw_text}
    """).strip()

    second_pass = textwrap.dedent("""
        基于第一阶段的扫描结果，请生成完整的【用户焦点·趋势信号深度分析报告】。
        此报告将直接输入给"趋势预测Agent"，必须信息量极高、具体详实、有理有据。

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 一、用户关注热点全景图（趋势温度计）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        按关注热度从高到低，逐一列出所有关注主题，每个主题包含：
        - 主题名称与核心描述（2-3句，精确定义）
        - 直接证据（引用具体声明原文，标注来源报告编号）
        - 信号强度：出现频次 + 跨报告一致性评估
        - 关注动机深度解析：用户为什么关注这个？是技术跃迁期？行业采纳临界点？还是风险暴露？
        - 趋势方向判断：[快速上升 / 稳定增长 / 高位震荡 / 开始分化 / 边缘化] + 判断理由

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 二、跨域演进阶段定位（用户认知视角）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        基于用户关注模式，判断该议题群当前处于哪个发展阶段，并充分论证：
        - Gartner炒作周期定位：[技术触发期 / 期望膨胀期 / 幻灭低谷期 / 启蒙爬升期 / 高原成熟期]（用于科技/研究信号）
        - 政策周期定位：[酝酿期 / 征求意见期 / 试点期 / 常态监管期]
        - 市场周期定位：[风险偏好抬升 / 交易拥挤 / 估值回归 / 基本面重估]
          论证：用哪些声明特征支持此判断？（需引用原文）
        - 技术成熟度评估（TRL 1-9）：当前处于哪个级别？依据是什么？（用于科技前沿）
        - 用户认知的"超前"与"滞后"：用户关注点是否落后于政策落地/市场定价/学术共识？
          举具体例子说明（引用原始声明）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 三、用户焦虑与期待的深层结构分析
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        深入解析用户在"期待/担忧"维度上的具体内容：

        **3.1 核心期待清单**（每条需引用原始声明，分析期待背后的行业驱动力）
        - 期待①：[具体技术能力] → 行业驱动力分析（谁在推动？为什么现在需要？）
        - 期待②：... （至少列出4条）

        **3.2 核心焦虑清单**（每条需引用原始声明，分析焦虑背后的实际风险）
        - 焦虑①：[具体问题或风险] → 风险来源分析（是技术本身的缺陷？部署复杂性？还是生态不成熟？）
        - 焦虑②：... （至少列出4条）

        **3.3 期待vs焦虑的博弈分析**
        - 用户心理中，期待与焦虑的比例如何？（基于信号数量和声明语气分析）
        - 这种博弈反映出该技术当前处于"观望期"还是"决策临界点"？
        - 哪个焦虑点一旦被解决，最可能触发大规模采纳？为什么？

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 四、跨领域渗透趋势分析
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        基于用户关注议题，分析信号在五大领域的渗透格局：
        - 已渗透领域（有具体数据/案例支撑）：新闻事件、政策框架、金融定价、研究共识、技术应用
        - 正在渗透领域（用户强烈关注但尚无定论）：分析渗透进展、主要障碍
        - 潜在渗透领域（用户隐性关注但尚未明说）：从关注模式推断，解释推断逻辑
        - 渗透顺序预测：基于用户关注先后与强度，预测跨域扩散的先后次序

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 五、趋势预测Agent行动指令（精确版）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        为趋势预测Agent提供具体可执行的分析指令：

        **指令①（最高优先级）**
        - 分析目标：[具体趋势问题，需精确到事件/政策/金融/研究/技术中的至少两类联动]
        - 数据需求：需要搜集哪些具体数据才能回答此问题？（列出5-8个具体数据点）
        - 分析方法：推荐使用哪种趋势分析方法？（S曲线/Bass扩散模型/Gartner等）为什么？
        - 预期输出：完成分析后应能得出什么结论？判断标准是什么？

        **指令②③④⑤**（同上格式，至少5条指令）
    """).strip()

    return _chain_of_thought_agent("Agent-A", system_prompt, first_pass, second_pass, max_tokens=4000)


# ──────────────────────────────────────────────
# Agent-B：内容-趋势证据深度评审师
# ──────────────────────────────────────────────

def analyze_page_info(all_page_info: list) -> str:
    """
    Agent-B：内容-趋势证据深度评审师
    核心任务：从页面内容中挖掘跨域演进的时间线证据、关键节点与里程碑
    分析视角：页面说了什么 → 这些内容如何构成跨域趋势的"证据链"
    """
    sections = []
    for item in all_page_info:
        idx = item["_report_idx"]
        pi  = item["page_info"]
        key_pts = "\n".join(f"    KP{i+1}: {p}" for i, p in enumerate(pi["key_points"])) or "    （无）"
        block = (
            f"【报告{idx} · 完整页面数据】\n"
            f"▸ 标题：{pi['title']}\n"
            f"▸ URL：{pi['url']}\n"
            f"▸ 可靠性得分：{pi['reliability_score']} | 评估说明：{pi['reliability_rationale']}\n"
            f"▸ 风险标记：{', '.join(pi['risk_flags']) or '无'}\n"
            f"▸ 生成方式：{pi['generator']} | 生成时间：{pi['generated_at']}\n"
            f"▸ 完整页面摘要：\n    {pi['page_summary']}\n"
            f"▸ 全部关键要点（{len(pi['key_points'])}条）：\n{key_pts}"
        )
        sections.append(block)

    raw_text = "\n\n" + ("─" * 50 + "\n").join(sections)

    system_prompt = textwrap.dedent("""
        你是 Agent-B：内容-趋势证据深度评审师。
        你的专业背景融合了：情报分析、政策研究、金融叙事分析、学术计量研究、科技媒体分析。

        【核心使命】
        你的任务不是评估"页面内容好不好"，而是从每个页面的内容中，
        系统性地挖掘跨域演进轨迹、关键节点、代际跃迁信号和扩散规律。
        你提供的分析将作为趋势预测Agent的"历史证据库"。

        【跨域证据类型】
        - 新闻事件证据：事件时间、影响对象、后续链式反应
        - 政策证据：草案条款方向、监管工具、执行时间窗
        - 金融证据：价格/收益率/波动率/资金流等市场信号
        - 学术证据：研究方法、样本规模、结论一致性、争议点
        - 科技证据：性能指标、能力边界、工程化进展

        【输出要求】
        - 必须从内容中提取具体的事件名称、政策方向、金融指标、研究对象、技术名称、时间节点、机构名称
        - 对每个演进节点，分析其"因果关系"：是什么驱动了这个变化？带来了什么后果？
        - 识别内容中的"代际/阶段"划分（可适用于政策、市场、研究、技术四类对象）
        - 必须区分"已发生的技术事实"与"预测/预期"，不得混为一谈
        - 提取内容中所有可量化的趋势指标（性能提升、政策覆盖范围、市场规模、资金变化、研究样本规模等）
        - 每节至少500字，充分展开，不得简略
    """).strip()

    first_pass = textwrap.dedent(f"""
        以下是 {len(all_page_info)} 个页面的完整内容数据，请完成第一阶段情报扫描：

        1. 提取所有带时间标记的关键事件（新闻/政策/市场/学术/技术）
        2. 提取所有可量化数据（性能、价格、规模、资金、样本、渗透率等）
        3. 识别被提及的主体与方案（机构、政策主体、市场参与者、研究团队、技术方案）
        4. 标记每个页面涉及的行业、区域和应用场景
        5. 识别每个页面聚焦的演进层级（事件冲击层/政策制度层/市场定价层/知识研究层/技术能力层）
        6. 列出你将在第二阶段重点展开的8个关键发现

        原始数据：
        {raw_text}
    """).strip()

    second_pass = textwrap.dedent("""
        基于第一阶段情报扫描，请生成完整的【内容·趋势证据深度评审报告】。
        此报告将作为趋势预测Agent的"原始证据库"，必须精确、具体、有数据支撑。

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 一、跨域演进时间轴重建（基于内容证据）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        从内容中提取所有时间标记的技术事件，按时间顺序排列：

        格式：[时间] → [关键事件/政策动作/市场信号/研究里程碑/技术节点] → [来源页面] → [重要性评级：★★★★★]
        要求：
        - 必须引用原始内容作为证据
        - 对每个里程碑，分析其在跨域演进中的"因果角色"（它触发了什么变化？）
        - 识别演进中的"断层点"（哪些时间段缺少数据？意味着什么？）
        - 找出内容中暗示的"即将到来的下一个里程碑"

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 二、核心跨域量化指标汇编
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        从所有页面中系统性提取全部量化数据：

        **能力/绩效指标**：
        - [指标名称]：[具体数值] vs [基准值/对比方案] = [提升幅度] | 来源：报告X | 数据可信度评估
        （至少提取8个性能指标，每个必须有原文引用）

        **成本/效率/价格指标**：
        - [指标名称]：[具体数值] | 比较对象 | 来源 | 对趋势预测的意义
        （至少提取4个）

        **规模指标**：
        - [应用规模/数据集规模等] | 来源 | 对采纳趋势的意义

        **指标趋势解读**：
        - 这些量化数据整体呈现什么趋势？（性能曲线是在加速提升？趋于平稳？还是遇到瓶颈？）
        - 哪个指标的改善最可能触发下一阶段的大规模采纳？为什么？

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 三、跨域主体生态图谱分析
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        基于内容中提及的政策主体、市场主体、研究团队与技术方案，构建生态格局分析：

        **主流主体/方案详解**（每项200字以上）：
        - 主体或方案名称 + 机构/作者 + 时间
        - 核心机制特征（政策机制/市场机制/研究方法/技术原理）
        - 已验证表现（引用具体数据）
        - 适用场景与限制条件
        - 在生态中的定位：[先驱者/主流推动者/挑战者/利基参与者]

        **方案比较矩阵**：
        | 主体/方案 | 核心机制 | 关键优势 | 局限性 | 适用场景 | 采纳/执行难度 |
        （至少列出5项，每个维度必须具体填写，不能写"N/A"或模糊描述）

        **竞争格局趋势**：
        - 当前哪个主体/方案在效果上领先？哪个在执行便利性上领先？
        - 未来12-24个月，哪个主体/方案最可能成为主流驱动？给出具体依据

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 四、场景与行业渗透深度分析（逐场景展开）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        对内容中涉及的每个应用场景，进行深度分析（每个场景至少200字）：

        **场景①：[场景名称]**
        - 当前渗透状态：[已验证/试点阶段/概念验证/理论探讨]
        - 具体应用案例：（引用原始内容中的具体案例）
        - 已有量化效果：（引用具体数据）
        - 渗透障碍分析：政策障碍/资金障碍/数据障碍/技术障碍/认知障碍
        - 渗透加速条件：什么变化会使渗透速度加快？
        - 趋势预判：未来2年在此场景的渗透率预估

        **场景②③④...** （覆盖内容中所有提及的场景）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 五、内容可信度与证据强度评级
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        为趋势预测Agent评估每类信息的可用程度：
        - A级证据（可直接用于趋势预测建模）：[列出具体内容条目]
        - B级证据（需交叉验证后可用）：[列出具体内容条目]
        - C级证据（仅供参考，不可作为预测依据）：[列出具体内容条目]
        - 证据缺口（趋势预测必需但当前完全缺失的数据）：[列出具体缺失项]
    """).strip()

    return _chain_of_thought_agent("Agent-B", system_prompt, first_pass, second_pass, max_tokens=4000)


# ──────────────────────────────────────────────
# Agent-C：事件-趋势关联推理师
# ──────────────────────────────────────────────

def analyze_related_events(all_related_events: list) -> str:
    """
    Agent-C：事件-趋势关联推理师
    核心任务：从声明核验数据中推断跨域扩散路径、行业采纳动态与知识沉淀规律
    分析视角：声明支持程度 → 政策/市场/研究/技术成熟度信号 → 趋势扩散动力学
    """
    sections = []
    for item in all_related_events:
        idx = item["_report_idx"]
        re  = item["related_events"]
        fv  = re["fast_verification"]
        qm  = re["quant_metrics"]

        def fmt_claims(claims_list, icon):
            if not claims_list:
                return "    （无）"
            lines = []
            for i, c in enumerate(claims_list):
                claim_text = c.get("claim", "")
                evidence   = c.get("evidence_from_page", "")[:200]
                lines.append(
                    f"    [{i+1}] 声明：{claim_text}\n"
                    f"         证据摘要：{evidence}..."
                )
            return "\n".join(lines)

        block = (
            f"【报告{idx} · 声明核验完整数据】\n"
            f"▸ 快速验证系统：置信度={fv['confidence_score']} | 判定={fv['verdict']} | "
            f"级别={fv['level_name']} | 描述={fv['level_desc']}\n"
            f"▸ 定量指标系统：置信度={qm['confidence_score']} | 判定={qm['verdict']} | "
            f"支持率={qm['support_ratio']} | 焦点覆盖={qm['focus_coverage']} | "
            f"相关对齐={qm['relevance_alignment']} | 级别={qm['level_name']}\n"
            f"\n▸ ✅ 已支持声明 [{len(re['claim_checks_supported'])}条]（含证据）：\n"
            + fmt_claims(re["claim_checks_supported"], "✅") + "\n"
            f"\n▸ ⚠️ 部分支持声明 [{len(re['claim_checks_partially_supported'])}条]（含证据）：\n"
            + fmt_claims(re["claim_checks_partially_supported"], "⚠️") + "\n"
            f"\n▸ ❓ 不明确声明 [{len(re['claim_checks_unclear'])}条]（含证据）：\n"
            + fmt_claims(re["claim_checks_unclear"], "❓")
        )
        sections.append(block)

    raw_text = "\n\n" + ("─" * 50 + "\n").join(sections)

    system_prompt = textwrap.dedent("""
        你是 Agent-C：事件-趋势关联推理师。
        你的专业背景融合了：扩散理论（Rogers创新扩散模型）、政策分析、金融市场微观结构、知识图谱演进、复杂系统动力学。

        【核心使命】
        你的任务不是"核查事实"，而是把声明的支持状态（supported/partially_supported/unclear）
        解读为跨域成熟度信号和趋势扩散动力学的量化指标。

        关键洞见框架：
        - 已支持声明（supported）= 已沉淀为"可执行共识"的事实 → 扩散已进入主流阶段
        - 部分支持声明（partially_supported）= 政策、市场、研究或技术边界的争议地带 → 摩擦点与加速机会并存
        - 不明确声明（unclear）= 信息前沿区域 → 可能是突破方向，也可能是误导性叙事

        双系统评分的趋势意义：
        - 快速验证分数（fast_verification.confidence_score）= 信息对齐当前用户关注的程度
        - 定量指标分数（quant_metrics.confidence_score）= 内容与话题的客观关联程度
        - 两者之差 = "炒作/低估系数"，正值表示用户关注超越内容证据，负值表示潜在价值被低估

        【输出要求】
        - 从扩散动力学角度解读每一类声明，不做简单的"真/假"判断
        - 必须引用具体声明内容作为推断依据
        - 提供可量化的趋势预测结论（如：当前处于Rogers扩散曲线的哪个阶段？）
        - 每节至少500字，充分展开，不得简略
    """).strip()

    first_pass = textwrap.dedent(f"""
        请对以下声明核验数据进行第一阶段趋势信号扫描：

        1. 计算每个报告的"共识沉淀率"（supported声明数 / 总声明数），绘制各报告的成熟度对比
        2. 计算每个报告的"炒作/低估系数"（fast_verification分数 - quant_metrics分数），识别信息价值被高估或低估的内容
        3. 从所有"supported"声明中，提取能直接证明跨域扩散已发生的具体内容（必须引用原文）
        4. 从所有"partially_supported"声明中，识别扩散的主要摩擦点（政策壁垒/资金壁垒/认知壁垒/数据壁垒/技术壁垒）
        5. 从所有"unclear"声明中，识别哪些可能代表下一阶段突破方向或叙事误导
        6. 识别跨报告中重复出现的声明（一致性=扩散共识形成的信号）
        7. 列出你将在第二阶段重点展开的6个关键趋势推断

        原始数据：
        {raw_text}
    """).strip()

    second_pass = textwrap.dedent("""
        基于第一阶段信号扫描，请生成完整的【事件·趋势关联推理报告】。
        此报告将直接输入趋势预测Agent作为"扩散动力学分析基础"。

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 一、跨域扩散路径推断（基于声明支持模式）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        运用Rogers创新扩散模型（创新者→早期采用者→早期大众→晚期大众→落后者），
        基于各类声明的支持状态，推断当前议题群处于哪个扩散阶段：

        **当前扩散阶段判定**：
        - 综合所有报告的共识沉淀率（计算具体数值）
        - 哪类用户群体正在成为"早期大众"的进入点？
        - 扩散的主要驱动力（引用具体supported声明作为证据）
        - 扩散的主要阻力（引用具体partially_supported/unclear声明作为证据）
        - 下一扩散跃迁的触发条件（具体描述，不能含糊）

        **扩散路径地图**：
        - 已完成扩散的领域/群体：[具体描述，引用证据]
        - 正在进行扩散的领域/群体：[具体描述，引用证据]
        - 尚未开始扩散的潜在领域：[具体描述，推断依据]

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 二、行业与市场采纳信号深度解读
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        对声明中涉及的行业/场景/政策窗口/市场反应的采纳信号进行深度解读：

        **强采纳信号（supported声明中的行业应用）**：
        对每个具体案例：
        - 原始声明（完整引用）
        - 采纳规模估计（引用具体数据：覆盖人数/机构数量/资金规模/价格波动幅度等）
        - 采纳驱动分析：为什么是这个行业率先采纳？
        - 示范效应预测：这个早期案例会在12个月内带动哪些跟随者？

        **弱采纳信号（partially_supported中的行业苗头）**：
        - 原始声明（完整引用）
        - 当前不完全支持的原因（政策原因/技术原因/数据原因/商业原因？）
        - 转化为强信号的条件：需要满足什么条件？
        - 时间预测：可能在何时转化为强信号？

        **炒作信号识别（fast_verification远高于quant_metrics的内容）**：
        - 哪些声明的实际技术支撑远弱于其被讨论的热度？
        - 炒作可能导致的风险（对趋势预测模型的污染风险）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 三、知识与制度沉淀度分析（成熟度动力学）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        **已沉淀为共识的知识（可用于稳定预测建模）**：
        - 列出所有"settled knowledge"（高支持率+跨页面一致的声明）
        - 为什么这些已经成为共识？（制度共识/市场验证/实验验证/产业实践）
        - 这些共识知识对趋势预测的价值：是技术演进的"已知基础"

        **仍在争议边界的知识（趋势的活跃前沿）**：
        - 哪些政策/市场/研究/技术声明在多个报告中持续出现"partial"状态？
        - 争议的本质是什么？（实验结果差异/应用场景差异/评估标准差异）
        - 争议解决的时间预测及解决后对趋势的影响

        **知识真空区（unclear声明揭示的盲区）**：
        - 哪些重要问题目前没有足够证据？
        - 这些知识真空是趋势预测的最大不确定性来源
        - 填补这些真空所需的数据类型和来源建议

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 四、风险-采纳动态模型
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        构建一个"风险-采纳"动态分析框架：

        **系统性风险识别**（基于partially_supported和unclear声明）：
        - 政策风险：[具体描述，引用声明证据]
        - 金融风险：[具体描述，引用声明证据]
        - 技术风险：[具体描述，引用声明证据]
        - 应用风险：[具体描述，引用声明证据]
        - 市场炒作风险：[具体描述，引用双系统评分差异]

        **风险缓解路径**：
        - 哪些风险的缓解会直接加速技术采纳？
        - 哪些风险如果未能缓解，会导致技术停滞或回调？
        - 风险缓解的时间轴预测

        **采纳拐点预测**：
        - 基于当前声明支持模式，技术采纳可能在什么条件下出现"拐点加速"？
        - 需要观察哪些"领先指标"来预判拐点的到来？

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ### 五、趋势预测Agent核查指令
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        给趋势预测Agent的5条精确指令：
        每条指令格式：
        【指令N】分析目标：___
        ▸ 所用证据来源：引用本报告哪些具体发现
        ▸ 建议分析方法：（扩散曲线拟合/Bass扩散模型/情景分析/德尔菲法等）
        ▸ 所需外部数据：（5-8个具体数据项，附推荐获取渠道）
        ▸ 预期输出形式：（定量预测/情景矩阵/时间轴/概率分布等）
        ▸ 置信度约束：基于当前证据，该预测的可信度上限是多少？为什么？
    """).strip()

    return _chain_of_thought_agent("Agent-C", system_prompt, first_pass, second_pass, max_tokens=4000)


# ═══════════════════════════════════════════════
# STEP 3：Agent-D 整合 → 趋势战略指导 TXT
# ═══════════════════════════════════════════════

def synthesize_agent_guide(
    keyword: str,
    report_count: int,
    generated_at: str,
    focus_analysis: str,
    page_analysis: str,
    event_analysis: str,
) -> str:
    """
    Agent-D：首席趋势战略整合师
    职责：整合三份趋势分析报告，生成供趋势预测Agent直接使用的战略情报文档
    策略：趋势信号汇聚 → 预测议题矩阵 → 数据资产盘点 → 执行路线图
    """
    combined = (
        "=" * 60 + "\n【Agent-A 输出：用户焦点·趋势信号解析】\n" + "=" * 60 + "\n"
        + focus_analysis + "\n\n"
        + "=" * 60 + "\n【Agent-B 输出：内容·趋势证据评审】\n" + "=" * 60 + "\n"
        + page_analysis + "\n\n"
        + "=" * 60 + "\n【Agent-C 输出：事件·趋势关联推理】\n" + "=" * 60 + "\n"
        + event_analysis
    )

    system_prompt = textwrap.dedent("""
        你是 Agent-D：首席趋势战略整合师，拥有技术预见学（Technology Foresight）、
        战略情报、预测分析与决策科学的顶级背景。
        你曾为麦肯锡全球研究院、Gartner 趋势研究、MIT Technology Review 提供战略整合服务。

        【核心使命】
        将 Agent-A（用户焦点·趋势信号）、Agent-B（内容·趋势证据）、Agent-C（事件·趋势扩散）
        三份深度报告整合为一份"趋势预测战略情报文档"。

        该文档是后续趋势预测Agent的"最高指令"，必须达到：
        - 趋势判断有证据支撑：每个趋势结论都必须引用三份报告中的具体内容
        - 可量化的预测基础：提供趋势预测模型可直接使用的参数与数据
        - 议题优先级清晰：哪个趋势最值得深入分析，原因充分
        - 执行路线图可操作：具体到Agent执行哪些动作、用什么方法

        【跨域整合范围】
        你必须统一整合五类信号：突发新闻、政策草案、金融信号、学术研究、科技前沿。
        你必须识别跨域联动链：事件冲击 → 政策响应 → 市场定价 → 学术/技术调整 → 新一轮事件。

        【整合原则】
        - 当三份报告从不同角度共同指向同一趋势时 → 提升趋势信号强度等级
        - 当三份报告存在矛盾时 → 分析矛盾本身的趋势含义（矛盾有时是转折点的信号）
        - 从三份报告的交叉中提炼"涌现趋势洞察"（任何单一报告都无法看到的模式）
        - 对每个趋势结论，必须给出明确的置信度（高/中/低）和置信度边界
        - 不得使用"可能""也许""大概"等模糊表述，用"预计""预测""基于X证据判断"替代
    """).strip()

    first_pass = textwrap.dedent(f"""
        搜索关键词：{keyword} | 报告数量：{report_count} | 数据时间：{generated_at}

        请进行第一阶段趋势战略摘要：

        1. 从 Agent-A 报告中提取：最强的3个趋势信号 + 跨域周期定位判断 + 最关键的用户行动指令
        2. 从 Agent-B 报告中提取：最重要的3个跨域演进证据 + 最关键的量化指标 + 最可信的案例
        3. 从 Agent-C 报告中提取：扩散阶段判定结论 + 最强的行业/市场采纳信号 + 主要扩散阻力
        4. 识别三份报告相互印证的"共识趋势"（多角度共同支持的结论）
        5. 识别三份报告中的"矛盾信号"（不同角度得出不同结论的地方）
        6. 提炼只有三份报告整合才能发现的"涌现趋势洞察"（至少3个）
        7. 列出你将在最终报告中重点呈现的趋势预测议题（至少8个）

        三份 Agent 报告全文：
        {combined}
    """).strip()

    second_pass = textwrap.dedent("""
        基于第一阶段趋势战略摘要，请生成完整的【趋势预测战略情报文档】。
        每节必须充实详尽，不得使用模糊表述，所有结论必须引用三份报告的具体内容。

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 一、跨域趋势总裁决（整合三份报告的最终判定）
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        **趋势总体判定**：
        - 当前议题群所处的发展阶段（Gartner周期 + Rogers扩散阶段 + 政策周期 + 市场周期 + TRL评级的综合判定）
        - 整合置信度：高/中/低 | 置信度边界：XX%-XX%范围内
        - 支撑本判定的三份报告关键证据（分别引用A/B/C的具体发现）

        **三维趋势信号汇聚分析**：
        - 用户焦点维度（A）的趋势温度：（引用Agent-A的具体结论）
        - 内容证据维度（B）的趋势温度：（引用Agent-B的具体结论）
        - 扩散动态维度（C）的趋势温度：（引用Agent-C的具体结论）
        - 三维汇聚后的综合趋势判定：（综合分析，给出量化结论）
        - 跨域联动链条：（突发新闻→政策→金融→学术→科技）如何闭环演化

        **涌现趋势洞察**（至少3个，每个至少200字）：
        - 洞察①：（只有整合三份报告才能发现的规律，充分展开）
        - 洞察②：（同上）
        - 洞察③：（同上）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 二、趋势预测议题优先级矩阵
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        按"趋势确定性 × 商业/社会影响力"四象限排列趋势预测议题：

        **高确定性 × 高影响力（核心预测议题）**：
        对每个议题（至少3个）：
        - 议题名称与详细描述（200字以上）
        - 证据基础：来自A/B/C三份报告的具体支撑
        - 趋势时间轴预测：短期（6个月内）/ 中期（6-18个月）/ 长期（18个月以上）的发展预判
        - 关键观测指标：什么数据可以验证这个趋势预测？
        - 预测风险：什么因素可能导致预测失准？

        **高确定性 × 中等影响力（重要监测议题）**：
        （至少2个，每个100字以上）

        **中等确定性 × 高影响力（高价值研究议题）**：
        （至少2个，每个100字以上）

        **低确定性但高潜力（前沿探索议题）**：
        （至少2个，每个100字以上）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 三、可用于趋势建模的数据资产盘点
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        系统盘点三份报告中所有可直接用于趋势预测建模的数据：

        **量化时间序列数据**（可用于趋势曲线拟合）：
        | 数据项 | 数值 | 时间点 | 来源 | 可信度 | 适用趋势模型 |
        （提取所有带具体数字和时间的数据点）

        **政策与制度数据**（可用于情景约束建模）：
        - 政策草案关键条款与生效窗口
        - 监管强度变化与覆盖范围

        **金融先行指标数据**（可用于市场预警建模）：
        - 价格/波动率/成交量/资金净流向等指标
        - 与事件或政策节点的时间对齐关系

        **技术能力边界数据**（可用于S曲线分析）：
        - 当前性能最优值：[指标=数值，来源，时间]
        - 历史性能节点：[时间→数值，来源]
        - 理论极限估计：[来自哪份报告的推断]

        **采纳规模数据**（可用于Bass扩散模型）：
        - 当前已知采纳者规模：[数据，来源]
        - 早期采用者特征：[具体描述]
        - 潜在市场规模估计：[来源]

        **竞争态势数据**（可用于市场份额预测）：
        - 主要方案的相对性能对比数据
        - 机构采纳意向数据

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 四、趋势预测所需补充数据清单
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        为每类缺失数据提供详细说明：

        **关键缺失数据（影响核心预测，必须补充）**：
        对每项缺失数据（至少5项）：
        - 数据名称与详细描述
        - 为什么这是关键数据（对哪类趋势预测的影响）
        - 推荐获取渠道（具体来源：论文/数据库/机构报告/API等）
        - 获取难度评估（容易/中等/困难）
        - 替代方案（如果无法直接获取，有什么代理指标？）

        **重要补充数据（有助于提升预测精度）**：
        （至少3项，每项100字以上）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 五、推荐的趋势预测模型与方法
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        针对不同趋势议题，推荐具体的预测方法：

        **议题1 → [推荐方法]**：
        - 方法名称（如：Bass扩散模型/Logistic增长模型/德尔菲法/情景分析）
        - 选择理由（为什么这个方法适合这个议题）
        - 所需数据输入（具体到参数名称）
        - 预期输出格式（时间序列预测/概率分布/情景矩阵等）
        - 方法局限性与不确定性来源

        （覆盖至少4个核心议题的预测方法推荐）

        **综合预测方法建议**：
        - 当前数据条件下最合适的总体预测框架
        - 多方法集成策略（如何结合多种方法提升预测可靠性）
        - 预测结果校验方案（如何验证预测质量）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 六、趋势预测Agent执行路线图
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        按阶段给出清晰的执行指令：

        **阶段一：数据补充与验证（优先执行，建议1-3天）**
        - 任务①：[具体描述] → 预期成果：[具体可验证的输出]
        - 任务②：[具体描述] → 预期成果：[具体可验证的输出]
        - 任务③：[具体描述] → 预期成果：[具体可验证的输出]

        **阶段二：趋势模型构建（核心执行，建议3-7天）**
        - 任务①：[具体描述] → 预期成果：[具体可验证的输出]
        - 任务②：[具体描述] → 预期成果：[具体可验证的输出]
        - 任务③：[具体描述] → 预期成果：[具体可验证的输出]

        **阶段三：预测输出与验证（收尾执行，建议2-3天）**
        - 任务①：[具体描述] → 预期成果：[具体可验证的输出]
        - 任务②：[具体描述] → 预期成果：[具体可验证的输出]

        **搜索查询策略**（供数据补充阶段使用）：
        - 中文精确搜索词（10条，需覆盖事件、政策、金融、学术、科技五类）
        - 英文学术/市场搜索词（10条，包含AND/OR逻辑组合）
        - 推荐数据来源（新闻数据库/政府公报/交易所数据/ArXiv/IEEE/GitHub/行业报告/专利数据库）

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ## 七、核心趋势假设与可证伪检验方案
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        为趋势预测建立严格的科学检验框架：

        **核心趋势假设清单**（每条假设100字以上）：
        - 假设H1：[明确陈述假设内容，引用证据支撑]
          → 支撑证据：[具体引用]
          → 可证伪条件：[什么情况下这个假设被证伪？]
          → 观测指标：[监测哪些数据来检验？]
          → 检验时间窗口：[多久后可以验证？]

        - 假设H2：（同上格式）
        - 假设H3：（同上格式）
        - 假设H4：（同上格式）
        - 假设H5：（同上格式）

        **反趋势风险预警**：
        - 哪些信号出现时，意味着当前趋势判断需要重大修正？
        - 对趋势预测模型的影响评估
        - 应急响应策略：检测到反转信号时，趋势预测Agent应如何调整？
        - 突发新闻与政策急转弯场景：给出快速重估流程（T+0、T+1、T+7）
    """).strip()

    return _chain_of_thought_agent("Agent-D", system_prompt, first_pass, second_pass, max_tokens=5000)


# ═══════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════

def run_pipeline(json_path: str, output_dir: str = "output") -> str:
    """
    完整 Pipeline：JSON → 提取 → Multi-Agent 趋势分析 → 整合 → 输出 TXT
    返回输出文件路径
    """
    print("=" * 60)
    print("📂  STEP 1：读取 JSON 并结构化提取三个维度")
    print("=" * 60)

    extracted_list, raw_data = load_and_extract(json_path)
    keyword       = raw_data.get("keyword", "未知")
    report_count  = raw_data.get("report_count", len(extracted_list))
    generated_at  = raw_data.get("generated_at", "未知")

    print(f"✅  成功加载 {len(extracted_list)} 条报告 | 关键词：{keyword}")

    # 为每条提取结果注入 report_idx，方便 LLM 函数使用
    all_user_focus     = [{"_report_idx": e["report_idx"], "user_focus":     e["user_focus"]}     for e in extracted_list]
    all_page_info      = [{"_report_idx": e["report_idx"], "page_info":      e["page_info"]}      for e in extracted_list]
    all_related_events = [{"_report_idx": e["report_idx"], "related_events": e["related_events"]} for e in extracted_list]

    print("\n" + "=" * 60)
    print("🤖  STEP 2：Multi-Agent 趋势协作分析（模型：gpt-4o）")
    print("=" * 60)

    focus_analysis = _run_with_spinner(
        "Agent-A [用户焦点·趋势信号解析师] 两阶段趋势信号解析",
        analyze_user_focus, all_user_focus
    )

    page_analysis = _run_with_spinner(
        "Agent-B [内容·趋势证据评审师]   技术演进证据挖掘   ",
        analyze_page_info, all_page_info
    )

    event_analysis = _run_with_spinner(
        "Agent-C [事件·趋势关联推理师]   扩散动力学推断     ",
        analyze_related_events, all_related_events
    )

    print("\n" + "=" * 60)
    print("🧭  STEP 3：Agent-D [首席趋势战略整合师] 整合三份报告 → 生成趋势预测战略文档")
    print("=" * 60)

    agent_guide = _run_with_spinner(
        "Agent-D [首席趋势战略整合师]    跨域战略整合       ",
        synthesize_agent_guide,
        keyword, report_count, generated_at,
        focus_analysis, page_analysis, event_analysis
    )

    # ── 拼装最终 Markdown ─────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"agent_guide_{timestamp}.md"

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    content_parts = [
        "# 趋势预测 Agent 导引文档（Multi-Agent 趋势分析协作版）",
        "",
        "## 文档信息",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 来源文件：`{os.path.basename(json_path)}`",
        f"- 搜索关键词：`{keyword}`",
        f"- 报告数量：`{report_count}`",
        "- 分析模型：`gpt-4o`",
        "- 架构：`Agent-A/B/C 趋势链式分析 + Agent-D 战略整合`",
        "",
        "## Agent-A 输出：用户焦点·趋势信号解析（趋势温度计 + 演进阶段定位）",
        "",
        focus_analysis,
        "",
        "## Agent-B 输出：内容·趋势证据评审（技术演进时间轴 + 量化指标汇编）",
        "",
        page_analysis,
        "",
        "## Agent-C 输出：事件·趋势关联推理（扩散路径 + 采纳动力学分析）",
        "",
        event_analysis,
        "",
        "## Agent-D 输出：趋势预测战略指导文档（首席趋势战略整合师）",
        "",
        agent_guide,
        "",
        "---",
        f"_文档结束：共处理 {report_count} 份报告，由 4 个专职趋势分析 Agent 协作完成。_",
    ]

    final_content = "\n".join(content_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"\n🎉  输出文件已保存：{output_path}")
    print("\n" + "─" * 60)
    print("【预览：趋势预测导引前500字】")
    print("─" * 60)
    print(agent_guide[:500] + "..." if len(agent_guide) > 500 else agent_guide)

    return output_path


# ═══════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    # ── 在这里指定要处理的 JSON 文件路径 ──────────────────
    # test_data/summary_report_20260312_155641.json
    INPUT_JSON = "test_data/summary_report_20260312_155641.json"
    # ────────────────────────────────────────────────────

    output_file = run_pipeline(INPUT_JSON, output_dir="output")
    print(f"\n✅  Pipeline 完成，输出文件：{output_file}")