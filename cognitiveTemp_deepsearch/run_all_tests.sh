#!/bin/bash

# ============================================================================
# DeepSearch Agent - Research Metrics 完整运行指南
# ============================================================================

set -e  # 遇到错误立即退出

PROJECT_DIR="/Users/suleynan_suir/Desktop/AIGC/project/option1-舆情分析/DeepSearch/DeepSearchAgent"

echo ""
echo "============================================================================"
echo "🚀 DeepSearch Agent - Research Metrics 完整集成测试"
echo "============================================================================"
echo ""

cd "$PROJECT_DIR"

# Step 1: 检查依赖
echo "📦 [Step 1/7] 检查并安装依赖..."
pip install -q openai requests tavily-python streamlit pydantic rich
echo "✅ 依赖安装完成"
echo ""

# Step 2: 语法检查
echo "🔍 [Step 2/7] 执行语法检查..."
echo "  • src/agent.py"
python3 -m py_compile src/agent.py

echo "  • src/llms/deepseek.py"
python3 -m py_compile src/llms/deepseek.py

echo "  • src/llms/openai_llm.py"
python3 -m py_compile src/llms/openai_llm.py

echo "  • src/visualization/*.py"
python3 -m py_compile src/visualization/metrics_model.py
python3 -m py_compile src/visualization/calculator.py
python3 -m py_compile src/visualization/visualizer.py
python3 -m py_compile src/visualization/token_pricing.py

echo "  • examples/streamlit_app.py"
python3 -m py_compile examples/streamlit_app.py

echo "✅ 所有文件语法检查通过"
echo ""

# Step 3: 运行单元测试
echo "🧪 [Step 3/7] 运行单元测试..."
python3 test_metrics.py
echo "✅ 单元测试通过"
echo ""

# Step 4: 运行快速开始示例
echo "🎯 [Step 4/7] 运行快速开始示例..."
python3 quick_start.py > /dev/null 2>&1
if [ -f "metrics_dashboard.html" ] && [ -f "metrics.json" ]; then
    echo "✅ 快速开始示例完成"
    echo "   生成的文件:"
    echo "   • metrics_dashboard.html"
    echo "   • metrics.json"
else
    echo "❌ 快速开始示例失败"
    exit 1
fi
echo ""

# Step 5: 运行完整工作流测试
echo "📊 [Step 5/7] 运行完整工作流测试..."
python3 test_complete_workflow.py > /dev/null 2>&1
if [ -f "metrics_complete_test.html" ] && [ -f "metrics_complete_test.json" ]; then
    echo "✅ 完整工作流测试通过"
    echo "   生成的文件:"
    echo "   • metrics_complete_test.html"
    echo "   • metrics_complete_test.json"
else
    echo "❌ 完整工作流测试失败"
    exit 1
fi
echo ""

# Step 6: 生成文件清单
echo "📋 [Step 6/7] 生成项目文件清单..."
echo ""
echo "核心模块文件:"
ls -lh src/visualization/*.py | awk '{print "  • " $9 " (" $5 ")"}'
echo ""
echo "测试文件:"
ls -lh test_*.py quick_start.py 2>/dev/null | awk '{print "  • " $9 " (" $5 ")"}'
echo ""
echo "文档文件:"
ls -lh *.md 2>/dev/null | grep -E "METRICS|README" | awk '{print "  • " $9 " (" $5 ")"}'
echo ""
echo "生成的输出文件:"
ls -lh *.html *.json 2>/dev/null | awk '{print "  • " $9 " (" $5 ")"}'
echo ""

# Step 7: 总结
echo "✅ [Step 7/7] 验证完成"
echo ""
echo "============================================================================"
echo "✨ 所有测试通过！Metrics系统已就绪"
echo "============================================================================"
echo ""
echo "📚 快速参考:"
echo ""
echo "1️⃣  查看metrics数据结构:"
echo "   cat metrics_complete_test.json | head -30"
echo ""
echo "2️⃣  查看HTML可视化:"
echo "   open metrics_complete_test.html"
echo ""
echo "3️⃣  运行完整测试:"
echo "   python3 test_complete_workflow.py"
echo ""
echo "4️⃣  查看快速开始示例:"
echo "   python3 quick_start.py"
echo ""
echo "5️⃣  查看集成文档:"
echo "   cat METRICS_INTEGRATION.md | head -50"
echo ""
echo "6️⃣  启动Streamlit应用 (需配置API密钥):"
echo "   streamlit run examples/streamlit_app.py"
echo ""
echo "📊 Key Metrics Summary:"
echo "============================================================================"

# 从JSON提取摘要信息
if [ -f "metrics_complete_test.json" ]; then
    echo ""
    python3 << 'EOF'
import json

with open("metrics_complete_test.json", "r") as f:
    data = json.load(f)

print(f"查询: {data['query']}")
print(f"章节: {data['total_sections']} | 来源: {data['total_sources']} | 反思: {data['total_reflections']}")
print(f"")
print(f"⏱️  时间消耗:")
print(f"   结构: {data['time_metrics']['structure_generation_time']:.1f}s")
print(f"   搜索: {data['time_metrics']['search_time']:.1f}s")
print(f"   反思: {data['time_metrics']['reflection_time']:.1f}s")
print(f"   报告: {data['time_metrics']['report_generation_time']:.1f}s")
print(f"")
print(f"💰 Token & 成本:")
print(f"   总Token: {data['token_metrics']['total_tokens']:,}")
print(f"   USD成本: ${data['token_metrics']['total_cost_usd']:.4f}")
print(f"   CNY成本: ¥{data['token_metrics']['total_cost_rmb']:.2f}")
print(f"")
print(f"🎯 搜索质量:")
print(f"   NDCG: {data['search_quality']['ndcg']:.4f}")
print(f"   MRR: {data['search_quality']['mrr']:.4f}")
print(f"   MAP: {data['search_quality']['map_score']:.4f}")
print(f"   P@1-10: {data['search_quality']['precision_at_1']:.2f} → {data['search_quality']['precision_at_10']:.2f}")
print(f"")
print(f"⭐ 综合评分: {data['overall_score']:.2f}/100")
EOF
    echo ""
fi

echo "============================================================================"
echo ""
echo "🎉 集成完成！您现在可以:"
echo ""
echo "  ✅ 在实际研究中使用 Research Metrics Dashboard"
echo "  ✅ 通过 Streamlit Web界面查看实时指标"
echo "  ✅ 导出JSON和HTML格式的metrics报告"
echo "  ✅ 对比不同研究的性能指标"
echo ""
echo "更多信息请查看 METRICS_INTEGRATION.md"
echo ""
