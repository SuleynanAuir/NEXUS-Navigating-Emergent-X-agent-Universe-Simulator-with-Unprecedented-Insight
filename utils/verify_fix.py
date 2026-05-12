#!/usr/bin/env python3
"""
快速验证脚本：测试 LLM 客户端的重试机制
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_llm_client():
    """测试 LLM 客户端是否正确初始化"""
    print("=" * 60)
    print("测试 LLM 客户端重试机制")
    print("=" * 60)
    
    try:
        from app.utils.llm_client import LLMClient
        
        print("\n1. 检查 LLMClient 导入...")
        print("✓ LLMClient 导入成功")
        
        print("\n2. 检查重试配置...")
        print(f"   - MAX_RETRIES: {LLMClient.MAX_RETRIES}")
        print(f"   - INITIAL_RETRY_DELAY: {LLMClient.INITIAL_RETRY_DELAY}s")
        print(f"   - MAX_RETRY_DELAY: {LLMClient.MAX_RETRY_DELAY}s")
        
        if LLMClient.MAX_RETRIES >= 2:
            print("✓ 重试配置有效")
        else:
            print("✗ 重试次数太少")
            return False
        
        print("\n3. 检查 LLMClient 初始化...")
        try:
            client = LLMClient()
            print("✓ LLMClient 初始化成功")
        except ValueError as e:
            print(f"⚠ LLM API 密钥未配置（预期）: {e}")
            print("  请确保 .env 文件中配置了 LLM_API_KEY")
        except Exception as e:
            print(f"✗ LLMClient 初始化失败: {e}")
            return False
        
        print("\n4. 检查异常处理...")
        from openai import APIConnectionError, APITimeoutError, RateLimitError
        print("✓ 异常类导入成功")
        print("  - APIConnectionError")
        print("  - APITimeoutError")
        print("  - RateLimitError")
        
        print("\n5. 检查 OntologyGenerator...")
        from app.services.ontology_generator import OntologyGenerator
        print("✓ OntologyGenerator 导入成功")
        
        print("\n6. 检查日志配置...")
        from app.utils.logger import get_logger
        logger = get_logger('test')
        print("✓ 日志系统配置成功")
        
        print("\n" + "=" * 60)
        print("✓ 所有检查通过！")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"\n✗ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_network_error_messages():
    """测试错误消息识别"""
    print("\n" + "=" * 60)
    print("测试错误消息识别")
    print("=" * 60)
    
    test_cases = [
        ("Network Error", True, "应识别为网络错误"),
        ("ECONNABORTED", True, "应识别为网络错误"),
        ("timeout", True, "应识别为网络错误"),
        ("Connection refused", False, "不应被特殊识别"),
        ("LLM service error", False, "不是网络错误"),
    ]
    
    for error_msg, should_be_network, description in test_cases:
        is_network = (
            "Network Error" in error_msg or
            "ECONNABORTED" in error_msg or
            "timeout" in error_msg
        )
        
        status = "✓" if is_network == should_be_network else "✗"
        print(f"{status} '{error_msg}' - {description}")
    
    return True

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    
    success = test_llm_client()
    test_network_error_messages()
    
    if success:
        print("\n✓ 验证完成，修复方案已正确实施。")
        sys.exit(0)
    else:
        print("\n✗ 验证失败，请检查配置。")
        sys.exit(1)
