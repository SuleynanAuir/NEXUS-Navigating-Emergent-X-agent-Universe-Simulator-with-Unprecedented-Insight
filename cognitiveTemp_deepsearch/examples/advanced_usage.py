"""
高级使用示例
演示Deep Search Agent的高级功能
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import DeepSearchAgent, Config
from src.utils.config import print_config


def advanced_example():
    """高级使用示例"""
    print("=" * 60)
    print("Deep Search Agent - 高级使用示例")
    print("=" * 60)
    
    try:
        # 自定义配置
        print("正在创建自定义配置...")
        config = Config(
            # 使用OpenAI而不是DeepSeek
            default_llm_provider="openai",
            openai_model="gpt-4o-mini",
            # 自定义搜索参数
            max_search_results=5,  # 更多搜索结果
            max_reflections=3,     # 更多反思次数
            max_content_length=15000,
            # 自定义输出
            output_dir="custom_reports",
            save_intermediate_states=True
        )
        
        # 从环境变量设置API密钥
        config.openai_api_key = os.getenv("OPENAI_API_KEY")
        config.tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not config.validate():
            print("配置验证失败，请检查API密钥设置")
            return
        
        print_config(config)
        
        # 创建Agent
        print("正在初始化Agent...")
        agent = DeepSearchAgent(config)
        
        # 执行多个研究任务
        queries = [
            "深度学习在医疗领域的应用",
            "区块链技术的最新发展",
            "可持续能源技术趋势"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*60}")
            print(f"执行研究任务 {i}/{len(queries)}: {query}")
            print(f"{'='*60}")
            
            try:
                # 执行研究
                final_report = agent.research(query, save_report=True)
                
                # 保存状态（示例）
                state_file = f"custom_reports/state_task_{i}.json"
                agent.save_state(state_file)
                
                print(f"任务 {i} 完成")
                print(f"报告长度: {len(final_report)} 字符")
                
                # 显示进度
                progress = agent.get_progress_summary()
                print(f"完成进度: {progress['progress_percentage']:.1f}%")
                
            except Exception as e:
                print(f"任务 {i} 失败: {str(e)}")
                continue
        
        print(f"\n{'='*60}")
        print("所有研究任务完成！")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"高级示例运行失败: {str(e)}")


def state_management_example():
    """状态管理示例"""
    print("\n" + "=" * 60)
    print("状态管理示例")
    print("=" * 60)
    
    try:
        # 创建配置
        config = Config.from_env()
        if not config.validate():
            print("配置验证失败")
            return
        
        # 创建Agent
        agent = DeepSearchAgent(config)
        
        query = "量子计算的发展现状"
        print(f"开始研究: {query}")
        
        # 执行研究
        final_report = agent.research(query)
        
        # 保存状态
        state_file = "custom_reports/quantum_computing_state.json"
        agent.save_state(state_file)
        print(f"状态已保存到: {state_file}")
        
        # 创建新的Agent并加载状态
        print("\n创建新Agent并加载状态...")
        new_agent = DeepSearchAgent(config)
        new_agent.load_state(state_file)
        
        # 检查加载的状态
        progress = new_agent.get_progress_summary()
        print("加载的状态信息:")
        print(f"- 查询: {new_agent.state.query}")
        print(f"- 报告标题: {new_agent.state.report_title}")
        print(f"- 段落数: {progress['total_paragraphs']}")
        print(f"- 完成状态: {progress['is_completed']}")
        
    except Exception as e:
        print(f"状态管理示例失败: {str(e)}")


if __name__ == "__main__":
    advanced_example()
    state_management_example()
