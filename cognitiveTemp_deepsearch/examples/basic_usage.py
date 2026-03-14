"""
基本使用示例
演示如何使用Deep Search Agent进行基本的深度搜索
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import DeepSearchAgent, load_config
from src.utils.config import print_config


def basic_example():
    """基本使用示例"""
    print("=" * 60)
    print("Deep Search Agent - 基本使用示例")
    print("=" * 60)
    
    try:
        # 加载配置
        print("正在加载配置...")
        config = load_config()
        print_config(config)
        
        # 创建Agent
        print("正在初始化Agent...")
        agent = DeepSearchAgent(config)
        
        # 执行研究
        query = "2025年人工智能发展趋势"
        print(f"开始研究: {query}")
        
        final_report = agent.research(query, save_report=True)
        
        # 显示结果
        print("\n" + "=" * 60)
        print("研究完成！最终报告预览:")
        print("=" * 60)
        print(final_report[:500] + "..." if len(final_report) > 500 else final_report)
        
        # 显示进度信息
        progress = agent.get_progress_summary()
        print(f"\n进度信息:")
        print(f"- 总段落数: {progress['total_paragraphs']}")
        print(f"- 已完成段落: {progress['completed_paragraphs']}")
        print(f"- 完成进度: {progress['progress_percentage']:.1f}%")
        print(f"- 是否完成: {progress['is_completed']}")
        
    except Exception as e:
        print(f"示例运行失败: {str(e)}")
        print("请检查：")
        print("1. 是否安装了所有依赖：pip install -r requirements.txt")
        print("2. 是否设置了必要的API密钥")
        print("3. 网络连接是否正常")
        print("4. 配置文件是否正确")


if __name__ == "__main__":
    basic_example()
