#!/usr/bin/env python3
"""
MARDS 系统检查工具
验证所有依赖和配置是否正确
"""

import sys
from pathlib import Path


def check_dependencies():
    """检查依赖包"""
    print("📦 检查依赖包...")
    required = ["aiohttp", "pydantic", "pydantic_settings", "dotenv"]
    missing = []
    
    for pkg in required:
        try:
            if pkg == "dotenv":
                __import__("dotenv")
            else:
                __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} - 未安装")
            missing.append(pkg)
    
    if missing:
        print(f"\n⚠️  缺少依赖: {', '.join(missing)}")
        print("运行: pip install -r requirements.txt")
        return False
    return True


def check_config():
    """检查配置文件"""
    print("\n⚙️  检查配置...")
    
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("  ❌ .env 文件不存在")
        print("  运行: python setup_config.py")
        return False
    
    print("  ✅ .env 文件存在")
    
    try:
        from config import settings
        
        # 检查 DeepSeek API Key
        if not settings.deepseek_api_key or settings.deepseek_api_key == "your_deepseek_api_key_here":
            print("  ❌ DeepSeek API Key 未配置")
            return False
        print(f"  ✅ DeepSeek API Key: {settings.deepseek_api_key[:10]}...")
        
        # 检查 Tavily API Key
        if not settings.tavily_api_key or settings.tavily_api_key == "your_tavily_api_key_here":
            print("  ❌ Tavily API Key 未配置")
            return False
        print(f"  ✅ Tavily API Key: {settings.tavily_api_key[:10]}...")
        
        # 显示其他配置
        print(f"  ℹ️  Model: {settings.deepseek_model}")
        print(f"  ℹ️  Timeout: {settings.request_timeout}s")
        print(f"  ℹ️  Max Retries: {settings.max_retries}")
        
        return True
    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        return False


def check_structure():
    """检查项目结构"""
    print("\n📁 检查项目结构...")
    
    required_dirs = ["agents", "prompts", "utils", "runs"]
    required_files = [
        "config.py",
        "schemas.py",
        "controller.py",
        "main.py",
        "agents/__init__.py",
        "agents/base_agent.py",
        "agents/planner.py",
        "agents/retriever.py",
        "agents/evaluator.py",
        "agents/reflection.py",
        "agents/debate.py",
        "agents/synthesis.py",
        "agents/uncertainty.py",
        "utils/logger.py",
        "utils/deepseek_client.py",
        "utils/tavily_client.py",
    ]
    
    base_path = Path(__file__).parent
    all_ok = True
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if dir_path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ - 不存在")
            all_ok = False
    
    for file_name in required_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} - 不存在")
            all_ok = False
    
    return all_ok


def check_imports():
    """检查关键模块导入"""
    print("\n🔧 检查模块导入...")
    
    try:
        import config
        print("  ✅ config")
    except Exception as e:
        print(f"  ❌ config: {e}")
        return False
    
    try:
        import schemas
        print("  ✅ schemas")
    except Exception as e:
        print(f"  ❌ schemas: {e}")
        return False
    
    try:
        import controller
        print("  ✅ controller")
    except Exception as e:
        print(f"  ❌ controller: {e}")
        return False
    
    try:
        from agents import PlannerAgent, RetrieverAgent
        print("  ✅ agents")
    except Exception as e:
        print(f"  ❌ agents: {e}")
        return False
    
    return True


def main():
    print("=" * 60)
    print("MARDS 系统检查")
    print("=" * 60)
    print()
    
    checks = [
        ("依赖包", check_dependencies),
        ("项目结构", check_structure),
        ("模块导入", check_imports),
        ("配置文件", check_config),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ {name} 检查失败: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    print()
    
    if all_passed:
        print("🎉 所有检查通过！系统已就绪。")
        print()
        print("运行示例:")
        print('  python main.py --query "量子计算的最新进展" --debate')
        return 0
    else:
        print("⚠️  部分检查未通过，请根据上述提示修复问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
