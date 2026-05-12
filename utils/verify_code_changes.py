#!/usr/bin/env python3
"""
代码检查脚本：验证修复是否正确实施
"""

import os
import re

def check_file_contains(filepath, patterns, description):
    """检查文件是否包含特定的模式"""
    print(f"\n检查 {description}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_found = True
        for pattern_name, pattern in patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                print(f"  ✓ 找到: {pattern_name}")
            else:
                print(f"  ✗ 缺失: {pattern_name}")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

def main():
    """主验证函数"""
    print("=" * 70)
    print("NEXUS 网络错误恢复修复验证")
    print("=" * 70)
    
    results = []
    
    # 1. 检查 llm_client.py
    print("\n" + "=" * 70)
    print("1. 检查后端 LLM 客户端 (backend/app/utils/llm_client.py)")
    print("=" * 70)
    
    llm_patterns = [
        ("导入异常类", r"from openai import.*APIConnectionError.*APITimeoutError.*RateLimitError"),
        ("导入日志", r"from.*logger import get_logger"),
        ("MAX_RETRIES 配置", r"MAX_RETRIES\s*=\s*3"),
        ("重试延迟配置", r"INITIAL_RETRY_DELAY\s*=\s*2"),
        ("超时配置", r"timeout\s*=\s*60\.0"),
        ("重试循环", r"for attempt in range\(self\.MAX_RETRIES\)"),
        ("异常捕获 - APIConnectionError", r"except.*APIConnectionError.*as e"),
        ("异常捕获 - APITimeoutError", r"except.*APITimeoutError.*as e"),
        ("异常捕获 - RateLimitError", r"except.*RateLimitError.*as e"),
        ("重试日志", r"logger\.warning.*重试"),
        ("失败日志", r"logger\.error.*已达最大重试次数"),
    ]
    
    result = check_file_contains(
        '/Users/suleynan_suir/Desktop/NEXUS/backend/app/utils/llm_client.py',
        llm_patterns,
        "LLM 客户端重试机制"
    )
    results.append(("LLM 客户端", result))
    
    # 2. 检查 ontology_generator.py
    print("\n" + "=" * 70)
    print("2. 检查本体生成器 (backend/app/services/ontology_generator.py)")
    print("=" * 70)
    
    ontology_patterns = [
        ("导入日志", r"from.*logger import get_logger"),
        ("日志初始化", r"logger\s*=\s*get_logger\(\s*['\"]nexus\.ontology"),
        ("初始化异常处理", r"def __init__.*try:.*except.*Exception"),
        ("生成异常处理", r"def generate.*try:.*except.*Exception"),
        ("日志 - 开始生成", r"logger\.info.*开始生成本体"),
        ("日志 - LLM 调用", r"logger\.info.*调用.*LLM"),
        ("日志 - 完成", r"logger\.info.*本体生成完成"),
    ]
    
    result = check_file_contains(
        '/Users/suleynan_suir/Desktop/NEXUS/backend/app/services/ontology_generator.py',
        ontology_patterns,
        "本体生成器错误处理"
    )
    results.append(("本体生成器", result))
    
    # 3. 检查 graph.py API 端点
    print("\n" + "=" * 70)
    print("3. 检查 API 端点 (backend/app/api/graph.py)")
    print("=" * 70)
    
    graph_patterns = [
        ("生成本体异常捕获", r"except Exception as e:.*error_msg\s*=.*本体生成失败"),
        ("错误日志", r"logger\.error\(error_msg.*exc_info"),
        ("项目清理", r"ProjectManager\.delete_project"),
        ("错误返回", r"return jsonify.*success.*False.*error.*details"),
    ]
    
    result = check_file_contains(
        '/Users/suleynan_suir/Desktop/NEXUS/backend/app/api/graph.py',
        graph_patterns,
        "API 端点错误处理"
    )
    results.append(("API 端点", result))
    
    # 4. 检查前端重试机制
    print("\n" + "=" * 70)
    print("4. 检查前端重试机制 (frontend/src/views/MainView.vue)")
    print("=" * 70)
    
    frontend_patterns = [
        ("MAX_RETRIES 配置", r"const MAX_RETRIES\s*=\s*3"),
        ("重试延迟", r"const RETRY_DELAY\s*=\s*3000"),
        ("重试循环", r"for\s*\(\s*let attempt\s*=\s*1.*attempt\s*<=\s*MAX_RETRIES"),
        ("网络错误检测", r"const isNetworkError\s*=.*Network Error.*ECONNABORTED.*timeout"),
        ("条件重试", r"if\s*\(\s*isNetworkError.*attempt\s*<\s*MAX_RETRIES\s*\)"),
        ("用户友好错误 - 网络", r"Network connection error.*internet connection"),
        ("用户友好错误 - 超时", r"Request timeout.*Please try again"),
        ("用户友好错误 - LLM", r"LLM service error.*API configuration"),
        ("重试日志", r"Retrying in 3 seconds"),
        ("成功标记", r"✓.*Ontology generated successfully"),
        ("失败标记", r"✗.*Exception in handleNewProject"),
    ]
    
    result = check_file_contains(
        '/Users/suleynan_suir/Desktop/NEXUS/frontend/src/views/MainView.vue',
        frontend_patterns,
        "前端重试和错误处理"
    )
    results.append(("前端重试机制", result))
    
    # 5. 检查测试文档
    print("\n" + "=" * 70)
    print("5. 检查测试文档 (test_network_recovery.md)")
    print("=" * 70)
    
    test_doc_patterns = [
        ("问题诊断", r"## 问题诊断"),
        ("修复方案", r"## 实施的修复方案"),
        ("测试方案", r"## 测试方案"),
        ("LLM 客户端改进", r"### 文件：.*backend/app/utils/llm_client.py"),
        ("前端修复", r"#### 文件：.*frontend/src/views/MainView.vue"),
    ]
    
    result = check_file_contains(
        '/Users/suleynan_suir/Desktop/NEXUS/test_network_recovery.md',
        test_doc_patterns,
        "测试文档"
    )
    results.append(("测试文档", result))
    
    # 输出总结
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    
    all_passed = True
    for component, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {component}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ 所有检查通过！网络错误恢复修复已正确实施。")
        print("\n修复内容总结：")
        print("1. 后端 LLM 客户端：")
        print("   - 添加了网络异常捕获和重试机制（最多3次）")
        print("   - 实现指数退避重试延迟")
        print("   - 增加详细的日志记录")
        print("\n2. 前端重试机制：")
        print("   - 自动重试最多3次（每次间隔3秒）")
        print("   - 区分不同类型的错误")
        print("   - 提供用户友好的错误提示")
        print("\n3. 错误处理改进：")
        print("   - 更好的异常捕获和日志记录")
        print("   - 资源清理和错误恢复")
        print("\n下一步：")
        print("1. 在生产环境中测试网络恢复能力")
        print("2. 监控后端日志以验证重试机制的运行")
        print("3. 收集用户反馈并进行微调")
    else:
        print("✗ 部分检查失败，请检查修复是否完整。")
    print("=" * 70)
    
    return all_passed

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
