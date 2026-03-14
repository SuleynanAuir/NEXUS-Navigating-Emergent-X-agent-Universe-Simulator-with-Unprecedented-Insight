"""
集成指标可视化到Streamlit应用
"""

def create_research_metrics_section(agent, language="ZH"):
    """
    创建Research Metrics可视化部分
    
    在streamlit_app.py的display_results函数中添加:
    
    metrics_html = create_research_metrics_section(agent, st.session_state.language)
    st.markdown(metrics_html, unsafe_allow_html=True)
    """
    
    from src.visualization import MetricsVisualizer
    
    # 检查是否有metrics数据
    if not hasattr(agent, 'metrics_collector') or agent.metrics_collector is None:
        return """
        <div style="padding: 2rem; background: #f0f0f0; border-radius: 10px; text-align: center;">
            <p>📊 No metrics data available</p>
        </div>
        """
    
    # 完成指标收集
    agent.metrics_collector.metrics.total_sections = len(agent.state.paragraphs)
    agent.metrics_collector.metrics.total_sources = sum(
        len(p.research.search_history) for p in agent.state.paragraphs
    )
    agent.metrics_collector.metrics.total_reflections = sum(
        p.research.reflection_iteration for p in agent.state.paragraphs
    )
    
    agent.metrics_collector.finalize()
    
    # 生成HTML
    visualizer = MetricsVisualizer()
    html = visualizer.generate_html_dashboard(
        agent.metrics_collector.metrics,
        language=language
    )
    
    return html


def integrate_metrics_to_agent(agent_class):
    """
    装饰器: 为Agent类添加指标收集能力
    
    用法:
    @integrate_metrics_to_agent
    class DeepSearchAgent:
        ...
    """
    from src.visualization import MetricsCollector
    
    original_init = agent_class.__init__
    
    def new_init(self, config):
        original_init(self, config)
        self.metrics_collector = MetricsCollector()
        self.metrics_collector.metrics.query = config.query if hasattr(config, 'query') else ""
    
    agent_class.__init__ = new_init
    return agent_class


# 在streamlit_app.py中使用的代码示例

STREAMLIT_INTEGRATION_CODE = """
# 在streamlit_app.py的显示结果部分添加

def display_results_with_metrics(agent, final_report):
    '''显示结果并包含指标仪表板'''
    import streamlit as st
    from src.visualization import MetricsVisualizer
    
    # 显示最终报告
    st.markdown(final_report)
    
    # 显示Research Metrics
    st.markdown("---")
    st.markdown("## 📊 Research Metrics")
    
    if hasattr(agent, 'metrics_collector') and agent.metrics_collector:
        # 更新最终统计
        agent.metrics_collector.metrics.total_sections = len(agent.state.paragraphs)
        agent.metrics_collector.metrics.total_sources = sum(
            len(p.research.search_history) for p in agent.state.paragraphs
        )
        agent.metrics_collector.metrics.total_reflections = sum(
            p.research.reflection_iteration for p in agent.state.paragraphs
        )
        
        agent.metrics_collector.finalize()
        
        # 生成可视化
        visualizer = MetricsVisualizer()
        metrics_html = visualizer.generate_html_dashboard(
            agent.metrics_collector.metrics,
            language=st.session_state.get("language", "ZH")
        )
        
        st.markdown(metrics_html, unsafe_allow_html=True)
    else:
        st.info("⚠️ Metrics data not available")


# 在agent初始化时添加指标收集器

def init_agent_with_metrics(config):
    '''创建支持指标收集的Agent'''
    from src.agent import DeepSearchAgent
    from src.visualization import MetricsCollector
    
    agent = DeepSearchAgent(config)
    agent.metrics_collector = MetricsCollector()
    agent.metrics_collector.metrics.query = config.query if hasattr(config, 'query') else ""
    
    return agent
"""

# 修改agent.py的建议代码

AGENT_MODIFICATION_CODE = """
# 在src/agent.py中的_generate_report_structure方法中添加:

def _generate_report_structure(self, query: str):
    '''生成报告结构'''
    if hasattr(self, 'metrics_collector'):
        self.metrics_collector.start_timer("report_structure")
    
    print(f"\\n[步骤 1] 生成报告结构...")
    
    # ... 原有代码 ...
    
    if hasattr(self, 'metrics_collector'):
        self.metrics_collector.end_timer("report_structure")


# 在_initial_search_and_summary方法中添加token记录:

def _initial_search_and_summary(self, index: int):
    '''执行初始搜索和总结'''
    if hasattr(self, 'metrics_collector'):
        self.metrics_collector.start_timer(f"search_paragraph_{index}")
    
    # ... 搜索代码 ...
    
    # 记录token使用
    if hasattr(self, 'metrics_collector'):
        # 假设LLM响应包含usage信息
        self.metrics_collector.add_token_usage(
            model=self.config.default_llm_provider,
            prompt_tokens=prompt_tokens,  # 从LLM响应获取
            completion_tokens=completion_tokens,  # 从LLM响应获取
            cost_usd=estimated_cost  # 计算或从LLM返回
        )
        self.metrics_collector.end_timer(f"search_paragraph_{index}")
"""

# 计算Token成本的辅助函数

TOKEN_COST_CALCULATOR = """
# 创建新文件: src/visualization/token_pricing.py

PRICING_MODELS = {
    "deepseek": {
        "chat": {
            "input_price": 0.14 / 1000000,  # 每个token的价格（美元）
            "output_price": 0.28 / 1000000,
        }
    },
    "openai": {
        "gpt-4o-mini": {
            "input_price": 0.15 / 1000000,
            "output_price": 0.60 / 1000000,
        },
        "gpt-4o": {
            "input_price": 5.00 / 1000000,
            "output_price": 15.00 / 1000000,
        }
    }
}

def calculate_token_cost(model: str, model_variant: str, 
                        prompt_tokens: int, completion_tokens: int) -> float:
    '''计算Token成本（美元）'''
    if model not in PRICING_MODELS:
        return 0.0
    
    pricing = PRICING_MODELS[model].get(model_variant, {})
    if not pricing:
        return 0.0
    
    input_cost = prompt_tokens * pricing.get("input_price", 0)
    output_cost = completion_tokens * pricing.get("output_price", 0)
    
    return input_cost + output_cost
"""
