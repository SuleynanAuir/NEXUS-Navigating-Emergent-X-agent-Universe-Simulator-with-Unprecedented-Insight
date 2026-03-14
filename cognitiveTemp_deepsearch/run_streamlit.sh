#!/bin/bash

# ============================================================================
# DeepSearch Agent - Streamlit Web 应用启动脚本
# 功能: 启动Streamlit Web界面，支持Research Metrics完整计算
# ============================================================================

set -e  # 遇到错误立即退出

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到项目目录
cd "$SCRIPT_DIR"

echo ""
echo "============================================================================"
echo "🚀 DeepSearch Agent - Streamlit Web 应用"
echo "============================================================================"
echo ""

# Step 0: 运行Metrics系统预检查
echo "🔍 [0/5] 运行Metrics系统预检查..."
if python3 preflight_check.py; then
    echo ""
else
    echo ""
    echo "❌ Metrics系统预检查失败，无法启动应用"
    echo ""
    exit 1
fi
echo ""

# Step 1: 检查Python环境
echo "📋 [1/5] 检查Python环境..."
python3 --version
echo ""

# Step 2: 安装/更新依赖
echo "📦 [2/5] 安装/更新依赖..."
pip install -q \
    streamlit>=1.28.0 \
    openai>=1.0.0 \
    requests>=2.25.0 \
    tavily-python>=0.3.0 \
    pydantic>=2.0.0 \
    rich>=13.0.0

echo "✅ 依赖安装完成"
echo ""

# Step 3: 验证关键文件
echo "🔍 [3/5] 验证关键文件..."
files=(
    "src/agent.py"
    "src/visualization/metrics_model.py"
    "src/visualization/calculator.py"
    "src/visualization/visualizer.py"
    "src/visualization/token_pricing.py"
    "examples/streamlit_app.py"
    "preflight_check.py"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo "❌ 部分关键文件缺失，请检查项目结构"
    exit 1
fi

echo ""
echo "✅ 所有关键文件已验证"
echo ""

# Step 4: 启动Streamlit应用
echo "🌐 [4/5] 启动Streamlit应用..."
echo ""
echo "============================================================================"
echo "✨ Streamlit应用已启动"
echo ""
echo "📍 本地地址: http://localhost:8501"
echo "🔧 编辑 & Rerun 功能已启用"
echo ""
echo "💡 功能说明:"
echo "  1. 选择LLM提供商 (DeepSeek/OpenAI)"
echo "  2. 配置API密钥"
echo "  3. 执行深度研究"
echo "  4. 查看Research Metrics Dashboard (Tab 5)"
echo "  5. 下载HTML和JSON报告"
echo ""
echo "⚙️  快捷键:"
echo "  • C: 清空缓存"
echo "  • R: 重新运行"
echo "  • Q: 退出应用 (按 Ctrl+C)"
echo ""
echo "============================================================================"
echo ""

# 启动Streamlit应用，启用热重载
streamlit run examples/streamlit_app.py \
    --logger.level=info \
    --client.showErrorDetails=true \
    --client.toolbarMode=minimal

echo ""
echo "============================================================================"
echo "👋 Streamlit应用已关闭"
echo "============================================================================"
echo ""
