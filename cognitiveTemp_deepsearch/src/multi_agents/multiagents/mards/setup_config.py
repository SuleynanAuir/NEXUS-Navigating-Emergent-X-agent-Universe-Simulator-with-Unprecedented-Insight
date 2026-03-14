#!/usr/bin/env python3
"""
MARDS 配置助手
帮助用户快速配置 API 密钥
"""

import os
from pathlib import Path


def main():
    print("=" * 60)
    print("MARDS 配置助手")
    print("=" * 60)
    print()
    
    env_path = Path(__file__).parent / ".env"
    
    # 读取现有配置
    existing_config = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    existing_config[key.strip()] = value.strip()
    
    # DeepSeek API Key
    print("📌 DeepSeek API 配置")
    print("   获取地址: https://platform.deepseek.com/api_keys")
    current_deepseek = existing_config.get("DEEPSEEK_API_KEY", "")
    if current_deepseek and current_deepseek != "your_deepseek_api_key_here":
        print(f"   当前值: {current_deepseek[:10]}...")
        deepseek_key = input("   新密钥 (留空保持不变): ").strip()
        if not deepseek_key:
            deepseek_key = current_deepseek
    else:
        deepseek_key = input("   请输入 DeepSeek API Key: ").strip()
    
    print()
    
    # Tavily API Key
    print("📌 Tavily API 配置")
    print("   获取地址: https://app.tavily.com/")
    current_tavily = existing_config.get("TAVILY_API_KEY", "")
    if current_tavily and current_tavily != "your_tavily_api_key_here":
        print(f"   当前值: {current_tavily[:10]}...")
        tavily_key = input("   新密钥 (留空保持不变): ").strip()
        if not tavily_key:
            tavily_key = current_tavily
    else:
        tavily_key = input("   请输入 Tavily API Key: ").strip()
    
    print()
    
    # 验证输入
    if not deepseek_key or deepseek_key == "your_deepseek_api_key_here":
        print("❌ 错误: DeepSeek API Key 不能为空")
        return
    
    if not tavily_key or tavily_key == "your_tavily_api_key_here":
        print("❌ 错误: Tavily API Key 不能为空")
        return
    
    # 写入配置文件
    config_content = f"""# MARDS API Configuration
# 由配置助手自动生成于 {os.popen('date').read().strip()}

# DeepSeek API 配置
DEEPSEEK_API_KEY={deepseek_key}

# Tavily API 配置  
TAVILY_API_KEY={tavily_key}

# 可选配置（取消注释以覆盖默认值）
# DEEPSEEK_BASE_URL=https://api.deepseek.com/v1/chat/completions
# DEEPSEEK_MODEL=deepseek-chat
# LOG_LEVEL=INFO
# REQUEST_TIMEOUT=30
# MAX_RETRIES=3
"""
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("✅ 配置已保存到 .env 文件")
    print()
    print("下一步:")
    print("  python main.py --query \"你的研究问题\" --debate")
    print()


if __name__ == "__main__":
    main()
